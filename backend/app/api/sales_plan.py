"""
D3. 销售计划API
提供销售计划数据的查询接口
"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, extract, text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.sys_user import SysUser
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable

router = APIRouter(prefix="/api/v1/sales-plan", tags=["sales-plan"])


def _normalize_to_month_start(d: date) -> str:
    """将日期统一为当月1日，便于涌益（月初）与钢联（月末）数据同行对齐"""
    return d.replace(day=1).isoformat()


class SalesPlanDataPoint(BaseModel):
    """销售计划数据点"""
    date: str  # YYYY-MM-DD格式
    region: str  # 区域：全国CR20、全国CR5、广东、四川、贵州、涌益、钢联
    source: str  # 数据来源
    actual_output: Optional[float] = None  # 当月出栏量
    plan_output: Optional[float] = None  # 当月计划
    month_on_month: Optional[float] = None  # 当月环比（当月出栏/上月出栏）
    plan_on_plan: Optional[float] = None  # 计划环比（当月计划/上月实际出栏）
    plan_completion_rate: Optional[float] = None  # 计划达成率（当月出栏/当月计划）


class SalesPlanResponse(BaseModel):
    """销售计划响应"""
    data: List[SalesPlanDataPoint]
    data_source: str
    update_time: Optional[str]
    latest_date: Optional[str]


@router.get("/data", response_model=SalesPlanResponse)
async def get_sales_plan_data(
    indicator: str = Query("全部", description="指标筛选：全部、当月环比、计划环比、计划达成率、当月出栏量"),
    region: str = Query("全部", description="区域筛选：全部、全国CR20、全国CR5、涌益、钢联、广东、四川、贵州"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取销售计划数据
    
    数据来源：
    - 全国CR20、全国CR5、广东、四川、贵州：来自《集团企业月度数据跟踪》的"汇总"sheet
    - 涌益：来自《涌益咨询 周度数据》的"月度计划出栏量"sheet
    - 钢联：来自《价格：钢联自动更新模板》的"月度数据"sheet
    """
    data_points: List[SalesPlanDataPoint] = []
    
    # 解析区域筛选
    target_regions = []
    if region == "全部":
        target_regions = ['全国CR20', '全国CR5', '广东', '四川', '贵州', '涌益', '钢联']
    else:
        target_regions = [region]
    
    # 1. 查询集团企业数据（全国CR20、全国CR5、广东、四川、贵州）
    enterprise_regions = ['全国CR20', '全国CR5', '广东', '四川', '贵州']
    enterprise_regions_to_query = [r for r in target_regions if r in enterprise_regions]
    
    if enterprise_regions_to_query:
        enterprise_data = _get_enterprise_data(db, enterprise_regions_to_query)
        data_points.extend(enterprise_data)
    
    # 2. 查询涌益数据
    if '涌益' in target_regions:
        yongyi_data = _get_yongyi_data(db)
        if yongyi_data:
            data_points.extend(yongyi_data)
    
    # 3. 查询钢联数据
    if '钢联' in target_regions:
        ganglian_data = _get_ganglian_data(db)
        if ganglian_data:
            data_points.extend(ganglian_data)
    
    # 根据indicator筛选数据
    if indicator != "全部":
        filtered_points = []
        for point in data_points:
            if indicator == "当月环比" and point.month_on_month is not None:
                filtered_points.append(point)
            elif indicator == "计划环比" and point.plan_on_plan is not None:
                filtered_points.append(point)
            elif indicator == "计划达成率" and point.plan_completion_rate is not None:
                filtered_points.append(point)
            elif indicator == "当月出栏量" and point.actual_output is not None:
                filtered_points.append(point)
        data_points = filtered_points
    
    # 按日期排序
    data_points.sort(key=lambda x: x.date, reverse=True)
    
    # 获取最新日期
    latest_date = data_points[0].date if data_points else None
    
    return SalesPlanResponse(
        data=data_points,
        data_source="企业集团出栏跟踪、涌益咨询、钢联",
        update_time=None,
        latest_date=latest_date
    )


