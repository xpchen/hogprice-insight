"""期货查询接口"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, extract
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import math
import numpy as np

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.models import FactFuturesDaily
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.utils.contract_parser import parse_futures_contract

router = APIRouter(prefix=f"{settings.API_V1_STR}/futures", tags=["futures"])


class FuturesDailyResponse(BaseModel):
    contract_code: str
    series: List[dict]


@router.get("/daily", response_model=FuturesDailyResponse)
async def get_futures_daily(
    contract: str = Query(..., description="合约代码，如 lh2603"),
    from_date: Optional[date] = Query(None, description="开始日期"),
    to_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """期货日线查询"""
    query = db.query(FactFuturesDaily).filter(
        FactFuturesDaily.contract_code == contract
    )
    
    if from_date:
        query = query.filter(FactFuturesDaily.trade_date >= from_date)
    if to_date:
        query = query.filter(FactFuturesDaily.trade_date <= to_date)
    
    results = query.order_by(FactFuturesDaily.trade_date).all()
    
    series = []
    for r in results:
        series.append({
            "date": r.trade_date.isoformat(),
            "open": float(r.open) if r.open else None,
            "high": float(r.high) if r.high else None,
            "low": float(r.low) if r.low else None,
            "close": float(r.close) if r.close else None,
            "settle": float(r.settle) if r.settle else None,
            "volume": int(r.volume) if r.volume else None,
            "open_interest": int(r.open_interest) if r.open_interest else None
        })
    
    return FuturesDailyResponse(
        contract_code=contract,
        series=series
    )


@router.get("/main")
async def get_main_contract(
    date: Optional[date] = Query(None, description="日期，默认今天"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """主力合约快照"""
    # 简化实现：返回持仓量最大的合约
    if date is None:
        from datetime import datetime
        date = datetime.now().date()
    
    # 查询指定日期持仓量最大的合约
    result = db.query(FactFuturesDaily).filter(
        FactFuturesDaily.trade_date == date
    ).order_by(FactFuturesDaily.open_interest.desc()).first()
    
    if not result:
        return {"contract_code": None, "message": "无数据"}
    
    return {
        "contract_code": result.contract_code,
        "date": date.isoformat(),
        "close": float(result.close) if result.close else None,
        "settle": float(result.settle) if result.settle else None,
        "open_interest": int(result.open_interest) if result.open_interest else None
    }


def get_national_spot_price(db: Session, trade_date: date) -> Optional[float]:
    """获取全国现货均价"""
    # 查询全国猪价指标 - 尝试多种匹配方式
    metric = db.query(DimMetric).filter(
        or_(
            DimMetric.raw_header.like("%中国%"),
            DimMetric.raw_header.like("%全国%")
        ),
        DimMetric.sheet_name == "分省区猪价",
        DimMetric.freq.in_(["D", "daily"])
    ).first()
    
    # 如果没找到，尝试通过metric_key查找
    if not metric:
        metric = db.query(DimMetric).filter(
            DimMetric.metric_key == "GL_D_PRICE_NATION"
        ).first()
    
    # 如果还是没找到，尝试通过metric_name查找
    if not metric:
        metric = db.query(DimMetric).filter(
            DimMetric.metric_name.like("%全国%"),
            DimMetric.metric_name.like("%价格%"),
            DimMetric.freq.in_(["D", "daily"])
        ).first()
    
    # 如果还是没找到，尝试只通过sheet_name和raw_header查找（不限制freq）
    if not metric:
        metric = db.query(DimMetric).filter(
            DimMetric.raw_header.like("%中国%"),
            DimMetric.sheet_name == "分省区猪价"
        ).first()
    
    if not metric:
        return None
    
    # 查询指定日期的价格
    obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date == trade_date,
        FactObservation.period_type == "day"
    ).first()
    
    if obs and obs.value:
        return float(obs.value)
    return None


def get_contract_date_range(contract_month: int, year: Optional[int] = None) -> tuple[date, date]:
    """
    获取合约的时间范围
    X月合约，时间从X+1月的1日至X-1月的31日
    
    例如：03合约（3月合约）在2026年：
    - 开始：2025年4月1日（上一年的X+1月）
    - 结束：2026年2月28日（当年的X-1月）
    
    Args:
        contract_month: 合约月份，如 3, 5, 7, 9, 11, 1
        year: 合约年份，如果不指定则使用当前年份
    
    Returns:
        (start_date, end_date)
    """
    if year is None:
        year = datetime.now().year
    
    # 计算开始日期：X+1月的1日（上一年的X+1月）
    start_month = contract_month + 1
    start_year = year - 1  # 从上一年的X+1月开始
    if start_month > 12:
        start_month = 1
        start_year = year  # 如果X+1月跨年，则从当年的1月开始
    
    # 计算结束日期：X-1月的最后一日（当年的X-1月）
    end_month = contract_month - 1
    end_year = year
    if end_month < 1:
        end_month = 12
        end_year = year - 1
    
    # 获取月份的最后一天
    if end_month == 12:
        next_month = 1
        next_year = end_year + 1
    else:
        next_month = end_month + 1
        next_year = end_year
    
    start_date = date(start_year, start_month, 1)
    # 结束日期是下个月的第一天减1天
    end_date = date(next_year, next_month, 1) - timedelta(days=1)
    
    return start_date, end_date


class PremiumDataPoint(BaseModel):
    """升贴水数据点"""
    date: str
    futures_settle: Optional[float]  # 期货结算价
    spot_price: Optional[float]  # 现货价格
    premium: Optional[float]  # 升贴水 = 期货结算价 - 现货价格


class PremiumSeries(BaseModel):
    """升贴水数据系列"""
    contract_month: int  # 合约月份，如 3, 5, 7, 9, 11, 1
    contract_name: str  # 合约名称，如 "03合约"
    data: List[PremiumDataPoint]


class PremiumResponse(BaseModel):
    """升贴水响应"""
    series: List[PremiumSeries]
    update_time: Optional[str] = None


@router.get("/premium/debug")
async def debug_premium_data(
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """调试端点：检查升贴水数据所需的基础数据"""
    result = {
        "futures_data": {},
        "spot_price_data": {},
        "issues": []
    }
    
    # 检查期货数据
    futures_count = db.query(func.count(FactFuturesDaily.id)).scalar()
    result["futures_data"]["total_count"] = futures_count
    
    if futures_count > 0:
        min_date = db.query(func.min(FactFuturesDaily.trade_date)).scalar()
        max_date = db.query(func.max(FactFuturesDaily.trade_date)).scalar()
        result["futures_data"]["date_range"] = {
            "min": min_date.isoformat() if min_date else None,
            "max": max_date.isoformat() if max_date else None
        }
        
        # 检查各月份合约
        for month in [3, 5, 7, 9, 11, 1]:
            month_str = f"{month:02d}"
            count = db.query(func.count(FactFuturesDaily.id)).filter(
                FactFuturesDaily.contract_code.like(f"%{month_str}")
            ).scalar()
            result["futures_data"][f"month_{month_str}"] = count
    else:
        result["issues"].append("数据库中没有期货数据")
    
    # 检查全国现货价格数据
    metric = db.query(DimMetric).filter(
        or_(
            DimMetric.raw_header.like("%中国%"),
            DimMetric.raw_header.like("%全国%")
        ),
        DimMetric.sheet_name == "分省区猪价"
    ).first()
    
    if metric:
        result["spot_price_data"]["metric_found"] = True
        result["spot_price_data"]["metric_id"] = metric.id
        result["spot_price_data"]["metric_name"] = metric.metric_name
        result["spot_price_data"]["raw_header"] = metric.raw_header
        
        obs_count = db.query(func.count(FactObservation.id)).filter(
            FactObservation.metric_id == metric.id,
            FactObservation.period_type == "day"
        ).scalar()
        result["spot_price_data"]["observation_count"] = obs_count
        
        if obs_count > 0:
            min_date = db.query(func.min(FactObservation.obs_date)).filter(
                FactObservation.metric_id == metric.id,
                FactObservation.period_type == "day"
            ).scalar()
            max_date = db.query(func.max(FactObservation.obs_date)).filter(
                FactObservation.metric_id == metric.id,
                FactObservation.period_type == "day"
            ).scalar()
            result["spot_price_data"]["date_range"] = {
                "min": min_date.isoformat() if min_date else None,
                "max": max_date.isoformat() if max_date else None
            }
        else:
            result["issues"].append("全国现货价格指标存在但没有观测数据")
    else:
        result["issues"].append("未找到全国现货价格指标")
    
    return result


@router.get("/premium", response_model=PremiumResponse)
async def get_premium_data(
    contract_month: Optional[int] = Query(None, description="合约月份，如 3, 5, 7, 9, 11, 1。不指定则返回所有6个合约"),
    start_year: Optional[int] = Query(None, description="起始年份"),
    end_year: Optional[int] = Query(None, description="结束年份"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取升贴水数据
    
    升贴水 = 期货结算价 - 全国现货均价
    6个合约：03、05、07、09、11、01
    每个合约的时间范围：X月合约，时间从X+1月的1日至X-1月的31日
    """
    contract_months = [contract_month] if contract_month else [3, 5, 7, 9, 11, 1]
    
    all_series = []
    
    # 检查是否有期货数据
    futures_count = db.query(func.count(FactFuturesDaily.id)).scalar()
    if futures_count == 0:
        raise HTTPException(status_code=404, detail="数据库中没有期货数据，请先导入期货数据")
    
    # 确定年份范围
    if start_year and end_year:
        years = list(range(start_year, end_year + 1))
    elif start_year:
        years = list(range(start_year, datetime.now().year + 1))
    elif end_year:
        years = list(range(2020, end_year + 1))  # 假设从2020年开始有数据
    else:
        # 查询数据库中的年份范围
        min_year = db.query(func.min(extract('year', FactFuturesDaily.trade_date))).scalar()
        max_year = db.query(func.max(extract('year', FactFuturesDaily.trade_date))).scalar()
        if min_year and max_year:
            years = list(range(min_year, max_year + 1))
        else:
            years = list(range(2020, datetime.now().year + 1))
    
    for month in contract_months:
        # 收集所有年份的数据
        month_str = f"{month:02d}"
        date_dict: Dict[date, List[FactFuturesDaily]] = {}
        
        # 直接查询该月份的所有合约数据（不限制时间范围，让数据自己决定）
        # 因为时间范围计算可能有问题，先获取所有数据
        base_query = db.query(FactFuturesDaily).filter(
            FactFuturesDaily.contract_code.like(f"%{month_str}")
        )
        
        # 如果指定了年份范围，限制年份
        if start_year:
            base_query = base_query.filter(
                extract('year', FactFuturesDaily.trade_date) >= start_year
            )
        if end_year:
            base_query = base_query.filter(
                extract('year', FactFuturesDaily.trade_date) <= end_year
            )
        
        # 如果指定了年份范围，进一步限制日期
        if start_year:
            base_query = base_query.filter(
                FactFuturesDaily.trade_date >= date(start_year, 1, 1)
            )
        if end_year:
            base_query = base_query.filter(
                FactFuturesDaily.trade_date <= date(end_year, 12, 31)
            )
        
        futures_data = base_query.order_by(FactFuturesDaily.trade_date).all()
        
        # 按日期分组，合并不同年份的同月份合约
        for f in futures_data:
            if f.trade_date not in date_dict:
                date_dict[f.trade_date] = []
            date_dict[f.trade_date].append(f)
        
        # 构建数据点
        data_points = []
        for trade_date, contracts in sorted(date_dict.items()):
            # 如果有多个合约，选择持仓量最大的
            best_contract = max(contracts, key=lambda x: x.open_interest or 0)
            
            futures_settle_raw = float(best_contract.settle) if best_contract.settle else None
            # 期货价格单位是元/吨，需要转换为元/公斤（除以1000）
            futures_settle = futures_settle_raw / 1000.0 if futures_settle_raw is not None else None
            spot_price = get_national_spot_price(db, trade_date)
            
            premium = None
            if futures_settle is not None and spot_price is not None:
                premium = futures_settle - spot_price
            
            # 即使premium为None也添加数据点，以便前端能看到期货价格和现货价格
            data_points.append(PremiumDataPoint(
                date=trade_date.isoformat(),
                futures_settle=futures_settle,
                spot_price=spot_price,
                premium=premium
            ))
        
        # 只要有数据点就添加，即使premium可能为None
        if data_points:
            all_series.append(PremiumSeries(
                contract_month=month,
                contract_name=f"{month:02d}合约",
                data=data_points
            ))
    
    if not all_series:
        raise HTTPException(
            status_code=404, 
            detail="未找到升贴水数据。可能原因：1. 没有对应月份的期货合约数据 2. 没有全国现货价格数据 3. 时间范围不匹配"
        )
    
    return PremiumResponse(series=all_series)


