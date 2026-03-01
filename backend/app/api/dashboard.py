"""默认首页聚合接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from datetime import date, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser

router = APIRouter(prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])


class CardData(BaseModel):
    card_id: str
    title: str
    chart_type: str
    data: dict
    update_time: str
    config: dict = {}


class DashboardResponse(BaseModel):
    cards: List[CardData]
    global_filters: dict


def _query_daily_series(db: Session, table: str, filter_col: str, filter_val: str,
                        region: str = "NATION", start: date = None, end: date = None,
                        source: str = None) -> dict:
    """通用日度时序查询"""
    # fact_slaughter_daily 没有 indicator_code/value 列，用 volume
    if table == "fact_slaughter_daily":
        val_col = "volume"
    else:
        val_col = "value"

    sql = f"SELECT trade_date, {val_col} FROM {table} WHERE region_code = :region"
    params = {"region": region}
    if filter_col and filter_val:
        sql += f" AND `{filter_col}` = :fval"
        params["fval"] = filter_val
    if start:
        sql += " AND trade_date >= :start"
        params["start"] = start
    if end:
        sql += " AND trade_date <= :end"
        params["end"] = end
    if source:
        sql += " AND source = :source"
        params["source"] = source
    sql += " ORDER BY trade_date"
    rows = db.execute(text(sql), params).fetchall()
    series = [{"date": r[0].isoformat(), "value": float(r[1])} for r in rows if r[1] is not None]
    update_time = series[-1]["date"] if series else ""
    return {"series": series, "update_time": update_time}


def _query_weekly_series(db: Session, indicator_code: str, region: str = "NATION",
                         start: date = None, end: date = None, source: str = None) -> dict:
    """通用周度时序查询"""
    sql = """
        SELECT week_end, value FROM fact_weekly_indicator
        WHERE region_code = :region AND indicator_code = :code
    """
    params = {"region": region, "code": indicator_code}
    if start:
        sql += " AND week_end >= :start"
        params["start"] = start
    if end:
        sql += " AND week_end <= :end"
        params["end"] = end
    if source:
        sql += " AND source = :source"
        params["source"] = source
    sql += " ORDER BY week_end"
    rows = db.execute(text(sql), params).fetchall()
    series = [{"date": r[0].isoformat(), "value": float(r[1])} for r in rows if r[1] is not None]
    update_time = series[-1]["date"] if series else ""
    return {"series": series, "update_time": update_time}


@router.get("/default", response_model=DashboardResponse)
async def get_default_dashboard(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """返回首页7个卡片数据"""
    end_date = date.today()
    start_date = end_date - timedelta(days=180)

    cards = []

    # 卡片1：全国出栏均价 + 标肥价差
    try:
        price = _query_daily_series(db, "fact_price_daily", "price_type", "标猪均价",
                                    start=start_date, end=end_date, source="YONGYI")
        spread = _query_daily_series(db, "fact_spread_daily", "spread_type", "std_fat_spread",
                                     start=start_date, end=end_date, source="YONGYI")
        cards.append(CardData(
            card_id="card_1_price_spread", title="全国出栏均价 + 标肥价差",
            chart_type="dual_axis",
            data={
                "series1": {"name": "全国出栏均价", "data": price["series"], "unit": "元/公斤"},
                "series2": {"name": "标肥价差", "data": spread["series"], "unit": "元/公斤"}
            },
            update_time=price["update_time"],
            config={"axis1": "left", "axis2": "right"}
        ))
    except Exception as e:
        cards.append(CardData(card_id="card_1_price_spread", title="全国出栏均价 + 标肥价差",
                              chart_type="dual_axis", data={"error": str(e)}, update_time=""))

    # 卡片2：日度屠宰量季节性
    try:
        slaughter = _query_daily_series(db, "fact_slaughter_daily", None, None,
                                        start=start_date - timedelta(days=365), end=end_date, source="YONGYI")
        cards.append(CardData(
            card_id="card_2_slaughter_seasonality", title="日度屠宰量季节性",
            chart_type="seasonality",
            data={"series": slaughter["series"], "unit": "头"},
            update_time=slaughter["update_time"],
            config={"lunar_alignment": True, "years": [end_date.year - 1, end_date.year]}
        ))
    except Exception as e:
        cards.append(CardData(card_id="card_2_slaughter_seasonality", title="日度屠宰量季节性",
                              chart_type="seasonality", data={"error": str(e)}, update_time=""))

    # 卡片3：价格&屠宰走势
    try:
        price_trend = _query_daily_series(db, "fact_price_daily", "price_type", "标猪均价",
                                          start=start_date, end=end_date, source="YONGYI")
        slaughter_trend = _query_daily_series(db, "fact_slaughter_daily", None, None,
                                              start=start_date, end=end_date, source="YONGYI")
        cards.append(CardData(
            card_id="card_3_price_slaughter_trend", title="价格&屠宰走势",
            chart_type="line",
            data={"series": [
                {"name": "价格", "data": price_trend["series"], "unit": "元/公斤"},
                {"name": "屠宰量", "data": slaughter_trend["series"], "unit": "头"}
            ]},
            update_time=price_trend["update_time"],
            config={"year_filter": True}
        ))
    except Exception as e:
        cards.append(CardData(card_id="card_3_price_slaughter_trend", title="价格&屠宰走势",
                              chart_type="line", data={"error": str(e)}, update_time=""))

    # 卡片4：均重专区入口
    cards.append(CardData(
        card_id="card_4_weight_entrance", title="均重专区", chart_type="entrance",
        data={"indicators": [
            {"code": "weight_avg", "name": "出栏均重"},
            {"code": "weight_slaughter", "name": "宰前均重"},
            {"code": "weight_pct_under90", "name": "90kg以下占比"},
            {"code": "weight_pct_over150", "name": "150kg以上占比"}
        ]},
        update_time=""
    ))

    # 卡片5：价差专区入口
    cards.append(CardData(
        card_id="card_5_spread_entrance", title="价差专区", chart_type="entrance",
        data={"indicators": [
            {"code": "std_fat_spread", "name": "标肥价差"},
            {"code": "region_spread", "name": "区域价差"},
            {"code": "mao_bai_spread", "name": "毛白价差"}
        ]},
        update_time=""
    ))

    # 卡片6：冻品库容率
    try:
        frozen = _query_weekly_series(db, "frozen_rate", start=start_date - timedelta(days=365),
                                      end=end_date, source="YONGYI")
        cards.append(CardData(
            card_id="card_6_frozen_capacity", title="冻品库容率", chart_type="seasonality",
            data={"series": frozen["series"], "unit": "%"},
            update_time=frozen["update_time"],
            config={"region_filter": True, "by_province": True}
        ))
    except Exception as e:
        cards.append(CardData(card_id="card_6_frozen_capacity", title="冻品库容率",
                              chart_type="seasonality", data={"error": str(e)}, update_time=""))

    # 卡片7：产业链周度汇总
    try:
        profit = _query_weekly_series(db, "profit_breeding_10000", start=start_date,
                                      end=end_date, source="YONGYI")
        feed = _query_weekly_series(db, "feed_price_complete", start=start_date,
                                    end=end_date, source="YONGYI")
        cards.append(CardData(
            card_id="card_7_industry_chain", title="产业链周度汇总", chart_type="line",
            data={"series": [
                {"name": "养殖利润", "data": profit["series"], "unit": "元/头"},
                {"name": "全价料价格", "data": feed["series"], "unit": "元/吨"}
            ]},
            update_time=profit["update_time"]
        ))
    except Exception as e:
        cards.append(CardData(card_id="card_7_industry_chain", title="产业链周度汇总",
                              chart_type="line", data={"error": str(e)}, update_time=""))

    return DashboardResponse(
        cards=cards,
        global_filters={
            "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "regions": ["NATION"],
            "years": [end_date.year - 1, end_date.year]
        }
    )
