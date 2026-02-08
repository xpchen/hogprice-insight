"""
E4. 统计局数据汇总 API
包含：
1. 表1：统计局季度数据汇总（B-Y列）
2. 图1：统计局生猪出栏量&屠宰量（季度出栏量J列、定点屠宰量P列、规模化率）
3. 图2：猪肉进口（月度进口量，分国别）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import json
import math

from app.core.database import get_db
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

router = APIRouter(prefix="/api/v1/statistics-bureau", tags=["statistics-bureau"])


class QuarterlyDataRow(BaseModel):
    """季度数据行"""
    period: str  # 季度，如"2024Q1"
    data: Dict[str, Optional[float]]  # B-Y列的数据，键为列名或列索引


class QuarterlyDataResponse(BaseModel):
    """季度数据汇总响应"""
    headers: List[str]  # B-Y列的列名
    data: List[QuarterlyDataRow]


class OutputSlaughterPoint(BaseModel):
    """出栏量&屠宰量数据点"""
    period: str  # 季度，如"2024Q1"
    output_volume: Optional[float] = None  # 季度出栏量（J列）
    slaughter_volume: Optional[float] = None  # 定点屠宰量（P列）
    scale_rate: Optional[float] = None  # 规模化率（屠宰量/出栏量）


class OutputSlaughterResponse(BaseModel):
    """出栏量&屠宰量响应"""
    data: List[OutputSlaughterPoint]
    latest_period: Optional[str] = None


class ImportMeatPoint(BaseModel):
    """猪肉进口数据点"""
    month: str  # 月份 YYYY-MM
    total_volume: Optional[float] = None  # 进口总量（万吨）
    top_country1: Optional[str] = None  # 最大国家1
    top_country1_volume: Optional[float] = None  # 最大国家1进口量
    top_country2: Optional[str] = None  # 最大国家2
    top_country2_volume: Optional[float] = None  # 最大国家2进口量


class ImportMeatResponse(BaseModel):
    """猪肉进口响应"""
    data: List[ImportMeatPoint]
    latest_month: Optional[str] = None


def _get_raw_table_data(db: Session, sheet_name: str) -> Optional[List[List]]:
    """获取raw_table数据"""
    sheet = db.query(RawSheet).join(RawFile).filter(
        RawSheet.sheet_name == sheet_name
    ).first()
    
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


def _parse_excel_date(excel_date: any) -> Optional[date]:
    """解析Excel日期"""
    if isinstance(excel_date, (int, float)):
        try:
            excel_epoch = datetime(1899, 12, 30)
            return (excel_epoch + timedelta(days=int(excel_date))).date()
        except:
            pass
    elif isinstance(excel_date, str):
        try:
            if 'T' in excel_date:
                return datetime.fromisoformat(excel_date.replace('Z', '+00:00')).date()
            return datetime.strptime(excel_date, '%Y-%m-%d').date()
        except:
            pass
    elif isinstance(excel_date, date):
        return excel_date
    elif isinstance(excel_date, datetime):
        return excel_date.date()
    return None


def _parse_quarter(period_str: str) -> Optional[str]:
    """解析季度字符串，返回YYYYQ格式"""
    if not period_str:
        return None
    
    period_str = str(period_str).strip()
    
    # 尝试解析"2024Q1"格式
    if 'Q' in period_str.upper():
        parts = period_str.upper().split('Q')
        if len(parts) == 2:
            try:
                year = int(parts[0])
                quarter = int(parts[1])
                if 1 <= quarter <= 4:
                    return f"{year}Q{quarter}"
            except:
                pass
    
    # 尝试解析"2024年1季度"格式
    if '年' in period_str and '季度' in period_str:
        parts = period_str.split('年')
        if len(parts) == 2:
            try:
                year = int(parts[0])
                quarter_str = parts[1].replace('季度', '').strip()
                quarter = int(quarter_str)
                if 1 <= quarter <= 4:
                    return f"{year}Q{quarter}"
            except:
                pass
    
    return None


@router.get("/quarterly-data", response_model=QuarterlyDataResponse)
def get_quarterly_data(
    db: Session = Depends(get_db)
):
    """
    获取统计局季度数据汇总（表1）
    数据来源：03.统计局季度数据 sheet，B-Y列
    """
    table_data = _get_raw_table_data(db, "03.统计局季度数据")
    
    if not table_data or len(table_data) == 0:
        return QuarterlyDataResponse(headers=[], data=[])
    
    # 假设第一行是表头，B-Y列是索引1-24
    headers = []
    if len(table_data) > 0:
        header_row = table_data[0]
        # B-Y列（索引1-24）
        headers = [str(header_row[i]) if i < len(header_row) else f"列{chr(66+i)}" for i in range(1, 25)]
    
    # 解析数据行
    data_rows = []
    for row_idx, row in enumerate(table_data[1:], start=1):
        if len(row) < 2:
            continue
        
        # 假设A列（索引0）是季度标识
        period_str = str(row[0]) if len(row) > 0 and row[0] else None
        if not period_str:
            continue
        
        period = _parse_quarter(period_str)
        if not period:
            # 如果无法解析季度，尝试使用原始字符串
            period = period_str
        
        # 提取B-Y列数据（索引1-24）
        row_data = {}
        for col_idx in range(1, 25):
            col_letter = chr(65 + col_idx)  # B=66, C=67, ..., Y=89
            if col_idx < len(row):
                value = row[col_idx]
                # 尝试转换为浮点数
                if value is not None and value != "":
                    try:
                        float_val = float(value)
                        if not (math.isnan(float_val) or math.isinf(float_val)):
                            row_data[col_letter] = float_val
                        else:
                            row_data[col_letter] = None
                    except:
                        row_data[col_letter] = None
                else:
                    row_data[col_letter] = None
            else:
                row_data[col_letter] = None
        
        data_rows.append(QuarterlyDataRow(period=period, data=row_data))
    
    return QuarterlyDataResponse(headers=headers, data=data_rows)


@router.get("/output-slaughter", response_model=OutputSlaughterResponse)
def get_output_slaughter(
    db: Session = Depends(get_db)
):
    """
    获取统计局生猪出栏量&屠宰量（图1）
    数据来源：03.统计局季度数据 sheet
    - J列（索引9）：季度出栏量
    - P列（索引15）：定点屠宰量
    - 规模化率 = 屠宰量 / 出栏量
    """
    table_data = _get_raw_table_data(db, "03.统计局季度数据")
    
    if not table_data or len(table_data) == 0:
        return OutputSlaughterResponse(data=[], latest_period=None)
    
    data_points = []
    latest_period = None
    
    for row_idx, row in enumerate(table_data[1:], start=1):
        if len(row) < 16:
            continue
        
        # A列（索引0）是季度标识
        period_str = str(row[0]) if len(row) > 0 and row[0] else None
        if not period_str:
            continue
        
        period = _parse_quarter(period_str)
        if not period:
            period = period_str
        
        # J列（索引9）：季度出栏量
        output_val = row[9] if len(row) > 9 else None
        output_volume = None
        if output_val is not None and output_val != "":
            try:
                output_volume = float(output_val)
                if math.isnan(output_volume) or math.isinf(output_volume):
                    output_volume = None
            except:
                pass
        
        # P列（索引15）：定点屠宰量
        slaughter_val = row[15] if len(row) > 15 else None
        slaughter_volume = None
        if slaughter_val is not None and slaughter_val != "":
            try:
                slaughter_volume = float(slaughter_val)
                if math.isnan(slaughter_volume) or math.isinf(slaughter_volume):
                    slaughter_volume = None
            except:
                pass
        
        # 计算规模化率
        scale_rate = None
        if output_volume is not None and slaughter_volume is not None and output_volume > 0:
            scale_rate = slaughter_volume / output_volume
        
        data_points.append(OutputSlaughterPoint(
            period=period,
            output_volume=output_volume,
            slaughter_volume=slaughter_volume,
            scale_rate=scale_rate
        ))
        
        if period and (not latest_period or period > latest_period):
            latest_period = period
    
    # 按季度排序
    data_points.sort(key=lambda x: x.period)
    
    return OutputSlaughterResponse(data=data_points, latest_period=latest_period)


@router.get("/import-meat", response_model=ImportMeatResponse)
def get_import_meat(
    db: Session = Depends(get_db)
):
    """
    获取猪肉进口数据（图2）
    数据来源：钢联模板 sheet "猪肉进口" 或 涌益周度数据 "进口肉"
    目前使用"进口肉"sheet：
    - M列（索引12）：日期（Excel序列号）
    - N列（索引13）：猪肉(万吨)
    - 需要查找分国别数据（如果存在）
    """
    # 先尝试查找"猪肉进口"sheet（钢联模板）
    table_data = _get_raw_table_data(db, "猪肉进口")
    
    # 如果没找到，尝试"进口肉"sheet（涌益周度数据）
    if not table_data:
        table_data = _get_raw_table_data(db, "进口肉")
    
    if not table_data or len(table_data) < 4:
        return ImportMeatResponse(data=[], latest_month=None)
    
    data_points = []
    latest_month = None
    
    # 分析表头，找出日期列和总量列
    # 从之前的分析看，"进口肉"sheet的结构：
    # - 第3行（索引2）是年份行
    # - 第4行（索引3）是表头行，M列是"日期"，N列是"猪肉(万吨)"，P列是"猪总量(万吨)"
    # - 数据从第5行（索引4）开始
    
    # 查找日期列和总量列
    date_col_idx = None
    total_col_idx = None
    
    if len(table_data) > 3:
        header_row = table_data[3]  # 第4行是表头
        for col_idx, header in enumerate(header_row):
            if header:
                header_str = str(header).strip()
                if "日期" in header_str:
                    date_col_idx = col_idx
                elif "猪总量" in header_str or "总量" in header_str:
                    total_col_idx = col_idx
    
    # 如果没找到，使用默认位置（M列索引12，P列索引15）
    if date_col_idx is None:
        date_col_idx = 12
    if total_col_idx is None:
        total_col_idx = 15
    
    # 解析数据行
    for row_idx in range(4, len(table_data)):
        row = table_data[row_idx]
        
        if len(row) <= max(date_col_idx, total_col_idx):
            continue
        
        # 解析日期
        date_val = row[date_col_idx] if date_col_idx < len(row) else None
        if not date_val:
            continue
        
        obs_date = _parse_excel_date(date_val)
        if not obs_date:
            continue
        
        month_str = obs_date.strftime("%Y-%m")
        
        # 解析总量
        total_val = row[total_col_idx] if total_col_idx < len(row) else None
        total_volume = None
        if total_val is not None and total_val != "":
            try:
                total_volume = float(total_val)
                if math.isnan(total_volume) or math.isinf(total_volume):
                    total_volume = None
            except:
                pass
        
        # TODO: 查找分国别数据
        # 目前"进口肉"sheet中没有分国别数据，需要查找其他sheet或等数据导入
        # 暂时只返回总量
        top_country1 = None
        top_country1_volume = None
        top_country2 = None
        top_country2_volume = None
        
        data_points.append(ImportMeatPoint(
            month=month_str,
            total_volume=total_volume,
            top_country1=top_country1,
            top_country1_volume=top_country1_volume,
            top_country2=top_country2,
            top_country2_volume=top_country2_volume
        ))
        
        if month_str and (not latest_month or month_str > latest_month):
            latest_month = month_str
    
    # 按月份排序
    data_points.sort(key=lambda x: x.month)
    
    return ImportMeatResponse(data=data_points, latest_month=latest_month)
