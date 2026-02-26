"""
企业集团统计API
提供D1页面的4个图表数据接口：
1. CR5企业日度出栏统计
2. 四川重点企业日度出栏
3. 广西重点企业日度出栏
4. 西南样本企业日度出栏
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
from app.models.dim_company import DimCompany
from app.models.dim_geo import DimGeo

router = APIRouter(prefix="/api/v1/enterprise-statistics", tags=["enterprise-statistics"])


class TimeSeriesDataPoint(BaseModel):
    """时间序列数据点"""
    date: str  # YYYY-MM-DD格式
    value: Optional[float]


class TimeSeriesSeries(BaseModel):
    """时间序列系列"""
    name: str
    data: List[TimeSeriesDataPoint]
    unit: Optional[str] = None


class EnterpriseStatisticsResponse(BaseModel):
    """企业统计响应"""
    chart_title: str
    series: List[TimeSeriesSeries]
    data_source: str
    update_time: Optional[str]
    latest_date: Optional[str]


def get_source_name_from_metric(metric: DimMetric) -> str:
    """从DimMetric推断数据来源名称"""
    if not metric:
        return "企业集团出栏跟踪"
    
    sheet_name = metric.sheet_name or ""
    if "CR5" in sheet_name:
        return "企业集团出栏跟踪"
    elif "西南" in sheet_name:
        return "企业集团出栏跟踪"
    
    return "企业集团出栏跟踪"


def format_update_date(date_obj: Optional[date]) -> Optional[str]:
    """格式化更新日期（只显示年月日）"""
    if not date_obj:
        return None
    return f"{date_obj.year}年{date_obj.month:02d}月{date_obj.day:02d}日"


@router.get("/cr5-daily", response_model=EnterpriseStatisticsResponse)
async def get_cr5_daily(
    months: int = Query(6, description="近N个月，0表示全部"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取CR5企业日度出栏统计
    
    指标：
    - 日度出栏（实际出栏）
    - 计划量（月度计划）
    - 价格（全国均价）
    """
    # 计算日期范围
    end_date = date.today()
    if months > 0:
        start_date = end_date - timedelta(days=months * 30)
    else:
        start_date = None
    
    # 查询指标
    metrics = db.query(DimMetric).filter(
        and_(
            DimMetric.sheet_name == "CR5日度",
            or_(
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'CR5_DAILY_OUTPUT',
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'CR5_MONTHLY_PLAN',
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'CR5_PRICE'
            )
        )
    ).all()
    
    if not metrics:
        raise HTTPException(status_code=404, detail="未找到CR5日度数据")
    
    # 构建指标映射
    metric_map = {}
    for m in metrics:
        metric_key = m.parse_json.get('metric_key') if m.parse_json else None
        if metric_key == 'CR5_DAILY_OUTPUT':
            metric_map['output'] = m
        elif metric_key == 'CR5_MONTHLY_PLAN':
            metric_map['plan'] = m
        elif metric_key == 'CR5_PRICE':
            metric_map['price'] = m
    
    # 查询数据
    series_list = []
    latest_date = None
    
    # 1. 日度出栏
    if 'output' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['output'].id,
            FactObservation.period_type == 'day'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
            if obs.obs_date and (not latest_date or obs.obs_date > latest_date):
                latest_date = obs.obs_date
        
        series_list.append(TimeSeriesSeries(
            name="日度出栏",
            data=data_points,
            unit=metric_map['output'].unit
        ))
    
    # 2. 计划量
    if 'plan' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['plan'].id,
            FactObservation.period_type == 'day'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
        
        series_list.append(TimeSeriesSeries(
            name="计划量",
            data=data_points,
            unit=metric_map['plan'].unit
        ))
    
    # 3. 价格
    if 'price' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['price'].id,
            FactObservation.period_type == 'day'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
        
        series_list.append(TimeSeriesSeries(
            name="价格",
            data=data_points,
            unit=metric_map['price'].unit
        ))
    
    # 获取数据来源
    data_source = get_source_name_from_metric(metrics[0]) if metrics else "企业集团出栏跟踪"
    
    return EnterpriseStatisticsResponse(
        chart_title="CR5企业日度出栏",
        series=series_list,
        data_source=data_source,
        update_time=format_update_date(latest_date),
        latest_date=latest_date.isoformat() if latest_date else None
    )


