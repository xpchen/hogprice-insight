"""
规模场数据汇总 API  (v3 — fact tables)

查询 hogprice_v3 的 fact_monthly_indicator / fact_weekly_indicator。

端点                                              数据源（均为 fact 表）
──────────────────────────────────────────────────────────────
/sow-efficiency                                   月度-生产指标（分娩窝数）
/pressure-coefficient                             月度-生产指标（窝均健仔数-全国）
/yongyi-production-indicators                     月度-生产指标（多区域窝均健仔数）
/yongyi-production-seasonality                    月度-生产指标2（五指标季节性）
/a1-sow-efficiency-pressure-seasonality           A1供给预测 F/N（母猪效能+压栏系数）
/a1-supply-forecast-table                         fact_monthly_indicator 组装 7 列表格
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
            s = dp.date[:10] if isinstance(dp.date, str) and len(dp.date) >= 10 else str(dp.date)
            d = datetime.strptime(s, "%Y-%m-%d").date()
            if d.year < 2010:
                continue
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
    数据源: fact_monthly_indicator，月度-生产指标2 对应 indicator_code (source=YONGYI)
    五指标：窝均健仔数、产房存活率、配种分娩率、断奶成活率、育肥出栏成活率
    当仅导入 2、【生猪产业数据】.xlsx 未导入涌益周度时，窝均健仔数回退为 A1 压栏系数，以便图表有数可显。
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
        # 窝均健仔数：无涌益数据时用 A1 压栏系数（同口径）回退
        if not data_points and display_name == "窝均健仔数":
            data_points = _query_monthly(
                db,
                indicator_code="prod_healthy_piglets_per_litter",
                source="A1",
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
    母猪效能 + 压栏系数 季节性，数据源优先级：
      1）A1供给预测（2、【生猪产业数据】.xlsx）F列=母猪效能、N列=压栏系数 → source=A1
      2）若无 A1 数据则回退：涌益 月度-生产指标 → source=YONGYI
    """
    empty_seasonality = lambda name: {
        "x_values": [f"{m}月" for m in range(1, 13)],
        "series": [],
        "meta": {"unit": "", "freq": "M", "metric_name": name},
    }

    # 母猪效能：优先 A1（F列），无则 YONGYI
    sow_data = _query_monthly(
        db,
        indicator_code="prod_farrowing_count",
        source="A1",
        region_code="NATION",
        sub_category="",
        value_type="abs",
    )
    if not sow_data:
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

    # 压栏系数：优先 A1（N列），无则 YONGYI
    press_data = _query_monthly(
        db,
        indicator_code="prod_healthy_piglets_per_litter",
        source="A1",
        region_code="NATION",
        sub_category="",
        value_type="abs",
    )
    if not press_data:
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


# ── A1 供给预测 表格（仅用 fact 数据）────────────────────────────────