def _get_enterprise_data(db: Session, regions: List[str]) -> List[SalesPlanDataPoint]:
    """从集团企业汇总sheet获取数据"""
    data_points: List[SalesPlanDataPoint] = []
    
    # 查询"汇总"sheet的指标
    metrics = db.query(DimMetric).filter(
        DimMetric.sheet_name == "汇总"
    ).all()
    
    if not metrics:
        return data_points
    
    metric_ids = [m.id for m in metrics]
    
    # 构建指标映射
    plan_metric = None
    actual_metric = None
    
    for m in metrics:
        metric_key = m.parse_json.get('metric_key') if m.parse_json else None
        if metric_key == 'PROVINCE_PLAN':
            plan_metric = m
        elif metric_key == 'PROVINCE_ACTUAL':
            actual_metric = m
    
    if not plan_metric or not actual_metric:
        return data_points
    
    # 查询月度数据（只查询period_type='月度'的数据）
    for region in regions:
        # 分别查询计划和实际出栏量
        plan_obs = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == plan_metric.id,
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.region')
            ) == region,
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.period_type')
            ) == '月度'
        ).order_by(FactObservation.obs_date.desc()).all()
        
        actual_obs = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == actual_metric.id,
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.region')
            ) == region,
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.period_type')
            ) == '月度'
        ).order_by(FactObservation.obs_date.desc()).all()
        
        # 按日期分组，统一为月初（与涌益、钢联对齐，便于同月数据同行展示）
        date_data: Dict[str, Dict[str, float]] = {}
        
        for obs in plan_obs:
            date_str = _normalize_to_month_start(obs.obs_date)
            if date_str not in date_data:
                date_data[date_str] = {}
            date_data[date_str]['plan'] = float(obs.value) if obs.value else None
        
        for obs in actual_obs:
            date_str = _normalize_to_month_start(obs.obs_date)
            if date_str not in date_data:
                date_data[date_str] = {}
            date_data[date_str]['actual'] = float(obs.value) if obs.value else None
        
        # 计算指标并构建数据点
        sorted_dates = sorted(date_data.keys(), reverse=True)
        for i, date_str in enumerate(sorted_dates):
            current_data = date_data[date_str]
            plan = current_data.get('plan')
            actual = current_data.get('actual')
            
            # 计算环比（需要上月数据）
            month_on_month = None
            plan_on_plan = None
            plan_completion_rate = None
            
            if actual and plan:
                plan_completion_rate = actual / plan if plan != 0 else None
            
            if i < len(sorted_dates) - 1:
                prev_date_str = sorted_dates[i + 1]
                prev_data = date_data[prev_date_str]
                prev_plan = prev_data.get('plan')
                prev_actual = prev_data.get('actual')
                
                if actual and prev_actual:
                    month_on_month = actual / prev_actual if prev_actual != 0 else None
                
                if plan and prev_actual:
                    plan_on_plan = plan / prev_actual if prev_actual != 0 else None
            
            data_points.append(SalesPlanDataPoint(
                date=date_str,
                region=region,
                source="企业集团出栏跟踪",
                actual_output=actual,
                plan_output=plan,
                month_on_month=month_on_month,
                plan_on_plan=plan_on_plan,
                plan_completion_rate=plan_completion_rate
            ))
    
    return data_points


