"""
D4. 结构分析 API
显示CR20集团出栏环比、涌益、钢联、农业部出栏环比和定点企业屠宰环比
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import date, timedelta, datetime
from pydantic import BaseModel
import math

from app.core.database import get_db
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

router = APIRouter(prefix="/api/v1/structure-analysis", tags=["structure-analysis"])


def _get_raw_table_data(db: Session, sheet_name: str, filename_pattern: str = None):
    """获取raw_table数据"""
    import json
    query = db.query(RawSheet).join(RawFile)
    
    if filename_pattern:
        query = query.filter(RawFile.filename.like(f'%{filename_pattern}%'))
    
    sheet = query.filter(RawSheet.sheet_name == sheet_name).first()
    
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


class StructureDataPoint(BaseModel):
    """结构分析数据点"""
    date: str  # 日期 YYYY-MM-DD
    source: str  # 数据源：CR20、涌益、钢联-全国、钢联-规模场、钢联-中小散户、农业部-全国、农业部-规模场、农业部-中小散户、定点企业屠宰
    value: Optional[float] = None  # 环比值（百分比）


class StructureTableRow(BaseModel):
    """结构分析表格行"""
    month: str  # 月份 YYYY-MM
    cr20: Optional[float] = None  # CR20集团出栏环比
    yongyi: Optional[float] = None  # 涌益出栏环比
    ganglian: Optional[float] = None  # 钢联出栏环比（全国）
    ministry_scale: Optional[float] = None  # 农业部规模场出栏环比
    ministry_scattered: Optional[float] = None  # 农业部散户出栏环比
    slaughter: Optional[float] = None  # 定点企业屠宰环比


class StructureAnalysisResponse(BaseModel):
    """结构分析响应（图表格式）"""
    data: List[StructureDataPoint]
    latest_date: Optional[str] = None  # 最新数据日期


class StructureTableResponse(BaseModel):
    """结构分析表格响应"""
    data: List[StructureTableRow]
    latest_month: Optional[str] = None  # 最新月份


def _get_cr20_month_on_month(db: Session) -> List[StructureDataPoint]:
    """获取CR20集团出栏环比
    数据来源：集团企业月度数据跟踪 -> 集团企业全国 sheet
    数据结构：稀疏格式（list of dicts）
    - 表头行：col=24, value='CR20'
    - 数据行：col=2, value='实际出栏量'，col=1是日期，col=24是CR20值
    """
    # 查找"集团企业全国"sheet
    enterprise_sheet = db.query(RawSheet).join(RawFile).filter(
        RawFile.filename.like('%集团企业月度数据跟踪%'),
        RawSheet.sheet_name == "集团企业全国"
    ).first()
    
    if not enterprise_sheet:
        return []
    
    # 查找raw_table
    raw_table = db.query(RawTable).filter(
        RawTable.raw_sheet_id == enterprise_sheet.id
    ).first()
    
    if not raw_table or not raw_table.table_json:
        return []
    
    # 解析稀疏格式数据
    table_data = raw_table.table_json
    
    # 构建完整表格（将稀疏格式转换为二维数组）
    # 先找到最大行和列
    max_row = 0
    max_col = 0
    for row in table_data:
        if isinstance(row, list):
            for cell in row:
                if isinstance(cell, dict):
                    max_row = max(max_row, cell.get('row', 0))
                    max_col = max(max_col, cell.get('col', 0))
    
    # 构建二维数组
    grid = {}
    for row in table_data:
        if isinstance(row, list):
            for cell in row:
                if isinstance(cell, dict):
                    r = cell.get('row', 0)
                    c = cell.get('col', 0)
                    if r not in grid:
                        grid[r] = {}
                    grid[r][c] = cell.get('value')
    
    # 提取CR20数据（优先使用"实际出栏量"，如果没有则使用"计划出栏量"）
    cr20_data = []
    # 先收集所有"实际出栏量"的数据
    actual_data = {}
    plan_data = {}
    
    for row_idx in sorted(grid.keys()):
        row_data = grid[row_idx]
        col2_val = row_data.get(2)  # col=2是类型
        
        if col2_val in ["实际出栏量", "计划出栏量"]:
            date_val = row_data.get(1)  # col=1是日期
            cr20_val = row_data.get(24)  # col=24是CR20值
            
            if date_val and cr20_val is not None:
                # 处理日期
                date_obj = None
                if isinstance(date_val, str):
                    try:
                        from datetime import datetime
                        # 处理ISO格式：2025-03-01T00:00:00
                        if 'T' in date_val:
                            date_str = date_val.split('T')[0]
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        else:
                            # 尝试多种日期格式
                            date_str = date_val.split()[0] if ' ' in date_val else date_val
                            # 尝试 YYYY-MM-DD
                            try:
                                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                            except:
                                # 尝试 YYYY/M/D 或 YYYY/MM/DD
                                try:
                                    date_obj = datetime.strptime(date_str, '%Y/%m/%d').date()
                                except:
                                    # 尝试 YYYY/M/D（单数字月份和日期）
                                    try:
                                        parts = date_str.split('/')
                                        if len(parts) == 3:
                                            year = int(parts[0])
                                            month = int(parts[1])
                                            day = int(parts[2])
                                            date_obj = date(year, month, day)
                                    except:
                                        continue
                    except:
                        continue
                elif isinstance(date_val, date):
                    date_obj = date_val
                elif hasattr(date_val, 'date'):
                    date_obj = date_val.date()
                
                if date_obj:
                    try:
                        cr20_float = float(cr20_val)
                        if col2_val == "实际出栏量":
                            actual_data[date_obj] = cr20_float
                        else:  # 计划出栏量
                            plan_data[date_obj] = cr20_float
                    except (ValueError, TypeError):
                        continue
    
    # 合并数据：优先使用实际出栏量，如果没有则使用计划出栏量
    for date_obj in sorted(set(list(actual_data.keys()) + list(plan_data.keys()))):
        value = actual_data.get(date_obj) or plan_data.get(date_obj)
        if value is not None:
            cr20_data.append({
                'date': date_obj,
                'value': value
            })
    
    if len(cr20_data) < 2:
        return []
    
    # 计算环比
    result = []
    for i in range(1, len(cr20_data)):
        prev_value = cr20_data[i-1]['value']
        curr_value = cr20_data[i]['value']
        
        # 检查值是否有效（不是None、NaN或0）
        if (prev_value is not None and curr_value is not None and 
            not math.isnan(prev_value) and not math.isnan(curr_value) and
            prev_value > 0):
            mom = (curr_value - prev_value) / prev_value * 100
            # 检查计算结果是否为NaN
            if not math.isnan(mom) and not math.isinf(mom):
                result.append(StructureDataPoint(
                    date=cr20_data[i]['date'].isoformat(),
                    source="CR20",
                    value=round(mom, 2)
                ))
    
    return result


def _get_yongyi_month_on_month(db: Session) -> List[StructureDataPoint]:
    """获取涌益月度出栏环比
    数据来源：月度-商品猪出栏量 sheet
    数据结构：第0行是标题，第1行是表头，第2行开始是数据
    表头格式：['日期', '全国', '环比', '同比', '较非瘟前', '日期', '华北', '环比', ...]
    数据格式：每5列一组（日期、区域、环比、同比、较非瘟前）
    全国数据在第0-4列：列0=日期，列1=全国出栏量，列2=环比
    """
    # 查找"月度-商品猪出栏量"sheet
    yongyi_sheet = db.query(RawSheet).join(RawFile).filter(
        RawFile.filename.like('%涌益%'),
        RawSheet.sheet_name == "月度-商品猪出栏量"
    ).first()
    
    if not yongyi_sheet:
        return []
    
    # 查找raw_table
    raw_table = db.query(RawTable).filter(
        RawTable.raw_sheet_id == yongyi_sheet.id
    ).first()
    
    if not raw_table or not raw_table.table_json:
        return []
    
    # 解析数据
    result = []
    table_data = raw_table.table_json
    
    if len(table_data) < 2:
        return []
    
    # 从第2行开始（跳过标题和表头）
    for row_idx in range(2, len(table_data)):
        row = table_data[row_idx]
        
        if not isinstance(row, list) or len(row) < 3:
            continue
        
        # 全国数据在第0-4列
        date_val = row[0] if len(row) > 0 else None
        mom_val = row[2] if len(row) > 2 else None  # 环比在列2
        
        # 处理日期
        if not date_val:
            continue
            
        date_obj = None
        if isinstance(date_val, str):
            try:
                from datetime import datetime
                # 处理ISO格式：2016-08-01T00:00:00
                if 'T' in date_val:
                    date_str = date_val.split('T')[0]
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                else:
                    # 尝试多种日期格式
                    date_str = date_val.split()[0] if ' ' in date_val else date_val
                    # 尝试 YYYY-MM-DD
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except:
                        # 尝试 YYYY/M/D 或 YYYY/MM/DD
                        try:
                            date_obj = datetime.strptime(date_str, '%Y/%m/%d').date()
                        except:
                            # 尝试 YYYY/M/D（单数字月份和日期）
                            try:
                                parts = date_str.split('/')
                                if len(parts) == 3:
                                    year = int(parts[0])
                                    month = int(parts[1])
                                    day = int(parts[2])
                                    date_obj = date(year, month, day)
                            except:
                                continue
            except:
                continue
        elif isinstance(date_val, (int, float)):
            # Excel日期序列号
            try:
                from datetime import datetime, timedelta
                excel_epoch = datetime(1899, 12, 30)
                date_obj = (excel_epoch + timedelta(days=int(date_val))).date()
            except:
                continue
        elif hasattr(date_val, 'date'):
            date_obj = date_val.date()
        elif isinstance(date_val, date):
            date_obj = date_val
        
        if not date_obj:
            continue
        
        # 处理环比值
        if mom_val is not None:
            try:
                mom_float = float(mom_val)
                # 检查是否为NaN
                if math.isnan(mom_float):
                    continue
                
                # 如果值小于1，认为是小数形式（如0.05），需要乘以100转换为百分比
                # 如果值大于1，认为已经是百分比形式（如5）
                if abs(mom_float) < 1:
                    mom_float = mom_float * 100
                
                # 再次检查计算结果是否为NaN或Inf
                if not math.isnan(mom_float) and not math.isinf(mom_float):
                    result.append(StructureDataPoint(
                        date=date_obj.isoformat(),
                        source="涌益",
                        value=round(mom_float, 2)
                    ))
            except (ValueError, TypeError):
                continue
    
    return sorted(result, key=lambda x: x.date)


def _get_ganglian_month_on_month(db: Session, scale_type: str = "全国") -> List[StructureDataPoint]:
    """获取钢联月度出栏环比
    scale_type: 全国、规模场、中小散户
    数据来源：钢联自动更新模板 -> 月度出栏 sheet
    """
    # 优先从"月度出栏"sheet读取原始数据
    monthly_output_data = _get_raw_table_data(db, "月度出栏", "钢联自动更新模板")
    
    if monthly_output_data and len(monthly_output_data) > 2:
        # 从原始数据中提取
        # 需要分析sheet结构来确定列索引
        # 暂时先尝试从fact_observation获取
        pass
    
    # 如果"月度出栏"sheet不存在或没有数据，尝试从fact_observation获取
    # 查找"月度数据"sheet中的出栏数指标（作为备选方案）
    output_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "月度数据",
        DimMetric.raw_header == "猪：出栏数：中国（月）"
    ).first()
    
    if not output_metric:
        return []
    
    # 查询月度数据（period_type='month'）
    obs_list = db.query(
        FactObservation.obs_date,
        FactObservation.value
    ).filter(
        FactObservation.metric_id == output_metric.id,
        FactObservation.period_type == 'month'
    ).order_by(FactObservation.obs_date.asc()).all()
    
    if len(obs_list) < 2:
        return []
    
    # 计算环比
    result = []
    for i in range(1, len(obs_list)):
        prev_value = float(obs_list[i-1].value) if obs_list[i-1].value else None
        curr_value = float(obs_list[i].value) if obs_list[i].value else None
        
        # 检查值是否有效（不是None、NaN或0）
        if (prev_value is not None and curr_value is not None and
            not math.isnan(prev_value) and not math.isnan(curr_value) and
            prev_value > 0):
            mom = (curr_value - prev_value) / prev_value * 100
            # 检查计算结果是否为NaN或Inf
            if not math.isnan(mom) and not math.isinf(mom):
                result.append(StructureDataPoint(
                    date=obs_list[i].obs_date.isoformat(),
                    source=f"钢联-{scale_type}",
                    value=round(mom, 2)
                ))
    
    return result


def _get_ministry_agriculture_month_on_month(db: Session, scale_type: str = "全国") -> List[StructureDataPoint]:
    """获取农业部出栏环比
    scale_type: 全国、规模场、中小散户
    数据来源：NYB sheet（来自2、【生猪产业数据】.xlsx）
    - T列（索引19）：出栏环比-全国
    - U列（索引20）：出栏环比-规模场
    - V列（索引21）：出栏环比-小散户
    """
    # 获取NYB数据
    nyb_data = _get_raw_table_data(db, "NYB", "2、【生猪产业数据】")
    
    if not nyb_data or len(nyb_data) < 3:
        return []
    
    # 确定列索引
    col_idx = None
    if scale_type == "全国":
        col_idx = 19  # T列
    elif scale_type == "规模场":
        col_idx = 20  # U列
    elif scale_type == "中小散户" or scale_type == "散户":
        col_idx = 21  # V列
    else:
        return []
    
    result = []
    # 从第3行开始（索引2）解析数据
    for row_idx in range(2, len(nyb_data)):
        row = nyb_data[row_idx]
        
        if len(row) <= col_idx:
            continue
        
        date_val = row[1] if len(row) > 1 else None  # B列（索引1）是日期
        value_val = row[col_idx] if len(row) > col_idx else None
        
        if not date_val or value_val is None or value_val == "":
            continue
        
        # 解析日期
        date_obj = None
        if isinstance(date_val, str):
            try:
                if 'T' in date_val:
                    date_str = date_val.split('T')[0]
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                else:
                    date_str = date_val.split()[0] if ' ' in date_val else date_val
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                continue
        elif isinstance(date_val, (int, float)):
            try:
                excel_epoch = datetime(1899, 12, 30)
                date_obj = (excel_epoch + timedelta(days=int(date_val))).date()
            except:
                continue
        elif hasattr(date_val, 'date'):
            date_obj = date_val.date()
        elif isinstance(date_val, date):
            date_obj = date_val
        
        if not date_obj:
            continue
        
        # 解析环比值
        try:
            value_float = float(value_val)
            if math.isnan(value_float) or math.isinf(value_float):
                continue
            
            # 如果值小于1，认为是小数形式（如0.05），需要乘以100转换为百分比
            # 如果值大于1，认为已经是百分比形式（如5）
            if abs(value_float) < 1:
                value_float = value_float * 100
            
            result.append(StructureDataPoint(
                date=date_obj.isoformat(),
                source=f"农业部-{scale_type}",
                value=round(value_float, 2)
            ))
        except (ValueError, TypeError):
            continue
    
    return sorted(result, key=lambda x: x.date)


def _get_slaughter_month_on_month(db: Session) -> List[StructureDataPoint]:
    """获取定点企业屠宰环比
    数据来源：A1供给预测 sheet（来自2、【生猪产业数据】.xlsx）
    - AG列（索引32）：定点屠宰
    - AH列（索引33）：环比
    """
    # 获取A1供给预测数据
    a1_data = _get_raw_table_data(db, "A1供给预测", "2、【生猪产业数据】")
    
    if not a1_data or len(a1_data) < 3:
        return []
    
    result = []
    # 从第3行开始（索引2）解析数据
    for row_idx in range(2, len(a1_data)):
        row = a1_data[row_idx]
        
        if len(row) <= 33:
            continue
        
        date_val = row[1] if len(row) > 1 else None  # B列（索引1）是日期
        mom_val = row[33] if len(row) > 33 else None  # AH列（索引33）是环比
        
        if not date_val or mom_val is None or mom_val == "":
            continue
        
        # 解析日期
        date_obj = None
        if isinstance(date_val, str):
            try:
                if 'T' in date_val:
                    date_str = date_val.split('T')[0]
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                else:
                    date_str = date_val.split()[0] if ' ' in date_val else date_val
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                continue
        elif isinstance(date_val, (int, float)):
            try:
                excel_epoch = datetime(1899, 12, 30)
                date_obj = (excel_epoch + timedelta(days=int(date_val))).date()
            except:
                continue
        elif hasattr(date_val, 'date'):
            date_obj = date_val.date()
        elif isinstance(date_val, date):
            date_obj = date_val
        
        if not date_obj:
            continue
        
        # 解析环比值
        try:
            mom_float = float(mom_val)
            if math.isnan(mom_float) or math.isinf(mom_float):
                continue
            
            # 如果值小于1，认为是小数形式（如0.05），需要乘以100转换为百分比
            # 如果值大于1，认为已经是百分比形式（如5）
            if abs(mom_float) < 1:
                mom_float = mom_float * 100
            
            result.append(StructureDataPoint(
                date=date_obj.isoformat(),
                source="定点企业屠宰",
                value=round(mom_float, 2)
            ))
        except (ValueError, TypeError):
            continue
    
    return sorted(result, key=lambda x: x.date)


@router.get("/data", response_model=StructureAnalysisResponse)
async def get_structure_analysis_data(
    sources: Optional[str] = Query(None, description="数据源，逗号分隔：CR20,涌益,钢联-全国,钢联-规模场,钢联-中小散户,农业部-全国,农业部-规模场,农业部-中小散户,定点企业屠宰"),
    db: Session = Depends(get_db)
):
    """
    获取结构分析数据（图表格式）
    """
    # 解析数据源列表
    if sources:
        source_list = [s.strip() for s in sources.split(',')]
    else:
        # 默认返回所有可用数据源
        source_list = ["CR20", "涌益", "钢联-全国", "定点企业屠宰"]
    
    all_data = []
    
    # 获取各数据源的数据
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
    
    # 过滤掉NaN值
    filtered_data = []
    for item in all_data:
        if item.value is not None and not math.isnan(item.value) and not math.isinf(item.value):
            filtered_data.append(item)
    
    # 按日期排序
    filtered_data.sort(key=lambda x: x.date)
    
    # 获取最新日期
    latest_date = filtered_data[-1].date if filtered_data else None
    
    return StructureAnalysisResponse(
        data=filtered_data,
        latest_date=latest_date
    )


@router.get("/table", response_model=StructureTableResponse)
async def get_structure_analysis_table(
    db: Session = Depends(get_db)
):
    """
    获取结构分析表格数据
    返回格式：按月份组织的表格数据，每行包含所有列的值
    """
    # 获取所有数据源的数据
    cr20_data = _get_cr20_month_on_month(db)
    yongyi_data = _get_yongyi_month_on_month(db)
    ganglian_data = _get_ganglian_month_on_month(db, "全国")  # 钢联使用全国数据
    ministry_scale_data = _get_ministry_agriculture_month_on_month(db, "规模场")
    ministry_scattered_data = _get_ministry_agriculture_month_on_month(db, "散户")  # 使用"散户"而不是"中小散户"
    slaughter_data = _get_slaughter_month_on_month(db)
    
    # 将所有数据转换为月份格式（YYYY-MM）的字典
    def date_to_month(date_str: str) -> str:
        """将日期字符串转换为月份字符串 YYYY-MM"""
        try:
            date_obj = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d').date()
            return date_obj.strftime('%Y-%m')
        except:
            return date_str[:7] if len(date_str) >= 7 else date_str
    
    # 构建月份到数据的映射
    data_map = {}
    
    for item in cr20_data:
        month = date_to_month(item.date)
        if month not in data_map:
            data_map[month] = {}
        data_map[month]['cr20'] = item.value
    
    for item in yongyi_data:
        month = date_to_month(item.date)
        if month not in data_map:
            data_map[month] = {}
        data_map[month]['yongyi'] = item.value
    
    for item in ganglian_data:
        month = date_to_month(item.date)
        if month not in data_map:
            data_map[month] = {}
        data_map[month]['ganglian'] = item.value
    
    for item in ministry_scale_data:
        month = date_to_month(item.date)
        if month not in data_map:
            data_map[month] = {}
        data_map[month]['ministry_scale'] = item.value
    
    for item in ministry_scattered_data:
        month = date_to_month(item.date)
        if month not in data_map:
            data_map[month] = {}
        data_map[month]['ministry_scattered'] = item.value
    
    for item in slaughter_data:
        month = date_to_month(item.date)
        if month not in data_map:
            data_map[month] = {}
        data_map[month]['slaughter'] = item.value
    
    # 构建表格行数据
    table_rows = []
    for month in sorted(data_map.keys()):
        row_data = data_map[month]
        table_rows.append(StructureTableRow(
            month=month,
            cr20=row_data.get('cr20'),
            yongyi=row_data.get('yongyi'),
            ganglian=row_data.get('ganglian'),
            ministry_scale=row_data.get('ministry_scale'),
            ministry_scattered=row_data.get('ministry_scattered'),
            slaughter=row_data.get('slaughter')
        ))
    
    latest_month = table_rows[-1].month if table_rows else None
    
    return StructureTableResponse(
        data=table_rows,
        latest_month=latest_month
    )