@router.get("/a1-supply-forecast-table")
async def get_a1_supply_forecast_table(db: Session = Depends(get_db)):
    """
    规模场数据汇总表格：数据全部来自 2、【生猪产业数据】.xlsx（NYB、A1供给预测、定点屠宰 等 sheet）。
    多列头：第 1 行「规模场供给预测」合并 17 列、「定点屠宰」合并 3 列；第 2 行为各列名；第 3 行为 环比/同比 等。
    """
    # 数据仅来自 2、【生猪产业数据】.xlsx：NYB、A1、STATISTICS_BUREAU(定点屠宰 sheet)，不用 YONGYI
    # 列：(显示名, indicator_code, sources [(source, sub_category, value_type)], 格式化)
    COLUMNS = [
        ("能繁存栏", "breeding_sow_inventory", [("A1", "", "abs")], "abs"),
        ("能繁环比", "breeding_sow_inventory", [("A1", "", "mom_pct"), ("NYB", "nation", "mom_pct")], "pct"),
        ("能繁同比", "breeding_sow_inventory", [("A1", "", "yoy_pct")], "pct"),
        ("母猪效能", "prod_farrowing_count", [("A1", "", "abs")], "abs"),
        ("新生仔猪", "piglet_inventory", [("A1", "", "abs")], "abs"),
        ("新生仔猪环比", "piglet_inventory", [("A1", "", "mom_pct"), ("NYB", "nation", "mom_pct")], "pct"),
        ("新生仔猪同比", "piglet_inventory", [("A1", "", "yoy_pct")], "pct"),
        ("5月大猪", "medium_large_hog", [("A1", "", "abs")], "abs"),
        ("5月大猪环比", "medium_large_hog", [("NYB", "nation", "mom_pct"), ("A1", "", "mom_pct")], "pct"),
        ("5月大猪同比", "medium_large_hog", [("A1", "", "yoy_pct")], "pct"),
        ("残差率", "supply_residual_rate", [("A1", "", "pct")], "pct"),
        ("生猪出栏", "hog_turnover", [("A1", "", "abs")], "abs"),
        ("生猪出栏环比", "hog_turnover", [("NYB", "nation", "mom_pct"), ("A1", "", "mom_pct")], "pct"),
        ("生猪出栏同比", "hog_turnover", [("A1", "", "yoy_pct")], "pct"),
        ("累计出栏", "hog_turnover", [("A1", "cumulative", "abs")], "abs"),
        ("累同", "hog_turnover", [("A1", "cumulative", "yoy_pct")], "pct"),
        # 定点屠宰：A1 供给预测 AC/AD/AE（如 2020/1 为 1509.34），无则 定点屠宰 sheet
        ("定点屠宰", "designated_slaughter", [("A1", "", "abs"), ("STATISTICS_BUREAU", "", "abs")], "abs"),
        ("定点屠宰环比", "designated_slaughter", [("A1", "", "mom_pct")], "pct"),
        ("定点屠宰同比", "designated_slaughter", [("A1", "", "yoy_pct")], "pct"),
    ]
    all_months: set = set()
    col_data: Dict[str, Dict[str, float]] = {}

    for col_name, code, sources, _fmt in COLUMNS:
        col_map: Dict[str, float] = {}
        if code and sources:
            for source, sub_cat, vtype in sources:
                data_points = _query_monthly(
                    db,
                    indicator_code=code,
                    source=source,
                    region_code="NATION",
                    sub_category=sub_cat,
                    value_type=vtype,
                )
                for dp in data_points:
                    # 定点屠宰等列优先用 A1：已有日期的不再被后续 source 覆盖
                    if dp.date not in col_map:
                        col_map[dp.date] = dp.value
                    all_months.add(dp.date)
        col_data[col_name] = col_map

    sorted_months = sorted(all_months)
    n_data_cols = len(COLUMNS)  # 19
    # 多列头：第 1 行 月度 | 规模场供给预测(合并 16 列) | 定点屠宰(合并 3 列)，共 1+16+3=20 列
    header_row_0 = ["月度"] + ["规模场供给预测"] + [""] * 15 + ["定点屠宰"] + ["", ""]
    # 第 2 行：各列名
    header_row_1 = ["月度"] + [c[0] for c in COLUMNS]
    # 第 3 行：环比/同比等
    header_row_2 = [
        "", "", "环比", "同比", "", "", "环比", "同比", "", "环比", "同比", "",
        "", "环比", "同比", "", "", "", "环比", "同比",
    ]
    # 合并单元格（1-based）：第 1 行 第 2～17 列「规模场供给预测」，第 18～20 列「定点屠宰」
    merged_cells_json = [
        {"min_row": 1, "max_row": 1, "min_col": 2, "max_col": 17},
        {"min_row": 1, "max_row": 1, "min_col": 18, "max_col": 20},
    ]
    rows = []
    for m in sorted_months:
        row: List[Any] = [m]
        for col_name, _code, _sources, fmt in COLUMNS:
            v = col_data.get(col_name, {}).get(m)
            if v is None:
                row.append("")
            elif fmt == "pct":
                row.append(f"{v:.1f}")
            else:
                row.append(f"{v:.2f}" if abs(v) < 1000 else f"{v:.0f}")
        rows.append(row)

    return {
        "header_row_0": header_row_0,
        "header_row_1": header_row_1,
        "header_row_2": header_row_2,
        "rows": rows,
        "column_count": 1 + n_data_cols,
        "merged_cells_json": merged_cells_json,
    }
