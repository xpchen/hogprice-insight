"""维度数据接口 - 查询 hogprice_v3 维度表"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser

router = APIRouter(prefix=f"{settings.API_V1_STR}/dim", tags=["metadata"])


# ── 指标目录（Python dict 维护） ──
METRIC_CATALOG = [
    # 日度价格
    {"metric_group": "price", "metric_name": "全国标猪均价", "code": "标猪均价", "unit": "元/公斤", "freq": "D"},
    {"metric_group": "price", "metric_name": "散户标猪价", "code": "散户标猪价", "unit": "元/公斤", "freq": "D"},
    {"metric_group": "price", "metric_name": "省份均价", "code": "省份均价", "unit": "元/公斤", "freq": "D"},
    {"metric_group": "price", "metric_name": "钢联猪价", "code": "hog_price", "unit": "元/公斤", "freq": "D"},
    {"metric_group": "price", "metric_name": "白条价格", "code": "white_strip_price", "unit": "元/公斤", "freq": "D"},
    # 日度价差
    {"metric_group": "spread", "metric_name": "标肥价差", "code": "std_fat_spread", "unit": "元/公斤", "freq": "D"},
    {"metric_group": "spread", "metric_name": "毛白价差", "code": "mao_bai_spread", "unit": "元/公斤", "freq": "D"},
    {"metric_group": "spread", "metric_name": "区域价差", "code": "region_spread", "unit": "元/公斤", "freq": "D"},
    # 日度屠宰
    {"metric_group": "slaughter", "metric_name": "屠宰量", "code": "slaughter_volume", "unit": "头", "freq": "D"},
    # 周度指标
    {"metric_group": "weekly", "metric_name": "商品猪出栏价", "code": "hog_price_out", "unit": "元/公斤", "freq": "W"},
    {"metric_group": "weekly", "metric_name": "出栏均重", "code": "weight_avg", "unit": "公斤", "freq": "W"},
    {"metric_group": "weekly", "metric_name": "冻品库容率", "code": "frozen_rate", "unit": "%", "freq": "W"},
    {"metric_group": "weekly", "metric_name": "仔猪价格", "code": "piglet_price_15kg", "unit": "元/公斤", "freq": "W"},
    {"metric_group": "weekly", "metric_name": "母猪价格", "code": "sow_price_50kg", "unit": "元/头", "freq": "W"},
    {"metric_group": "weekly", "metric_name": "养殖利润(万头)", "code": "profit_breeding_10000", "unit": "元/头", "freq": "W"},
    {"metric_group": "weekly", "metric_name": "全价料价格", "code": "feed_price_complete", "unit": "元/吨", "freq": "W"},
    {"metric_group": "weekly", "metric_name": "鲜销率", "code": "fresh_sale_rate", "unit": "%", "freq": "W"},
    # 月度指标
    {"metric_group": "monthly", "metric_name": "能繁母猪存栏", "code": "breeding_sow_inventory", "unit": "头", "freq": "M"},
    {"metric_group": "monthly", "metric_name": "仔猪存栏", "code": "piglet_inventory", "unit": "头", "freq": "M"},
    {"metric_group": "monthly", "metric_name": "大猪存栏", "code": "hog_inventory", "unit": "头", "freq": "M"},
    {"metric_group": "monthly", "metric_name": "商品猪出栏量", "code": "hog_output_volume", "unit": "头", "freq": "M"},
    {"metric_group": "monthly", "metric_name": "淘汰母猪屠宰", "code": "cull_slaughter", "unit": "头", "freq": "M"},
    {"metric_group": "monthly", "metric_name": "PSY", "code": "prod_psy", "unit": "头", "freq": "M"},
    {"metric_group": "monthly", "metric_name": "MSY", "code": "prod_msy", "unit": "头", "freq": "M"},
    # 季度指标
    {"metric_group": "quarterly", "metric_name": "统计局生猪存栏", "code": "nbs_hog_inventory", "unit": "万头", "freq": "Q"},
    {"metric_group": "quarterly", "metric_name": "统计局能繁存栏", "code": "nbs_sow_inventory", "unit": "万头", "freq": "Q"},
    {"metric_group": "quarterly", "metric_name": "统计局生猪出栏", "code": "nbs_hog_output", "unit": "万头", "freq": "Q"},
    {"metric_group": "quarterly", "metric_name": "统计局猪肉产量", "code": "nbs_pork_output", "unit": "万吨", "freq": "Q"},
    # 期货
    {"metric_group": "futures", "metric_name": "期货收盘价", "code": "futures_close", "unit": "元/吨", "freq": "D"},
    {"metric_group": "futures", "metric_name": "期货结算价", "code": "futures_settle", "unit": "元/吨", "freq": "D"},
]


class MetricInfo(BaseModel):
    id: int
    metric_group: str
    metric_name: str
    unit: Optional[str]
    freq: str
    raw_header: str


class GeoInfo(BaseModel):
    id: int
    province: str
    region: Optional[str]


class CompanyInfo(BaseModel):
    id: int
    company_name: str
    province: Optional[str]


@router.get("/metrics", response_model=List[MetricInfo])
async def get_metrics(
    group: Optional[str] = Query(None, description="指标组筛选"),
    freq: Optional[str] = Query(None, description="频率筛选"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取指标列表"""
    results = []
    groups = [g.strip() for g in group.split(",")] if group else None
    for i, m in enumerate(METRIC_CATALOG, 1):
        if groups and m["metric_group"] not in groups:
            continue
        if freq and m["freq"] != freq:
            continue
        results.append({
            "id": i,
            "metric_group": m["metric_group"],
            "metric_name": m["metric_name"],
            "unit": m.get("unit"),
            "freq": m["freq"],
            "raw_header": m.get("code", "")
        })
    return results


