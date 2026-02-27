"""
价格展示API
提供5个图表所需的数据接口：
1. 全国猪价（季节性）
2. 标肥价差（季节性）
3. 猪价&标肥价差（可年度筛选）
4. 日度屠宰量（农历）
5. 标肥价差（分省区）
6. 区域价差（季节性）
"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime
import re
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, extract, text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.sys_user import SysUser
from app.models.fact_observation import FactObservation
from app.models.fact_observation_tag import FactObservationTag
from app.models.dim_metric import DimMetric
from app.models.dim_region import DimRegion
from app.models.dim_geo import DimGeo
from app.services.lunar_alignment_service import (
    solar_to_lunar,
    _calculate_lunar_day_index,
    get_leap_month_info,
    get_lunar_year_date_range
)
from app.utils.price_display_utils import resolve_update_time

router = APIRouter(prefix="/api/v1/price-display", tags=["price-display"])


def get_source_name_from_metric(metric: DimMetric) -> str:
    """
    从DimMetric推断数据来源名称（标准化）
    
    根据sheet_name或其他字段判断数据来源：
    - 钢联相关sheet -> "钢联"
    - 涌益相关sheet -> "涌益"
    """
    if not metric:
        return "未知"
    
    sheet_name = metric.sheet_name or ""
    
    # 钢联数据源
    if any(keyword in sheet_name for keyword in ["分省区猪价", "肥标价差", "毛白价差", "区域价差"]):
        return "钢联"
    
    # 涌益数据源
    if any(keyword in sheet_name for keyword in ["价格+宰量", "涌益"]):
        return "涌益"
    
    # 默认返回钢联（大部分数据来自钢联）
    return "钢联"


def format_update_date(date_obj: Optional[date]) -> Optional[str]:
    """
    格式化更新日期（只显示年月日，不显示时刻）
    
    返回格式：YYYY年MM月DD日
    """
    if not date_obj:
        return None
    
    return f"{date_obj.year}年{date_obj.month:02d}月{date_obj.day:02d}日"


@router.get("/test")
async def test_price_display():
    """测试端点，验证路由是否工作"""
    return {"status": "ok", "message": "Price display API is working"}


class SeasonalityDataPoint(BaseModel):
    """季节性数据点"""
    year: int
    month_day: str  # "MM-DD"格式
    value: Optional[float]
    lunar_day_index: Optional[int] = None  # 农历日期索引（用于农历对齐）


class SeasonalitySeries(BaseModel):
    """季节性数据系列"""
    year: int
    data: List[SeasonalityDataPoint]
    color: Optional[str] = None
    is_leap_month: Optional[bool] = False  # 是否为闰月系列
    leap_month: Optional[int] = None  # 如果是闰月，记录闰月月份


class SeasonalityResponse(BaseModel):
    """季节性数据响应"""
    metric_name: str
    unit: str
    series: List[SeasonalitySeries]
    update_time: Optional[str] = None
    latest_date: Optional[str] = None


class PriceSpreadResponse(BaseModel):
    """价格和价差响应"""
    price_data: List[Dict[str, Any]]  # 价格数据
    spread_data: List[Dict[str, Any]]  # 价差数据
    available_years: List[int]  # 可用年份
    update_time: Optional[str] = None


class SlaughterLunarResponse(BaseModel):
    """日度屠宰量（农历）响应"""
    metric_name: str
    unit: str
    series: List[SeasonalitySeries]
    update_time: Optional[str] = None
    latest_date: Optional[str] = None
    x_axis_labels: Optional[Dict[int, str]] = None  # 索引到农历日期标签的映射，如 {1: "正月初八", 30: "二月初一"}


class SlaughterPriceTrendResponse(BaseModel):
    """屠宰量&价格走势响应（农历年度日期范围）"""
    slaughter_data: List[Dict[str, Any]]
    price_data: List[Dict[str, Any]]
    available_lunar_years: List[int]
    update_time: Optional[str] = None
    latest_date: Optional[str] = None


class LiveWhiteSpreadDualAxisResponse(BaseModel):
    """毛白价差双轴数据响应"""
    spread_data: List[Dict[str, Any]]  # 毛白价差数据 [{date, value}]
    ratio_data: List[Dict[str, Any]]  # 价差比率数据 [{date, value}]
    spread_unit: str  # 毛白价差单位
    ratio_unit: str  # 价差比率单位
    update_time: Optional[str] = None
    latest_date: Optional[str] = None


@router.get("/slaughter-price-trend/lunar-year", response_model=SlaughterPriceTrendResponse)
async def get_slaughter_price_trend_lunar_year(
    lunar_year: Optional[int] = Query(None, description="农历年份（如2024），如果为None则返回所有可用年份"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取屠宰量&价格走势数据（农历年度日期范围）
    
    日期范围：每年2月20日至次年2月10日
    条件：
    - 2月20日必须对应农历的正月
    - 2月10日（次年）必须对应农历的腊月或之前
    
    图例年份为农历年份
    """
    # 查询日度屠宰量指标（优先 _1 全量，再 _2，与 /slaughter/lunar 一致）
    slaughter_metric = db.query(DimMetric).filter(
        func.json_extract(DimMetric.parse_json, '$.metric_key') == 'YY_D_SLAUGHTER_TOTAL_1',
        DimMetric.sheet_name == "价格+宰量",
        DimMetric.freq == "D"
    ).first()
    if not slaughter_metric:
        slaughter_metric = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, '$.metric_key') == 'YY_D_SLAUGHTER_TOTAL_2',
            DimMetric.freq == "D"
        ).first()
    if not slaughter_metric:
        slaughter_metric = db.query(DimMetric).filter(
            DimMetric.metric_name.like("%屠宰量%"),
            DimMetric.sheet_name == "价格+宰量",
            DimMetric.freq == "D"
        ).first()
    if not slaughter_metric:
        slaughter_metric = db.query(DimMetric).filter(
            or_(
                DimMetric.raw_header.like("%屠宰量%"),
                DimMetric.raw_header.like("%宰量%")
            ),
            DimMetric.sheet_name == "价格+宰量",
            DimMetric.freq == "D"
        ).first()
    # 查询价格指标
    price_metric = db.query(DimMetric).filter(
        DimMetric.metric_name.like("%价格%"),
        DimMetric.sheet_name == "价格+宰量",
        DimMetric.freq == "D"
    ).first()
    
    if not slaughter_metric:
        raise HTTPException(status_code=404, detail="未找到日度屠宰量指标")
    if not price_metric:
        raise HTTPException(status_code=404, detail="未找到价格指标")
    
    # 获取可用的农历年份范围（最近5年）
    current_solar_year = datetime.now().year
    lunar_years_to_check = list(range(current_solar_year - 2, current_solar_year + 3))
    
    # 查找符合条件的农历年度日期范围
    valid_lunar_years: List[int] = []
    lunar_year_ranges: Dict[int, Tuple[date, date]] = {}
    
    for check_year in lunar_years_to_check:
        date_range = get_lunar_year_date_range(check_year)
        if date_range:
            valid_lunar_years.append(check_year)
            lunar_year_ranges[check_year] = date_range
    
    if not valid_lunar_years:
        return SlaughterPriceTrendResponse(
            slaughter_data=[],
            price_data=[],
            available_lunar_years=[],
            update_time=None,
            latest_date=None
        )
    
    # 如果指定了lunar_year，只查询该年份
    if lunar_year is not None:
        if lunar_year not in valid_lunar_years:
            raise HTTPException(status_code=400, detail=f"农历年份{lunar_year}不符合条件或没有数据")
        valid_lunar_years = [lunar_year]
    
    # 查询所有符合条件的日期范围的数据
    all_start_dates = [r[0] for r in lunar_year_ranges.values()]
    all_end_dates = [r[1] for r in lunar_year_ranges.values()]
    min_start_date = min(all_start_dates)
    max_end_date = max(all_end_dates)
    
    # 查询屠宰量数据
    slaughter_query = db.query(FactObservation).filter(
        FactObservation.metric_id == slaughter_metric.id,
        FactObservation.period_type == "day",
        FactObservation.obs_date >= min_start_date,
        FactObservation.obs_date <= max_end_date
    )
    slaughter_obs = slaughter_query.order_by(FactObservation.obs_date).all()
    
    # 查询价格数据
    price_query = db.query(FactObservation).filter(
        FactObservation.metric_id == price_metric.id,
        FactObservation.period_type == "day",
        FactObservation.obs_date >= min_start_date,
        FactObservation.obs_date <= max_end_date
    )
    price_obs = price_query.order_by(FactObservation.obs_date).all()
    
    # 构建响应数据：按农历年度分组
    slaughter_data: List[Dict[str, Any]] = []
    price_data: List[Dict[str, Any]] = []
    
    for lunar_year_val in valid_lunar_years:
        start_date, end_date = lunar_year_ranges[lunar_year_val]
        
        # 筛选该农历年度范围内的数据
        for obs in slaughter_obs:
            if start_date <= obs.obs_date <= end_date:
                slaughter_data.append({
                    "date": obs.obs_date.isoformat(),
                    "year": lunar_year_val,  # 使用农历年份
                    "value": float(obs.value) if obs.value is not None else None
                })
        
        for obs in price_obs:
            if start_date <= obs.obs_date <= end_date:
                price_data.append({
                    "date": obs.obs_date.isoformat(),
                    "year": lunar_year_val,  # 使用农历年份
                    "value": float(obs.value) if obs.value is not None else None
                })
    
    # 获取最新日期
    latest_date = None
    if slaughter_obs:
        latest_date = slaughter_obs[-1].obs_date.isoformat()
    elif price_obs:
        latest_date = price_obs[-1].obs_date.isoformat()
    
    return SlaughterPriceTrendResponse(
        slaughter_data=slaughter_data,
        price_data=price_data,
        available_lunar_years=valid_lunar_years,
        update_time=latest_date,
        latest_date=latest_date
    )