@router.get("/sichuan-daily", response_model=EnterpriseStatisticsResponse)
async def get_sichuan_daily(
    months: int = Query(6, description="近N个月，0表示全部"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取四川重点企业日度出栏
    
    指标：
    - 日度出栏（实际成交）
    - 计划出栏（计划日均）
    - 完成率
    - 价格
    """
    # 计算日期范围
    end_date = date.today()
    if months > 0:
        start_date = end_date - timedelta(days=months * 30)
    else:
        start_date = None
    
    # 查询指标（西南汇总sheet，四川地区）
    metrics = db.query(DimMetric).filter(
        and_(
            DimMetric.sheet_name == "西南汇总",
            or_(
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_ACTUAL_OUTPUT',
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_PLAN_OUTPUT',
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_COMPLETION_RATE',
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_PRICE'
            )
        )
    ).all()
    
    if not metrics:
        raise HTTPException(status_code=404, detail="未找到四川重点企业数据")
    
    # 构建指标映射
    metric_map = {}
    for m in metrics:
        metric_key = m.parse_json.get('metric_key') if m.parse_json else None
        if metric_key == 'SOUTHWEST_ACTUAL_OUTPUT':
            metric_map['actual'] = m
        elif metric_key == 'SOUTHWEST_PLAN_OUTPUT':
            metric_map['plan'] = m
        elif metric_key == 'SOUTHWEST_COMPLETION_RATE':
            metric_map['rate'] = m
        elif metric_key == 'SOUTHWEST_PRICE':
            metric_map['price'] = m
    
    # 查询数据（过滤tags中的region=四川）
    series_list = []
    latest_date = None
    
    # 1. 实际成交（日度出栏）
    if 'actual' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['actual'].id,
            FactObservation.period_type == 'day',
            func.json_extract(FactObservation.tags_json, '$.region') == '四川'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
            if obs.obs_date and (not latest_date or obs.obs_date > latest_date):
                latest_date = obs.obs_date
        
        series_list.append(TimeSeriesSeries(
            name="日度出栏",
            data=data_points,
            unit=metric_map['actual'].unit
        ))
    
    # 2. 计划出栏
    if 'plan' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['plan'].id,
            FactObservation.period_type == 'day',
            func.json_extract(FactObservation.tags_json, '$.region') == '四川'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
        
        series_list.append(TimeSeriesSeries(
            name="计划出栏",
            data=data_points,
            unit=metric_map['plan'].unit
        ))
    
    # 3. 完成率
    if 'rate' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['rate'].id,
            FactObservation.period_type == 'day',
            func.json_extract(FactObservation.tags_json, '$.region') == '四川'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
        
        series_list.append(TimeSeriesSeries(
            name="完成率",
            data=data_points,
            unit=metric_map['rate'].unit
        ))
    
    # 4. 价格
    if 'price' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['price'].id,
            FactObservation.period_type == 'day',
            func.json_extract(FactObservation.tags_json, '$.region') == '四川'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
        
        series_list.append(TimeSeriesSeries(
            name="价格",
            data=data_points,
            unit=metric_map['price'].unit
        ))
    
    data_source = get_source_name_from_metric(metrics[0]) if metrics else "企业集团出栏跟踪"
    
    return EnterpriseStatisticsResponse(
        chart_title="四川重点企业日度出栏",
        series=series_list,
        data_source=data_source,
        update_time=format_update_date(latest_date),
        latest_date=latest_date.isoformat() if latest_date else None
    )


@router.get("/guangxi-daily", response_model=EnterpriseStatisticsResponse)
async def get_guangxi_daily(
    months: int = Query(6, description="近N个月，0表示全部"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取广西重点企业日度出栏
    
    指标：
    - 日度出栏（实际成交）
    - 完成率
    - 价格
    """
    # 计算日期范围
    end_date = date.today()
    if months > 0:
        start_date = end_date - timedelta(days=months * 30)
    else:
        start_date = None
    
    # 查询指标（西南汇总sheet，广西地区）
    metrics = db.query(DimMetric).filter(
        and_(
            DimMetric.sheet_name == "西南汇总",
            or_(
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_ACTUAL_OUTPUT',
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_COMPLETION_RATE',
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_PRICE'
            )
        )
    ).all()
    
    if not metrics:
        raise HTTPException(status_code=404, detail="未找到广西重点企业数据")
    
    # 构建指标映射
    metric_map = {}
    for m in metrics:
        metric_key = m.parse_json.get('metric_key') if m.parse_json else None
        if metric_key == 'SOUTHWEST_ACTUAL_OUTPUT':
            metric_map['actual'] = m
        elif metric_key == 'SOUTHWEST_COMPLETION_RATE':
            metric_map['rate'] = m
        elif metric_key == 'SOUTHWEST_PRICE':
            metric_map['price'] = m
    
    # 查询数据（过滤tags中的region=广西）
    series_list = []
    latest_date = None
    
    # 1. 实际成交（日度出栏）
    if 'actual' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['actual'].id,
            FactObservation.period_type == 'day',
            func.json_extract(FactObservation.tags_json, '$.region') == '广西'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
            if obs.obs_date and (not latest_date or obs.obs_date > latest_date):
                latest_date = obs.obs_date
        
        series_list.append(TimeSeriesSeries(
            name="日度出栏",
            data=data_points,
            unit=metric_map['actual'].unit
        ))
    
    # 2. 完成率
    if 'rate' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['rate'].id,
            FactObservation.period_type == 'day',
            func.json_extract(FactObservation.tags_json, '$.region') == '广西'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
        
        series_list.append(TimeSeriesSeries(
            name="完成率",
            data=data_points,
            unit=metric_map['rate'].unit
        ))
    
    # 3. 价格
    if 'price' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['price'].id,
            FactObservation.period_type == 'day',
            func.json_extract(FactObservation.tags_json, '$.region') == '广西'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
        
        series_list.append(TimeSeriesSeries(
            name="价格",
            data=data_points,
            unit=metric_map['price'].unit
        ))
    
    data_source = get_source_name_from_metric(metrics[0]) if metrics else "企业集团出栏跟踪"
    
    return EnterpriseStatisticsResponse(
        chart_title="广西重点企业日度出栏",
        series=series_list,
        data_source=data_source,
        update_time=format_update_date(latest_date),
        latest_date=latest_date.isoformat() if latest_date else None
    )


@router.get("/southwest-sample-daily", response_model=EnterpriseStatisticsResponse)
async def get_southwest_sample_daily(
    months: int = Query(6, description="近N个月，0表示全部"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取西南样本企业日度出栏
    
    指标：
    - 出栏量（量）
    - 均重（重）
    - 价格（价）
    """
    # 计算日期范围
    end_date = date.today()
    if months > 0:
        start_date = end_date - timedelta(days=months * 30)
    else:
        start_date = None
    
    # 查询指标（西南汇总sheet，西南样本企业）
    metrics = db.query(DimMetric).filter(
        and_(
            DimMetric.sheet_name == "西南汇总",
            or_(
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_OUTPUT',
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_AVG_WEIGHT',
                func.json_extract(DimMetric.parse_json, '$.metric_key') == 'SOUTHWEST_PRICE'
            )
        )
    ).all()
    
    if not metrics:
        raise HTTPException(status_code=404, detail="未找到西南样本企业数据")
    
    # 构建指标映射
    metric_map = {}
    for m in metrics:
        metric_key = m.parse_json.get('metric_key') if m.parse_json else None
        if metric_key == 'SOUTHWEST_OUTPUT':
            metric_map['output'] = m
        elif metric_key == 'SOUTHWEST_AVG_WEIGHT':
            metric_map['weight'] = m
        elif metric_key == 'SOUTHWEST_PRICE':
            metric_map['price'] = m
    
    # 查询数据（过滤tags中的region=西南样本企业）
    series_list = []
    latest_date = None
    
    # 1. 出栏量
    if 'output' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['output'].id,
            FactObservation.period_type == 'day',
            func.json_extract(FactObservation.tags_json, '$.region') == '西南样本企业'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
            if obs.obs_date and (not latest_date or obs.obs_date > latest_date):
                latest_date = obs.obs_date
        
        series_list.append(TimeSeriesSeries(
            name="出栏量",
            data=data_points,
            unit=metric_map['output'].unit
        ))
    
    # 2. 均重
    if 'weight' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['weight'].id,
            FactObservation.period_type == 'day',
            func.json_extract(FactObservation.tags_json, '$.region') == '西南样本企业'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
        
        series_list.append(TimeSeriesSeries(
            name="均重",
            data=data_points,
            unit=metric_map['weight'].unit
        ))
    
    # 3. 价格
    if 'price' in metric_map:
        query = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric_map['price'].id,
            FactObservation.period_type == 'day',
            func.json_extract(FactObservation.tags_json, '$.region') == '西南样本企业'
        )
        if start_date:
            query = query.filter(FactObservation.obs_date >= start_date)
        query = query.order_by(FactObservation.obs_date)
        
        data_points = []
        for obs in query.all():
            data_points.append(TimeSeriesDataPoint(
                date=obs.obs_date.isoformat(),
                value=float(obs.value) if obs.value is not None else None
            ))
        
        series_list.append(TimeSeriesSeries(
            name="价格",
            data=data_points,
            unit=metric_map['price'].unit
        ))
    
    data_source = get_source_name_from_metric(metrics[0]) if metrics else "企业集团出栏跟踪"
    
    return EnterpriseStatisticsResponse(
        chart_title="西南样本企业日度出栏",
        series=series_list,
        data_source=data_source,
        update_time=format_update_date(latest_date),
        latest_date=latest_date.isoformat() if latest_date else None
    )


class ProvinceSummaryTableRow(BaseModel):
    """省份汇总表格行"""
    date: str  # YYYY-MM-DD格式
    period_type: str  # 旬度类型：上旬、中旬、月度
    province: str  # 省份名称
    value: Optional[float]


class ProvinceSummaryTableResponse(BaseModel):
    """省份汇总表格响应"""
    columns: List[str]  # 列名（包含日期、旬度、以及各省份各指标的组合，如"广东-出栏计划"）
    rows: List[Dict[str, Any]]  # 行数据，每行包含date、period_type和各个省份各指标的值
    data_source: str
    update_time: Optional[str]
    latest_date: Optional[str]


@router.get("/province-summary-table", response_model=ProvinceSummaryTableResponse)
async def get_province_summary_table(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取重点省份旬度汇总表格数据
    
    数据来源：重点省区汇总sheet
    按省份展示计划量数据
    """
    # 解析日期范围
    start = None
    end = None
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    # 如果没有指定日期范围，先查询数据的实际最新日期
    if not start or not end:
        # 先查询"汇总"sheet的指标，获取数据的实际日期范围
        temp_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总"
        ).all()
        
        if temp_metrics:
            temp_metric_ids = [m.id for m in temp_metrics]
            # 查询数据的实际最新日期
            actual_max_date = db.query(func.max(FactObservation.obs_date)).filter(
                FactObservation.metric_id.in_(temp_metric_ids)
            ).scalar()
            
            if actual_max_date:
                # 使用数据的实际最新日期作为结束日期
                end = end or actual_max_date
                # 从最新日期往前推4个月（120天）
                start = start or (end - timedelta(days=120))
            else:
                # 如果没有数据，使用今天
                end = end or date.today()
                start = start or (end - timedelta(days=120))
        else:
            # 如果没有找到指标，使用今天
            end = end or date.today()
            start = start or (end - timedelta(days=120))
    
    # 查询指标（优先查找"汇总"sheet，如果没有则查找"重点省区汇总"sheet）
    # 查询汇总sheet的所有指标
    metrics = db.query(DimMetric).filter(
        DimMetric.sheet_name == "汇总"
    ).all()
    
    if not metrics:
        # 如果没有找到汇总sheet，尝试查找重点省区汇总sheet
        metrics = db.query(DimMetric).filter(
            and_(
                DimMetric.sheet_name == "重点省区汇总",
                or_(
                    func.json_extract(DimMetric.parse_json, '$.metric_key') == 'PROVINCE_PLAN',
                    DimMetric.metric_name.like('%计划%')
                )
            )
        ).all()
    
    if not metrics:
        # 返回空数据而不是抛出异常，让前端显示空表格
        return ProvinceSummaryTableResponse(
            columns=['日期', '旬度'],
            rows=[],
            data_source="企业集团出栏跟踪",
            update_time=None,
            latest_date=None
        )
    
    # 过滤出有效的DimMetric对象
    valid_metrics = [m for m in metrics if hasattr(m, 'id') and hasattr(m, 'metric_name')]
    if not valid_metrics:
        return ProvinceSummaryTableResponse(
            columns=['日期', '旬度'],
            rows=[],
            data_source="企业集团出栏跟踪",
            update_time=None,
            latest_date=None
        )
    
    metric_ids = [m.id for m in valid_metrics]
    
    # 获取所有省份列表（从tags_json中提取region）
    # 只显示广东、四川、贵州三个省份
    target_provinces = ['广东', '四川', '贵州']
    
    try:
        # 使用json_unquote去除引号，因为json_extract返回的值可能带引号
        provinces_query = db.query(
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.region')
            ).label('region')
        ).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start,
            FactObservation.obs_date <= end,
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.region')
            ).in_(target_provinces)
        ).distinct()
        
        found_provinces = [p.region for p in provinces_query.all() if p.region and p.region in target_provinces]
        # 确保顺序：广东、四川、贵州
        provinces = [p for p in target_provinces if p in found_provinces]
    except Exception as e:
        print(f"获取省份列表失败: {e}")
        provinces = target_provinces  # 使用默认列表
    
    # 如果没有从tags中获取到省份，使用默认省份列表
    if not provinces:
        provinces = target_provinces
    
    # 定义指标映射（指标名称 -> metric_key）
    metric_mapping = {
        '出栏计划': 'PROVINCE_PLAN',
        '计划出栏量': 'PROVINCE_PLAN',
        '实际出栏量': 'PROVINCE_ACTUAL',
        '计划完成率': 'PROVINCE_COMPLETION_RATE',
        '计划达成率': 'PROVINCE_COMPLETION_RATE',
        '均重': 'PROVINCE_AVG_WEIGHT',
        '实际均重': 'PROVINCE_AVG_WEIGHT',
        '计划均重': 'PROVINCE_PLAN_WEIGHT',
        '销售均价': 'PROVINCE_PRICE'
    }
    
    # 定义要显示的指标列表（按顺序）
    display_metrics = ['出栏计划', '实际出栏量', '计划完成率', '均重', '销售均价']
    
    # 定义各省份的指标配置
    province_metrics_config = {
        '广东': ['出栏计划', '实际出栏量', '计划完成率', '均重', '销售均价'],
        '四川': ['出栏计划', '实际出栏量', '计划完成率', '均重'],  # 四川没有销售均价
        '贵州': ['计划出栏量', '实际出栏量', '计划达成率', '实际均重']  # 贵州的指标名称不同
    }
    
    # 构建列名：日期、旬度、以及各省份各指标的组合
    columns = ['日期', '旬度']
    for province in provinces:
        province_metrics_list = province_metrics_config.get(province, display_metrics)
        for metric in province_metrics_list:
            columns.append(f"{province}-{metric}")
    
    # 获取所有日期和旬度类型
    dates_periods_query = db.query(
        FactObservation.obs_date,
        func.json_unquote(
            func.json_extract(FactObservation.tags_json, '$.period_type')
        ).label('period_type')
    ).filter(
        FactObservation.metric_id.in_(metric_ids),
        FactObservation.obs_date >= start,
        FactObservation.obs_date <= end,
        func.json_extract(FactObservation.tags_json, '$.period_type').isnot(None)
    ).distinct().order_by(FactObservation.obs_date)
    
    dates_periods = [(d.obs_date, d.period_type) for d in dates_periods_query.all()]
    
    # 如果没有旬度信息，尝试从日期推断
    if not dates_periods:
        dates_query = db.query(
            FactObservation.obs_date
        ).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start,
            FactObservation.obs_date <= end
        ).distinct().order_by(FactObservation.obs_date)
        
        dates = [d.obs_date for d in dates_query.all()]
        # 根据日期推断旬度
        dates_periods = []
        for date_val in dates:
            day = date_val.day
            if day <= 10:
                period_type = '上旬'
            elif day <= 20:
                period_type = '中旬'
            else:
                period_type = '月度'
            dates_periods.append((date_val, period_type))
    
    # 构建表格数据
    rows = []
    for date_val, period_type in dates_periods:
        row: Dict[str, Any] = {
            'date': date_val.isoformat(),
            'period_type': period_type if period_type else '月度'
        }
        
        # 查询每个省份每个指标的数据
        for province in provinces:
            metrics_list = province_metrics_config.get(province, display_metrics)
            for metric_display in metrics_list:
                # 查找对应的metric_key
                target_metric_key = metric_mapping.get(metric_display)
                if not target_metric_key:
                    continue
                
                # 查找对应的DimMetric（通过metric_key或metric_name匹配）
                target_metric = None
                for m in valid_metrics:
                    metric_key = m.parse_json.get('metric_key') if m.parse_json else None
                    metric_name = m.metric_name or ""
                    
                    # 优先匹配metric_key
                    if metric_key == target_metric_key:
                        target_metric = m
                        break
                    # 如果metric_key不匹配，尝试通过metric_name匹配
                    elif metric_display in metric_name:
                        # 如果metric_key为空或匹配，使用这个metric
                        if not metric_key or metric_key == target_metric_key:
                            target_metric = m
                            break
                
                if not target_metric:
                    row[f"{province}-{metric_display}"] = None
                    continue
                
                # 查询数据（同时匹配region和period_type）
                # 使用json_unquote去除引号
                obs_query = db.query(FactObservation).filter(
                    FactObservation.metric_id == target_metric.id,
                    FactObservation.obs_date == date_val,
                    func.json_unquote(
                        func.json_extract(FactObservation.tags_json, '$.region')
                    ) == province
                )
                
                # 如果period_type存在且不为空，也匹配period_type
                if period_type and period_type.strip():
                    obs_query = obs_query.filter(
                        func.json_unquote(
                            func.json_extract(FactObservation.tags_json, '$.period_type')
                        ) == period_type
                    )
                
                obs = obs_query.first()
                
                if obs and obs.value is not None:
                    try:
                        row[f"{province}-{metric_display}"] = float(obs.value)
                    except (ValueError, TypeError):
                        row[f"{province}-{metric_display}"] = None
                else:
                    row[f"{province}-{metric_display}"] = None
        
        rows.append(row)
    
    # 获取数据来源和更新时间：以实际出栏量（PROVINCE_ACTUAL）有数据的日期为准
    latest_date = None
    actual_output_metric = next(
        (
            m for m in valid_metrics
            if (m.parse_json or {}).get('metric_key') == 'PROVINCE_ACTUAL'
            or (m.metric_name or '').find('实际出栏') >= 0
        ),
        None
    )
    if actual_output_metric:
        actual_max = db.query(func.max(FactObservation.obs_date)).filter(
            FactObservation.metric_id == actual_output_metric.id,
            FactObservation.obs_date >= start,
            FactObservation.obs_date <= end,
            FactObservation.value.isnot(None)
        ).scalar()
        latest_date = actual_max
    if latest_date is None and dates_periods:
        latest_date = max([dp[0] for dp in dates_periods])
    data_source = get_source_name_from_metric(valid_metrics[0]) if valid_metrics else "企业集团出栏跟踪"
    
    return ProvinceSummaryTableResponse(
        columns=columns,
        rows=rows,
        data_source=data_source,
        update_time=format_update_date(latest_date),
        latest_date=latest_date.isoformat() if latest_date else None
    )
