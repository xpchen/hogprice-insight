"""
企业集团统计API (hogprice_v3)
查询 fact_enterprise_daily + dim_company
提供D1页面的4个图表数据接口
"""
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sys_user import SysUser

router = APIRouter(prefix="/api/v1/enterprise-statistics", tags=["enterprise-statistics"])


class TimeSeriesDataPoint(BaseModel):
    date: str
    value: Optional[float]


class TimeSeriesSeries(BaseModel):
    name: str
    data: List[TimeSeriesDataPoint]
    unit: Optional[str] = None


class EnterpriseStatisticsResponse(BaseModel):
    chart_title: str
    series: List[TimeSeriesSeries]
    data_source: str
    update_time: Optional[str]
    latest_date: Optional[str]


def _compute_start_date(months: int) -> Optional[date]:
    if months <= 0:
        return None
    return date.today() - timedelta(days=months * 30)


def _format_update_date(d: Optional[date]) -> Optional[str]:
    if not d:
        return None
    return f"{d.year}年{d.month:02d}月{d.day:02d}日"


def _query_aggregate(db: Session, company_code: str, metric_type: str,
                     region_code: str = "NATION", start: Optional[date] = None) -> List[dict]:
    sql = """SELECT trade_date, value, unit FROM fact_enterprise_daily
             WHERE metric_type = :mt AND company_code = :cc AND region_code = :rc AND value IS NOT NULL"""
    params: dict = {"mt": metric_type, "cc": company_code, "rc": region_code}
    if start:
        sql += " AND trade_date >= :s"
        params["s"] = start
    sql += " ORDER BY trade_date"
    return [{"trade_date": r[0], "value": float(r[1]) if r[1] else None, "unit": r[2]}
            for r in db.execute(text(sql), params).fetchall()]


def _query_region_sum(db: Session, region_code: str, metric_type: str,
                      start: Optional[date] = None) -> List[dict]:
    sql = """SELECT trade_date, SUM(value) AS v, MAX(unit) AS u FROM fact_enterprise_daily
             WHERE metric_type = :mt AND region_code = :rc AND value IS NOT NULL"""
    params: dict = {"mt": metric_type, "rc": region_code}
    if start:
        sql += " AND trade_date >= :s"
        params["s"] = start
    sql += " GROUP BY trade_date ORDER BY trade_date"
    return [{"trade_date": r[0], "value": float(r[1]) if r[1] else None, "unit": r[2]}
            for r in db.execute(text(sql), params).fetchall()]


def _query_region_avg(db: Session, region_code: str, metric_type: str,
                      start: Optional[date] = None) -> List[dict]:
    sql = """SELECT trade_date, AVG(value) AS v, MAX(unit) AS u FROM fact_enterprise_daily
             WHERE metric_type = :mt AND region_code = :rc AND value IS NOT NULL"""
    params: dict = {"mt": metric_type, "rc": region_code}
    if start:
        sql += " AND trade_date >= :s"
        params["s"] = start
    sql += " GROUP BY trade_date ORDER BY trade_date"
    return [{"trade_date": r[0], "value": round(float(r[1]), 4) if r[1] else None, "unit": r[2]}
            for r in db.execute(text(sql), params).fetchall()]


def _to_series(rows: List[dict], name: str, unit: str = None) -> TimeSeriesSeries:
    pts = [TimeSeriesDataPoint(date=r["trade_date"].isoformat(), value=r["value"]) for r in rows]
    return TimeSeriesSeries(name=name, data=pts, unit=unit or (rows[0].get("unit") if rows else None))


def _latest(rows: List[dict]) -> Optional[date]:
    return rows[-1]["trade_date"] if rows else None


def _max_date(*dates: Optional[date]) -> Optional[date]:
    valid = [d for d in dates if d]
    return max(valid) if valid else None


def _build_response(title: str, output_rows, price_rows) -> EnterpriseStatisticsResponse:
    series = []
    ld = None
    if output_rows:
        series.append(_to_series(output_rows, "日度出栏", "头"))
        ld = _max_date(ld, _latest(output_rows))
    if price_rows:
        series.append(_to_series(price_rows, "价格", "元/公斤"))
        ld = _max_date(ld, _latest(price_rows))
    if not series:
        return EnterpriseStatisticsResponse(
            chart_title=title, series=[], data_source="企业集团出栏跟踪",
            update_time=None, latest_date=None)
    return EnterpriseStatisticsResponse(
        chart_title=title, series=series, data_source="企业集团出栏跟踪",
        update_time=_format_update_date(ld), latest_date=ld.isoformat() if ld else None)