class ProvinceSpreadInfo(BaseModel):
    """省区标肥价差信息"""
    province_name: str  # 省区名称
    province_code: Optional[str] = None  # 省区代码
    metric_id: int  # 指标ID
    latest_date: Optional[str] = None  # 最新数据日期
    latest_value: Optional[float] = None  # 最新值


class ProvinceSpreadListResponse(BaseModel):
    """省区标肥价差列表响应"""
    provinces: List[ProvinceSpreadInfo]
    unit: str


@router.get("/fat-std-spread/provinces", response_model=ProvinceSpreadListResponse)
async def get_fat_std_spread_provinces(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取所有有标肥价差数据的省区列表
    
    从"肥标价差"sheet中查找所有省区的指标
    """
    # 查询"肥标价差"sheet下的所有指标（排除"中国"）
    metrics = db.query(DimMetric).filter(
        DimMetric.sheet_name == "肥标价差",
        ~DimMetric.raw_header.like("%中国%")
    ).all()
    
    if not metrics:
        return ProvinceSpreadListResponse(provinces=[], unit="元/公斤")
    
    # 提取省区名称并获取最新数据
    provinces_info = []
    unit = "元/公斤"
    
    for metric in metrics:
        # 从raw_header中提取省区名称，例如："生猪标肥：价差：四川（日）" -> "四川"
        raw_header = metric.raw_header
        province_name = None
        
        # 尝试提取省区名称（在"："和"（"之间）
        match = re.search(r'：([^：（）]+)（', raw_header)
        if match:
            province_name = match.group(1).strip()
        else:
            # 如果没有匹配到，尝试其他方式
            # 查找常见的省份名称
            provinces_list = ["四川", "贵州", "重庆", "湖南", "江西", "湖北", "河北", "河南", 
                            "山东", "山西", "辽宁", "吉林", "黑龙江"]
            for p in provinces_list:
                if p in raw_header:
                    province_name = p
                    break
        
        if not province_name:
            continue
        
        # 获取最新数据
        latest_obs = db.query(FactObservation).filter(
            FactObservation.metric_id == metric.id
        ).order_by(FactObservation.obs_date.desc()).first()
        
        unit = metric.unit or "元/公斤"
        
        provinces_info.append(ProvinceSpreadInfo(
            province_name=province_name,
            metric_id=metric.id,
            latest_date=latest_obs.obs_date.isoformat() if latest_obs else None,
            latest_value=float(latest_obs.value) if latest_obs and latest_obs.value else None
        ))
    
    # 按省区名称排序
    provinces_info.sort(key=lambda x: x.province_name)
    
    return ProvinceSpreadListResponse(provinces=provinces_info, unit=unit)


@router.get("/fat-std-spread/province/{province_name}/seasonality", response_model=SeasonalityResponse)
async def get_fat_std_spread_province_seasonality(
    province_name: str,
    start_year: Optional[int] = Query(None, description="起始年份"),
    end_year: Optional[int] = Query(None, description="结束年份"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取指定省区的标肥价差季节性数据
    
    返回按年份对齐的季节性数据
    """
    # 查询指定省区的标肥价差指标
    metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "肥标价差",
        DimMetric.raw_header.like(f"%{province_name}%")
    ).first()
    
    if not metric:
        raise HTTPException(status_code=404, detail=f"未找到{province_name}的标肥价差指标")
    
    # 构建查询
    query = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.period_type == "day"
    )
    
    if start_year:
        query = query.filter(extract('year', FactObservation.obs_date) >= start_year)
    if end_year:
        query = query.filter(extract('year', FactObservation.obs_date) <= end_year)
    
    observations = query.order_by(FactObservation.obs_date).all()
    
    if not observations:
        return SeasonalityResponse(
            metric_name=f"{province_name}标肥价差",
            unit=metric.unit or "元/公斤",
            series=[],
            update_time=None,
            latest_date=None
        )
    
    # 按年份分组
    year_data: Dict[int, List[Dict]] = {}
    for obs in observations:
        year = obs.obs_date.year
        if year not in year_data:
            year_data[year] = []
        
        month_day = obs.obs_date.strftime("%m-%d")
        year_data[year].append({
            "month_day": month_day,
            "value": float(obs.value) if obs.value else None,
            "date": obs.obs_date
        })
    
    # 构建响应
    series = []
    for year in sorted(year_data.keys()):
        data_points = []
        for item in sorted(year_data[year], key=lambda x: x["date"]):
            data_points.append(SeasonalityDataPoint(
                year=year,
                month_day=item["month_day"],
                value=item["value"]
            ))
        
        series.append(SeasonalitySeries(
            year=year,
            data=data_points
        ))
    
    latest_obs = observations[-1] if observations else None
    update_time = resolve_update_time(metric, latest_obs) if latest_obs else None
    if not update_time and latest_obs:
        update_time = latest_obs.obs_date.isoformat()
    
    return SeasonalityResponse(
        metric_name=f"{province_name}标肥价差",
        unit=metric.unit or "元/公斤",
        series=series,
        update_time=update_time,
        latest_date=update_time
    )


@router.get("/fat-std-spread/province/{province_name}/changes")
async def get_fat_std_spread_province_changes(
    province_name: str,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取指定省区标肥价差的涨跌数据
    
    返回5日/10日涨跌幅
    """
    # 查询指定省区的标肥价差指标
    metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "肥标价差",
        DimMetric.raw_header.like(f"%{province_name}%")
    ).first()
    
    if not metric:
        raise HTTPException(status_code=404, detail=f"未找到{province_name}的标肥价差指标")
    
    # 获取最新数据
    latest_obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id
    ).order_by(FactObservation.obs_date.desc()).first()
    
    if not latest_obs:
        return {
            "current_value": None,
            "day5_change": None,
            "day10_change": None
        }
    
    latest_date = latest_obs.obs_date
    latest_value = float(latest_obs.value) if latest_obs.value else None
    
    # 查询5日/10日前的数据
    day5_date = date.fromordinal(latest_date.toordinal() - 5)
    day10_date = date.fromordinal(latest_date.toordinal() - 10)
    
    day5_obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date == day5_date
    ).first()
    
    day10_obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date == day10_date
    ).first()
    
    # 计算涨跌
    day5_change = None
    day10_change = None
    
    if latest_value is not None:
        if day5_obs and day5_obs.value:
            day5_change = latest_value - float(day5_obs.value)
        if day10_obs and day10_obs.value:
            day10_change = latest_value - float(day10_obs.value)
    
    return {
        "current_value": latest_value,
        "latest_date": latest_date.isoformat(),
        "day5_change": day5_change,
        "day10_change": day10_change,
        "unit": metric.unit or "元/公斤"
    }


@router.get("/region-spread/seasonality", response_model=SeasonalityResponse)
async def get_region_spread_seasonality(
    region_pair: str = Query(..., description="区域对，格式：XX-YY，如'广东-广西'"),
    start_year: Optional[int] = Query(None, description="起始年份"),
    end_year: Optional[int] = Query(None, description="结束年份"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取区域价差季节性数据
    
    返回指定区域对的季节性价差数据，支持按年份筛选
    """
    # 解析区域对
    regions = region_pair.split('-')
    if len(regions) != 2:
        raise HTTPException(status_code=400, detail="区域对格式错误，应为'XX-YY'格式")
    
    region1, region2 = regions[0].strip(), regions[1].strip()
    
    # 查询区域价差指标
    # 数据库中metric_name是"出栏均价"，需要通过raw_header匹配
    # raw_header格式：商品猪：出栏均价：广东（日） - 商品猪：出栏均价：广西（日）
    metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "区域价差",
        DimMetric.raw_header.like(f"%{region1}%"),
        DimMetric.raw_header.like(f"%{region2}%")
    ).first()
    
    if not metric:
        raise HTTPException(status_code=404, detail=f"未找到区域价差指标：{region_pair}")
    
    # 构建查询
    query = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.period_type == "day"
    )
    
    if start_year:
        query = query.filter(extract('year', FactObservation.obs_date) >= start_year)
    if end_year:
        query = query.filter(extract('year', FactObservation.obs_date) <= end_year)
    
    observations = query.order_by(FactObservation.obs_date).all()
    
    if not observations:
        return SeasonalityResponse(
            metric_name=metric.metric_name,
            unit=metric.unit or "元/公斤",
            series=[],
            update_time=None,
            latest_date=None
        )
    
    # 按年份分组
    year_data: Dict[int, List[Dict]] = {}
    for obs in observations:
        year = obs.obs_date.year
        if year not in year_data:
            year_data[year] = []
        
        month_day = obs.obs_date.strftime("%m-%d")
        year_data[year].append({
            "month_day": month_day,
            "value": float(obs.value) if obs.value else None,
            "date": obs.obs_date
        })
    
    # 构建响应
    series = []
    for year in sorted(year_data.keys()):
        data_points = []
        for item in sorted(year_data[year], key=lambda x: x["date"]):
            data_points.append(SeasonalityDataPoint(
                year=year,
                month_day=item["month_day"],
                value=item["value"]
            ))
        
        series.append(SeasonalitySeries(
            year=year,
            data=data_points
        ))
    
    latest_obs = observations[-1] if observations else None
    update_time = resolve_update_time(metric, latest_obs) if latest_obs else None
    if not update_time and latest_obs:
        update_time = latest_obs.obs_date.isoformat()
    
    return SeasonalityResponse(
        metric_name=metric.metric_name,
        unit=metric.unit or "元/公斤",
        series=series,
        update_time=update_time,
        latest_date=update_time
    )


