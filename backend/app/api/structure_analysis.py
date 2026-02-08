"""
D4. 结构分析 API
显示CR20集团出栏环比、涌益、钢联、农业部出栏环比和定点企业屠宰环比
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import date, timedelta
from pydantic import BaseModel
import math

from app.core.database import get_db
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

router = APIRouter(prefix="/api/v1/structure-analysis", tags=["structure-analysis"])


class StructureDataPoint(BaseModel):
    """结构分析数据点"""
    date: str  # 日期 YYYY-MM-DD
    source: str  # 数据源：CR20、涌益、钢联-全国、钢联-规模场、钢联-中小散户、农业部-全国、农业部-规模场、农业部-中小散户、定点企业屠宰
    value: Optional[float] = None  # 环比值（百分比）


class StructureAnalysisResponse(BaseModel):
    """结构分析响应"""
    data: List[StructureDataPoint]
    latest_date: Optional[str] = None  # 最新数据日期


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
    """
    # 查找"月度数据"sheet中的出栏数指标
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
    """
    # TODO: 需要确认农业部数据的指标名称和sheet名称
    # 目前未找到农业部数据，返回空列表
    return []


def _get_slaughter_month_on_month(db: Session) -> List[StructureDataPoint]:
    """获取定点企业屠宰环比"""
    # 查找屠宰相关的指标（日度屠宰量）
    slaughter_metric = db.query(DimMetric).filter(
        DimMetric.raw_header.like('%屠宰%'),
        or_(
            DimMetric.raw_header.like('%日度屠宰量%'),
            DimMetric.raw_header.like('%日屠宰量%')
        )
    ).first()
    
    if not slaughter_metric:
        return []
    
    # 查询月度聚合数据（需要按月份聚合日度数据）
    # 先查询所有日度数据
    daily_obs = db.query(
        func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
        func.sum(FactObservation.value).label('monthly_total')
    ).filter(
        FactObservation.metric_id == slaughter_metric.id,
        FactObservation.period_type == 'day'
    ).group_by('month').order_by('month').all()
    
    if len(daily_obs) < 2:
        return []
    
    # 计算环比
    result = []
    for i in range(1, len(daily_obs)):
        prev_value = float(daily_obs[i-1].monthly_total) if daily_obs[i-1].monthly_total else None
        curr_value = float(daily_obs[i].monthly_total) if daily_obs[i].monthly_total else None
        
        # 检查值是否有效（不是None、NaN或0）
        if (prev_value is not None and curr_value is not None and
            not math.isnan(prev_value) and not math.isnan(curr_value) and
            prev_value > 0):
            mom = (curr_value - prev_value) / prev_value * 100
            # 检查计算结果是否为NaN或Inf
            if not math.isnan(mom) and not math.isinf(mom):
                # 使用月份的第一天作为日期
                result.append(StructureDataPoint(
                    date=f"{daily_obs[i].month}-01",
                    source="定点企业屠宰",
                    value=round(mom, 2)
                ))
    
    return result


@router.get("/data", response_model=StructureAnalysisResponse)
async def get_structure_analysis_data(
    sources: Optional[str] = Query(None, description="数据源，逗号分隔：CR20,涌益,钢联-全国,钢联-规模场,钢联-中小散户,农业部-全国,农业部-规模场,农业部-中小散户,定点企业屠宰"),
    db: Session = Depends(get_db)
):
    """
    获取结构分析数据
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