def _get_yongyi_data(db: Session) -> List[SalesPlanDataPoint]:
    """从涌益月度计划出栏量sheet获取数据"""
    data_points: List[SalesPlanDataPoint] = []
    
    # 查找最新的raw_sheet
    raw_sheet = db.query(RawSheet).filter(
        RawSheet.sheet_name == "月度计划出栏量"
    ).order_by(RawSheet.created_at.desc()).first()
    
    if not raw_sheet:
        return data_points
    
    # 获取raw_table数据
    raw_table = db.query(RawTable).filter(
        RawTable.raw_sheet_id == raw_sheet.id
    ).first()
    
    if not raw_table or not raw_table.table_json:
        return data_points
    
    table_json = raw_table.table_json
    
    # 处理数据格式：可能是二维数组，也可能是稀疏格式，也可能是混合格式（二维数组但元素是字典列表）
    rows = []
    if isinstance(table_json, list) and len(table_json) > 0:
        # 判断格式
        if isinstance(table_json[0], list):
            # 二维数组格式，但需要检查内层元素是否是字典
            if len(table_json[0]) > 0 and isinstance(table_json[0][0], dict):
                # 混合格式：外层是二维数组，内层是稀疏格式字典
                # 需要将每行转换为普通数组
                rows = []
                for row_list in table_json:
                    if isinstance(row_list, list):
                        # 找到该行的最大列
                        max_col = max([item.get('col', 0) for item in row_list if isinstance(item, dict)]) if row_list else 0
                        # 创建该行的数组
                        row_array = [None] * (max_col + 1)
                        for item in row_list:
                            if isinstance(item, dict):
                                col_idx = item.get('col', 0) - 1  # col从1开始
                                if 0 <= col_idx < len(row_array):
                                    row_array[col_idx] = item.get('value')
                        rows.append(row_array)
                    else:
                        rows.append(row_list)
            else:
                # 纯二维数组格式
                rows = table_json
        elif isinstance(table_json[0], dict):
            # 完全稀疏格式，需要转换为二维数组
            # 找到最大行和列
            max_row = max([item.get('row', 0) for item in table_json if isinstance(item, dict)])
            max_col = max([item.get('col', 0) for item in table_json if isinstance(item, dict)])
            
            # 创建二维数组
            rows = [[None] * (max_col + 1) for _ in range(max_row + 1)]
            for item in table_json:
                if isinstance(item, dict):
                    row_idx = item.get('row', 0) - 1  # row从1开始
                    col_idx = item.get('col', 0) - 1  # col从1开始
                    if 0 <= row_idx < len(rows) and 0 <= col_idx < len(rows[0]):
                        rows[row_idx][col_idx] = item.get('value')
    
    if len(rows) < 3:
        return data_points
    
    # 第1行（索引0）：标题行，Q列（索引16）是"上月样本企业合计销售"，R列（索引17）是"本月计划销售"
    # 第2行（索引1）：表头行
    # 第3行开始（索引2+）：数据行，第1列（索引0）是日期，Q列（索引16）是上月出栏（需要修正为当月出栏），R列（索引17）是当月计划
    
    date_data: Dict[str, Dict[str, float]] = {}
    
    for row_idx in range(2, len(rows)):
        row = rows[row_idx]
        if len(row) < 18:
            continue
        
        # 第1列是日期
        date_val = row[0]
        if not date_val:
            continue
        
        # 解析日期
        try:
            if isinstance(date_val, str):
                # 处理ISO格式日期字符串
                if 'T' in date_val:
                    date_val = date_val.split('T')[0]
                date_obj = datetime.strptime(date_val, "%Y-%m-%d").date()
            elif isinstance(date_val, datetime):
                date_obj = date_val.date()
            else:
                continue
        except:
            continue
        
        date_str = _normalize_to_month_start(date_obj)
        
        # Q列（索引16）：上月样本企业合计销售（但用户说原数据是上月出栏，需要修正为当月出栏）
        # 注意：用户说Q列原数据是上月出栏，但需要修正为当月出栏，这意味着我们需要将Q列的值作为当月出栏
        q_value = row[16] if len(row) > 16 else None
        
        # R列（索引17）：本月计划销售（当月计划）
        r_value = row[17] if len(row) > 17 else None
        
        # 清理数值
        def clean_value(val):
            if val is None or val == '***' or val == '':
                return None
            try:
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    val = val.strip()
                    if val == '***' or val == '':
                        return None
                    return float(val)
                return None
            except:
                return None
        
        actual_output = clean_value(q_value)  # Q列作为当月出栏
        plan_output = clean_value(r_value)  # R列作为当月计划
        
        if date_str not in date_data:
            date_data[date_str] = {}
        
        if actual_output is not None:
            date_data[date_str]['actual'] = actual_output
        if plan_output is not None:
            date_data[date_str]['plan'] = plan_output
    
    # 计算指标并构建数据点
    sorted_dates = sorted(date_data.keys(), reverse=True)
    for i, date_str in enumerate(sorted_dates):
        current_data = date_data[date_str]
        plan = current_data.get('plan')
        actual = current_data.get('actual')
        
        # 计算环比（需要上月数据）
        month_on_month = None
        plan_on_plan = None
        plan_completion_rate = None
        
        if actual and plan:
            plan_completion_rate = actual / plan if plan != 0 else None
        
        if i < len(sorted_dates) - 1:
            prev_date_str = sorted_dates[i + 1]
            prev_data = date_data[prev_date_str]
            prev_plan = prev_data.get('plan')
            prev_actual = prev_data.get('actual')
            
            if actual and prev_actual:
                month_on_month = actual / prev_actual if prev_actual != 0 else None
            
            if plan and prev_actual:
                plan_on_plan = plan / prev_actual if prev_actual != 0 else None
        
        data_points.append(SalesPlanDataPoint(
            date=date_str,
            region="涌益",
            source="涌益咨询",
            actual_output=actual,
            plan_output=plan,
            month_on_month=month_on_month,
            plan_on_plan=plan_on_plan,
            plan_completion_rate=plan_completion_rate
        ))
    
    return data_points


