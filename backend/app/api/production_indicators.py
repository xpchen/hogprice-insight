"""
规模场数据汇总 API
包含：母猪效能（F列）、压栏系数（N列）、涌益生产指标
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
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
    query = db.query(RawSheet).join(RawFile).filter(RawSheet.sheet_name == sheet_name)
    if filename_pattern:
        query = query.filter(RawFile.filename.like(f'%{filename_pattern}%'))
    sheet = query.first()
    
    if not sheet:
        return None
    
    raw_table = db.query(RawTable).filter(
        RawTable.raw_sheet_id == sheet.id
    ).first()
    
    if not raw_table:
        return None
    
    table_data = raw_table.table_json
    if isinstance(table_data, str):
        table_data = json.loads(table_data)
    
    return table_data


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


@router.get("/yongyi-production-indicators", response_model=ProductionIndicatorsResponse)
async def get_yongyi_production_indicators(db: Session = Depends(get_db)):
    """
    获取涌益生产指标数据
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


@router.get("/a1-supply-forecast-table")
async def get_a1_supply_forecast_table(db: Session = Depends(get_db)):
    """
    A1供给预测表格（sheet_name: A1供给预测）
    按 Excel 原样：全表两行表头 + 数据行；月度 yyyy-MM-dd，数字 1 位小数，清理无效行。
    """
    table_data = _get_raw_table_data(db, "A1供给预测", "2、【生猪产业数据】")
    if not table_data or len(table_data) < 2:
        return {
            "header_row_0": [],
            "header_row_1": [],
            "rows": [],
            "column_count": 0,
        }
    max_col = max(len(table_data[0]), len(table_data[1]), *(len(r) for r in table_data[2:]), 1)

    def pad_row(row, length):
        r = list(row) if row else []
        return [r[i] if i < len(r) else "" for i in range(length)]

    row0 = pad_row(table_data[0], max_col)
    row1 = pad_row(table_data[1], max_col)
    header_row_0 = [_format_a1_cell(v) or "" for v in row0]
    header_row_1 = [_format_a1_cell(v) or "" for v in row1]

    rows = []
    for row_idx in range(2, len(table_data)):
        row = pad_row(table_data[row_idx], max_col)
        if not _is_a1_row_valid(row, max_col):
            continue
        rows.append([_format_a1_cell(v) for v in row])

    return {
        "header_row_0": header_row_0,
        "header_row_1": header_row_1,
        "rows": rows,
        "column_count": max_col,
    }