@router.get("/cr5-daily", response_model=EnterpriseStatisticsResponse)
async def get_cr5_daily(
    months: int = Query(6, description="近N个月，0表示全部"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """CR5企业日度出栏统计"""
    sd = _compute_start_date(months)
    return _build_response("CR5企业日度出栏",
                           _query_aggregate(db, "CR5", "output_cumulative", "NATION", sd),
                           _query_aggregate(db, "CR5", "avg_price", "NATION", sd))


@router.get("/sichuan-daily", response_model=EnterpriseStatisticsResponse)
async def get_sichuan_daily(
    months: int = Query(6, description="近N个月，0表示全部"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """四川重点企业日度出栏"""
    # Frontend expects leftSeries=['日度出栏','计划出栏'] rightSeries=['成交率']
    sd = _compute_start_date(months)
    output_rows = _query_region_sum(db, "SICHUAN", "actual_sales", sd)
    plan_rows = _query_region_sum(db, "SICHUAN", "planned_volume", sd)
    deal_rows = _query_region_avg(db, "SICHUAN", "deal_rate", sd)
    series = []
    ld = None
    if output_rows:
        series.append(_to_series(output_rows, "日度出栏", "头"))
        ld = _max_date(ld, _latest(output_rows))
    if plan_rows:
        series.append(_to_series(plan_rows, "计划出栏", "头"))
        ld = _max_date(ld, _latest(plan_rows))
    if deal_rows:
        series.append(_to_series(deal_rows, "成交率", "%"))
        ld = _max_date(ld, _latest(deal_rows))
    if not series:
        return EnterpriseStatisticsResponse(
            chart_title="四川重点企业日度出栏", series=[], data_source="企业集团出栏跟踪",
            update_time=None, latest_date=None)
    return EnterpriseStatisticsResponse(
        chart_title="四川重点企业日度出栏", series=series, data_source="企业集团出栏跟踪",
        update_time=_format_update_date(ld), latest_date=ld.isoformat() if ld else None)


@router.get("/guangxi-daily", response_model=EnterpriseStatisticsResponse)
async def get_guangxi_daily(
    months: int = Query(6, description="近N个月，0表示全部"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """广西重点企业日度出栏"""
    # Frontend expects leftSeries=['日度出栏'] rightSeries=['成交率']
    sd = _compute_start_date(months)
    output_rows = _query_region_sum(db, "GUANGXI", "actual_sales", sd)
    deal_rows = _query_region_avg(db, "GUANGXI", "deal_rate", sd)
    series = []
    ld = None
    if output_rows:
        series.append(_to_series(output_rows, "日度出栏", "头"))
        ld = _max_date(ld, _latest(output_rows))
    if deal_rows:
        series.append(_to_series(deal_rows, "成交率", "%"))
        ld = _max_date(ld, _latest(deal_rows))
    if not series:
        return EnterpriseStatisticsResponse(
            chart_title="广西重点企业日度出栏", series=[], data_source="企业集团出栏跟踪",
            update_time=None, latest_date=None)
    return EnterpriseStatisticsResponse(
        chart_title="广西重点企业日度出栏", series=series, data_source="企业集团出栏跟踪",
        update_time=_format_update_date(ld), latest_date=ld.isoformat() if ld else None)


@router.get("/southwest-sample-daily", response_model=EnterpriseStatisticsResponse)
@router.get("/southwest-daily", response_model=EnterpriseStatisticsResponse)
async def get_southwest_daily(
    months: int = Query(6, description="近N个月，0表示全部"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """西南样本企业日度出栏"""
    sd = _compute_start_date(months)
    # Frontend expects series named '出栏量' (left axis) and '均重' (right axis)
    output = _query_aggregate(db, "SAMPLE", "sample_volume", "SOUTHWEST", sd)
    if not output:
        output = _query_region_sum(db, "SOUTHWEST", "actual_sales", sd)
    weight = _query_aggregate(db, "SAMPLE", "sample_weight", "SOUTHWEST", sd)

    series = []
    ld = None
    if output:
        series.append(_to_series(output, "出栏量", "头"))
        ld = _max_date(ld, _latest(output))
    if weight:
        series.append(_to_series(weight, "均重", "公斤"))
        ld = _max_date(ld, _latest(weight))
    if not series:
        return EnterpriseStatisticsResponse(
            chart_title="西南样本企业日度出栏", series=[], data_source="企业集团出栏跟踪",
            update_time=None, latest_date=None)
    return EnterpriseStatisticsResponse(
        chart_title="西南样本企业日度出栏", series=series, data_source="企业集团出栏跟踪",
        update_time=_format_update_date(ld), latest_date=ld.isoformat() if ld else None)


# ---------------------------------------------------------------------------
# Province summary table (D2 page)
# ---------------------------------------------------------------------------

PROVINCE_SUMMARY_REGIONS = [
    ("四川", "SICHUAN"),
    ("广西", "GUANGXI"),
    ("贵州", "GUIZHOU"),
]


class ProvinceSummaryTableResponse(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    data_source: str = "企业集团出栏跟踪"
    update_time: Optional[str] = None
    latest_date: Optional[str] = None


def _get_period_type(d: date) -> str:
    """Determine 旬度 period for a date."""
    if d.day <= 10:
        return "上旬"
    elif d.day <= 20:
        return "中旬"
    return "月度"


def _period_start(d: date) -> date:
    """Get the start date of the 旬 period containing d."""
    if d.day <= 10:
        return d.replace(day=1)
    elif d.day <= 20:
        return d.replace(day=11)
    else:
        return d.replace(day=21)


@router.get("/province-summary-table", response_model=ProvinceSummaryTableResponse)
async def get_province_summary_table(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """重点省份旬度汇总表格"""
    # Determine date range — default to latest 4 months
    if not end_date:
        r = db.execute(text(
            "SELECT MAX(trade_date) FROM fact_enterprise_daily "
            "WHERE metric_type IN ('actual_sales','planned_volume')"
        )).scalar()
        ed = r if r else date.today()
    else:
        ed = date.fromisoformat(end_date)

    if not start_date:
        sd = ed - timedelta(days=120)
    else:
        sd = date.fromisoformat(start_date)

    # Query data per province
    sql = """
        SELECT trade_date, region_code, metric_type, SUM(value) AS v
        FROM fact_enterprise_daily
        WHERE region_code IN ('SICHUAN','GUANGXI','GUIZHOU')
          AND metric_type IN ('actual_sales','planned_volume')
          AND trade_date BETWEEN :sd AND :ed
          AND value IS NOT NULL
          AND company_code != 'SAMPLE'
        GROUP BY trade_date, region_code, metric_type
        ORDER BY trade_date
    """
    rows = db.execute(text(sql), {"sd": sd, "ed": ed}).fetchall()

    # Also get MS average price per province
    price_sql = """
        SELECT trade_date, region_code, value
        FROM fact_enterprise_daily
        WHERE region_code IN ('SICHUAN','GUANGXI','GUIZHOU')
          AND metric_type = 'ms_avg_price'
          AND company_code = 'MS'
          AND trade_date BETWEEN :sd AND :ed
          AND value IS NOT NULL
        ORDER BY trade_date
    """
    price_rows = db.execute(text(price_sql), {"sd": sd, "ed": ed}).fetchall()

    # Build period-level aggregation: (period_start, region) -> {metric: sum}
    region_name_map = {code: name for name, code in PROVINCE_SUMMARY_REGIONS}
    period_data: Dict[tuple, Dict[str, float]] = {}  # (period_start, period_type) -> {col: val}

    for r in rows:
        td, rgn, mt, val = r[0], r[1], r[2], float(r[3])
        prov_name = region_name_map.get(rgn, rgn)
        ps = _period_start(td)
        pt = _get_period_type(td)
        key = (ps, pt)
        if key not in period_data:
            period_data[key] = {}
        col = f"{prov_name}-{'出栏计划' if mt == 'planned_volume' else '实际出栏量'}"
        period_data[key][col] = period_data[key].get(col, 0) + val

    # Aggregate prices: average over the period
    price_agg: Dict[tuple, Dict[str, list]] = {}
    for r in price_rows:
        td, rgn, val = r[0], r[1], float(r[2])
        prov_name = region_name_map.get(rgn, rgn)
        ps = _period_start(td)
        pt = _get_period_type(td)
        key = (ps, pt)
        col = f"{prov_name}-均价"
        if key not in price_agg:
            price_agg[key] = {}
        if col not in price_agg[key]:
            price_agg[key][col] = []
        price_agg[key][col].append(val)

    for key, cols in price_agg.items():
        if key not in period_data:
            period_data[key] = {}
        for col, vals in cols.items():
            period_data[key][col] = round(sum(vals) / len(vals), 2)

    # Compute completion rates
    for key, cols in period_data.items():
        for prov_name, _ in PROVINCE_SUMMARY_REGIONS:
            plan_col = f"{prov_name}-出栏计划"
            actual_col = f"{prov_name}-实际出栏量"
            rate_col = f"{prov_name}-计划完成率"
            plan = cols.get(plan_col, 0)
            actual = cols.get(actual_col, 0)
            if plan and plan > 0:
                cols[rate_col] = round(actual / plan, 4)

    # Build columns
    columns = ["日期", "旬度"]
    for prov_name, _ in PROVINCE_SUMMARY_REGIONS:
        columns.extend([
            f"{prov_name}-出栏计划",
            f"{prov_name}-实际出栏量",
            f"{prov_name}-计划完成率",
            f"{prov_name}-均价",
        ])

    # Build rows sorted by date descending
    sorted_keys = sorted(period_data.keys(), key=lambda x: x[0], reverse=True)
    result_rows = []
    for ps, pt in sorted_keys:
        row: Dict[str, Any] = {"date": ps.isoformat(), "period_type": pt}
        row.update(period_data[(ps, pt)])
        result_rows.append(row)

    latest = sorted_keys[0][0].isoformat() if sorted_keys else None

    return ProvinceSummaryTableResponse(
        columns=columns,
        rows=result_rows,
        latest_date=latest,
        update_time=_format_update_date(sorted_keys[0][0]) if sorted_keys else None,
    )
