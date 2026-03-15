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


def _convert_wan_to_head(rows: List[dict]) -> List[dict]:
    """DB 中 CR5 出栏/计划为万头，图表展示为头：value * 10000"""
    if not rows:
        return rows
    out = []
    for r in rows:
        v, u = r.get("value"), r.get("unit")
        if u == "万头" and v is not None:
            out.append({**r, "value": round(float(v) * 10000, 2), "unit": "头"})
        else:
            out.append(dict(r))
    return out


def _normalize_deal_rate_for_display(rows: List[dict]) -> List[dict]:
    """成交率：Excel/DB 常为小数 0.85=85%，前端按「数值+%」显示，需转为 0-100。与 P8 解析器逻辑一致。"""
    if not rows:
        return rows
    out = []
    for r in rows:
        v = r.get("value")
        if v is not None:
            f = float(v)
            if 0 < f <= 1.5:
                out.append({**r, "value": round(f * 100, 2)})
            else:
                out.append(dict(r))
        else:
            out.append(dict(r))
    return out


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
    """CR5企业日度出栏统计。数据来源: fact_enterprise_daily（r03 CR5日度 sheet），出栏/计划量 DB 存万头，接口转为头以与旧版图表尺度一致。"""
    sd = _compute_start_date(months)
    output_rows = _convert_wan_to_head(_query_aggregate(db, "CR5", "output_cumulative", "NATION", sd))
    plan_rows = _convert_wan_to_head(_query_aggregate(db, "CR5", "planned_volume", "NATION", sd))
    price_rows = _query_aggregate(db, "CR5", "avg_price", "NATION", sd)
    series = []
    ld = None
    if output_rows:
        series.append(_to_series(output_rows, "日度出栏", "头"))
        ld = _max_date(ld, _latest(output_rows))
    if plan_rows:
        series.append(_to_series(plan_rows, "计划量", "头"))
        ld = _max_date(ld, _latest(plan_rows))
    if price_rows:
        series.append(_to_series(price_rows, "价格", "元/公斤"))
        ld = _max_date(ld, _latest(price_rows))
    if not series:
        return EnterpriseStatisticsResponse(
            chart_title="CR5企业日度出栏", series=[], data_source="企业集团出栏跟踪",
            update_time=None, latest_date=None)
    return EnterpriseStatisticsResponse(
        chart_title="CR5企业日度出栏", series=series, data_source="企业集团出栏跟踪",
        update_time=_format_update_date(ld), latest_date=ld.isoformat() if ld else None)