@router.get("/region-spread/changes")
async def get_region_spread_changes(
    region_pair: str = Query(..., description="区域对，格式：XX-YY，如'广东-广西'"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取区域价差的涨跌数据
    
    返回5日/10日涨跌幅
    注释：5日涨跌，10日涨跌
    """
    # 解析区域对
    regions = region_pair.split('-')
    if len(regions) != 2:
        raise HTTPException(status_code=400, detail="区域对格式错误，应为'XX-YY'格式")
    
    region1, region2 = regions[0].strip(), regions[1].strip()
    
    # 查询区域价差指标
    # 数据库中metric_name是"出栏均价"，需要通过raw_header匹配
    # raw_header格式：商品猪：出栏均价：广东（日） - 商品猪：出栏均价：广西（日）
    metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "区域价差",
        DimMetric.raw_header.like(f"%{region1}%"),
        DimMetric.raw_header.like(f"%{region2}%")
    ).first()
    
    if not metric:
        raise HTTPException(status_code=404, detail=f"未找到区域价差指标：{region_pair}")
    
    # 获取最新数据
    latest_obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id
    ).order_by(FactObservation.obs_date.desc()).first()
    
    if not latest_obs:
        return {
            "current_value": None,
            "latest_date": None,
            "day5_change": None,
            "day10_change": None,
            "unit": metric.unit or "元/公斤"
        }
    
    latest_date = latest_obs.obs_date
    latest_value = float(latest_obs.value) if latest_obs.value else None
    
    # 查询5日/10日前的数据
    day5_date = date.fromordinal(latest_date.toordinal() - 5)
    day10_date = date.fromordinal(latest_date.toordinal() - 10)
    
    day5_obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date == day5_date
    ).first()
    
    day10_obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date == day10_date
    ).first()
    
    # 计算涨跌
    day5_change = None
    day10_change = None
    
    if latest_value is not None:
        if day5_obs and day5_obs.value:
            day5_change = latest_value - float(day5_obs.value)
        if day10_obs and day10_obs.value:
            day10_change = latest_value - float(day10_obs.value)
    
    return {
        "current_value": latest_value,
        "latest_date": latest_date.isoformat(),
        "day5_change": day5_change,
        "day10_change": day10_change,
        "unit": metric.unit or "元/公斤"
    }


@router.get("/live-white-spread/dual-axis", response_model=LiveWhiteSpreadDualAxisResponse)
async def get_live_white_spread_dual_axis(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取毛白价差双轴数据
    
    返回毛白价差和价差比率的时间序列数据，支持时间范围筛选
    左轴：毛白价差
    右轴：价差比率
    """
    # 查询毛白价差指标
    spread_metric = db.query(DimMetric).filter(
        DimMetric.raw_header == "毛白：价差：中国（日）",
        DimMetric.sheet_name == "毛白价差"
    ).first()
    
    # 查询价差比率指标
    ratio_metric = db.query(DimMetric).filter(
        DimMetric.raw_header == "毛白：价差：中国（日） / 商品猪：出栏均价：中国（日）",
        DimMetric.sheet_name == "毛白价差"
    ).first()
    
    if not spread_metric:
        raise HTTPException(status_code=404, detail="未找到毛白价差指标")
    
    if not ratio_metric:
        raise HTTPException(status_code=404, detail="未找到价差比率指标")
    
    # 构建查询
    spread_query = db.query(FactObservation).filter(
        FactObservation.metric_id == spread_metric.id,
        FactObservation.period_type == "day"
    )
    
    ratio_query = db.query(FactObservation).filter(
        FactObservation.metric_id == ratio_metric.id,
        FactObservation.period_type == "day"
    )
    
    # 应用时间范围筛选
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            spread_query = spread_query.filter(FactObservation.obs_date >= start_dt)
            ratio_query = ratio_query.filter(FactObservation.obs_date >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="起始日期格式错误，应为YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            spread_query = spread_query.filter(FactObservation.obs_date <= end_dt)
            ratio_query = ratio_query.filter(FactObservation.obs_date <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误，应为YYYY-MM-DD")
    
    # 获取数据
    spread_obs = spread_query.order_by(FactObservation.obs_date).all()
    ratio_obs = ratio_query.order_by(FactObservation.obs_date).all()
    
    # 构建响应数据
    spread_data = [
        {
            "date": obs.obs_date.isoformat(),
            "value": float(obs.value) if obs.value is not None else None
        }
        for obs in spread_obs
    ]
    
    ratio_data = [
        {
            "date": obs.obs_date.isoformat(),
            "value": float(obs.value) if obs.value is not None else None
        }
        for obs in ratio_obs
    ]
    
    # 获取最新日期（优先使用 Excel 更新时间 source_updated_at）
    latest_date = None
    if spread_obs:
        latest_date = resolve_update_time(spread_metric, spread_obs[-1])
    if not latest_date and ratio_obs:
        latest_date = resolve_update_time(ratio_metric, ratio_obs[-1])
    if not latest_date and spread_obs:
        latest_date = spread_obs[-1].obs_date.isoformat()
    elif not latest_date and ratio_obs:
        latest_date = ratio_obs[-1].obs_date.isoformat()
    
    return LiveWhiteSpreadDualAxisResponse(
        spread_data=spread_data,
        ratio_data=ratio_data,
        spread_unit=spread_metric.unit or "元/公斤",
        ratio_unit=ratio_metric.unit or "元/公斤",
        update_time=latest_date,
        latest_date=latest_date
    )


class FrozenInventoryProvinceInfo(BaseModel):
    """冻品库容率省份信息"""
    province_name: str
    metric_id: int
    latest_date: Optional[str] = None
    latest_value: Optional[float] = None


class FrozenInventoryProvinceListResponse(BaseModel):
    """冻品库容率省份列表响应"""
    provinces: List[FrozenInventoryProvinceInfo]
    unit: str


class FrozenInventorySeasonalityResponse(BaseModel):
    """冻品库容率季节性数据响应（包含涨跌信息）"""
    metric_name: str
    unit: str
    province_name: str
    series: List[SeasonalitySeries]
    update_time: Optional[str] = None
    latest_date: Optional[str] = None
    # 涨跌信息
    period_change: Optional[float] = None  # 本期涨跌（较上期）
    yoy_change: Optional[float] = None  # 较去年同期涨跌


@router.get("/frozen-inventory/provinces", response_model=FrozenInventoryProvinceListResponse)
async def get_frozen_inventory_provinces(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取所有有冻品库容率数据的省份列表
    
    从"周度-冻品库存"sheet中查找所有省份的数据
    """
    # 查询"周度-冻品库存"sheet下的指标
    metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "周度-冻品库存",
        func.json_unquote(
            func.json_extract(DimMetric.parse_json, '$.metric_key')
        ) == "YY_W_FROZEN_INVENTORY_RATIO"
    ).first()
    
    if not metric:
        return FrozenInventoryProvinceListResponse(provinces=[], unit="ratio")
    
    # 查询所有有数据的省份（通过geo_id关联）
    # 使用period_end而不是obs_date，因为周度数据使用period_end
    provinces_query = db.query(
        DimGeo.province,
        func.max(FactObservation.period_end).label("latest_date"),
        func.max(FactObservation.value).label("latest_value")
    ).join(
        FactObservation, FactObservation.geo_id == DimGeo.id
    ).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.period_type == "week"
    ).group_by(DimGeo.province).order_by(DimGeo.province)
    
    provinces_result = provinces_query.all()
    
    provinces_info = []
    unit = metric.unit or "ratio"
    
    for row in provinces_result:
        province_name = row.province
        latest_date = row.latest_date.isoformat() if row.latest_date else None
        latest_value = float(row.latest_value) if row.latest_value else None
        
        provinces_info.append(FrozenInventoryProvinceInfo(
            province_name=province_name,
            metric_id=metric.id,
            latest_date=latest_date,
            latest_value=latest_value
        ))
    
    return FrozenInventoryProvinceListResponse(provinces=provinces_info, unit=unit)


@router.get("/frozen-inventory/province/{province_name}/seasonality", response_model=FrozenInventorySeasonalityResponse)
async def get_frozen_inventory_province_seasonality(
    province_name: str,
    start_year: Optional[int] = Query(None, description="起始年份"),
    end_year: Optional[int] = Query(None, description="结束年份"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取指定省份的冻品库容率季节性数据
    
    返回按年份对齐的季节性数据，包含涨跌信息
    """
    # 查询"周度-冻品库存"sheet下的指标
    metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "周度-冻品库存",
        func.json_unquote(
            func.json_extract(DimMetric.parse_json, '$.metric_key')
        ) == "YY_W_FROZEN_INVENTORY_RATIO"
    ).first()
    
    if not metric:
        raise HTTPException(status_code=404, detail="未找到冻品库容率指标")
    
    # 查询省份的geo_id
    geo = db.query(DimGeo).filter(DimGeo.province == province_name).first()
    if not geo:
        raise HTTPException(status_code=404, detail=f"未找到省份：{province_name}")
    
    # 构建查询
    query = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.geo_id == geo.id,
        FactObservation.period_type == "week"
    )
    
    # 应用年份筛选
    if start_year:
        query = query.filter(extract('year', FactObservation.period_end) >= start_year)
    if end_year:
        query = query.filter(extract('year', FactObservation.period_end) <= end_year)
    
    observations = query.order_by(FactObservation.period_end).all()
    
    if not observations:
        return FrozenInventorySeasonalityResponse(
            metric_name=metric.metric_name or "冻品库容率",
            unit=metric.unit or "ratio",
            province_name=province_name,
            series=[],
            update_time=None,
            latest_date=None,
            period_change=None,
            yoy_change=None
        )
    
    # 计算涨跌信息
    # 1. 本期涨跌（较上期）
    latest_obs = observations[-1]
    period_change = None
    if len(observations) >= 2:
        prev_obs = observations[-2]
        if latest_obs.value is not None and prev_obs.value is not None:
            period_change = float(latest_obs.value) - float(prev_obs.value)
    
    # 2. 较去年同期涨跌
    yoy_change = None
    if latest_obs.period_end:
        latest_year = latest_obs.period_end.year
        latest_week = latest_obs.period_end.isocalendar()[1]  # ISO周序号
        
        # 查找去年同期的数据
        for obs in observations:
            if obs.period_end:
                obs_year = obs.period_end.year
                obs_week = obs.period_end.isocalendar()[1]
                if obs_year == latest_year - 1 and obs_week == latest_week:
                    if latest_obs.value is not None and obs.value is not None:
                        yoy_change = float(latest_obs.value) - float(obs.value)
                    break
    
    # 按年份和周序号分组（周度数据使用周序号）
    year_data: Dict[int, Dict[int, List[float]]] = {}  # {year: {week: [values]}}
    
    for obs in observations:
        if obs.period_end:
            year = obs.period_end.year
            if year not in year_data:
                year_data[year] = {}
            
            # 计算ISO周序号
            week_of_year = obs.period_end.isocalendar()[1]
            # 限制在1-52范围内
            week_of_year = max(1, min(52, week_of_year))
            
            if week_of_year not in year_data[year]:
                year_data[year][week_of_year] = []
            
            if obs.value is not None:
                year_data[year][week_of_year].append(float(obs.value))
    
    # 构建响应（使用周序号，但为了兼容性，month_day使用period_end的月-日）
    series = []
    for year in sorted(year_data.keys()):
        data_points = []
        # 遍历1-52周
        for week in range(1, 53):
            week_values = year_data[year].get(week, [])
            if week_values:
                # 如果有多个值，取平均值（周度数据通常只有一个值）
                value = sum(week_values) / len(week_values)
            else:
                value = None
            
            # 为了兼容SeasonalityDataPoint格式，需要month_day
            # 使用该周的第一天（简化处理：year年第week周的第一天）
            from datetime import datetime, timedelta
            jan1 = datetime(year, 1, 1)
            # 计算该周的第一天（周一）
            days_offset = (week - 1) * 7 - jan1.weekday()
            week_start = jan1 + timedelta(days=days_offset)
            month_day = week_start.strftime("%m-%d")
            
            data_points.append(SeasonalityDataPoint(
                year=year,
                month_day=month_day,
                value=value
            ))
        
        series.append(SeasonalitySeries(
            year=year,
            data=data_points
        ))
    
    # 获取更新时间
    latest_date = latest_obs.period_end.isoformat() if latest_obs.period_end else None
    
    return FrozenInventorySeasonalityResponse(
        metric_name=metric.metric_name or "冻品库容率",
        unit=metric.unit or "ratio",
        province_name=province_name,
        series=series,
        update_time=latest_date,
        latest_date=latest_date,
        period_change=period_change,
        yoy_change=yoy_change
    )


# 产业链数据指标映射配置
# 注意：profit_type的值来自Excel文件"养殖利润（周度）"sheet的第2行（指标名称行）
INDUSTRY_CHAIN_METRICS = {
    "二元母猪价格": "二元母猪：每头重50kg：样本养殖企业：均价：中国（周）",
    "仔猪价格": "仔猪：每头重7kg：规模化养殖场：出栏均价：中国（周）",
    "淘汰母猪价格": "淘汰母猪：样本养殖企业：均价：中国（周）",
    "淘汰母猪折扣率": "淘汰母猪：样本养殖企业：均价：中国（周） / 标猪：市场价：中国（日）",
    "猪料比": "生猪饲料：比价：中国（周）",
    "屠宰利润": "猪：屠宰利润（周）",
    "自养利润": "猪：外购利润（周）",  # 注意：根据实际Excel数据，可能需要调整为"自繁自养利润"等
    "代养利润": "猪：外购利润（周）",  # 注意：根据实际Excel数据，可能需要调整为"代养利润"等
    "白条价格": "白条肉：前三级：均价：中国（日）（变频周平均值）",
    "1#鲜肉价格": "鲜猪肉：1号：市场均价：中国（周）",
    "2#冻肉价格": "冻肉：2号：市场价：中国（日）（变频周平均值）",
    "4#冻肉价格": "冻肉：4号：市场价：中国（日）（变频周平均值）",
    "2号冻肉/1#鲜肉": None,  # 需要计算：2#冻肉价格 / 1#鲜肉价格
    "4#冻肉/白条": None,  # 需要计算：4#冻肉价格 / 白条价格
    "冻品库容率": None  # 不在这个sheet中，需要从其他表查询（yongyi_weekly_frozen_inventory）
}


class IndustryChainSeasonalityResponse(BaseModel):
    """产业链数据季节性数据响应（包含涨跌信息）"""
    metric_name: str
    unit: str
    series: List[SeasonalitySeries]
    update_time: Optional[str] = None
    latest_date: Optional[str] = None
    # 涨跌信息
    period_change: Optional[float] = None  # 本期涨跌（较上期）
    yoy_change: Optional[float] = None  # 较去年同期涨跌


@router.get("/industry-chain/seasonality", response_model=IndustryChainSeasonalityResponse)
async def get_industry_chain_seasonality(
    metric_name: str = Query(..., description="指标名称"),
    start_year: Optional[int] = Query(None, description="起始年份"),
    end_year: Optional[int] = Query(None, description="结束年份"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取产业链数据季节性数据（周度1-52周）
    
    支持的指标：
    - 二元母猪价格
    - 仔猪价格
    - 淘汰母猪价格
    - 淘汰母猪折扣率
    - 猪料比
    - 屠宰利润
    - 自养利润
    - 代养利润
    - 白条价格
    - 1#鲜肉价格
    - 2#冻肉价格
    - 4#冻肉价格
    - 2号冻肉/1#鲜肉（计算指标）
    - 4#冻肉/白条（计算指标）
    - 冻品库容率（从其他表查询）
    """
    # #region agent log
    import json
    import urllib.parse
    try:
        with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "price_display.py:1365",
                "message": "API called with metric_name",
                "data": {
                    "metric_name": metric_name,
                    "metric_name_repr": repr(metric_name),
                    "metric_name_encoded": urllib.parse.quote(metric_name),
                    "start_year": start_year,
                    "end_year": end_year
                },
                "timestamp": int(__import__('time').time() * 1000)
            }, ensure_ascii=False) + '\n')
    except Exception:
        pass
    # #endregion
    
    # 获取profit_type
    profit_type = INDUSTRY_CHAIN_METRICS.get(metric_name)
    
    # #region agent log
    try:
        with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B",
                "location": "price_display.py:1394",
                "message": "profit_type lookup result",
                "data": {
                    "metric_name": metric_name,
                    "profit_type": profit_type,
                    "is_none": profit_type is None,
                    "available_keys": list(INDUSTRY_CHAIN_METRICS.keys())
                },
                "timestamp": int(__import__('time').time() * 1000)
            }, ensure_ascii=False) + '\n')
    except Exception:
        pass
    # #endregion
    
    if profit_type is None:
        # #region agent log
        try:
            with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "C",
                    "location": "price_display.py:1396",
                    "message": "Entering special handling for calculated metrics",
                    "data": {
                        "metric_name": metric_name,
                        "matches_2号冻肉": metric_name == "2号冻肉/1#鲜肉",
                        "matches_4#冻肉": metric_name == "4#冻肉/白条",
                        "matches_冻品库容率": metric_name == "冻品库容率"
                    },
                    "timestamp": int(__import__('time').time() * 1000)
                }, ensure_ascii=False) + '\n')
        except Exception:
            pass
        # #endregion
        
        # 对于计算指标，需要特殊处理
        if metric_name == "2号冻肉/1#鲜肉":
            # #region agent log
            try:
                with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                        "location": "price_display.py:1398",
                        "message": "Calling _get_calculated_metric_seasonality for 2号冻肉/1#鲜肉",
                        "data": {
                            "numerator": "2#冻肉价格",
                            "denominator": "1#鲜肉价格"
                        },
                        "timestamp": int(__import__('time').time() * 1000)
                    }, ensure_ascii=False) + '\n')
            except Exception:
                pass
            # #endregion
            # 需要查询两个指标并计算比值
            try:
                result = await _get_calculated_metric_seasonality(
                    db, "2#冻肉价格", "1#鲜肉价格", metric_name, start_year, end_year, operation="divide"
                )
                # #region agent log
                try:
                    with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "D",
                            "location": "price_display.py:1400",
                            "message": "_get_calculated_metric_seasonality returned successfully",
                            "data": {
                                "series_count": len(result.series) if result.series else 0
                            },
                            "timestamp": int(__import__('time').time() * 1000)
                        }, ensure_ascii=False) + '\n')
                except Exception:
                    pass
                # #endregion
                return result
            except Exception as e:
                # #region agent log
                try:
                    with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "D",
                            "location": "price_display.py:1400",
                            "message": "_get_calculated_metric_seasonality raised exception",
                            "data": {
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            },
                            "timestamp": int(__import__('time').time() * 1000)
                        }, ensure_ascii=False) + '\n')
                except Exception:
                    pass
                # #endregion
                raise
        elif metric_name == "4#冻肉/白条":
            # #region agent log
            try:
                with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "E",
                        "location": "price_display.py:1403",
                        "message": "Calling _get_calculated_metric_seasonality for 4#冻肉/白条",
                        "data": {
                            "numerator": "4#冻肉价格",
                            "denominator": "白条价格"
                        },
                        "timestamp": int(__import__('time').time() * 1000)
                    }, ensure_ascii=False) + '\n')
            except Exception:
                pass
            # #endregion
            try:
                result = await _get_calculated_metric_seasonality(
                    db, "4#冻肉价格", "白条价格", metric_name, start_year, end_year, operation="divide"
                )
                # #region agent log
                try:
                    with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "E",
                            "location": "price_display.py:1405",
                            "message": "_get_calculated_metric_seasonality returned successfully",
                            "data": {
                                "series_count": len(result.series) if result.series else 0
                            },
                            "timestamp": int(__import__('time').time() * 1000)
                        }, ensure_ascii=False) + '\n')
                except Exception:
                    pass
                # #endregion
                return result
            except Exception as e:
                # #region agent log
                try:
                    with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "E",
                            "location": "price_display.py:1405",
                            "message": "_get_calculated_metric_seasonality raised exception",
                            "data": {
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            },
                            "timestamp": int(__import__('time').time() * 1000)
                        }, ensure_ascii=False) + '\n')
                except Exception:
                    pass
                # #endregion
                raise
        elif metric_name == "冻品库容率":
            # 冻品库容率从fact_observation表查询（钢联数据）
            # 查询指标：sheet_name="冻品库容率"，metric_key="GL_W_FROZEN_CAPACITY_RATE"
            metric = db.query(DimMetric).filter(
                DimMetric.sheet_name == "冻品库容率",
                DimMetric.raw_header.like("%库容率%中国%")
            ).first()
            
            if not metric:
                # 如果找不到，返回空数据
                return IndustryChainSeasonalityResponse(
                    metric_name="冻品库容率",
                    unit="%",
                    series=[],
                    update_time=None,
                    latest_date=None,
                    period_change=None,
                    yoy_change=None
                )
            
            # 查询fact_observation表的数据（全国数据，geo_id为None或tags中有scope="nation"）
            query = db.query(FactObservation).filter(
                FactObservation.metric_id == metric.id,
                FactObservation.period_type == "week"
            )
            
            # 应用年份筛选
            if start_year:
                query = query.filter(extract('year', FactObservation.obs_date) >= start_year)
            if end_year:
                query = query.filter(extract('year', FactObservation.obs_date) <= end_year)
            
            observations = query.order_by(FactObservation.obs_date).all()
            
            if not observations:
                return IndustryChainSeasonalityResponse(
                    metric_name=metric.metric_name or "冻品库容率",
                    unit=metric.unit or "%",
                    series=[],
                    update_time=None,
                    latest_date=None,
                    period_change=None,
                    yoy_change=None
                )
            
            # 计算涨跌信息
            latest_obs = observations[-1]
            period_change = None
            if len(observations) >= 2:
                prev_obs = observations[-2]
                if latest_obs.value is not None and prev_obs.value is not None:
                    period_change = float(latest_obs.value) - float(prev_obs.value)
            
            # 较去年同期涨跌
            yoy_change = None
            if latest_obs.obs_date:
                latest_year = latest_obs.obs_date.year
                latest_week = latest_obs.obs_date.isocalendar()[1]
                
                # 查找去年同期的数据
                for obs in observations:
                    if obs.obs_date:
                        obs_year = obs.obs_date.year
                        obs_week = obs.obs_date.isocalendar()[1]
                        if obs_year == latest_year - 1 and obs_week == latest_week:
                            if latest_obs.value is not None and obs.value is not None:
                                yoy_change = float(latest_obs.value) - float(obs.value)
                            break
            
            # 按年份和周序号分组
            year_data: Dict[int, Dict[int, List[float]]] = {}
            
            for obs in observations:
                if obs.obs_date:
                    year = obs.obs_date.year
                    if year not in year_data:
                        year_data[year] = {}
                    
                    # 计算ISO周序号
                    week_of_year = obs.obs_date.isocalendar()[1]
                    week_of_year = max(1, min(52, week_of_year))
                    
                    if week_of_year not in year_data[year]:
                        year_data[year][week_of_year] = []
                    
                    if obs.value is not None:
                        year_data[year][week_of_year].append(float(obs.value))
            
            # 构建响应
            series = []
            for year in sorted(year_data.keys()):
                data_points = []
                # 遍历1-52周
                for week in range(1, 53):
                    week_values = year_data[year].get(week, [])
                    if week_values:
                        # 如果有多个值，取平均值
                        value = sum(week_values) / len(week_values)
                    else:
                        value = None
                    
                    # 计算该周的日期（用于month_day）
                    from datetime import datetime, timedelta
                    jan1 = datetime(year, 1, 1)
                    days_offset = (week - 1) * 7 - jan1.weekday()
                    week_start = jan1 + timedelta(days=days_offset)
                    month_day = week_start.strftime("%m-%d")
                    
                    data_points.append(SeasonalityDataPoint(
                        year=year,
                        month_day=month_day,
                        value=value
                    ))
                
                series.append(SeasonalitySeries(
                    year=year,
                    data=data_points
                ))
            
            # 获取更新时间
            latest_date_str = latest_obs.obs_date.isoformat() if latest_obs.obs_date else None
            
            # 获取批次更新时间
            update_time = None
            if latest_obs.batch_id:
                from app.models.import_batch import ImportBatch
                batch = db.query(ImportBatch).filter(ImportBatch.id == latest_obs.batch_id).first()
                if batch and batch.created_at:
                    update_time = batch.created_at.isoformat()
            
            return IndustryChainSeasonalityResponse(
                metric_name=metric.metric_name or "冻品库容率",
                unit=metric.unit or "%",
                series=series,
                update_time=update_time,
                latest_date=latest_date_str,
                period_change=period_change,
                yoy_change=yoy_change
            )
        else:
            # #region agent log
            try:
                with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "G",
                        "location": "price_display.py:1411",
                        "message": "Unknown metric_name, raising 404",
                        "data": {
                            "metric_name": metric_name
                        },
                        "timestamp": int(__import__('time').time() * 1000)
                    }, ensure_ascii=False) + '\n')
            except Exception:
                pass
            # #endregion
            raise HTTPException(status_code=404, detail=f"不支持的指标：{metric_name}")
    
    # 查询ganglian_weekly_farm_profit表
    query_sql = """
        SELECT 
            period_end,
            value,
            unit
        FROM ganglian_weekly_farm_profit
        WHERE profit_type = :profit_type
    """
    
    params = {"profit_type": profit_type}
    
    if start_year:
        query_sql += " AND YEAR(period_end) >= :start_year"
        params["start_year"] = start_year
    
    if end_year:
        query_sql += " AND YEAR(period_end) <= :end_year"
        params["end_year"] = end_year
    
    query_sql += " ORDER BY period_end"
    
    result = db.execute(text(query_sql), params)
    rows = result.fetchall()
    
    if not rows:
        # 获取单位（从第一条记录或默认值）
        unit = "元/头" if "价格" in metric_name or "利润" in metric_name else "-"
        return IndustryChainSeasonalityResponse(
            metric_name=metric_name,
            unit=unit,
            series=[],
            update_time=None,
            latest_date=None,
            period_change=None,
            yoy_change=None
        )
    
    # 获取单位（从第一条记录）
    unit = rows[0][2] if rows[0][2] else ("元/头" if "价格" in metric_name or "利润" in metric_name else "-")
    
    # 计算涨跌信息
    latest_row = rows[-1]
    period_change = None
    if len(rows) >= 2:
        prev_row = rows[-2]
        if latest_row[1] is not None and prev_row[1] is not None:
            period_change = float(latest_row[1]) - float(prev_row[1])
    
    # 较去年同期涨跌
    yoy_change = None
    if latest_row[0]:  # period_end
        latest_date = latest_row[0]
        latest_year = latest_date.year
        latest_week = latest_date.isocalendar()[1]
        
        # 查找去年同期的数据
        for row in rows:
            if row[0]:  # period_end
                obs_date = row[0]
                obs_year = obs_date.year
                obs_week = obs_date.isocalendar()[1]
                if obs_year == latest_year - 1 and obs_week == latest_week:
                    if latest_row[1] is not None and row[1] is not None:
                        yoy_change = float(latest_row[1]) - float(row[1])
                    break
    
    # 按年份和周序号分组
    year_data: Dict[int, Dict[int, List[float]]] = {}
    
    for row in rows:
        period_end = row[0]
        value = row[1]
        
        if period_end:
            year = period_end.year
            if year not in year_data:
                year_data[year] = {}
            
            # 计算ISO周序号
            week_of_year = period_end.isocalendar()[1]
            week_of_year = max(1, min(52, week_of_year))
            
            if week_of_year not in year_data[year]:
                year_data[year][week_of_year] = []
            
            if value is not None:
                year_data[year][week_of_year].append(float(value))
    
    # 构建响应
    series = []
    for year in sorted(year_data.keys()):
        data_points = []
        for week in range(1, 53):
            week_values = year_data[year].get(week, [])
            if week_values:
                value = sum(week_values) / len(week_values)
            else:
                value = None
            
            # 计算month_day
            from datetime import datetime, timedelta
            jan1 = datetime(year, 1, 1)
            days_offset = (week - 1) * 7 - jan1.weekday()
            week_start = jan1 + timedelta(days=days_offset)
            month_day = week_start.strftime("%m-%d")
            
            data_points.append(SeasonalityDataPoint(
                year=year,
                month_day=month_day,
                value=value
            ))
        
        series.append(SeasonalitySeries(
            year=year,
            data=data_points
        ))
    
    latest_date = latest_row[0].isoformat() if latest_row[0] else None
    
    return IndustryChainSeasonalityResponse(
        metric_name=metric_name,
        unit=unit,
        series=series,
        update_time=latest_date,
        latest_date=latest_date,
        period_change=period_change,
        yoy_change=yoy_change
    )


async def _get_calculated_metric_seasonality(
    db: Session,
    numerator_metric: str,
    denominator_metric: str,
    result_metric_name: str,
    start_year: Optional[int],
    end_year: Optional[int],
    operation: str = "divide"
):
    """获取计算指标的季节性数据（如比值）"""
    # #region agent log
    import json
    try:
        with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H",
                "location": "price_display.py:1544",
                "message": "_get_calculated_metric_seasonality called",
                "data": {
                    "numerator_metric": numerator_metric,
                    "denominator_metric": denominator_metric,
                    "result_metric_name": result_metric_name
                },
                "timestamp": int(__import__('time').time() * 1000)
            }, ensure_ascii=False) + '\n')
    except Exception:
        pass
    # #endregion
    
    # 获取两个指标的profit_type
    numerator_type = INDUSTRY_CHAIN_METRICS.get(numerator_metric)
    denominator_type = INDUSTRY_CHAIN_METRICS.get(denominator_metric)
    
    # #region agent log
    try:
        with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "H",
                "location": "price_display.py:1555",
                "message": "profit_type lookup for numerator and denominator",
                "data": {
                    "numerator_type": numerator_type,
                    "denominator_type": denominator_type,
                    "numerator_found": numerator_type is not None,
                    "denominator_found": denominator_type is not None
                },
                "timestamp": int(__import__('time').time() * 1000)
            }, ensure_ascii=False) + '\n')
    except Exception:
        pass
    # #endregion
    
    if not numerator_type or not denominator_type:
        # #region agent log
        try:
            with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "H",
                    "location": "price_display.py:1557",
                    "message": "Missing profit_type, raising 404",
                    "data": {
                        "numerator_metric": numerator_metric,
                        "denominator_metric": denominator_metric
                    },
                    "timestamp": int(__import__('time').time() * 1000)
                }, ensure_ascii=False) + '\n')
        except Exception:
            pass
        # #endregion
        raise HTTPException(status_code=404, detail=f"无法找到计算所需的指标：{numerator_metric} 或 {denominator_metric}")
    
    # 查询两个指标的数据（分别查询）
    numerator_query_sql = """
        SELECT period_end, value, unit
        FROM ganglian_weekly_farm_profit
        WHERE profit_type = :profit_type
    """
    numerator_params = {"profit_type": numerator_type}
    
    if start_year:
        numerator_query_sql += " AND YEAR(period_end) >= :start_year"
        numerator_params["start_year"] = start_year
    
    if end_year:
        numerator_query_sql += " AND YEAR(period_end) <= :end_year"
        numerator_params["end_year"] = end_year
    
    numerator_query_sql += " ORDER BY period_end"
    
    denominator_query_sql = numerator_query_sql.replace(":profit_type", ":denominator_type")
    denominator_params = {"denominator_type": denominator_type}
    if start_year:
        denominator_params["start_year"] = start_year
    if end_year:
        denominator_params["end_year"] = end_year
    
    numerator_result = db.execute(text(numerator_query_sql), numerator_params)
    numerator_rows = numerator_result.fetchall()
    
    denominator_result = db.execute(text(denominator_query_sql), denominator_params)
    denominator_rows = denominator_result.fetchall()
    
    # 构建period_end到value的映射
    numerator_dict = {row[0]: float(row[1]) for row in numerator_rows if row[0] and row[1] is not None}
    denominator_dict = {row[0]: float(row[1]) for row in denominator_rows if row[0] and row[1] is not None}
    
    # 找到共同的period_end
    common_periods = set(numerator_dict.keys()) & set(denominator_dict.keys())
    
    if not common_periods:
        return IndustryChainSeasonalityResponse(
            metric_name=result_metric_name,
            unit="-",
            series=[],
            update_time=None,
            latest_date=None,
            period_change=None,
            yoy_change=None
        )
    
    # 计算比值并构建季节性数据
    year_data: Dict[int, Dict[int, List[float]]] = {}
    
    for period_end in sorted(common_periods):
        if denominator_dict[period_end] != 0:
            ratio = numerator_dict[period_end] / denominator_dict[period_end]
            
            year = period_end.year
            if year not in year_data:
                year_data[year] = {}
            
            week_of_year = period_end.isocalendar()[1]
            week_of_year = max(1, min(52, week_of_year))
            
            if week_of_year not in year_data[year]:
                year_data[year][week_of_year] = []
            
            year_data[year][week_of_year].append(ratio)
    
    # 构建响应
    series = []
    for year in sorted(year_data.keys()):
        data_points = []
        for week in range(1, 53):
            week_values = year_data[year].get(week, [])
            if week_values:
                value = sum(week_values) / len(week_values)
            else:
                value = None
            
            from datetime import datetime, timedelta
            jan1 = datetime(year, 1, 1)
            days_offset = (week - 1) * 7 - jan1.weekday()
            week_start = jan1 + timedelta(days=days_offset)
            month_day = week_start.strftime("%m-%d")
            
            data_points.append(SeasonalityDataPoint(
                year=year,
                month_day=month_day,
                value=value
            ))
        
        series.append(SeasonalitySeries(
            year=year,
            data=data_points
        ))
    
    # 计算涨跌信息
    period_change = None
    yoy_change = None
    latest_date = None
    
    if series and series[-1].data:
        latest_year_data = series[-1].data
        latest_value = None
        latest_week_idx = None
        
        # 找到最后一个非空值
        for i in range(len(latest_year_data) - 1, -1, -1):
            if latest_year_data[i].value is not None:
                latest_value = latest_year_data[i].value
                latest_week_idx = i
                break
        
        if latest_value is not None:
            # 本期涨跌（较上期）
            if latest_week_idx is not None and latest_week_idx > 0:
                prev_value = None
                for i in range(latest_week_idx - 1, -1, -1):
                    if latest_year_data[i].value is not None:
                        prev_value = latest_year_data[i].value
                        break
                if prev_value is not None:
                    period_change = latest_value - prev_value
            
            # 较去年同期
            if len(series) >= 2 and latest_week_idx is not None:
                prev_year_data = series[-2].data
                if latest_week_idx < len(prev_year_data) and prev_year_data[latest_week_idx].value is not None:
                    yoy_change = latest_value - prev_year_data[latest_week_idx].value
        
        # 获取最新日期
        if common_periods:
            latest_date = max(common_periods).isoformat()
    
    return IndustryChainSeasonalityResponse(
        metric_name=result_metric_name,
        unit="-",
        series=series,
        update_time=latest_date,
        latest_date=latest_date,
        period_change=period_change,
        yoy_change=yoy_change
    )


class ProvinceIndicatorsResponse(BaseModel):
    """省份指标数据响应"""
    province_name: str
    indicators: Dict[str, SeasonalityResponse]  # key: 指标名称, value: 季节性数据


@router.get("/province-indicators/{province_name}/seasonality", response_model=ProvinceIndicatorsResponse)
async def get_province_indicators_seasonality(
    province_name: str,
    start_year: Optional[int] = Query(None, description="起始年份"),
    end_year: Optional[int] = Query(None, description="结束年份"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """
    获取指定省份的6个指标季节性数据
    
    6个指标：
    1. 日度 均价 - 从"分省区猪价"sheet获取
    2. 日度 散户标肥价差 - 从"肥标价差"sheet获取
    3. 周度 出栏均重 - YY_W_OUT_WEIGHT, indicator='均重'
    4. 周度 宰后均重 - 钢联数据库，sheet表均重（需要查找）
    5. 周度 90KG占比 - YY_W_OUT_WEIGHT, indicator='90Kg出栏占比'
    6. 周度 冻品库容 - 从"周度-冻品库存"sheet获取
    """
    indicators_data = {}
    
    # 1. 日度 均价
    try:
        # #region agent log
        import json
        try:
            with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A",
                    "location": "price_display.py:2013",
                    "message": "开始查询日度均价metric",
                    "data": {
                        "province_name": province_name,
                        "metric_key": "YY_D_PRICE_PROVINCE_AVG",
                        "freq_filter": ["D", "daily", "D"]
                    },
                    "timestamp": int(__import__('time').time() * 1000)
                }, ensure_ascii=False) + '\n')
        except Exception:
            pass
        # #endregion
        
        # 查询YY_D_PRICE_PROVINCE_AVG指标（涌益各省份均价）
        price_metric = db.query(DimMetric).filter(
            func.json_unquote(
                func.json_extract(DimMetric.parse_json, '$.metric_key')
            ) == "YY_D_PRICE_PROVINCE_AVG"
        ).first()
        
        # 如果没找到，尝试通过sheet_name查找（兼容旧数据）
        if not price_metric:
            price_metric = db.query(DimMetric).filter(
                DimMetric.sheet_name == "各省份均价"
            ).first()
        
        # 如果还是没找到，尝试查找"分省区猪价"sheet（钢联数据，作为备选）
        if not price_metric:
            price_metric = db.query(DimMetric).filter(
                DimMetric.sheet_name == "分省区猪价",
                DimMetric.raw_header.like(f"%{province_name}%"),
                DimMetric.freq.in_(["D", "daily", "D"])
            ).first()
        
        # #region agent log
        try:
            with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A",
                    "location": "price_display.py:2021",
                    "message": "日度均价metric查询结果",
                    "data": {
                        "province_name": province_name,
                        "metric_found": price_metric is not None,
                        "metric_id": price_metric.id if price_metric else None,
                        "metric_name": price_metric.metric_name if price_metric else None,
                        "raw_header": price_metric.raw_header if price_metric else None,
                        "freq": price_metric.freq if price_metric else None
                    },
                    "timestamp": int(__import__('time').time() * 1000)
                }, ensure_ascii=False) + '\n')
        except Exception:
            pass
        # #endregion
        
        if price_metric:
            # 判断是否是钢联数据（通过sheet_name判断）
            is_ganglian_data = price_metric.sheet_name == "分省区猪价"
            
            observations = []
            
            if is_ganglian_data:
                # 钢联数据：直接查询metric_id，不需要geo_id过滤（因为raw_header已经包含省份信息）
                query = db.query(FactObservation).filter(
                    FactObservation.metric_id == price_metric.id,
                    FactObservation.period_type == "day"
                )
                
                if start_year:
                    query = query.filter(extract('year', FactObservation.obs_date) >= start_year)
                if end_year:
                    query = query.filter(extract('year', FactObservation.obs_date) <= end_year)
                
                observations = query.order_by(FactObservation.obs_date).all()
            else:
                # 涌益数据（YY_D_PRICE_PROVINCE_AVG）：需要通过geo_id过滤
                geo = db.query(DimGeo).filter(DimGeo.province == province_name).first()
                
                if not geo:
                    # #region agent log
                    try:
                        with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "A",
                                "location": "price_display.py:2085",
                                "message": "未找到省份geo信息",
                                "data": {
                                    "province_name": province_name
                                },
                                "timestamp": int(__import__('time').time() * 1000)
                            }, ensure_ascii=False) + '\n')
                    except Exception:
                        pass
                    # #endregion
                else:
                    query = db.query(FactObservation).filter(
                        FactObservation.metric_id == price_metric.id,
                        FactObservation.geo_id == geo.id,
                        FactObservation.period_type == "day"
                    )
                    
                    if start_year:
                        query = query.filter(extract('year', FactObservation.obs_date) >= start_year)
                    if end_year:
                        query = query.filter(extract('year', FactObservation.obs_date) <= end_year)
                    
                    observations = query.order_by(FactObservation.obs_date).all()
                
                # #region agent log
                try:
                    with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "B",
                            "location": "price_display.py:2114",
                            "message": "日度均价observations查询结果",
                            "data": {
                                "province_name": province_name,
                                "metric_id": price_metric.id,
                                "geo_id": geo.id,
                                "observations_count": len(observations),
                                "has_data": len(observations) > 0,
                                "first_obs_date": observations[0].obs_date.isoformat() if observations else None,
                                "last_obs_date": observations[-1].obs_date.isoformat() if observations else None
                            },
                            "timestamp": int(__import__('time').time() * 1000)
                        }, ensure_ascii=False) + '\n')
                except Exception:
                    pass
                # #endregion
            
            if observations:
                year_data: Dict[int, List[Dict]] = {}
                for obs in observations:
                    year = obs.obs_date.year
                    if year not in year_data:
                        year_data[year] = []
                    
                    month_day = obs.obs_date.strftime("%m-%d")
                    year_data[year].append({
                        "month_day": month_day,
                        "value": float(obs.value) if obs.value else None,
                        "date": obs.obs_date
                    })
                
                series = []
                for year in sorted(year_data.keys()):
                    data_points = []
                    for item in sorted(year_data[year], key=lambda x: x["date"]):
                        data_points.append(SeasonalityDataPoint(
                            year=year,
                            month_day=item["month_day"],
                            value=item["value"]
                        ))
                    
                    series.append(SeasonalitySeries(
                        year=year,
                        data=data_points
                    ))
                
                latest_obs = observations[-1] if observations else None
                update_time = latest_obs.obs_date.isoformat() if latest_obs else None
                
                indicators_data["日度 均价"] = SeasonalityResponse(
                    metric_name=f"{province_name}均价",
                    unit=price_metric.unit or "元/公斤",
                    series=series,
                    update_time=update_time,
                    latest_date=update_time
                )
    except Exception as e:
        # #region agent log
        try:
            import traceback
            with open('d:\\Workspace\\hogprice-insight\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A",
                    "location": "price_display.py:2074",
                    "message": "获取日度均价异常",
                    "data": {
                        "province_name": province_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc()
                    },
                    "timestamp": int(__import__('time').time() * 1000)
                }, ensure_ascii=False) + '\n')
        except Exception:
            pass
        # #endregion
        print(f"获取日度均价失败: {e}")
    
    # 2. 日度 散户标肥价差
    try:
        spread_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "肥标价差",
            DimMetric.raw_header.like(f"%{province_name}%")
        ).first()
        
        if spread_metric:
            query = db.query(FactObservation).filter(
                FactObservation.metric_id == spread_metric.id,
                FactObservation.period_type == "day"
            )
            
            if start_year:
                query = query.filter(extract('year', FactObservation.obs_date) >= start_year)
            if end_year:
                query = query.filter(extract('year', FactObservation.obs_date) <= end_year)
            
            observations = query.order_by(FactObservation.obs_date).all()
            
            if observations:
                year_data: Dict[int, List[Dict]] = {}
                for obs in observations:
                    year = obs.obs_date.year
                    if year not in year_data:
                        year_data[year] = []
                    
                    month_day = obs.obs_date.strftime("%m-%d")
                    year_data[year].append({
                        "month_day": month_day,
                        "value": float(obs.value) if obs.value else None,
                        "date": obs.obs_date
                    })
                
                series = []
                for year in sorted(year_data.keys()):
                    data_points = []
                    for item in sorted(year_data[year], key=lambda x: x["date"]):
                        data_points.append(SeasonalityDataPoint(
                            year=year,
                            month_day=item["month_day"],
                            value=item["value"]
                        ))
                    
                    series.append(SeasonalitySeries(
                        year=year,
                        data=data_points
                    ))
                
                latest_obs = observations[-1] if observations else None
                update_time = latest_obs.obs_date.isoformat() if latest_obs else None
                
                indicators_data["日度 散户标肥价差"] = SeasonalityResponse(
                    metric_name=f"{province_name}散户标肥价差",
                    unit=spread_metric.unit or "元/公斤",
                    series=series,
                    update_time=update_time,
                    latest_date=update_time
                )
    except Exception as e:
        print(f"获取日度散户标肥价差失败: {e}")
    
    # 3. 周度 出栏均重
    try:
        # 查询省份的geo_id
        geo = db.query(DimGeo).filter(DimGeo.province == province_name).first()
        
        if geo:
            weight_metric = db.query(DimMetric).filter(
                func.json_unquote(
                    func.json_extract(DimMetric.parse_json, '$.metric_key')
                ) == "YY_W_OUT_WEIGHT"
            ).first()
            
            if weight_metric:
                query = db.query(FactObservation).filter(
                    FactObservation.metric_id == weight_metric.id,
                    FactObservation.geo_id == geo.id,
                    FactObservation.period_type == "week",
                    func.json_unquote(
                        func.json_extract(FactObservation.tags_json, '$.indicator')
                    ) == "均重"
                )
                
                if start_year:
                    query = query.filter(extract('year', FactObservation.period_end) >= start_year)
                if end_year:
                    query = query.filter(extract('year', FactObservation.period_end) <= end_year)
                
                observations = query.order_by(FactObservation.period_end).all()
                
                if observations:
                    year_data: Dict[int, Dict[int, List[float]]] = {}
                    
                    for obs in observations:
                        if obs.period_end:
                            year = obs.period_end.year
                            if year not in year_data:
                                year_data[year] = {}
                            
                            week_of_year = obs.period_end.isocalendar()[1]
                            week_of_year = max(1, min(52, week_of_year))
                            
                            if week_of_year not in year_data[year]:
                                year_data[year][week_of_year] = []
                            
                            if obs.value is not None:
                                year_data[year][week_of_year].append(float(obs.value))
                    
                    series = []
                    for year in sorted(year_data.keys()):
                        data_points = []
                        for week in range(1, 53):
                            week_values = year_data[year].get(week, [])
                            if week_values:
                                value = sum(week_values) / len(week_values)
                            else:
                                value = None
                            
                            from datetime import datetime, timedelta
                            jan1 = datetime(year, 1, 1)
                            days_offset = (week - 1) * 7 - jan1.weekday()
                            week_start = jan1 + timedelta(days=days_offset)
                            month_day = week_start.strftime("%m-%d")
                            
                            data_points.append(SeasonalityDataPoint(
                                year=year,
                                month_day=month_day,
                                value=value
                            ))
                        
                        series.append(SeasonalitySeries(
                            year=year,
                            data=data_points
                        ))
                    
                    latest_obs = observations[-1] if observations else None
                    update_time = latest_obs.period_end.isoformat() if latest_obs and latest_obs.period_end else None
                    
                    indicators_data["周度 出栏均重"] = SeasonalityResponse(
                        metric_name=f"{province_name}出栏均重",
                        unit=weight_metric.unit or "kg",
                        series=series,
                        update_time=update_time,
                        latest_date=update_time
                    )
    except Exception as e:
        print(f"获取周度出栏均重失败: {e}")
    
    # 4. 周度 宰后均重（钢联数据库，从"宰后均重"sheet查询）
    try:
        # 查询钢联数据库的宰后均重指标
        # 每个省份有独立的metric，通过raw_header中包含省份名称来查找
        # raw_header格式：白条肉：屠宰企业：宰后均重：{省份}（周）
        slaughter_weight_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "宰后均重",
            DimMetric.metric_name == "宰后均重",
            DimMetric.raw_header.like(f"%{province_name}%"),
            DimMetric.freq.in_(["W", "week", "W"])
        ).first()
        
        if slaughter_weight_metric:
            # 查询该省份的宰后均重数据
            # 每个metric对应一个省份，直接查询该metric的所有数据
            query = db.query(FactObservation).filter(
                FactObservation.metric_id == slaughter_weight_metric.id,
                FactObservation.period_type == "week"
            )
            
            if start_year:
                query = query.filter(extract('year', FactObservation.obs_date) >= start_year)
            if end_year:
                query = query.filter(extract('year', FactObservation.obs_date) <= end_year)
            
            observations = query.order_by(FactObservation.obs_date).all()
            
            if observations:
                year_data: Dict[int, Dict[int, List[float]]] = {}
                
                for obs in observations:
                    # 使用obs_date字段（钢联数据使用obs_date而不是period_end）
                    if obs.obs_date:
                        year = obs.obs_date.year
                        if year not in year_data:
                            year_data[year] = {}
                        
                        week_of_year = obs.obs_date.isocalendar()[1]
                        week_of_year = max(1, min(52, week_of_year))
                        
                        if week_of_year not in year_data[year]:
                            year_data[year][week_of_year] = []
                        
                        if obs.value is not None:
                            year_data[year][week_of_year].append(float(obs.value))
                
                series = []
                for year in sorted(year_data.keys()):
                    data_points = []
                    for week in range(1, 53):
                        week_values = year_data[year].get(week, [])
                        if week_values:
                            value = sum(week_values) / len(week_values)
                        else:
                            value = None
                        
                        from datetime import datetime, timedelta
                        jan1 = datetime(year, 1, 1)
                        days_offset = (week - 1) * 7 - jan1.weekday()
                        week_start = jan1 + timedelta(days=days_offset)
                        month_day = week_start.strftime("%m-%d")
                        
                        data_points.append(SeasonalityDataPoint(
                            year=year,
                            month_day=month_day,
                            value=value
                        ))
                    
                    series.append(SeasonalitySeries(
                        year=year,
                        data=data_points
                    ))
                
                latest_obs = observations[-1] if observations else None
                update_time = latest_obs.obs_date.isoformat() if latest_obs and latest_obs.obs_date else None
                
                indicators_data["周度 宰后均重"] = SeasonalityResponse(
                    metric_name=f"{province_name}宰后均重",
                    unit=slaughter_weight_metric.unit or "千克",
                    series=series,
                    update_time=update_time,
                    latest_date=update_time
                )
    except Exception as e:
        import traceback
        print(f"获取周度宰后均重失败: {e}")
        traceback.print_exc()
    
    # 5. 周度 90KG占比
    try:
        geo = db.query(DimGeo).filter(DimGeo.province == province_name).first()
        
        if geo:
            weight_metric = db.query(DimMetric).filter(
                func.json_unquote(
                    func.json_extract(DimMetric.parse_json, '$.metric_key')
                ) == "YY_W_OUT_WEIGHT"
            ).first()
            
            if weight_metric:
                query = db.query(FactObservation).filter(
                    FactObservation.metric_id == weight_metric.id,
                    FactObservation.geo_id == geo.id,
                    FactObservation.period_type == "week",
                    func.json_unquote(
                        func.json_extract(FactObservation.tags_json, '$.indicator')
                    ) == "90Kg出栏占比"
                )
                
                if start_year:
                    query = query.filter(extract('year', FactObservation.period_end) >= start_year)
                if end_year:
                    query = query.filter(extract('year', FactObservation.period_end) <= end_year)
                
                observations = query.order_by(FactObservation.period_end).all()
                
                if observations:
                    year_data: Dict[int, Dict[int, List[float]]] = {}
                    
                    for obs in observations:
                        if obs.period_end:
                            year = obs.period_end.year
                            if year not in year_data:
                                year_data[year] = {}
                            
                            week_of_year = obs.period_end.isocalendar()[1]
                            week_of_year = max(1, min(52, week_of_year))
                            
                            if week_of_year not in year_data[year]:
                                year_data[year][week_of_year] = []
                            
                            if obs.value is not None:
                                year_data[year][week_of_year].append(float(obs.value))
                    
                    series = []
                    for year in sorted(year_data.keys()):
                        data_points = []
                        for week in range(1, 53):
                            week_values = year_data[year].get(week, [])
                            if week_values:
                                value = sum(week_values) / len(week_values)
                            else:
                                value = None
                            
                            from datetime import datetime, timedelta
                            jan1 = datetime(year, 1, 1)
                            days_offset = (week - 1) * 7 - jan1.weekday()
                            week_start = jan1 + timedelta(days=days_offset)
                            month_day = week_start.strftime("%m-%d")
                            
                            data_points.append(SeasonalityDataPoint(
                                year=year,
                                month_day=month_day,
                                value=value
                            ))
                        
                        series.append(SeasonalitySeries(
                            year=year,
                            data=data_points
                        ))
                    
                    latest_obs = observations[-1] if observations else None
                    update_time = latest_obs.period_end.isoformat() if latest_obs and latest_obs.period_end else None
                    
                    indicators_data["周度 90KG占比"] = SeasonalityResponse(
                        metric_name=f"{province_name}90KG占比",
                        unit=weight_metric.unit or "%",
                        series=series,
                        update_time=update_time,
                        latest_date=update_time
                    )
    except Exception as e:
        print(f"获取周度90KG占比失败: {e}")
    
    # 6. 周度 冻品库容
    try:
        geo = db.query(DimGeo).filter(DimGeo.province == province_name).first()
        
        if geo:
            frozen_metric = db.query(DimMetric).filter(
                DimMetric.sheet_name == "周度-冻品库存",
                func.json_unquote(
                    func.json_extract(DimMetric.parse_json, '$.metric_key')
                ) == "YY_W_FROZEN_INVENTORY_RATIO"
            ).first()
            
            if frozen_metric:
                query = db.query(FactObservation).filter(
                    FactObservation.metric_id == frozen_metric.id,
                    FactObservation.geo_id == geo.id,
                    FactObservation.period_type == "week"
                )
                
                if start_year:
                    query = query.filter(extract('year', FactObservation.period_end) >= start_year)
                if end_year:
                    query = query.filter(extract('year', FactObservation.period_end) <= end_year)
                
                observations = query.order_by(FactObservation.period_end).all()
                
                if observations:
                    year_data: Dict[int, Dict[int, List[float]]] = {}
                    
                    for obs in observations:
                        if obs.period_end:
                            year = obs.period_end.year
                            if year not in year_data:
                                year_data[year] = {}
                            
                            week_of_year = obs.period_end.isocalendar()[1]
                            week_of_year = max(1, min(52, week_of_year))
                            
                            if week_of_year not in year_data[year]:
                                year_data[year][week_of_year] = []
                            
                            if obs.value is not None:
                                year_data[year][week_of_year].append(float(obs.value))
                    
                    series = []
                    for year in sorted(year_data.keys()):
                        data_points = []
                        for week in range(1, 53):
                            week_values = year_data[year].get(week, [])
                            if week_values:
                                value = sum(week_values) / len(week_values)
                            else:
                                value = None
                            
                            from datetime import datetime, timedelta
                            jan1 = datetime(year, 1, 1)
                            days_offset = (week - 1) * 7 - jan1.weekday()
                            week_start = jan1 + timedelta(days=days_offset)
                            month_day = week_start.strftime("%m-%d")
                            
                            data_points.append(SeasonalityDataPoint(
                                year=year,
                                month_day=month_day,
                                value=value
                            ))
                        
                        series.append(SeasonalitySeries(
                            year=year,
                            data=data_points
                        ))
                    
                    latest_obs = observations[-1] if observations else None
                    update_time = latest_obs.period_end.isoformat() if latest_obs and latest_obs.period_end else None
                    
                    indicators_data["周度 冻品库容"] = SeasonalityResponse(
                        metric_name=f"{province_name}冻品库容",
                        unit=frozen_metric.unit or "ratio",
                        series=series,
                        update_time=update_time,
                        latest_date=update_time
                    )
    except Exception as e:
        print(f"获取周度冻品库容失败: {e}")
    
    return ProvinceIndicatorsResponse(
        province_name=province_name,
        indicators=indicators_data
    )


# A1. 价格（全国） 专用接口已拆到 price_national 模块（末尾挂载避免循环导入）
from app.api import price_national
router.include_router(price_national.router)
