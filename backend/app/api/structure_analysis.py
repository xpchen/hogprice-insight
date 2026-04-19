"""
D4. 结构分析 API
显示CR20集团出栏环比、涌益、钢联、农业部出栏环比和定点企业屠宰环比
数据来源：hogprice_v3 的 fact_enterprise_monthly + fact_monthly_indicator
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import date
from pydantic import BaseModel
import math

from app.core.database import get_db

router = APIRouter(prefix="/api/v1/structure-analysis", tags=["structure-analysis"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class StructureDataPoint(BaseModel):
    date: str
    source: str
    value: Optional[float] = None


class StructureTableRow(BaseModel):
    month: str
    cr20: Optional[float] = None
    yongyi: Optional[float] = None
    ganglian: Optional[float] = None
    ganglian_large: Optional[float] = None
    ganglian_small: Optional[float] = None
    ministry_scale: Optional[float] = None
    ministry_scattered: Optional[float] = None
    slaughter: Optional[float] = None


class StructureAnalysisResponse(BaseModel):
    data: List[StructureDataPoint]
    latest_date: Optional[str] = None


class StructureTableResponse(BaseModel):
    data: List[StructureTableRow]
    latest_month: Optional[str] = None


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 2)
    except (ValueError, TypeError):
        return None


def _compute_mom(rows) -> List[StructureDataPoint]:
    """Compute month-on-month % from absolute values. rows = [(date, value, source_label)]"""
    result = []
    prev_val = None
    for row in rows:
        curr_val = _safe_float(row[1])
        if curr_val is not None and prev_val is not None and prev_val > 0:
            mom = round((curr_val - prev_val) / prev_val * 100, 2)
            result.append(StructureDataPoint(
                date=row[0].isoformat(),
                source=row[2],
                value=mom,
            ))
        prev_val = curr_val
    return result


# ---------------------------------------------------------------------------
# CR20 出栏环比 — from fact_enterprise_monthly
# ---------------------------------------------------------------------------
def _get_cr20_month_on_month(db: Session) -> List[StructureDataPoint]:
    # 仅用实际出栏算环比；当月仅有计划无实际时该月不输出环比（避免 3 月等用计划算出的错误环比）
    sql = text("""
        SELECT month_date,
            MAX(CASE WHEN indicator IN ('actual_output_monthly','实际出栏量','实际出栏量_月度') THEN value END) AS actual,
            MAX(CASE WHEN indicator IN ('planned_output_monthly','计划出栏量','计划出栏量_月度') THEN value END) AS planned
        FROM fact_enterprise_monthly
        WHERE company_code = 'CR20'
          AND indicator IN (
              'actual_output_monthly','planned_output_monthly',
              '实际出栏量','实际出栏量_月度','计划出栏量','计划出栏量_月度'
          )
        GROUP BY month_date
        ORDER BY month_date
    """)
    rows = db.execute(sql).fetchall()
    if len(rows) < 2:
        return []

    result = []
    for i in range(1, len(rows)):
        prev_actual = _safe_float(rows[i - 1][1])
        curr_actual = _safe_float(rows[i][1])
        if prev_actual is not None and curr_actual is not None and prev_actual > 0:
            mom = round((curr_actual - prev_actual) / prev_actual * 100, 2)
            result.append(StructureDataPoint(
                date=rows[i][0].isoformat(),
                source="CR20",
                value=mom,
            ))
    return result


# ---------------------------------------------------------------------------
# 涌益 出栏环比 — 优先使用「月度-商品猪出栏量」C列环比(mom_pct)，无则用 B 列绝对值计算
# ---------------------------------------------------------------------------
def _get_yongyi_month_on_month(db: Session) -> List[StructureDataPoint]:
    sql_mom = text("""
        SELECT month_date, value
        FROM fact_monthly_indicator
        WHERE source = 'YONGYI'
          AND indicator_code = 'hog_output_volume'
          AND value_type = 'mom_pct'
          AND COALESCE(region_code, 'NATION') = 'NATION'
          AND value IS NOT NULL
        ORDER BY month_date
    """)
    rows_mom = db.execute(sql_mom).fetchall()
    if rows_mom:
        return [
            StructureDataPoint(date=r[0].isoformat(), source="涌益", value=_safe_float(r[1]))
            for r in rows_mom
            if _safe_float(r[1]) is not None
        ]
    sql_abs = text("""
        SELECT month_date, value
        FROM fact_monthly_indicator
        WHERE source = 'YONGYI'
          AND indicator_code = 'hog_output_volume'
          AND value_type = 'abs'
          AND COALESCE(region_code, 'NATION') = 'NATION'
          AND value IS NOT NULL
        ORDER BY month_date
    """)
    rows = db.execute(sql_abs).fetchall()
    labeled = [(r[0], r[1], "涌益") for r in rows]
    return _compute_mom(labeled)


# ---------------------------------------------------------------------------
# 钢联 出栏环比 — compute MoM from abs values
# ---------------------------------------------------------------------------
def _get_ganglian_month_on_month(db: Session, scale_type: str = "全国") -> List[StructureDataPoint]:
    # Map scale type to indicator code
    ind_map = {"全国": "hog_output_total", "规模场": "hog_output_large", "中小散户": "hog_output_small"}
    ind = ind_map.get(scale_type, "hog_output_total")

    sql = text("""
        SELECT month_date, value
        FROM fact_monthly_indicator
        WHERE source = 'GANGLIAN'
          AND indicator_code = :ind
          AND value_type = 'abs'
          AND value IS NOT NULL
        ORDER BY month_date
    """)
    rows = db.execute(sql, {"ind": ind}).fetchall()
    labeled = [(r[0], r[1], f"钢联-{scale_type}") for r in rows]
    return _compute_mom(labeled)


# ---------------------------------------------------------------------------
# 农业部(NYB) 出栏环比 — direct mom_pct available
# ---------------------------------------------------------------------------
def _get_ministry_agriculture_month_on_month(db: Session, scale_type: str = "全国") -> List[StructureDataPoint]:
    # sub_category mapping
    sub_map = {"全国": "nation", "规模场": "scale", "中小散户": "small", "散户": "small"}
    sub = sub_map.get(scale_type, "nation")

    sql = text("""
        SELECT month_date, value
        FROM fact_monthly_indicator
        WHERE source = 'NYB'
          AND indicator_code = 'hog_turnover'
          AND value_type = 'mom_pct'
          AND COALESCE(sub_category, 'nation') = :sub
          AND COALESCE(region_code, 'NATION') = 'NATION'
          AND value IS NOT NULL
        ORDER BY month_date
    """)
    rows = db.execute(sql, {"sub": sub}).fetchall()
    result = []
    for r in rows:
        v = _safe_float(r[1])
        if v is not None:
            result.append(StructureDataPoint(
                date=r[0].isoformat(),
                source=f"农业部-{scale_type}",
                value=v,
            ))
    return result


# ---------------------------------------------------------------------------
# 定点企业屠宰环比 — 优先 A1 供给预测 AD 列(mom_pct)，无则用定点屠宰 sheet 绝对值算环比
# ---------------------------------------------------------------------------
def _get_slaughter_month_on_month(db: Session) -> List[StructureDataPoint]:
    sql_a1 = text("""
        SELECT month_date, value
        FROM fact_monthly_indicator
        WHERE source = 'A1'
          AND indicator_code = 'designated_slaughter'
          AND value_type = 'mom_pct'
          AND COALESCE(region_code, 'NATION') = 'NATION'
          AND value IS NOT NULL
        ORDER BY month_date
    """)
    rows_a1 = db.execute(sql_a1).fetchall()
    if rows_a1:
        return [
            StructureDataPoint(date=r[0].isoformat(), source="定点企业屠宰", value=_safe_float(r[1]))
            for r in rows_a1
            if _safe_float(r[1]) is not None
        ]
    sql_abs = text("""
        SELECT month_date, value
        FROM fact_monthly_indicator
        WHERE source = 'STATISTICS_BUREAU'
          AND indicator_code = 'designated_slaughter'
          AND value_type = 'abs'
          AND COALESCE(region_code, 'NATION') = 'NATION'
          AND value IS NOT NULL
        ORDER BY month_date
    """)
    rows = db.execute(sql_abs).fetchall()
    labeled = [(r[0], r[1], "定点企业屠宰") for r in rows]
    return _compute_mom(labeled)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/data", response_model=StructureAnalysisResponse)
async def get_structure_analysis_data(
    sources: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    if sources:
        source_list = [s.strip() for s in sources.split(',')]
    else:
        source_list = ["CR20", "涌益", "钢联-全国", "定点企业屠宰"]

    all_data: List[StructureDataPoint] = []

    if "CR20" in source_list:
        all_data.extend(_get_cr20_month_on_month(db))
    if "涌益" in source_list:
        all_data.extend(_get_yongyi_month_on_month(db))
    if "钢联-全国" in source_list:
        all_data.extend(_get_ganglian_month_on_month(db, "全国"))
    if "钢联-规模场" in source_list:
        all_data.extend(_get_ganglian_month_on_month(db, "规模场"))
    if "钢联-中小散户" in source_list:
        all_data.extend(_get_ganglian_month_on_month(db, "中小散户"))
    if "农业部-全国" in source_list:
        all_data.extend(_get_ministry_agriculture_month_on_month(db, "全国"))
    if "农业部-规模场" in source_list:
        all_data.extend(_get_ministry_agriculture_month_on_month(db, "规模场"))
    if "农业部-中小散户" in source_list:
        all_data.extend(_get_ministry_agriculture_month_on_month(db, "中小散户"))
    if "定点企业屠宰" in source_list:
        all_data.extend(_get_slaughter_month_on_month(db))

    filtered_data = [item for item in all_data if item.value is not None]
    filtered_data.sort(key=lambda x: x.date)
    latest_date = filtered_data[-1].date if filtered_data else None

    return StructureAnalysisResponse(data=filtered_data, latest_date=latest_date)


@router.get("/table", response_model=StructureTableResponse)
async def get_structure_analysis_table(
    db: Session = Depends(get_db)
):
    cr20_data = _get_cr20_month_on_month(db)
    yongyi_data = _get_yongyi_month_on_month(db)
    ganglian_data = _get_ganglian_month_on_month(db, "全国")
    ganglian_large_data = _get_ganglian_month_on_month(db, "规模场")
    ganglian_small_data = _get_ganglian_month_on_month(db, "中小散户")
    ministry_scale_data = _get_ministry_agriculture_month_on_month(db, "规模场")
    ministry_scattered_data = _get_ministry_agriculture_month_on_month(db, "散户")
    slaughter_data = _get_slaughter_month_on_month(db)

    def _to_month(date_str: str) -> str:
        return date_str[:7] if len(date_str) >= 7 else date_str

    data_map: dict = {}
    for label, items in [
        ("cr20", cr20_data),
        ("yongyi", yongyi_data),
        ("ganglian", ganglian_data),
        ("ganglian_large", ganglian_large_data),
        ("ganglian_small", ganglian_small_data),
        ("ministry_scale", ministry_scale_data),
        ("ministry_scattered", ministry_scattered_data),
        ("slaughter", slaughter_data),
    ]:
        for item in items:
            month = _to_month(item.date)
            data_map.setdefault(month, {})[label] = item.value

    table_rows = []
    for month in sorted(data_map.keys()):
        row_data = data_map[month]
        table_rows.append(StructureTableRow(
            month=month,
            cr20=row_data.get('cr20'),
            yongyi=row_data.get('yongyi'),
            ganglian=row_data.get('ganglian'),
            ganglian_large=row_data.get('ganglian_large'),
            ganglian_small=row_data.get('ganglian_small'),
            ministry_scale=row_data.get('ministry_scale'),
            ministry_scattered=row_data.get('ministry_scattered'),
            slaughter=row_data.get('slaughter'),
        ))

    latest_month = table_rows[-1].month if table_rows else None
    return StructureTableResponse(data=table_rows, latest_month=latest_month)
