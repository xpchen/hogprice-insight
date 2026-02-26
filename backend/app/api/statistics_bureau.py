"""
E4. 统计局数据汇总 API
包含：
1. 表1：统计局季度数据汇总（B-Y列）
2. 图1：统计局生猪出栏量&屠宰量（季度出栏量J列、定点屠宰量P列、规模化率）
3. 图2：猪肉进口（实际是钢联全国猪价的月度均值/历年平均值系数）
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
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation
from sqlalchemy import func, or_

router = APIRouter(prefix="/api/v1/statistics-bureau", tags=["statistics-bureau"])


class QuarterlyDataRow(BaseModel):
    """季度数据行"""
    period: str  # 季度，如"2024Q1"
    data: Dict[str, Optional[float]]  # B-Y列的数据，键为列名或列索引


class QuarterlyDataResponse(BaseModel):
    """季度数据汇总响应"""
    headers: List[str]  # B-Y列的列名
    data: List[QuarterlyDataRow]


class QuarterlyDataRawResponse(BaseModel):
    """季度数据汇总（按 Excel 原样，多级表头 + 合并单元格）"""
    header_row_0: List[str]
    header_row_1: List[str]
    rows: List[List]
    column_count: int
    merged_cells_json: List[Dict]


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
    """猪肉进口数据点（实际是猪价系数）"""
    month: str  # 月份 YYYY-MM
    price_coefficient: Optional[float] = None  # 猪价系数（月度均值/历年平均值）


class ImportMeatResponse(BaseModel):
    """猪肉进口响应（实际是猪价系数响应）"""
    data: List[ImportMeatPoint]
    latest_month: Optional[str] = None


def _get_raw_table_data(db: Session, sheet_name: str) -> Optional[List[List]]:
    """获取raw_table数据"""
    result = _get_raw_table_with_meta(db, sheet_name)
    return result[0] if result else None


def _get_raw_table_with_meta(db: Session, sheet_name: str) -> Optional[tuple]:
    """获取raw_table数据及merged_cells_json，返回 (table_data, merged_cells_json)"""
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
    merged = raw_table.merged_cells_json
    if isinstance(merged, str):
        merged = json.loads(merged) if merged else []
    return (table_data, merged or [])


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


def _format_statistics_cell(val) -> str:
    """格式化统计局表格单元格"""
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return ""
        return str(int(val)) if val == int(val) else f"{val:.2f}"
    if hasattr(val, "isoformat"):
        return val.isoformat()[:10]
    return str(val).strip()


@router.get("/quarterly-data", response_model=QuarterlyDataRawResponse)
def get_quarterly_data(
    db: Session = Depends(get_db)
):
    """
    获取统计局季度数据汇总（表1）
    按 Excel 原样：2 行表头、合并单元格、数据行；B-Y 列。
    数据来源：03.统计局季度数据 sheet
    """
    result = _get_raw_table_with_meta(db, "03.统计局季度数据")
    if not result or len(result[0]) < 2:
        return QuarterlyDataRawResponse(
            header_row_0=[],
            header_row_1=[],
            rows=[],
            column_count=0,
            merged_cells_json=[],
        )
    table_data, merged_cells = result
    max_col = min(
        max(len(table_data[0]), len(table_data[1]), *(len(r) for r in table_data[2:]), 1),
        25,  # B-Y 共 24 列 + B 列季度，限 25 列
    )

    def pad_row(row, length):
        r = list(row) if row else []
        return [r[i] if i < len(r) else "" for i in range(length)]

    row0 = pad_row(table_data[0], max_col)
    row1 = pad_row(table_data[1], max_col)
    header_row_0 = [_format_statistics_cell(v) or "" for v in row0]
    header_row_1 = [_format_statistics_cell(v) or "" for v in row1]

    rows = []
    for row_idx in range(2, len(table_data)):
        row = pad_row(table_data[row_idx], max_col)
        if len(row) < 2 or not row[1]:  # B 列为季度，不能为空
            continue
        parsed_date = _parse_excel_date(row[1])
        if parsed_date:
            year = parsed_date.year
            quarter = (parsed_date.month - 1) // 3 + 1
            row[1] = f"{year}Q{quarter}"
        else:
            q = _parse_quarter(str(row[1]))
            if q:
                row[1] = q
        rows.append([_format_statistics_cell(v) for v in row])

    return QuarterlyDataRawResponse(
        header_row_0=header_row_0,
        header_row_1=header_row_1,
        rows=rows,
        column_count=max_col,
        merged_cells_json=merged_cells,
    )


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
    
    数据结构：
    - 第1行（索引0）：主表头
    - 第2行（索引1）：子表头
    - 第3行（索引2）开始：数据行（B列是季度日期，J列是出栏量，P列是屠宰量）
    """
    table_data = _get_raw_table_data(db, "03.统计局季度数据")
    
    if not table_data or len(table_data) < 3:
        return OutputSlaughterResponse(data=[], latest_period=None)
    
    data_points = []
    latest_period = None
    
    # 从第3行开始解析数据（索引2）
    for row_idx, row in enumerate(table_data[2:], start=3):
        if len(row) < 16:
            continue
        
        # B列（索引1）是季度日期
        period_str = row[1] if len(row) > 1 and row[1] else None
        if not period_str:
            continue
        
        # 解析季度日期
        period = None
        parsed_date = _parse_excel_date(period_str)
        if parsed_date:
            # 转换为季度格式：YYYYQ格式
            year = parsed_date.year
            quarter = (parsed_date.month - 1) // 3 + 1
            period = f"{year}Q{quarter}"
        else:
            # 尝试直接解析季度字符串
            period = _parse_quarter(str(period_str))
            if not period:
                period = str(period_str)
        
        # J列（索引9）：季度出栏量
        output_val = row[9] if len(row) > 9 else None
        output_volume = None
        if output_val is not None and output_val != "":
            try:
                output_volume = float(output_val)
                if math.isnan(output_volume) or math.isinf(output_volume):
                    output_volume = None
            except (ValueError, TypeError):
                pass
        
        # P列（索引15）：定点屠宰量
        slaughter_val = row[15] if len(row) > 15 else None
        slaughter_volume = None
        if slaughter_val is not None and slaughter_val != "":
            try:
                slaughter_volume = float(slaughter_val)
                if math.isnan(slaughter_volume) or math.isinf(slaughter_volume):
                    slaughter_volume = None
            except (ValueError, TypeError):
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
    实际返回：钢联全国猪价的月度均值/历年平均值系数
    数据来源：钢联全国猪价（日度数据，按月聚合）
    计算公式：系数 = 月度均值 / 历年平均值
    """
    # 1. 获取钢联全国猪价数据（日度，需要按月聚合）
    # 优先查找：分省区猪价sheet中的"中国"列
    price_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "分省区猪价",
        or_(
            DimMetric.raw_header.like('%中国%'),
            DimMetric.raw_header.like('%全国%')
        ),
        DimMetric.freq.in_(["D", "daily"])
    ).first()
    
    # 如果没找到，尝试通过metric_key查找
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, '$.metric_key') == 'GL_D_PRICE_NATION',
            DimMetric.freq.in_(["D", "daily"])
        ).first()
    
    # 如果还没找到，尝试其他方式
    if not price_metric:
        price_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name.like('%钢联%'),
            or_(
                DimMetric.raw_header.like('%全国%价%'),
                DimMetric.raw_header.like('%中国%价%')
            ),
            DimMetric.freq.in_(["D", "daily"])
        ).first()
    
    if not price_metric:
        return ImportMeatResponse(data=[], latest_month=None)
    
    # 2. 查询价格数据并按月聚合
    price_monthly = db.query(
        func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
        func.avg(FactObservation.value).label('monthly_avg')
    ).filter(
        FactObservation.metric_id == price_metric.id,
        FactObservation.period_type == 'day'
    ).group_by('month').order_by('month').all()
    
    if not price_monthly:
        return ImportMeatResponse(data=[], latest_month=None)
    
    # 3. 计算历年平均值
    price_values = [float(item.monthly_avg) for item in price_monthly if item.monthly_avg]
    price_avg = sum(price_values) / len(price_values) if price_values else None
    
    if not price_avg or price_avg <= 0:
        return ImportMeatResponse(data=[], latest_month=None)
    
    # 4. 计算系数并构建数据点
    data_points = []
    latest_month = None
    
    for item in price_monthly:
        if not item.monthly_avg:
            continue
        
        month_str = item.month
        monthly_avg = float(item.monthly_avg)
        
        # 计算系数：月度均值 / 历年平均值
        price_coef = monthly_avg / price_avg
        
        data_points.append(ImportMeatPoint(
            month=month_str,
            price_coefficient=round(price_coef, 4)
        ))
        
        if month_str and (not latest_month or month_str > latest_month):
            latest_month = month_str
    
    # 按月份排序
    data_points.sort(key=lambda x: x.month)
    
    return ImportMeatResponse(data=data_points, latest_month=latest_month)