class CalendarSpreadDataPoint(BaseModel):
    """月间价差数据点"""
    date: str
    near_contract_settle: Optional[float]  # 近月合约结算价
    far_contract_settle: Optional[float]  # 远月合约结算价
    spread: Optional[float]  # 价差 = 远月 - 近月


class CalendarSpreadSeries(BaseModel):
    """月间价差数据系列"""
    spread_name: str  # 价差名称，如 "03-05价差"
    near_month: int  # 近月月份
    far_month: int  # 远月月份
    data: List[CalendarSpreadDataPoint]


class CalendarSpreadResponse(BaseModel):
    """月间价差响应"""
    series: List[CalendarSpreadSeries]
    update_time: Optional[str] = None


def get_spread_date_range(near_month: int, far_month: int, year: Optional[int] = None) -> tuple[date, date]:
    """
    获取月间价差的时间范围
    X-Y价差，时间从Y+1月的1日至X-1月的最后一日
    
    Args:
        near_month: 近月月份（Y），如 3
        far_month: 远月月份（X），如 5
        year: 合约年份，如果不指定则使用当前年份
    
    Returns:
        (start_date, end_date)
    """
    if year is None:
        year = datetime.now().year
    
    # 开始日期：Y+1月的1日
    start_month = near_month + 1
    start_year = year
    if start_month > 12:
        start_month = 1
        start_year = year + 1
    
    # 结束日期：X-1月的最后一日
    end_month = far_month - 1
    end_year = year
    if end_month < 1:
        end_month = 12
        end_year = year - 1
    
    # 获取月份的最后一天
    if end_month == 12:
        next_month = 1
        next_year = end_year + 1
    else:
        next_month = end_month + 1
        next_year = end_year
    
    start_date = date(start_year, start_month, 1)
    end_date = date(next_year, next_month, 1) - timedelta(days=1)
    
    return start_date, end_date