def _get_ganglian_data(db: Session) -> List[SalesPlanDataPoint]:
    """从钢联月度数据sheet获取数据"""
    data_points: List[SalesPlanDataPoint] = []
    
    # 查询钢联月度数据的指标
    # B列：猪：出栏数：中国（月）- 当月出栏
    # C列：猪：计划出栏量：中国（月）- 当月计划
    
    actual_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "月度数据",
        DimMetric.raw_header.like("%出栏数%中国%")
    ).first()
    
    plan_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "月度数据",
        DimMetric.raw_header.like("%计划出栏量%中国%")
    ).first()
    
    if not actual_metric or not plan_metric:
        return data_points
    
    # 查询数据（月度数据，period_type应该是month）
    actual_obs = db.query(
        FactObservation.obs_date,
        FactObservation.value
    ).filter(
        FactObservation.metric_id == actual_metric.id,
        FactObservation.period_type == "month"
    ).order_by(FactObservation.obs_date.desc()).all()
    
    plan_obs = db.query(
        FactObservation.obs_date,
        FactObservation.value
    ).filter(
        FactObservation.metric_id == plan_metric.id,
        FactObservation.period_type == "month"
    ).order_by(FactObservation.obs_date.desc()).all()
    
    # 按日期分组，统一为月初（与涌益对齐，便于同月数据同行展示）
    date_data: Dict[str, Dict[str, float]] = {}
    
    for obs in actual_obs:
        date_str = _normalize_to_month_start(obs.obs_date)
        if date_str not in date_data:
            date_data[date_str] = {}
        date_data[date_str]['actual'] = float(obs.value) if obs.value else None
    
    for obs in plan_obs:
        date_str = _normalize_to_month_start(obs.obs_date)
        if date_str not in date_data:
            date_data[date_str] = {}
        date_data[date_str]['plan'] = float(obs.value) if obs.value else None
    
    # 计算指标并构建数据点
    sorted_dates = sorted(date_data.keys(), reverse=True)
    for i, date_str in enumerate(sorted_dates):
        current_data = date_data[date_str]
        plan = current_data.get('plan')
        actual = current_data.get('actual')
        
        # 计算环比（需要上月数据）
        month_on_month = None
        plan_on_plan = None
        plan_completion_rate = None
        
        if actual and plan:
            plan_completion_rate = actual / plan if plan != 0 else None
        
        if i < len(sorted_dates) - 1:
            prev_date_str = sorted_dates[i + 1]
            prev_data = date_data[prev_date_str]
            prev_plan = prev_data.get('plan')
            prev_actual = prev_data.get('actual')
            
            if actual and prev_actual:
                month_on_month = actual / prev_actual if prev_actual != 0 else None
            
            if plan and prev_actual:
                plan_on_plan = plan / prev_actual if prev_actual != 0 else None
        
        data_points.append(SalesPlanDataPoint(
            date=date_str,
            region="钢联",
            source="钢联",
            actual_output=actual,
            plan_output=plan,
            month_on_month=month_on_month,
            plan_on_plan=plan_on_plan,
            plan_completion_rate=plan_completion_rate
        ))
    
    return data_points
