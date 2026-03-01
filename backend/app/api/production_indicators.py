"""
规模场数据汇总 API  (v3 — fact tables)

查询 hogprice_v3 的 fact_monthly_indicator / fact_weekly_indicator，
替代原先从 raw_table JSON 解析的逻辑。

端点                                              原数据源
──────────────────────────────────────────────────────────────
/sow-efficiency                                   月度-生产指标（分娩窝数）
/pressure-coefficient                             月度-生产指标（窝均健仔数-全国）
/yongyi-production-indicators                     月度-生产指标（多区域窝均健仔数）
/yongyi-production-seasonality                    月度-生产指标2（五指标季节性）
/a1-sow-efficiency-pressure-seasonality           A1供给预测（母猪效能+压栏系数）
/a1-supply-forecast-table                         A1供给预测表格
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel
from collections import defaultdict

from app.core.database import get_db

router = APIRouter(prefix="/api/v1/production-indicators", tags=["production-indicators"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Response Models (保持与前端一致)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ProductionDataPoint(BaseModel):
    """生产指标数据点"""
    date: str  # 日期 YYYY-MM-DD
    value: Optional[float] = None


class ProductionIndicatorResponse(BaseModel):
    """生产指标响应"""
    data: List[ProductionDataPoint]
    indicator_name: str
    latest_date: Optional[str] = None


class ProductionIndicatorsResponse(BaseModel):
    """多个生产指标响应"""
    indicators: Dict[str, List[ProductionDataPoint]]
    indicator_names: List[str]
    latest_date: Optional[str] = None


class YongyiProductionSeasonalityResponse(BaseModel):
    """涌益生产指标季节性数据"""
    indicators: Dict[str, Dict[str, Any]]
    indicator_names: List[str]


class A1SeasonalityResponse(BaseModel):
    """A1 表格 F/N 列季节性数据（母猪效能、压栏系数）"""
    sow_efficiency: Dict
    pressure_coefficient: Dict


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helper: 查询 fact_monthly_indicator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _query_monthly(
    db: Session,
    indicator_code: str,
    source: Optional[str] = None,
    region_code: str = "NATION",
    sub_category: Optional[str] = None,
    value_type: Optional[str] = None,
) -> List[ProductionDataPoint]:
    """从 fact_monthly_indicator 查询指定指标，返回按日期排序的数据点列表。"""
    sql = """
        SELECT month_date, value
        FROM fact_monthly_indicator
        WHERE indicator_code = :indicator_code
          AND region_code = :region_code
          AND value IS NOT NULL
    """
    params: dict = {
        "indicator_code": indicator_code,
        "region_code": region_code,
    }
    if source is not None:
        sql += " AND source = :source"
        params["source"] = source
    if sub_category is not None:
        sql += " AND (sub_category = :sub_category)"
        params["sub_category"] = sub_category
    if value_type is not None:
        sql += " AND value_type = :value_type"
        params["value_type"] = value_type
    sql += " ORDER BY month_date"

    rows = db.execute(text(sql), params).fetchall()
    return [
        ProductionDataPoint(
            date=row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
            value=round(float(row[1]), 2) if row[1] is not None else None,
        )
        for row in rows
    ]


def _query_monthly_multi_region(
    db: Session,
    indicator_code: str,
    region_codes: List[str],
    source: Optional[str] = None,
    sub_category: Optional[str] = None,
    value_type: Optional[str] = None,
) -> Dict[str, List[ProductionDataPoint]]:
    """从 fact_monthly_indicator 查询多个区域的同一指标。"""
    sql = """
        SELECT month_date, region_code, value
        FROM fact_monthly_indicator
        WHERE indicator_code = :indicator_code
          AND region_code IN :region_codes
          AND value IS NOT NULL
    """
    params: dict = {
        "indicator_code": indicator_code,
        "region_codes": tuple(region_codes),
    }
    if source is not None:
        sql += " AND source = :source"
        params["source"] = source
    if sub_category is not None:
        sql += " AND (sub_category = :sub_category)"
        params["sub_category"] = sub_category
    if value_type is not None:
        sql += " AND value_type = :value_type"
        params["value_type"] = value_type
    sql += " ORDER BY month_date"

    # SQLAlchemy text() 不直接支持 IN :tuple，改用字符串拼接 placeholders
    placeholders = ", ".join([f":rc_{i}" for i in range(len(region_codes))])
    sql_fixed = f"""
        SELECT month_date, region_code, value
        FROM fact_monthly_indicator
        WHERE indicator_code = :indicator_code
          AND region_code IN ({placeholders})
          AND value IS NOT NULL
    """
    params_fixed: dict = {"indicator_code": indicator_code}
    for i, rc in enumerate(region_codes):
        params_fixed[f"rc_{i}"] = rc
    if source is not None:
        sql_fixed += " AND source = :source"
        params_fixed["source"] = source
    if sub_category is not None:
        sql_fixed += " AND (sub_category = :sub_category)"
        params_fixed["sub_category"] = sub_category
    if value_type is not None:
        sql_fixed += " AND value_type = :value_type"
        params_fixed["value_type"] = value_type
    sql_fixed += " ORDER BY month_date"

    rows = db.execute(text(sql_fixed), params_fixed).fetchall()

    result: Dict[str, List[ProductionDataPoint]] = {rc: [] for rc in region_codes}
    for row in rows:
        dt_str = row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
        rc = row[1]
        val = round(float(row[2]), 2) if row[2] is not None else None
        if rc in result:
            result[rc].append(ProductionDataPoint(date=dt_str, value=val))
    return result


def _to_seasonality(data_points: List[ProductionDataPoint]) -> Dict[str, Any]:
    """把时间序列数据转为季节性格式（按年月分组，多年叠线）。"""
    by_year_month: Dict[tuple, float] = {}
    for dp in data_points:
        try:
            d = datetime.strptime(dp.date[:10], "%Y-%m-%d").date()
            if dp.value is not None:
                by_year_month[(d.year, d.month)] = dp.value
        except (ValueError, TypeError):
            continue

    years = sorted({y for y, _ in by_year_month.keys()})
    x_values = [f"{m}月" for m in range(1, 13)]
    series = []
    for year in years:
        values = [by_year_month.get((year, m)) for m in range(1, 13)]
        series.append({"year": year, "values": values})
    return {"x_values": x_values, "series": series, "meta": {"unit": "", "freq": "M", "metric_name": ""}}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/sow-efficiency", response_model=ProductionIndicatorResponse)
async def get_sow_efficiency(db: Session = Depends(get_db)):
    """
    获取母猪效能数据（分娩窝数）
    来源: fact_monthly_indicator, indicator_code = prod_farrowing_count
    """
    data_points = _query_monthly(
        db,
        indicator_code="prod_farrowing_count",
        source="YONGYI",
        region_code="NATION",
        sub_category="",
        value_type="abs",
    )
    latest_date = data_points[-1].date if data_points else None
    return ProductionIndicatorResponse(
        data=data_points,
        indicator_name="分娩窝数",
        latest_date=latest_date,
    )


@router.get("/pressure-coefficient", response_model=ProductionIndicatorResponse)
async def get_pressure_coefficient(db: Session = Depends(get_db)):
    """
    获取压栏系数数据（窝均健仔数-全国）
    来源: fact_monthly_indicator, indicator_code = prod_healthy_piglets_per_litter
    """
    data_points = _query_monthly(
        db,
        indicator_code="prod_healthy_piglets_per_litter",
        source="YONGYI",
        region_code="NATION",
        sub_category="",
        value_type="abs",
    )
    latest_date = data_points[-1].date if data_points else None
    return ProductionIndicatorResponse(
        data=data_points,
        indicator_name="窝均健仔数（全国）",
        latest_date=latest_date,
    )


# ── 涌益·多区域窝均健仔数 ─────────────────────────────────────

# 区域代码 -> 前端显示名
_REGION_DISPLAY_NAMES = {
    "NATION": "全国",
    "NORTHEAST": "东北",
    "NORTH": "华北",
    "EAST": "华东",
    "CENTRAL": "华中",
    "SOUTH": "华南",
    "SOUTHWEST": "西南",
    "NORTHWEST": "西北",
}


@router.get("/yongyi-production-indicators", response_model=ProductionIndicatorsResponse)
async def get_yongyi_production_indicators(db: Session = Depends(get_db)):
    """
    获取涌益生产指标数据
    原接口返回 5 省份窝均健仔数，现在从 fact_monthly_indicator 查询
    indicator_code = prod_healthy_piglets_per_litter, 多区域
    """
    # 查询所有区域的窝均健仔数数据
    sql = """
        SELECT month_date, region_code, value
        FROM fact_monthly_indicator
        WHERE indicator_code = :indicator_code
          AND source = :source
          AND value IS NOT NULL
        ORDER BY month_date
    """
    rows = db.execute(text(sql), {
        "indicator_code": "prod_healthy_piglets_per_litter",
        "source": "YONGYI",
    }).fetchall()

    # 按区域分组
    indicators_data: Dict[str, List[ProductionDataPoint]] = defaultdict(list)
    all_dates: List[str] = []

    for row in rows:
        dt_str = row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
        region = row[1]
        val = round(float(row[2]), 2) if row[2] is not None else None
        display_name = _REGION_DISPLAY_NAMES.get(region, region)
        indicators_data[display_name].append(ProductionDataPoint(date=dt_str, value=val))
        all_dates.append(dt_str)

    # 如果只有 NATION 数据，也返回（向后兼容）
    indicator_names = sorted(indicators_data.keys())
    latest_date = max(all_dates) if all_dates else None

    return ProductionIndicatorsResponse(
        indicators=dict(indicators_data),
        indicator_names=indicator_names,
        latest_date=latest_date,
    )


# ── 涌益生产指标季节性（生产指标2 五指标） ─────────────────────

# 生产指标2 的五个指标：中文名 -> (indicator_code, unit_hint)
_PROD2_SEASONALITY_MAP = [
    ("窝均健仔数", "prod2_healthy_piglets_per_litter", ""),
    ("产房存活率", "prod2_farrowing_survival_rate", "ratio"),
    ("配种分娩率", "prod2_mating_farrowing_rate", "ratio"),
    ("断奶成活率", "prod2_weaning_survival_rate", "ratio"),
    ("育肥出栏成活率", "prod2_fattening_survival_rate", "ratio"),
]


@router.get("/yongyi-production-seasonality", response_model=YongyiProductionSeasonalityResponse)
async def get_yongyi_production_seasonality(db: Session = Depends(get_db)):
    """
    涌益生产指标季节性数据
    数据源: fact_monthly_indicator，月度-生产指标2 对应 indicator_code
    五指标：窝均健仔数、产房存活率、配种分娩率、断奶成活率、育肥出栏成活率
    """
    indicator_names = [name for name, _, _ in _PROD2_SEASONALITY_MAP]
    result: Dict[str, Dict[str, Any]] = {}

    for display_name, code, unit_hint in _PROD2_SEASONALITY_MAP:
        data_points = _query_monthly(
            db,
            indicator_code=code,
            source="YONGYI",
            region_code="NATION",
            sub_category="",
            value_type="abs",
        )
        seasonality = _to_seasonality(data_points)
        seasonality["meta"]["metric_name"] = display_name
        if unit_hint:
            seasonality["meta"]["unit"] = unit_hint
        result[display_name] = seasonality

    return YongyiProductionSeasonalityResponse(
        indicators=result,
        indicator_names=indicator_names,
    )


# ── A1 母猪效能 + 压栏系数 季节性 ──────────────────────────────

@router.get("/a1-sow-efficiency-pressure-seasonality", response_model=A1SeasonalityResponse)
async def get_a1_sow_efficiency_pressure_seasonality(db: Session = Depends(get_db)):
    """
    母猪效能(分娩窝数) + 压栏系数(窝均健仔数) 季节性
    原A1供给预测F/N列 -> 现在查 fact_monthly_indicator:
      - 母猪效能: prod_farrowing_count
      - 压栏系数: prod_healthy_piglets_per_litter
    """
    empty_seasonality = lambda name: {
        "x_values": [f"{m}月" for m in range(1, 13)],
        "series": [],
        "meta": {"unit": "", "freq": "M", "metric_name": name},
    }

    # 母猪效能 = 分娩窝数
    sow_data = _query_monthly(
        db,
        indicator_code="prod_farrowing_count",
        source="YONGYI",
        region_code="NATION",
        sub_category="",
        value_type="abs",
    )
    if sow_data:
        sow = _to_seasonality(sow_data)
        sow["meta"]["metric_name"] = "母猪效能"
    else:
        sow = empty_seasonality("母猪效能")

    # 压栏系数 = 窝均健仔数
    press_data = _query_monthly(
        db,
        indicator_code="prod_healthy_piglets_per_litter",
        source="YONGYI",
        region_code="NATION",
        sub_category="",
        value_type="abs",
    )
    if press_data:
        press = _to_seasonality(press_data)
        press["meta"]["metric_name"] = "压栏系数"
    else:
        press = empty_seasonality("压栏系数")

    return A1SeasonalityResponse(sow_efficiency=sow, pressure_coefficient=press)


# ── A1 供给预测 表格 ────────────────────────────────────────────

@router.get("/a1-supply-forecast-table")
async def get_a1_supply_forecast_table(db: Session = Depends(get_db)):
    """
    A1供给预测表格

    原来从 raw_table JSON 渲染整张 Excel 表格。
    现在改为从 fact_monthly_indicator 查询关键供给指标并组装成表格格式，
    保持前端所需的 header + rows + merged_cells 结构。

    选取的核心指标列：
      月度 | 能繁母猪存栏 | 新生仔猪 | 生猪存栏 | 出栏量 | 分娩窝数 | 窝均健仔数
    """
    # 定义表格列 => (显示名, indicator_code, source, sub_category, value_type, region_code)
    COLUMNS = [
        ("能繁母猪存栏(环比%)", "breeding_sow_inventory", "NYB", "nation", "mom_pct", "NATION"),
        ("新生仔猪(环比%)", "piglet_inventory", "NYB", "nation", "mom_pct", "NATION"),
        ("生猪存栏(环比%)", "hog_inventory", "NYB", "nation", "mom_pct", "NATION"),
        ("出栏(环比%)", "hog_turnover", "NYB", "nation", "mom_pct", "NATION"),
        ("分娩窝数", "prod_farrowing_count", "YONGYI", "", "abs", "NATION"),
        ("窝均健仔数", "prod_healthy_piglets_per_litter", "YONGYI", "", "abs", "NATION"),
    ]

    # 收集所有月份
    all_months: set = set()
    col_data: Dict[str, Dict[str, float]] = {}  # col_name -> {month_str -> value}

    for col_name, code, source, sub_cat, vtype, region in COLUMNS:
        data_points = _query_monthly(
            db,
            indicator_code=code,
            source=source,
            region_code=region,
            sub_category=sub_cat,
            value_type=vtype,
        )
        col_map: Dict[str, float] = {}
        for dp in data_points:
            col_map[dp.date] = dp.value
            all_months.add(dp.date)
        col_data[col_name] = col_map

    # 排序月份
    sorted_months = sorted(all_months)

    # 构建表头
    header_row_0 = ["月度"] + [c[0] for c in COLUMNS]
    header_row_1 = []  # 无子表头

    # 构建数据行
    rows = []
    for m in sorted_months:
        row = [m]
        for col_name, *_ in COLUMNS:
            v = col_data.get(col_name, {}).get(m)
            row.append(f"{v:.1f}" if v is not None else "")
        rows.append(row)

    return {
        "header_row_0": header_row_0,
        "header_row_1": header_row_1,
        "header_row_2": [],
        "rows": rows,
        "column_count": len(header_row_0),
        "merged_cells_json": [],
    }