@router.get("/calendar-spread", response_model=CalendarSpreadResponse)
async def get_calendar_spread(
    spread_pair: Optional[str] = Query(None, description="价差对，如 '03-05'。不指定则返回所有6个价差"),
    start_year: Optional[int] = Query(None, description="起始年份"),
    end_year: Optional[int] = Query(None, description="结束年份"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取月间价差数据
    
    价差 = 远月合约结算价 - 近月合约结算价
    6个价差：03-05、05-07、07-09、09-11、11-01、01-03
    时间范围：X-Y价差，时间从Y+1月的1日至X-1月的最后一日
    """
    spread_pairs = []
    if spread_pair:
        # 解析价差对，如 "03-05"
        parts = spread_pair.split('-')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="价差对格式错误，应为'MM-MM'格式")
        near_month = int(parts[0])
        far_month = int(parts[1])
        spread_pairs.append((near_month, far_month))
    else:
        # 默认6个价差
        spread_pairs = [(3, 5), (5, 7), (7, 9), (9, 11), (11, 1), (1, 3)]
    
    # 确定年份范围
    if start_year and end_year:
        years = list(range(start_year, end_year + 1))
    elif start_year:
        years = list(range(start_year, datetime.now().year + 1))
    elif end_year:
        years = list(range(2020, end_year + 1))  # 假设从2020年开始有数据
    else:
        # 查询数据库中的年份范围
        min_year = db.query(func.min(extract('year', FactFuturesDaily.trade_date))).scalar()
        max_year = db.query(func.max(extract('year', FactFuturesDaily.trade_date))).scalar()
        if min_year and max_year:
            years = list(range(min_year, max_year + 1))
        else:
            years = list(range(2020, datetime.now().year + 1))
    
    all_series = []
    
    for near_month, far_month in spread_pairs:
        near_month_str = f"{near_month:02d}"
        far_month_str = f"{far_month:02d}"
        
        # 收集所有年份的数据
        date_dict_near: Dict[date, List[FactFuturesDaily]] = {}
        date_dict_far: Dict[date, List[FactFuturesDaily]] = {}
        
        for year in years:
            # 获取该年份的时间范围
            start_date, end_date = get_spread_date_range(near_month, far_month, year)
            
            # 如果指定了年份范围，进一步限制
            if start_year:
                start_date = max(start_date, date(start_year, 1, 1))
            if end_year:
                end_date = min(end_date, date(end_year, 12, 31))
            
            # 查询近月合约
            near_futures = db.query(FactFuturesDaily).filter(
                FactFuturesDaily.contract_code.like(f"%{near_month_str}"),
                FactFuturesDaily.trade_date >= start_date,
                FactFuturesDaily.trade_date <= end_date
            ).order_by(FactFuturesDaily.trade_date).all()
            
            # 查询远月合约
            far_futures = db.query(FactFuturesDaily).filter(
                FactFuturesDaily.contract_code.like(f"%{far_month_str}"),
                FactFuturesDaily.trade_date >= start_date,
                FactFuturesDaily.trade_date <= end_date
            ).order_by(FactFuturesDaily.trade_date).all()
            
            # 按日期分组
            for f in near_futures:
                if f.trade_date not in date_dict_near:
                    date_dict_near[f.trade_date] = []
                date_dict_near[f.trade_date].append(f)
            
            for f in far_futures:
                if f.trade_date not in date_dict_far:
                    date_dict_far[f.trade_date] = []
                date_dict_far[f.trade_date].append(f)
        
        # 找出两个合约都存在的日期
        common_dates = set(date_dict_near.keys()) & set(date_dict_far.keys())
        
        # 构建数据点
        data_points = []
        for trade_date in sorted(common_dates):
            near_contracts = date_dict_near[trade_date]
            far_contracts = date_dict_far[trade_date]
            
            # 选择持仓量最大的合约
            near_contract = max(near_contracts, key=lambda x: x.open_interest or 0)
            far_contract = max(far_contracts, key=lambda x: x.open_interest or 0)
            
            # 期货价格单位是元/吨，需要转换为元/公斤（除以1000）
            near_settle_raw = float(near_contract.settle) if near_contract.settle else None
            far_settle_raw = float(far_contract.settle) if far_contract.settle else None
            near_settle = near_settle_raw / 1000.0 if near_settle_raw is not None else None
            far_settle = far_settle_raw / 1000.0 if far_settle_raw is not None else None
            
            spread = None
            if near_settle is not None and far_settle is not None:
                spread = far_settle - near_settle
            
            data_points.append(CalendarSpreadDataPoint(
                date=trade_date.isoformat(),
                near_contract_settle=near_settle,
                far_contract_settle=far_settle,
                spread=spread
            ))
        
        if data_points:
            all_series.append(CalendarSpreadSeries(
                spread_name=f"{near_month_str}-{far_month_str}价差",
                near_month=near_month,
                far_month=far_month,
                data=data_points
            ))
    
    return CalendarSpreadResponse(series=all_series)


class RegionPremiumData(BaseModel):
    """区域升贴水数据"""
    region: str  # 区域名称
    contract_month: int  # 合约月份
    contract_name: str  # 合约名称
    spot_price: Optional[float]  # 区域现货价格
    futures_settle: Optional[float]  # 期货结算价
    premium: Optional[float]  # 升贴水
    date: str  # 日期


class RegionPremiumResponse(BaseModel):
    """重点区域升贴水响应"""
    data: List[RegionPremiumData]
    update_time: Optional[str] = None


@router.get("/region-premium", response_model=RegionPremiumResponse)
async def get_region_premium(
    contract_month: int = Query(..., description="合约月份，如 3, 5, 7, 9, 11, 1"),
    regions: Optional[str] = Query(None, description="区域列表，逗号分隔，如'广东,广西,四川'。默认返回重点区域"),
    trade_date: Optional[date] = Query(None, description="交易日期，默认最新日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取重点区域升贴水数据（表格）
    
    升贴水 = 期货结算价 - 区域现货价格
    """
    # 默认重点区域
    default_regions = ["广东", "广西", "四川", "贵州", "重庆", "湖南", "江西", "湖北", 
                      "陕西", "河南", "河北", "山东", "山西", "江苏", "安徽", "辽宁", 
                      "吉林", "黑龙江"]
    
    if regions:
        region_list = [r.strip() for r in regions.split(',')]
    else:
        region_list = default_regions
    
    # 确定查询日期
    if not trade_date:
        # 查询最新有数据的日期
        latest = db.query(func.max(FactFuturesDaily.trade_date)).scalar()
        if not latest:
            raise HTTPException(status_code=404, detail="无期货数据")
        trade_date = latest
    
    # 查询期货结算价
    month_str = f"{contract_month:02d}"
    futures_query = db.query(FactFuturesDaily).filter(
        FactFuturesDaily.contract_code.like(f"%{month_str}"),
        FactFuturesDaily.trade_date == trade_date
    ).order_by(FactFuturesDaily.open_interest.desc()).first()
    
    if not futures_query:
        raise HTTPException(status_code=404, detail=f"未找到{contract_month:02d}合约在{trade_date}的数据")
    
    # 期货价格单位是元/吨，需要转换为元/公斤（除以1000）
    futures_settle_raw = float(futures_query.settle) if futures_query.settle else None
    futures_settle = futures_settle_raw / 1000.0 if futures_settle_raw is not None else None
    
    # 查询各区域现货价格
    result_data = []
    for region in region_list:
        # 查询区域价格指标
        metric = db.query(DimMetric).filter(
            DimMetric.raw_header.like(f"%{region}%"),
            DimMetric.sheet_name == "分省区猪价",
            DimMetric.freq.in_(["D", "daily"])
        ).first()
        
        spot_price = None
        if metric:
            obs = db.query(FactObservation).filter(
                FactObservation.metric_id == metric.id,
                FactObservation.obs_date == trade_date,
                FactObservation.period_type == "day"
            ).first()
            
            if obs and obs.value:
                spot_price = float(obs.value)
        
        premium = None
        if futures_settle is not None and spot_price is not None:
            premium = futures_settle - spot_price
        
        result_data.append(RegionPremiumData(
            region=region,
            contract_month=contract_month,
            contract_name=f"{contract_month:02d}合约",
            spot_price=spot_price,
            futures_settle=futures_settle,
            premium=premium,
            date=trade_date.isoformat()
        ))
    
    return RegionPremiumResponse(data=result_data)


class VolatilityDataPoint(BaseModel):
    """波动率数据点"""
    date: str
    close_price: Optional[float]  # 收盘价
    volatility_5d: Optional[float]  # 5日波动率（年化）
    volatility_10d: Optional[float]  # 10日波动率（年化）


class VolatilitySeries(BaseModel):
    """波动率数据系列"""
    contract_code: str
    contract_month: int
    data: List[VolatilityDataPoint]


class VolatilityResponse(BaseModel):
    """波动率响应"""
    series: List[VolatilitySeries]
    update_time: Optional[str] = None


def calculate_volatility(prices: List[float], window: int) -> Optional[float]:
    """
    计算波动率
    
    Args:
        prices: 价格列表（按时间顺序）
        window: 窗口大小（5或10）
    
    Returns:
        年化波动率（百分比）
    """
    if len(prices) < window + 1:
        return None
    
    # 计算对数收益率
    returns = []
    for i in range(1, len(prices)):
        if prices[i-1] and prices[i] and prices[i-1] > 0:
            log_return = math.log(prices[i] / prices[i-1])
            returns.append(log_return)
    
    if len(returns) < window:
        return None
    
    # 取最近window个收益率
    recent_returns = returns[-window:]
    
    # 计算标准差
    if len(recent_returns) < 2:
        return None
    
    mean_return = sum(recent_returns) / len(recent_returns)
    variance = sum((r - mean_return) ** 2 for r in recent_returns) / (len(recent_returns) - 1)
    std_dev = math.sqrt(variance)
    
    # 年化处理：乘以√252（一年252个交易日）
    annualized_vol = std_dev * math.sqrt(252) * 100  # 转换为百分比
    
    return annualized_vol


@router.get("/volatility", response_model=VolatilityResponse)
async def get_volatility(
    contract_month: Optional[int] = Query(None, description="合约月份，如 3, 5, 7, 9, 11, 1。不指定则返回所有6个合约"),
    min_volatility_5d: Optional[float] = Query(None, description="5日波动率最小值筛选"),
    max_volatility_5d: Optional[float] = Query(None, description="5日波动率最大值筛选"),
    min_volatility_10d: Optional[float] = Query(None, description="10日波动率最小值筛选"),
    max_volatility_10d: Optional[float] = Query(None, description="10日波动率最大值筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取波动率数据
    
    计算5日、10日波动率
    使用对数收益率和标准差，年化处理（乘以√252）
    """
    contract_months = [contract_month] if contract_month else [3, 5, 7, 9, 11, 1]
    
    all_series = []
    
    for month in contract_months:
        month_str = f"{month:02d}"
        
        # 查询该月份的所有合约数据
        query = db.query(FactFuturesDaily).filter(
            FactFuturesDaily.contract_code.like(f"%{month_str}")
        )
        
        if start_date:
            query = query.filter(FactFuturesDaily.trade_date >= start_date)
        if end_date:
            query = query.filter(FactFuturesDaily.trade_date <= end_date)
        
        futures_data = query.order_by(FactFuturesDaily.trade_date).all()
        
        if not futures_data:
            continue
        
        # 按日期分组，合并不同年份的同月份合约
        date_dict: Dict[date, List[FactFuturesDaily]] = {}
        for f in futures_data:
            if f.trade_date not in date_dict:
                date_dict[f.trade_date] = []
            date_dict[f.trade_date].append(f)
        
        # 按日期排序，构建价格序列
        sorted_dates = sorted(date_dict.keys())
        prices = []
        dates = []
        
        for trade_date in sorted_dates:
            contracts = date_dict[trade_date]
            # 选择持仓量最大的合约
            best_contract = max(contracts, key=lambda x: x.open_interest or 0)
            close_price = float(best_contract.close) if best_contract.close else None
            prices.append(close_price)
            dates.append(trade_date)
        
        # 计算每个日期的波动率
        data_points = []
        for i in range(len(prices)):
            if i < 10:  # 需要至少10个数据点才能计算10日波动率
                continue
            
            # 获取最近的价格序列
            recent_prices = prices[max(0, i-10):i+1]
            
            # 过滤掉None值
            valid_prices = [p for p in recent_prices if p is not None]
            
            if len(valid_prices) < 6:  # 至少需要6个有效价格
                continue
            
            # 计算5日和10日波动率
            vol_5d = None
            vol_10d = None
            
            if len(valid_prices) >= 6:
                vol_5d = calculate_volatility(valid_prices[-6:], 5)
            if len(valid_prices) >= 11:
                vol_10d = calculate_volatility(valid_prices[-11:], 10)
            
            # 应用筛选条件
            if min_volatility_5d is not None and vol_5d is not None and vol_5d < min_volatility_5d:
                continue
            if max_volatility_5d is not None and vol_5d is not None and vol_5d > max_volatility_5d:
                continue
            if min_volatility_10d is not None and vol_10d is not None and vol_10d < min_volatility_10d:
                continue
            if max_volatility_10d is not None and vol_10d is not None and vol_10d > max_volatility_10d:
                continue
            
            data_points.append(VolatilityDataPoint(
                date=dates[i].isoformat(),
                close_price=prices[i],
                volatility_5d=vol_5d,
                volatility_10d=vol_10d
            ))
        
        if data_points:
            # 获取合约代码（使用最新的合约）
            latest_contract = max(date_dict[sorted_dates[-1]], key=lambda x: x.open_interest or 0)
            all_series.append(VolatilitySeries(
                contract_code=latest_contract.contract_code,
                contract_month=month,
                data=data_points
            ))
    
    return VolatilityResponse(series=all_series)
