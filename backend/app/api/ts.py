"""统一时序接口 - 查询 hogprice_v3 各 fact 表"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser

router = APIRouter(prefix=f"{settings.API_V1_STR}/ts", tags=["timeseries"])


# 指标 → (表名, 日期列, 过滤列, 过滤值, 默认source) 路由
INDICATOR_ROUTING = {
    # 日度价格
    "hog_price_nation": ("fact_price_daily", "trade_date", "price_type", "标猪均价", "YONGYI"),
    "hog_price_ganglian": ("fact_price_daily", "trade_date", "price_type", "hog_price", "GANGLIAN"),
    # 日度价差
    "spread_std_fat": ("fact_spread_daily", "trade_date", "spread_type", "fat_std_spread", "GANGLIAN"),
    "spread_mao_bai": ("fact_spread_daily", "trade_date", "spread_type", "mao_bai_spread", "YONGYI"),
    # 日度屠宰
    "slaughter_daily": ("fact_slaughter_daily", "trade_date", None, None, "YONGYI"),
}

# 周度指标直接映射到 fact_weekly_indicator.indicator_code
WEEKLY_INDICATORS = {
    "hog_price_out", "weight_avg", "weight_pct_under90", "weight_pct_over150",
    "weight_slaughter", "frozen_rate", "frozen_inventory_multi",
    "piglet_price_15kg", "sow_price_50kg", "cull_sow_price",
    "carcass_price", "pork_carcass_price", "fresh_sale_rate",
    "slaughter_volume_daily", "mao_bai_spread",
    "profit_breeding_500", "profit_breeding_3000", "profit_breeding_10000",
    "profit_breeding_50000", "profit_breeding_group", "profit_breeding_free_range",
    "profit_piglet_purchase", "profit_contract_farming",
    "feed_price_complete",
    "std_pig_price_wavg", "frozen_no2_price_wavg", "frozen_no4_price_wavg",
    "carcass_top3_price_wavg",
}

# 月度指标直接映射到 fact_monthly_indicator.indicator_code
MONTHLY_INDICATORS = {
    "breeding_sow_inventory", "piglet_inventory", "hog_inventory",
    "breeding_sow_inventory_old", "piglet_inventory_old", "hog_output_volume",
    "cull_slaughter", "slaughter_utilization", "male_ratio",
    "feed_sales_total", "feed_sales_mom",
    "prod_psy", "prod_msy", "prod_npd", "prod_litter_size", "prod_survival_rate",
    "nyb_breeding_sow", "nyb_total_sow",
    "assoc_breeding_sow", "assoc_sow_total",
    "yz_breeding_sow", "gl_breeding_sow",
}


class TimeSeriesResponse(BaseModel):
    indicator_code: str
    indicator_name: str
    unit: Optional[str]
    series: List[dict]
    update_time: Optional[str]
    metrics: Optional[dict] = None


@router.get("", response_model=TimeSeriesResponse)
async def get_timeseries(
    indicator_code: str = Query(..., description="指标代码"),
    region_code: Optional[str] = Query(None, description="区域代码"),
    freq: str = Query("D", description="频率（D/W/M）"),
    from_date: Optional[date] = Query(None, description="开始日期"),
    to_date: Optional[date] = Query(None, description="结束日期"),
    include_metrics: bool = Query(False, description="是否包含预计算metrics"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """统一时序查询接口"""
    region = region_code or "NATION"
    series = []
    unit = None

    # 1. 尝试路由表匹配
    if indicator_code in INDICATOR_ROUTING:
        table, date_col, filter_col, filter_val, default_source = INDICATOR_ROUTING[indicator_code]
        # fact_slaughter_daily 没有 indicator_code/value/unit 列
        if table == "fact_slaughter_daily":
            val_col = "volume"
            unit_expr = "'头' as unit"
        else:
            val_col = "value"
            unit_expr = "unit"
        sql = f"SELECT `{date_col}`, {val_col}, {unit_expr} FROM `{table}` WHERE region_code = :region"
        params = {"region": region}
        if filter_col and filter_val:
            sql += f" AND `{filter_col}` = :fval"
            params["fval"] = filter_val
        if from_date:
            sql += f" AND `{date_col}` >= :from_d"
            params["from_d"] = from_date
        if to_date:
            sql += f" AND `{date_col}` <= :to_d"
            params["to_d"] = to_date
        sql += f" AND source = :src ORDER BY `{date_col}`"
        params["src"] = default_source
        rows = db.execute(text(sql), params).fetchall()
        series = [{"date": r[0].isoformat(), "value": float(r[1])} for r in rows if r[1] is not None]
        if rows:
            unit = rows[0][2]

    # 2. 周度指标
    elif indicator_code in WEEKLY_INDICATORS or freq == "W":
        sql = "SELECT week_end, value, unit FROM fact_weekly_indicator WHERE indicator_code = :code AND region_code = :region"
        params = {"code": indicator_code, "region": region}
        if from_date:
            sql += " AND week_end >= :from_d"
            params["from_d"] = from_date
        if to_date:
            sql += " AND week_end <= :to_d"
            params["to_d"] = to_date
        sql += " ORDER BY week_end"
        rows = db.execute(text(sql), params).fetchall()
        series = [{"date": r[0].isoformat(), "value": float(r[1])} for r in rows if r[1] is not None]
        if rows:
            unit = rows[0][2]

    # 3. 月度指标
    elif indicator_code in MONTHLY_INDICATORS or freq == "M":
        sql = "SELECT month_date, value, unit FROM fact_monthly_indicator WHERE indicator_code = :code AND region_code = :region AND value_type = 'abs'"
        params = {"code": indicator_code, "region": region}
        if from_date:
            sql += " AND month_date >= :from_d"
            params["from_d"] = from_date
        if to_date:
            sql += " AND month_date <= :to_d"
            params["to_d"] = to_date
        sql += " ORDER BY month_date"
        rows = db.execute(text(sql), params).fetchall()
        series = [{"date": r[0].isoformat(), "value": float(r[1])} for r in rows if r[1] is not None]
        if rows:
            unit = rows[0][2]

    # 4. 尝试在所有表中搜索
    else:
        for tbl, dcol in [("fact_weekly_indicator", "week_end"), ("fact_monthly_indicator", "month_date")]:
            sql = f"SELECT `{dcol}`, value, unit FROM `{tbl}` WHERE indicator_code = :code AND region_code = :region"
            params = {"code": indicator_code, "region": region}
            if from_date:
                sql += f" AND `{dcol}` >= :from_d"
                params["from_d"] = from_date
            if to_date:
                sql += f" AND `{dcol}` <= :to_d"
                params["to_d"] = to_date
            sql += f" ORDER BY `{dcol}`"
            rows = db.execute(text(sql), params).fetchall()
            if rows:
                series = [{"date": r[0].isoformat(), "value": float(r[1])} for r in rows if r[1] is not None]
                unit = rows[0][2]
                break

    update_time = series[-1]["date"] if series else None

    return TimeSeriesResponse(
        indicator_code=indicator_code,
        indicator_name=indicator_code,
        unit=unit,
        series=series,
        update_time=update_time,
        metrics=None
    )
