"""
规模场数据汇总 API
包含：母猪效能（F列）、压栏系数（N列）、涌益生产指标
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel
import json
import math

from app.core.database import get_db
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

router = APIRouter(prefix="/api/v1/production-indicators", tags=["production-indicators"])


class ProductionDataPoint(BaseModel):
    """生产指标数据点"""
    date: str  # 日期 YYYY-MM-DD
    value: Optional[float] = None


class ProductionIndicatorResponse(BaseModel):
    """生产指标响应"""
    data: List[ProductionDataPoint]
    indicator_name: str  # 指标名称
    latest_date: Optional[str] = None


class ProductionIndicatorsResponse(BaseModel):
    """多个生产指标响应"""
    indicators: Dict[str, List[ProductionDataPoint]]  # key: 指标名称, value: 数据点列表
    indicator_names: List[str]  # 指标名称列表
    latest_date: Optional[str] = None


def _parse_date(value: any) -> Optional[date]:
    """解析日期"""
    if isinstance(value, date):
        return value
    elif isinstance(value, datetime):
        return value.date()
    elif isinstance(value, str):
        try:
            # 处理 ISO 格式
            if 'T' in value:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
            # 处理 YYYY-MM-DD
            return datetime.strptime(value, '%Y-%m-%d').date()
        except:
            pass
    return None


def _get_raw_table_data(db: Session, sheet_name: str, filename_pattern: str = None) -> Optional[List[List]]:
    """获取raw_table数据"""
    result = _get_raw_table_with_meta(db, sheet_name, filename_pattern)
    return result[0] if result else None


def _get_raw_table_with_meta(db: Session, sheet_name: str, filename_pattern: str = None) -> Optional[tuple]:
    """获取raw_table数据及merged_cells_json，返回 (table_data, merged_cells_json)"""
    query = db.query(RawSheet).join(RawFile).filter(RawSheet.sheet_name == sheet_name)
    if filename_pattern:
        query = query.filter(RawFile.filename.like(f'%{filename_pattern}%'))
    sheet = query.first()
    if not sheet:
        return None
    raw_table = db.query(RawTable).filter(RawTable.raw_sheet_id == sheet.id).first()
    if not raw_table:
        return None
    table_data = raw_table.table_json
    if isinstance(table_data, str):
        table_data = json.loads(table_data)
    merged = raw_table.merged_cells_json
    if isinstance(merged, str):
        merged = json.loads(merged) if merged else []
    return (table_data, merged or [])


@router.get("/sow-efficiency", response_model=ProductionIndicatorResponse)
async def get_sow_efficiency(db: Session = Depends(get_db)):
    """
    获取母猪效能数据（F列：分娩窝数）
    """
    table_data = _get_raw_table_data(db, "月度-生产指标（2021.5.7新增）")
    
    if not table_data or len(table_data) < 3:
        return ProductionIndicatorResponse(
            data=[],
            indicator_name="分娩窝数",
            latest_date=None
        )
    
    data_points = []
    
    # F列是第6列（索引5）
    for row_idx, row in enumerate(table_data):
        if row_idx < 2:  # 跳过表头
            continue
        
        if len(row) > 5:
            date_val = row[0] if len(row) > 0 else None
            f_val = row[5] if len(row) > 5 else None
            
            if date_val and f_val is not None and f_val != "":
                parsed_date = _parse_date(date_val)
                if parsed_date:
                    try:
                        value = float(f_val)
                        if not math.isnan(value) and not math.isinf(value):
                            data_points.append(ProductionDataPoint(
                                date=parsed_date.isoformat(),
                                value=round(value, 2)
                            ))
                    except:
                        pass
    
    # 按日期排序
    data_points.sort(key=lambda x: x.date)
    
    latest_date = data_points[-1].date if data_points else None
    
    return ProductionIndicatorResponse(
        data=data_points,
        indicator_name="分娩窝数",
        latest_date=latest_date
    )


@router.get("/pressure-coefficient", response_model=ProductionIndicatorResponse)
async def get_pressure_coefficient(db: Session = Depends(get_db)):
    """
    获取压栏系数数据（N列：窝均健仔数-河南）
    """
    table_data = _get_raw_table_data(db, "月度-生产指标（2021.5.7新增）")
    
    if not table_data or len(table_data) < 3:
        return ProductionIndicatorResponse(
            data=[],
            indicator_name="窝均健仔数（河南）",
            latest_date=None
        )
    
    data_points = []
    
    # N列是第14列（索引13）
    for row_idx, row in enumerate(table_data):
        if row_idx < 2:  # 跳过表头
            continue
        
        if len(row) > 13:
            date_val = row[0] if len(row) > 0 else None
            n_val = row[13] if len(row) > 13 else None
            
            if date_val and n_val is not None and n_val != "":
                parsed_date = _parse_date(date_val)
                if parsed_date:
                    try:
                        value = float(n_val)
                        if not math.isnan(value) and not math.isinf(value):
                            data_points.append(ProductionDataPoint(
                                date=parsed_date.isoformat(),
                                value=round(value, 2)
                            ))
                    except:
                        pass
    
    # 按日期排序
    data_points.sort(key=lambda x: x.date)
    
    latest_date = data_points[-1].date if data_points else None
    
    return ProductionIndicatorResponse(
        data=data_points,
        indicator_name="窝均健仔数（河南）",
        latest_date=latest_date
    )


class YongyiProductionSeasonalityResponse(BaseModel):
    """涌益生产指标季节性数据（月度-生产指标2，F:J 列五指标）"""
    indicators: Dict[str, Dict[str, Any]]  # key: 指标名称, value: { x_values, series, meta }
    indicator_names: List[str]


@router.get("/yongyi-production-seasonality", response_model=YongyiProductionSeasonalityResponse)
async def get_yongyi_production_seasonality(db: Session = Depends(get_db)):
    """
    涌益生产指标季节性数据
    数据源：《涌益咨询周度数据》- 月度-生产指标2，F:J 列
    五指标：窝均健仔数、产房存活率、配种分娩率、断奶成活率、育肥出栏成活率
    """
    table_data = _get_raw_table_data(db, "月度-生产指标2", "涌益")
    indicator_names = ["窝均健仔数", "产房存活率", "配种分娩率", "断奶成活率", "育肥出栏成活率"]
    # 月度-生产指标2：row0=生产指标, row1=日期+列名, data from row2; 日期=col0, F:J=col5-9
    date_col = 0
    col_mapping = {name: 5 + i for i, name in enumerate(indicator_names)}
    empty_result = {
        "x_values": [f"{m}月" for m in range(1, 13)],
        "series": [],
        "meta": {"unit": "", "freq": "M", "metric_name": ""},
    }
    if not table_data or len(table_data) < 3:
        return YongyiProductionSeasonalityResponse(
            indicators={name: {**empty_result, "meta": {**empty_result["meta"], "metric_name": name}} for name in indicator_names},
            indicator_names=indicator_names,
        )
    data_start = 2
    result = {}
    for name, value_col in col_mapping.items():
        seasonality = _extract_a1_column_seasonality(table_data, date_col, value_col, data_start)
        seasonality["meta"]["metric_name"] = name
        if name == "产房存活率" or name == "配种分娩率" or name == "断奶成活率" or name == "育肥出栏成活率":
            seasonality["meta"]["unit"] = "ratio"
        result[name] = seasonality
    return YongyiProductionSeasonalityResponse(indicators=result, indicator_names=indicator_names)


@router.get("/yongyi-production-indicators", response_model=ProductionIndicatorsResponse)
async def get_yongyi_production_indicators(db: Session = Depends(get_db)):
    """
    获取涌益生产指标数据（旧接口，保留兼容）
    返回5个省份的窝均健仔数：辽宁(J列)、广东(L列)、河南(N列)、湖南(P列)、四川(R列)
    """
    table_data = _get_raw_table_data(db, "月度-生产指标（2021.5.7新增）")
    
    if not table_data or len(table_data) < 3:
        return ProductionIndicatorsResponse(
            indicators={},
            indicator_names=[],
            latest_date=None
        )
    
    # 列映射：省份 -> 列索引
    # J列（索引9）：辽宁，L列（索引11）：广东，N列（索引13）：河南，P列（索引15）：湖南，R列（索引17）：四川
    column_mapping = {
        "辽宁": 9,
        "广东": 11,
        "河南": 13,
        "湖南": 15,
        "四川": 17
    }
    
    indicators_data = {name: [] for name in column_mapping.keys()}
    
    for row_idx, row in enumerate(table_data):
        if row_idx < 2:  # 跳过表头
            continue
        
        date_val = row[0] if len(row) > 0 else None
        if not date_val:
            continue
        
        parsed_date = _parse_date(date_val)
        if not parsed_date:
            continue
        
        for province_name, col_idx in column_mapping.items():
            if len(row) > col_idx:
                value = row[col_idx]
                if value is not None and value != "":
                    try:
                        float_val = float(value)
                        if not math.isnan(float_val) and not math.isinf(float_val):
                            indicators_data[province_name].append(ProductionDataPoint(
                                date=parsed_date.isoformat(),
                                value=round(float_val, 2)
                            ))
                    except:
                        pass
    
    # 按日期排序
    for province_name in indicators_data:
        indicators_data[province_name].sort(key=lambda x: x.date)
    
    # 获取最新日期
    all_dates = []
    for data_list in indicators_data.values():
        if data_list:
            all_dates.extend([d.date for d in data_list])
    
    latest_date = max(all_dates) if all_dates else None
    
    return ProductionIndicatorsResponse(
        indicators={name: data_list for name, data_list in indicators_data.items()},
        indicator_names=list(column_mapping.keys()),
        latest_date=latest_date
    )


def _format_a1_cell(val) -> str:
    """A1 表格单元格格式化：日期 -> yyyy-MM-dd，数字 -> 保留 1 位小数，空 -> 空字符串"""
    if val is None or val == "":
        return ""
    if isinstance(val, (int, float)):
        if not isinstance(val, bool):
            return f"{float(val):.1f}"
        return str(val)
    if hasattr(val, "isoformat"):
        return val.strftime("%Y-%m-%d") if hasattr(val, "strftime") else str(val)[:10]
    s = str(val).strip()
    if not s:
        return ""
    # 日期字符串如 2017-01-01 或 2017-01-01T00:00:00
    if s[:4].isdigit() and "-" in s:
        return s.split("T")[0][:10]
    return s


def _is_a1_row_valid(row: list, max_col: int) -> bool:
    """过滤无效行：整行空或月度列（索引 1）为空且无其他有效数据则视为无效"""
    if not row:
        return False
    padded = (row + [""] * max_col)[:max_col]
    non_empty = sum(1 for c in padded if c is not None and str(c).strip() != "")
    if non_empty == 0:
        return False
    # 月度在 B 列（索引 1），若存在则更可能是有效数据行
    return True


def _is_a1_header_row_2(row: list) -> bool:
    """判断是否为第三行表头（含环比/同比等子表头）"""
    if not row or len(row) < 3:
        return False
    row_str = " ".join(str(c or "").strip() for c in row[:50])
    return "环比" in row_str or "同比" in row_str


class A1SeasonalityResponse(BaseModel):
    """A1 表格 F/N 列季节性数据（母猪效能、压栏系数）"""
    sow_efficiency: Dict  # { x_values, series, meta }
    pressure_coefficient: Dict  # { x_values, series, meta }


def _extract_a1_column_seasonality(table_data: list, date_col: int, value_col: int, data_start: int) -> Dict[str, Any]:
    """从 A1 表格提取指定列，转为季节性格式（按年月分组，多年叠线）"""
    # 收集 (year, month) -> value
    by_year_month: Dict[tuple, float] = {}
    for row_idx in range(data_start, len(table_data)):
        row = table_data[row_idx] if row_idx < len(table_data) else []
        if len(row) <= max(date_col, value_col):
            continue
        date_val = row[date_col] if date_col < len(row) else None
        val = row[value_col] if value_col < len(row) else None
        if not date_val or val is None or val == "":
            continue
        parsed = _parse_date(date_val)
        if not parsed:
            continue
        try:
            fv = float(val)
            if math.isnan(fv) or math.isinf(fv):
                continue
            by_year_month[(parsed.year, parsed.month)] = round(fv, 2)
        except (ValueError, TypeError):
            continue
    # 按年分组，构建 series（x 轴用 "1月".."12月"）
    years = sorted({y for y, _ in by_year_month.keys()})
    x_values = [f"{m}月" for m in range(1, 13)]
    series = []
    for year in years:
        values = [by_year_month.get((year, m)) for m in range(1, 13)]
        series.append({"year": year, "values": values})
    return {"x_values": x_values, "series": series, "meta": {"unit": "", "freq": "M", "metric_name": ""}}


@router.get("/a1-sow-efficiency-pressure-seasonality", response_model=A1SeasonalityResponse)
async def get_a1_sow_efficiency_pressure_seasonality(db: Session = Depends(get_db)):
    """
    从 A1供给预测 表格 F 列（母猪效能）、N 列（压栏系数）提取数据，返回季节性格式。
    数据源：2、【生猪产业数据】.xlsx - A1供给预测
    """
    result = _get_raw_table_with_meta(db, "A1供给预测", "2、【生猪产业数据】")
    if not result or len(result[0]) < 2:
        return A1SeasonalityResponse(
            sow_efficiency={"x_values": [f"{m}月" for m in range(1, 13)], "series": [], "meta": {"unit": "", "freq": "M", "metric_name": "母猪效能"}},
            pressure_coefficient={"x_values": [f"{m}月" for m in range(1, 13)], "series": [], "meta": {"unit": "", "freq": "M", "metric_name": "压栏系数"}},
        )
    table_data, _ = result
    max_col = max(len(r) for r in table_data) if table_data else 0
    data_start = 2
    row2 = list(table_data[2]) if len(table_data) > 2 and table_data[2] else []
    if len(table_data) >= 3 and _is_a1_header_row_2(row2):
        data_start = 3
    # B 列(索引1)=月度, F 列(索引5)=母猪效能, N 列(索引13)=压栏系数
    date_col, f_col, n_col = 1, 5, 13
    if max_col <= n_col:
        return A1SeasonalityResponse(
            sow_efficiency={"x_values": [f"{m}月" for m in range(1, 13)], "series": [], "meta": {"unit": "", "freq": "M", "metric_name": "母猪效能"}},
            pressure_coefficient={"x_values": [f"{m}月" for m in range(1, 13)], "series": [], "meta": {"unit": "", "freq": "M", "metric_name": "压栏系数"}},
        )
    sow = _extract_a1_column_seasonality(table_data, date_col, f_col, data_start)
    sow["meta"]["metric_name"] = "母猪效能"
    press = _extract_a1_column_seasonality(table_data, date_col, n_col, data_start)
    press["meta"]["metric_name"] = "压栏系数"
    return A1SeasonalityResponse(sow_efficiency=sow, pressure_coefficient=press)


@router.get("/a1-supply-forecast-table")
async def get_a1_supply_forecast_table(db: Session = Depends(get_db)):
    """
    A1供给预测表格（sheet_name: A1供给预测）
    按 Excel 原样：支持 2～3 行表头、合并单元格、数据行；月度 yyyy-MM-dd，数字 1 位小数。
    """
    result = _get_raw_table_with_meta(db, "A1供给预测", "2、【生猪产业数据】")
    if not result or len(result[0]) < 2:
        return {
            "header_row_0": [],
            "header_row_1": [],
            "header_row_2": [],
            "rows": [],
            "column_count": 0,
            "merged_cells_json": [],
        }
    table_data, merged_cells = result
    max_col = max(len(table_data[0]), len(table_data[1]), *(len(r) for r in table_data[2:]), 1)

    def pad_row(row, length):
        r = list(row) if row else []
        return [r[i] if i < len(r) else "" for i in range(length)]

    # 表头行（排除第1列「天数」）
    SKIP_COL = 1  # A列/天数，1-based
    row0 = pad_row(table_data[0], max_col)
    row1 = pad_row(table_data[1], max_col)
    header_row_0 = [_format_a1_cell(v) or "" for v in row0[SKIP_COL:]]
    header_row_1 = [_format_a1_cell(v) or "" for v in row1[SKIP_COL:]]

    # 判断是否存在第三行表头
    data_start = 2
    header_row_2 = []
    if len(table_data) >= 3:
        row2 = pad_row(table_data[2], max_col)
        if _is_a1_header_row_2(row2):
            header_row_2 = [_format_a1_cell(v) or "" for v in row2[SKIP_COL:]]
            data_start = 3

    rows = []
    for row_idx in range(data_start, len(table_data)):
        row = pad_row(table_data[row_idx], max_col)
        if not _is_a1_row_valid(row, max_col):
            continue
        rows.append([_format_a1_cell(v) for v in row[SKIP_COL:]])

    # 合并单元格：排除第1列（天数），列索引整体左移（1-based）
    new_merged = []
    for m in (merged_cells or []):
        mc, mx = (m.get("min_col") or 1), (m.get("max_col") or 1)
        if mx < SKIP_COL:
            continue
        new_min = 1 if mc <= SKIP_COL else mc - SKIP_COL
        new_max = mx - SKIP_COL
        if new_min > new_max:
            continue
        new_merged.append({
            "min_row": m.get("min_row"),
            "max_row": m.get("max_row"),
            "min_col": new_min,
            "max_col": new_max,
        })

    return {
        "header_row_0": header_row_0,
        "header_row_1": header_row_1,
        "header_row_2": header_row_2,
        "rows": rows,
        "column_count": max(0, max_col - SKIP_COL),
        "merged_cells_json": new_merged,
    }