@router.get("/sichuan-daily", response_model=EnterpriseStatisticsResponse)
async def get_sichuan_daily(
    months: int = Query(6, description="近N个月，0表示全部"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """四川重点企业日度出栏。数据来自 西南汇总：D列=实际成交(日度出栏)、E列=成交率、F列=计划日均(计划出栏)。"""
    sd = _compute_start_date(months)
    output_rows = _query_aggregate(db, "SAMPLE", "actual_volume", "SICHUAN", sd)
    if not output_rows:
        output_rows = _query_region_sum(db, "SICHUAN", "actual_sales", sd)
    plan_rows = _query_aggregate(db, "SAMPLE", "planned_daily", "SICHUAN", sd)
    if not plan_rows:
        plan_rows = _query_region_sum(db, "SICHUAN", "planned_volume", sd)
    deal_rows = _query_aggregate(db, "SAMPLE", "deal_rate", "SICHUAN", sd)
    if not deal_rows:
        deal_rows = _query_region_avg(db, "SICHUAN", "deal_rate", sd)
    deal_rows = _normalize_deal_rate_for_display(deal_rows)
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
    """广西重点企业日度出栏。与 CR5/西南一致：优先用 西南汇总 sheet 的 实际成交(actual_volume)、成交率(deal_rate)。"""
    sd = _compute_start_date(months)
    output_rows = _query_aggregate(db, "SAMPLE", "actual_volume", "GUANGXI", sd)
    if not output_rows:
        output_rows = _query_region_sum(db, "GUANGXI", "actual_sales", sd)
    deal_rows = _query_aggregate(db, "SAMPLE", "deal_rate", "GUANGXI", sd)
    if not deal_rows:
        deal_rows = _query_region_avg(db, "GUANGXI", "deal_rate", sd)
    deal_rows = _normalize_deal_rate_for_display(deal_rows)
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

# D2 重点省份出栏统计：仅 广东、四川、贵州，按此顺序；不含广西
PROVINCE_SUMMARY_REGIONS = [
    ("广东", "GUANGDONG"),
    ("四川", "SICHUAN"),
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


# 汇总 sheet（集团企业月度）indicator 后缀 -> 旬度显示
_INDICATOR_PERIOD_TO_LABEL = {"first_10d": "上旬", "mid_10d": "中旬", "monthly": "月度"}

# 汇总 sheet：region_code + indicator 前缀 -> 前端列名（与 Excel 汇总 B:Q 一致）
_PROVINCE_SUMMARY_COL_MAP = [
    ("GUANGDONG", "planned_output", "广东", "出栏计划"),
    ("GUANGDONG", "actual_output", "广东", "实际出栏量"),
    ("GUANGDONG", "plan_completion_rate", "广东", "计划完成率"),
    ("GUANGDONG", "avg_weight", "广东", "均重"),
    ("GUANGDONG", "avg_price", "广东", "均价"),
    ("SICHUAN", "planned_output", "四川", "出栏计划"),
    ("SICHUAN", "actual_output", "四川", "实际出栏量"),
    ("SICHUAN", "plan_completion_rate", "四川", "计划完成率"),
    ("SICHUAN", "avg_weight", "四川", "均重"),
    ("SICHUAN", "planned_avg_weight", "四川", "计划均重"),
    ("GUIZHOU", "planned_output", "贵州", "计划出栏量"),
    ("GUIZHOU", "actual_output", "贵州", "实际出栏量"),
    ("GUIZHOU", "plan_completion_rate", "贵州", "计划达成率"),
    ("GUIZHOU", "avg_weight", "贵州", "实际均重"),
    ("GUIZHOU", "planned_avg_weight", "贵州", "计划均重"),
]
# 中文 indicator 前缀 -> 英文 base，保证库里有中文时也能 1:1 展示
_METRIC_CN_TO_BASE = {
    "出栏计划": "planned_output", "计划出栏量": "planned_output",
    "实际出栏量": "actual_output",
    "计划完成率": "plan_completion_rate", "计划达成率": "plan_completion_rate",
    "均重": "avg_weight", "实际均重": "avg_weight", "计划均重": "planned_avg_weight",
    "均价": "avg_price", "销售均价": "avg_price",
}


def _display_date_for_period(month_dt: date, period_tag: str) -> date:
    """汇总 上旬/中旬/月度 对应显示日期（与 Excel 汇总 sheet B 列一致）"""
    if period_tag == "first_10d":
        return month_dt.replace(day=10) if month_dt.month != 2 else month_dt.replace(day=min(10, 28))
    if period_tag == "mid_10d":
        return month_dt.replace(day=20) if month_dt.month != 2 else month_dt.replace(day=min(20, 28))
    # monthly: 月末
    if month_dt.month == 12:
        return month_dt.replace(day=31)
    from calendar import monthrange
    _, last = monthrange(month_dt.year, month_dt.month)
    return month_dt.replace(day=last)


def _date_to_yyyy_mm_dd(d: date) -> str:
    """日期原样输出格式：yyyy/MM/dd"""
    return d.strftime("%Y/%m/%d")


@router.get("/province-summary-table", response_model=ProvinceSummaryTableResponse)
async def get_province_summary_table(
    scope: Optional[str] = Query(None, description="all=全部, recent_4_months=近4个月"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    """重点省份旬度汇总表格。数据来源：集团企业月度数据跟踪 - 汇总 sheet（B:Q 列）。
    与 Excel 一一对应：接口按库内 (month_date, period_tag) 原样返回，每行对应 Excel 汇总的一行（日期+旬度+三省指标）。"""
    # 取库内 month_date 范围
    min_max = db.execute(text(
        "SELECT MIN(month_date), MAX(month_date) FROM fact_enterprise_monthly "
        "WHERE company_code = 'TOTAL' AND region_code IN ('GUANGDONG','SICHUAN','GUIZHOU')"
    )).fetchone()
    db_min, db_max = (min_max[0], min_max[1]) if min_max and min_max[0] else (None, None)

    if scope == "recent_4_months":
        ed = db_max if db_max else date.today()
        ed_first = ed.replace(day=1) if ed.day != 1 else ed
        y, m = ed_first.year, ed_first.month
        m -= 3
        if m <= 0:
            m += 12
            y -= 1
        sd = date(y, m, 1)
    elif start_date and end_date:
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
    else:
        # 全部：不传或 scope=all，用库内最小/最大
        sd = db_min if db_min else date(2020, 1, 1)
        ed = db_max if db_max else date.today()

    # 查询 汇总 sheet 写入的数据：company_code=TOTAL，广东/四川/贵州
    sql = """
        SELECT month_date, region_code, indicator, value
        FROM fact_enterprise_monthly
        WHERE company_code = 'TOTAL'
          AND region_code IN ('GUANGDONG','SICHUAN','GUIZHOU')
          AND month_date >= :sd AND month_date <= :ed
          AND value IS NOT NULL
        ORDER BY month_date, region_code, indicator
    """
    rows = db.execute(text(sql), {"sd": sd, "ed": ed}).fetchall()

    # 与 Excel 1:1：每个 (month_date, period_tag) 对应汇总 sheet 一行
    # indicator 格式为 {metric}_{period_tag}，period_tag 可能为 first_10d / mid_10d / monthly 或 上旬/中旬/月度
    # 注意：first_10d 用最后 _ 分割会得到 suffix="10d"，需用倒数第二段 first/mid 还原
    _PERIOD_NORMALIZE = {"上旬": "first_10d", "中旬": "mid_10d", "月度": "monthly"}
    period_data: Dict[tuple, Dict[str, Any]] = {}  # (month_date, period_tag) -> {列名: 值}
    for r in rows:
        month_dt, region_code, indicator, val = r[0], r[1], r[2], float(r[3])
        if "_" not in indicator:
            continue
        parts = indicator.rsplit("_", 1)
        metric_base, period_tag_raw = parts[0], parts[1]
        if period_tag_raw == "10d" and metric_base.endswith("_first"):
            period_tag = "first_10d"
            metric_base = metric_base[:-6]  # 去掉 _first
        elif period_tag_raw == "10d" and metric_base.endswith("_mid"):
            period_tag = "mid_10d"
            metric_base = metric_base[:-4]  # 去掉 _mid
        else:
            period_tag = _PERIOD_NORMALIZE.get(period_tag_raw, period_tag_raw)
        period_label = _INDICATOR_PERIOD_TO_LABEL.get(period_tag)
        if not period_label:
            continue
        key = (month_dt, period_tag)
        if key not in period_data:
            period_data[key] = {}
        base_to_try = metric_base if metric_base in ("planned_output", "actual_output", "plan_completion_rate", "avg_weight", "planned_avg_weight", "avg_price") else _METRIC_CN_TO_BASE.get(metric_base, metric_base)
        for reg, base, prov_name, col_label in _PROVINCE_SUMMARY_COL_MAP:
            if reg != region_code or base != base_to_try:
                continue
            col_key = f"{prov_name}-{col_label}"
            period_data[key][col_key] = val
            break

    # 表头列顺序：日期、旬度，再按 广东/四川/贵州 及指标顺序
    columns = ["日期", "旬度"]
    for _, _, prov_name, col_label in _PROVINCE_SUMMARY_COL_MAP:
        columns.append(f"{prov_name}-{col_label}")

    # 去重列名（保持顺序）
    seen = set()
    columns_ordered = []
    for c in columns:
        if c not in seen:
            seen.add(c)
            columns_ordered.append(c)
    columns = columns_ordered

    # 与 Excel 一致：按日期升序，同月内 上旬→中旬→月度
    PERIOD_ORDER = {"first_10d": 0, "mid_10d": 1, "monthly": 2}

    def sort_key(item):
        month_dt, period_tag = item
        return (month_dt.year, month_dt.month, PERIOD_ORDER.get(period_tag, 3))

    sorted_keys = sorted(period_data.keys(), key=sort_key)
    result_rows = []
    for month_dt, period_tag in sorted_keys:
        cell_values = period_data[(month_dt, period_tag)]
        # 与 Excel 一致：只显示至少有一个非空值的行（汇总 sheet 该行 C:Q 至少一格有数）
        if not any(v is not None and v != "" for v in cell_values.values()):
            continue
        display_d = _display_date_for_period(month_dt, period_tag)
        period_label = _INDICATOR_PERIOD_TO_LABEL.get(period_tag) or "月度"  # 旬度与 Excel A 列一致：上旬/中旬/月度
        row: Dict[str, Any] = {"date": _date_to_yyyy_mm_dd(display_d), "period_type": period_label}
        row.update(cell_values)
        result_rows.append(row)

    latest = result_rows[-1]["date"] if result_rows else None
    latest_d = None
    if latest:
        from datetime import datetime as dt
        try:
            latest_d = dt.strptime(latest, "%Y/%m/%d").date()
        except ValueError:
            try:
                latest_d = date.fromisoformat(latest.replace("/", "-"))
            except ValueError:
                pass

    return ProvinceSummaryTableResponse(
        columns=columns,
        rows=result_rows,
        latest_date=latest,
        update_time=_format_update_date(latest_d) if latest_d else None,
        data_source="集团企业月度数据跟踪",
    )
