"""
E4. 统计局数据汇总 API  (v3 — reads from hogprice_v3 fact tables)
包含：
1. 表1：统计局季度数据汇总  → fact_quarterly_stats
2. 图1：统计局生猪出栏量&屠宰量  → fact_quarterly_stats
3. 图2：猪肉进口  → fact_monthly_indicator (pork_import, source=GANGLIAN)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict
from datetime import date
from pydantic import BaseModel
from decimal import Decimal

from app.core.database import get_db

router = APIRouter(prefix="/api/v1/statistics-bureau", tags=["statistics-bureau"])


# ── Pydantic 响应模型 ────────────────────────────────────


class QuarterlyDataRow(BaseModel):
    """季度数据行"""
    period: str  # 季度，如"2024Q1"
    data: Dict[str, Optional[float]]  # 键为 indicator_code，值为数值


class QuarterlyDataResponse(BaseModel):
    """季度数据汇总响应"""
    headers: List[str]  # indicator_code 列表
    data: List[QuarterlyDataRow]


class QuarterlyDataRawResponse(BaseModel):
    """季度数据汇总（结构化多级表头 + 数据行）"""
    header_row_0: List[str]
    header_row_1: List[str]
    rows: List[List]
    column_count: int
    merged_cells_json: List[Dict]


class OutputSlaughterPoint(BaseModel):
    """出栏量&屠宰量数据点"""
    period: str  # 季度，如"2024Q1"
    output_volume: Optional[float] = None  # 季度出栏量（万头）
    slaughter_volume: Optional[float] = None  # 定点屠宰量（万头）
    scale_rate: Optional[float] = None  # 规模化率（屠宰量/出栏量）


class OutputSlaughterResponse(BaseModel):
    """出栏量&屠宰量响应"""
    data: List[OutputSlaughterPoint]
    latest_period: Optional[str] = None


class ImportMeatCountryPoint(BaseModel):
    """国别进口量"""
    country: str
    value: Optional[float] = None


class ImportMeatPoint(BaseModel):
    """猪肉进口数据点"""
    month: str  # 月份 YYYY-MM
    total: Optional[float] = None  # 进口总量（吨）
    top_countries: List[ImportMeatCountryPoint] = []  # 进口量前2的国家


class ImportMeatResponse(BaseModel):
    """猪肉进口响应"""
    data: List[ImportMeatPoint]
    latest_month: Optional[str] = None


# ── Helper ────────────────────────────────────────────────


def _to_float(val) -> Optional[float]:
    """安全地把 Decimal / int / float / None 转为 float"""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _quarter_label(d: date) -> str:
    """date -> '2024Q1' 字符串"""
    q = (d.month - 1) // 3 + 1
    return f"{d.year}Q{q}"


def _fmt_cell(val) -> str:
    """格式化单元格用于 raw 表格返回"""
    if val is None:
        return ""
    f = _to_float(val)
    if f is None:
        return str(val)
    if f == int(f):
        return str(int(f))
    return f"{f:.2f}"


# ── 季度数据指标配置 ──
# 按 Excel 原始列序（B-Y 列），对应 fact_quarterly_stats 中的 indicator_code
# 每条 = (indicator_code, 中文名, 单位)
_QUARTERLY_COLUMNS = [
    # ── B列: 季度（由 quarter_date 生成，不在这里列出） ──
    # ── C-E: 能繁母猪 ──
    ("breeding_sow_inventory", "能繁母猪存栏", "万头"),
    ("breeding_sow_inventory_qoq", "能繁环比", "%"),
    ("breeding_sow_inventory_yoy", "能繁同比", "%"),
    # ── F-I: 生猪存栏 ──
    ("hog_inventory", "生猪存栏", "万头"),
    ("commercial_hog_inventory", "商品猪存栏", "万头"),
    ("hog_inventory_qoq", "生猪环比", "%"),
    ("hog_inventory_yoy", "生猪同比", "%"),
    # ── J-N: 出栏 ──
    ("hog_turnover", "季度出栏", "万头"),
    ("hog_turnover_qoq", "出栏环比", "%"),     # Note: col K is empty in some data
    ("hog_turnover_qoq", "出栏环比", "%"),     # placeholder to keep column alignment
    ("hog_turnover_yoy", "出栏同比", "%"),
    ("hog_turnover_cumulative", "累计出栏", "万头"),
    ("hog_turnover_cumulative_yoy", "累计出栏同比", "%"),
    # ── O-S: 定点屠宰 ──
    ("designated_slaughter", "定点屠宰量", "万头"),
    ("designated_slaughter_yoy", "定点屠宰同比", "%"),
    (None, "", ""),  # placeholder for empty columns
    (None, "", ""),
    (None, "", ""),
    # ── T-V: 猪肉产量 ──
    ("pork_production", "猪肉产量", "万吨"),
    ("pork_production_yoy", "猪肉产量同比", "%"),
    (None, "", ""),
    (None, "", ""),
    # ── W-Y: 猪肉进口 ──
    ("pork_import", "猪肉进口", "万吨"),
    ("pork_import_yoy", "猪肉进口同比", "%"),
]

# unique indicator_codes actually stored (for SQL IN clause)
_QUARTERLY_INDICATOR_CODES = sorted({
    code for code, _, _ in _QUARTERLY_COLUMNS if code
})


# ── Endpoints ─────────────────────────────────────────────


@router.get("/quarterly-data", response_model=QuarterlyDataRawResponse)
def get_quarterly_data(
    db: Session = Depends(get_db),
):
    """
    获取统计局季度数据汇总（表1）
    以结构化表头 + 数据行返回，兼容前端原有的 raw 格式。
    数据来源：fact_quarterly_stats (region_code='NATION')
    """
    # 1. 查询所有全国级季度数据
    sql = text("""
        SELECT quarter_date, indicator_code, value
        FROM fact_quarterly_stats
        WHERE region_code = 'NATION'
        ORDER BY quarter_date, indicator_code
    """)
    rows = db.execute(sql).fetchall()

    if not rows:
        return QuarterlyDataRawResponse(
            header_row_0=[], header_row_1=[], rows=[],
            column_count=0, merged_cells_json=[],
        )

    # 2. 按季度分组：{quarter_date: {indicator_code: value}}
    quarter_map: Dict[date, Dict[str, Optional[float]]] = {}
    for r in rows:
        qd = r[0]  # quarter_date
        ic = r[1]  # indicator_code
        v = _to_float(r[2])
        quarter_map.setdefault(qd, {})[ic] = v

    # 3. 构建表头
    # header_row_0: 大类标题（模拟原 Excel 合并单元格）
    # header_row_1: 每列具体指标名
    header_row_0 = ["", "季度",
                     "能繁母猪", "", "",
                     "生猪存栏", "", "", "",
                     "出栏", "", "", "", "", "",
                     "定点屠宰", "", "", "", "",
                     "猪肉产量", "", "", "",
                     "猪肉进口", ""]
    header_row_1 = ["", "季度"] + [name for _, name, _ in _QUARTERLY_COLUMNS]
    col_count = len(header_row_1)

    # 4. 构建数据行（与 _QUARTERLY_COLUMNS 对齐）
    data_rows = []
    for qd in sorted(quarter_map.keys()):
        period = _quarter_label(qd)
        indicator_vals = quarter_map[qd]
        row: list = ["", period]
        for code, _, _ in _QUARTERLY_COLUMNS:
            if code is None:
                row.append("")
            else:
                row.append(_fmt_cell(indicator_vals.get(code)))
        data_rows.append(row)

    # 5. merged_cells 描述（简化版：只描述 header_row_0 的跨列合并）
    merged_cells = [
        {"min_row": 1, "min_col": 3, "max_row": 1, "max_col": 5},   # 能繁母猪
        {"min_row": 1, "min_col": 6, "max_row": 1, "max_col": 9},   # 生猪存栏
        {"min_row": 1, "min_col": 10, "max_row": 1, "max_col": 15}, # 出栏
        {"min_row": 1, "min_col": 16, "max_row": 1, "max_col": 20}, # 定点屠宰
        {"min_row": 1, "min_col": 21, "max_row": 1, "max_col": 24}, # 猪肉产量
        {"min_row": 1, "min_col": 25, "max_row": 1, "max_col": 26}, # 猪肉进口
    ]

    # pad headers to same length
    header_row_0 = (header_row_0 + [""] * col_count)[:col_count]
    header_row_1 = (header_row_1 + [""] * col_count)[:col_count]
    data_rows = [r[:col_count] + [""] * max(0, col_count - len(r)) for r in data_rows]

    return QuarterlyDataRawResponse(
        header_row_0=header_row_0,
        header_row_1=header_row_1,
        rows=data_rows,
        column_count=col_count,
        merged_cells_json=merged_cells,
    )


@router.get("/output-slaughter", response_model=OutputSlaughterResponse)
def get_output_slaughter(
    db: Session = Depends(get_db),
):
    """
    获取统计局生猪出栏量&屠宰量（图1）
    - 季度出栏量: indicator_code = 'hog_turnover'
    - 定点屠宰量: indicator_code = 'designated_slaughter'
    - 规模化率 = 屠宰量 / 出栏量
    数据来源：fact_quarterly_stats (region_code='NATION')
    """
    sql = text("""
        SELECT quarter_date, indicator_code, value
        FROM fact_quarterly_stats
        WHERE region_code = 'NATION'
          AND indicator_code IN ('hog_turnover', 'designated_slaughter')
        ORDER BY quarter_date
    """)
    rows = db.execute(sql).fetchall()

    if not rows:
        return OutputSlaughterResponse(data=[], latest_period=None)

    # 按季度分组
    quarter_map: Dict[date, Dict[str, Optional[float]]] = {}
    for r in rows:
        qd = r[0]
        ic = r[1]
        v = _to_float(r[2])
        quarter_map.setdefault(qd, {})[ic] = v

    data_points = []
    latest_period = None

    for qd in sorted(quarter_map.keys()):
        period = _quarter_label(qd)
        vals = quarter_map[qd]
        output_volume = vals.get("hog_turnover")
        slaughter_volume = vals.get("designated_slaughter")

        scale_rate = None
        if output_volume and slaughter_volume and output_volume > 0:
            scale_rate = round(slaughter_volume / output_volume, 4)

        data_points.append(OutputSlaughterPoint(
            period=period,
            output_volume=output_volume,
            slaughter_volume=slaughter_volume,
            scale_rate=scale_rate,
        ))
        latest_period = period

    return OutputSlaughterResponse(data=data_points, latest_period=latest_period)


@router.get("/import-meat", response_model=ImportMeatResponse)
def get_import_meat(
    db: Session = Depends(get_db),
):
    """
    获取猪肉进口数据（图2）
    优先从 fact_monthly_indicator 读取按国别的月度进口量 (indicator_code='pork_import', source='GANGLIAN')
    回退：从 fact_quarterly_stats 读取季度猪肉进口总量 (indicator_code='pork_import')
    返回：每月进口总量 + 进口量前2的国家
    """
    # ── 策略1: 从 fact_monthly_indicator 读取月度分国别数据 ──
    sql_monthly = text("""
        SELECT month_date, sub_category, value
        FROM fact_monthly_indicator
        WHERE indicator_code = 'pork_import'
          AND region_code = 'NATION'
          AND value_type = 'abs'
          AND source = 'GANGLIAN'
        ORDER BY month_date, sub_category
    """)
    monthly_rows = db.execute(sql_monthly).fetchall()

    if monthly_rows:
        # 按月份分组: {month_str: [(country, value), ...]}
        month_map: Dict[str, list] = {}
        for r in monthly_rows:
            md: date = r[0]
            country: str = r[1] or ""
            val = _to_float(r[2])
            if val is None or val <= 0:
                continue
            month_str = md.strftime("%Y-%m")
            month_map.setdefault(month_str, []).append((country, val))

        if month_map:
            data_points = []
            for month_str in sorted(month_map.keys()):
                entries = month_map[month_str]

                # 总量: 如果有 "全球" sub_category 则直接取，否则求和
                total = None
                country_entries = []
                for country, val in entries:
                    if country in ("全球", "total", ""):
                        total = val
                    else:
                        country_entries.append((country, val))

                if total is None and country_entries:
                    total = sum(v for _, v in country_entries)

                # top 2 国家
                top2 = sorted(country_entries, key=lambda x: -x[1])[:2]

                data_points.append(ImportMeatPoint(
                    month=month_str,
                    total=round(total, 2) if total else None,
                    top_countries=[
                        ImportMeatCountryPoint(country=c, value=round(v, 2))
                        for c, v in top2
                    ],
                ))

            latest_month = data_points[-1].month if data_points else None
            return ImportMeatResponse(data=data_points, latest_month=latest_month)

    # ── 策略2: 从 fact_monthly_indicator 不限 source 读取 ──
    sql_monthly_any = text("""
        SELECT month_date, sub_category, source, value
        FROM fact_monthly_indicator
        WHERE indicator_code = 'pork_import'
          AND region_code = 'NATION'
          AND value_type = 'abs'
        ORDER BY month_date, sub_category
    """)
    monthly_any_rows = db.execute(sql_monthly_any).fetchall()

    if monthly_any_rows:
        month_map2: Dict[str, list] = {}
        for r in monthly_any_rows:
            md: date = r[0]
            country: str = r[1] or ""
            val = _to_float(r[3])
            if val is None or val <= 0:
                continue
            month_str = md.strftime("%Y-%m")
            month_map2.setdefault(month_str, []).append((country, val))

        if month_map2:
            data_points = []
            for month_str in sorted(month_map2.keys()):
                entries = month_map2[month_str]
                total = None
                country_entries = []
                for country, val in entries:
                    if country in ("全球", "total", "", "pork_only"):
                        total = val
                    else:
                        country_entries.append((country, val))

                if total is None and country_entries:
                    total = sum(v for _, v in country_entries)

                top2 = sorted(country_entries, key=lambda x: -x[1])[:2]

                data_points.append(ImportMeatPoint(
                    month=month_str,
                    total=round(total, 2) if total else None,
                    top_countries=[
                        ImportMeatCountryPoint(country=c, value=round(v, 2))
                        for c, v in top2
                    ],
                ))

            latest_month = data_points[-1].month if data_points else None
            return ImportMeatResponse(data=data_points, latest_month=latest_month)

    # ── 策略3: 从 fact_quarterly_stats 季度猪肉进口回退 ──
    sql_quarterly = text("""
        SELECT quarter_date, value
        FROM fact_quarterly_stats
        WHERE indicator_code = 'pork_import'
          AND region_code = 'NATION'
          AND value IS NOT NULL
        ORDER BY quarter_date
    """)
    quarterly_rows = db.execute(sql_quarterly).fetchall()

    if quarterly_rows:
        data_points = []
        for r in quarterly_rows:
            qd: date = r[0]
            val = _to_float(r[1])
            if val is None or val <= 0:
                continue
            # 用季度首月代表该季度
            q = (qd.month - 1) // 3 + 1
            month_num = (q - 1) * 3 + 1
            month_str = f"{qd.year}-{month_num:02d}"
            data_points.append(ImportMeatPoint(
                month=month_str,
                total=round(val, 2),
                top_countries=[],
            ))

        latest_month = data_points[-1].month if data_points else None
        return ImportMeatResponse(data=data_points, latest_month=latest_month)

    return ImportMeatResponse(data=[], latest_month=None)