@router.get("/geo", response_model=List[GeoInfo])
async def get_geo(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取地区列表"""
    rows = db.execute(text(
        "SELECT region_code, region_name, parent_code FROM dim_region WHERE region_level = 2 ORDER BY region_code"
    )).fetchall()
    return [{"id": i, "province": r[1], "region": r[2]} for i, r in enumerate(rows, 1)]


@router.get("/company", response_model=List[CompanyInfo])
async def get_company(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取企业列表"""
    rows = db.execute(text(
        "SELECT company_code, company_name, short_name FROM dim_company ORDER BY company_code"
    )).fetchall()
    return [{"id": i, "company_name": r[1], "province": r[2]} for i, r in enumerate(rows, 1)]


@router.get("/warehouse")
async def get_warehouse(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取交割库列表（从期货基差数据中提取）"""
    rows = db.execute(text(
        "SELECT DISTINCT indicator_code FROM fact_futures_basis WHERE indicator_code LIKE 'warehouse_%' ORDER BY indicator_code"
    )).fetchall()
    return [{"id": i, "warehouse_name": r[0].replace("warehouse_", ""), "province": None}
            for i, r in enumerate(rows, 1)]


@router.get("/metrics/completeness")
async def get_metrics_completeness_api(
    as_of: Optional[str] = Query(None, description="基准日期 YYYY-MM-DD"),
    window: int = Query(7, description="窗口天数"),
    metric_group: Optional[str] = Query(None, description="指标组过滤"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取各表数据完整度"""
    from datetime import datetime, timedelta

    as_of_date = datetime.strptime(as_of, "%Y-%m-%d").date() if as_of else datetime.now().date()
    start = as_of_date - timedelta(days=window)

    tables = [
        ("fact_price_daily", "trade_date"),
        ("fact_spread_daily", "trade_date"),
        ("fact_slaughter_daily", "trade_date"),
        ("fact_weekly_indicator", "week_end"),
        ("fact_monthly_indicator", "month_date"),
        ("fact_enterprise_daily", "trade_date"),
    ]

    results = []
    for tbl, dcol in tables:
        row = db.execute(text(
            f"SELECT COUNT(*), MAX(`{dcol}`) FROM `{tbl}` WHERE `{dcol}` BETWEEN :s AND :e"
        ), {"s": start, "e": as_of_date}).fetchone()
        results.append({
            "table": tbl,
            "count_in_window": row[0],
            "latest_date": row[1].isoformat() if row[1] else None,
            "window_start": start.isoformat(),
            "window_end": as_of_date.isoformat()
        })
    return {"completeness": results}
