"""期货查询接口"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, extract
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import math
import numpy as np
import json
import calendar

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.models import FactFuturesDaily
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile
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


def _get_raw_table_data(db: Session, sheet_name: str, filename_pattern: str = None):
    """获取raw_table数据"""
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


def _parse_excel_date(excel_date: any) -> Optional[date]:
    """解析Excel日期"""
    if isinstance(excel_date, str):
        try:
            if 'T' in excel_date:
                date_str = excel_date.split('T')[0]
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                date_str = excel_date.split()[0] if ' ' in excel_date else excel_date
                return datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            pass
    elif isinstance(excel_date, (int, float)):
        try:
            excel_epoch = datetime(1899, 12, 30)
            return (excel_epoch + timedelta(days=int(excel_date))).date()
        except:
            pass
    elif isinstance(excel_date, date):
        return excel_date
    elif hasattr(excel_date, 'date'):
        return excel_date.date()
    return None


def _is_weekend(d: date) -> bool:
    """判断是否为周末"""
    return d.weekday() >= 5  # 5=Saturday, 6=Sunday


def _is_chinese_holiday(d: date) -> bool:
    """判断是否为中国法定节假日
    简化实现：只判断春节、国庆等主要节假日
    实际应该使用holidays库或维护一个节假日列表
    """
    # TODO: 实现完整的中国节假日判断逻辑
    # 这里先返回False，后续可以完善
    return False


def _is_trading_day(d: date) -> bool:
    """判断是否为交易日（非周末且非节假日）"""
    return not _is_weekend(d) and not _is_chinese_holiday(d)


def is_in_seasonal_range(date_obj: date, contract_month: int) -> bool:
    """
    判断日期是否在合约的季节性图时间范围内
    X月合约的季节性图为X+1月的1日至X-1月的最后一日
    
    例如：03合约的季节性图为4月1日至次年2月29日
    即：从4月1日到次年2月29日（跨年）
    
    判断逻辑：对于日期d，如果：
    - d的月份 >= X+1月 且 d的月份 <= 12月，或者
    - d的月份 >= 1月 且 d的月份 <= X-1月
    则d在范围内
    """
    month = date_obj.month
    start_month = (contract_month + 1) % 12
    if start_month == 0:
        start_month = 12
    end_month = contract_month - 1
    if end_month == 0:
        end_month = 12
    
    # 如果start_month < end_month，说明不跨年（例如07合约：8月到6月，这种情况不存在）
    # 如果start_month > end_month，说明跨年（例如03合约：4月到2月）
    if start_month > end_month:
        # 跨年情况：从start_month到12月，或从1月到end_month
        return month >= start_month or month <= end_month
    else:
        # 不跨年情况（理论上不应该出现，但为了完整性保留）
        return start_month <= month <= end_month


def get_contract_date_range(contract_month: int, year: Optional[int] = None) -> tuple[date, date]:
    """
    获取X月合约升贴水的时间范围：从 (X+1)月1日 到 (X-1)月最后一日。
    - 03合约：4月1日～次年2月最后一日（year=近月所在年）
    - 05合约：6月1日～次年4月最后一日
    - 01合约：2月1日～当年12月31日（同年）

    Args:
        contract_month: 合约月份，如 1, 3, 5, 7, 9, 11
        year: 合约（交割月）所在年份

    Returns:
        (start_date, end_date)
    """
    if year is None:
        year = datetime.now().year

    start_month = contract_month + 1
    if start_month > 12:
        start_month = 1
    end_month = contract_month - 1
    if end_month < 1:
        end_month = 12

    # 跨年：开始月 > 结束月（如03：4月>2月；11：12月>10月）→ 开始在上一年，结束在当年
    if start_month > end_month:
        start_year = year - 1
        end_year = year
    else:
        # 同年（如01：2月～12月）
        start_year = year
        end_year = year

    if end_month == 12:
        next_month, next_year = 1, end_year + 1
    else:
        next_month, next_year = end_month + 1, end_year
    start_date = date(start_year, start_month, 1)
    end_date = date(next_year, next_month, 1) - timedelta(days=1)
    return start_date, end_date


def is_date_in_contract_range(date_obj: date, contract_month: int) -> bool:
    """判断日期是否在X合约时间范围内（(X+1)月1日～(X-1)月最后一日），尝试 year / year-1 / year+1。"""
    for y in (date_obj.year, date_obj.year - 1, date_obj.year + 1):
        start_d, end_d = get_contract_date_range(contract_month, y)
        if start_d <= date_obj <= end_d:
            return True
    return False


class PremiumDataPoint(BaseModel):
    """升贴水数据点"""
    date: str
    futures_settle: Optional[float]  # 期货结算价
    spot_price: Optional[float]  # 现货价格
    premium: Optional[float]  # 升贴水 = 期货结算价 - 现货价格
    premium_ratio: Optional[float] = None  # 升贴水比率 = (期货结算价 - 现货价格) / 现货价格 * 100


class PremiumSeries(BaseModel):
    """升贴水数据系列"""
    contract_month: int  # 合约月份，如 3, 5, 7, 9, 11, 1
    contract_name: str  # 合约名称，如 "03合约"
    data: List[PremiumDataPoint]


class PremiumResponse(BaseModel):
    """升贴水响应"""
    series: List[PremiumSeries]
    update_time: Optional[str] = None


class PremiumDataPointV2(BaseModel):
    """升贴水数据点（V2版本，支持区域）"""
    date: str
    futures_settle: Optional[float]  # 期货结算价（元/公斤）
    spot_price: Optional[float]  # 现货价格（元/公斤）
    premium: Optional[float]  # 升贴水（元/公斤）= 期货结算价 - 现货价格
    premium_ratio: Optional[float] = None  # 升贴水比率（%）= (期货结算价 - 现货价格) / 现货价格 * 100
    year: Optional[int] = None  # 年份，用于季节性图


class PremiumSeriesV2(BaseModel):
    """升贴水数据系列（V2版本）"""
    contract_month: int  # 合约月份，如 3, 5, 7, 9, 11, 1
    contract_name: str  # 合约名称，如 "03合约"
    region: str  # 区域名称，如 "全国均价"、"贵州"等
    data: List[PremiumDataPointV2]


class PremiumResponseV2(BaseModel):
    """升贴水响应（V2版本）"""
    series: List[PremiumSeriesV2]
    region_premiums: Dict[str, float] = {}  # 省区升贴水注释，如 {"贵州": -300, "四川": -100}
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


def get_region_spot_price(db: Session, trade_date: date, region: str) -> Optional[float]:
    """获取区域现货价格
    region: 区域名称，如 "全国均价"、"贵州"、"四川"等
    """
    if region == "全国均价":
        return get_national_spot_price(db, trade_date)
    
    # 查询区域现货价格（支持 内蒙->内蒙古，放宽 freq）
    region_pattern = "内蒙古" if region == "内蒙" else region
    metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "分省区猪价",
        DimMetric.raw_header.like(f'%{region_pattern}%'),
        DimMetric.freq.in_(["D", "daily", "day", "d"])
    ).first()
    if not metric:
        metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价",
            DimMetric.raw_header.like(f'%{region}%')
        ).first()
    
    if not metric:
        return None
    
    obs = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date == trade_date,
        FactObservation.period_type == "day"
    ).first()
    
    if obs and obs.value:
        return float(obs.value)
    return None


def get_region_spot_prices_batch(db: Session, trade_dates: List[date], region: str) -> Dict[date, float]:
    """批量获取区域现货价格，避免 N+1 查询导致超时。
    返回 date -> 价格(元/公斤) 的字典。
    """
    if not trade_dates:
        return {}
    
    if region == "全国均价":
        metric = db.query(DimMetric).filter(
            or_(
                DimMetric.raw_header.like("%中国%"),
                DimMetric.raw_header.like("%全国%")
            ),
            DimMetric.sheet_name == "分省区猪价",
            DimMetric.freq.in_(["D", "daily"])
        ).first()
        if not metric:
            metric = db.query(DimMetric).filter(DimMetric.metric_key == "GL_D_PRICE_NATION").first()
        if not metric:
            metric = db.query(DimMetric).filter(
                DimMetric.metric_name.like("%全国%"),
                DimMetric.metric_name.like("%价格%"),
                DimMetric.freq.in_(["D", "daily"])
            ).first()
        if not metric:
            metric = db.query(DimMetric).filter(
                DimMetric.raw_header.like("%中国%"),
                DimMetric.sheet_name == "分省区猪价"
            ).first()
    else:
        # 省份：支持 内蒙->内蒙古 等别名；放宽 freq 过滤（部分指标可能为 day/null）
        region_pattern = "内蒙古" if region == "内蒙" else region
        metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价",
            DimMetric.raw_header.like(f'%{region_pattern}%'),
            DimMetric.freq.in_(["D", "daily", "day", "d"])
        ).first()
        if not metric:
            metric = db.query(DimMetric).filter(
                DimMetric.sheet_name == "分省区猪价",
                DimMetric.raw_header.like(f'%{region}%')
            ).first()
    
    if not metric:
        return {}
    
    rows = db.query(FactObservation.obs_date, FactObservation.value).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.obs_date.in_(trade_dates),
        FactObservation.period_type == "day",
        FactObservation.value.isnot(None)
    ).all()
    
    return {r.obs_date: float(r.value) for r in rows if r.value is not None}


@router.get("/premium/v2", response_model=PremiumResponseV2)
async def get_premium_data_v2(
    contract_month: Optional[int] = Query(None, description="合约月份，如 3, 5, 7, 9, 11, 1。不指定则返回所有6个合约"),
    region: str = Query("全国均价", description="区域：全国均价、贵州、四川、云南、广东、广西、江苏、内蒙"),
    view_type: str = Query("全部日期", description="视图类型：季节性、全部日期"),
    format_type: str = Query("全部格式", description="格式类型：全部格式"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取升贴水数据（V2版本，从Excel文件读取）
    
    数据来源：4.1、生猪期货升贴水数据（盘面结算价）.xlsx
    Sheet：期货结算价(1月交割连续)_生猪
    
    数据结构：
    - 第1行：表头（指标名称）
    - 第2行：单位（元/吨）
    - 第3行：来源（大连商品交易所）
    - 第4行开始：数据
      - A列：日期
      - B列：01合约（1月交割连续）
      - C列：03合约（3月交割连续）
      - D列：05合约（5月交割连续）
      - E列：07合约（7月交割连续）
      - F列：09合约（9月交割连续）
      - G列：11合约（11月交割连续）
    
    升贴水 = 期货结算价 - 区域现货价格
    升贴水比率 = 升贴水 / 合约价格 * 100
    """
    # 省区升贴水注释
    region_premiums = {
        "贵州": -300,
        "四川": -100,
        "内蒙": -300,
        "广西": -200,
        "云南": -600,
        "江苏": 500,
        "广东": 500,
        "全国均价": 0  # 全国均价没有升贴水
    }
    
    # 获取Excel数据
    excel_data = _get_raw_table_data(db, "期货结算价(1月交割连续)_生猪", "4.1、生猪期货升贴水数据")
    
    if not excel_data or len(excel_data) < 4:
        raise HTTPException(status_code=404, detail="未找到期货结算价Excel数据")
    
    # 先收集所有日期（A列），用于一次性批量查询现货价格，避免 N+1 导致超时
    all_dates_set = set()
    for row_idx in range(3, len(excel_data)):
        row = excel_data[row_idx]
        if len(row) < 1:
            continue
        date_val = row[0]
        date_obj = _parse_excel_date(date_val)
        if date_obj:
            all_dates_set.add(date_obj)
    all_dates_list = list(all_dates_set)
    spot_price_map = get_region_spot_prices_batch(db, all_dates_list, region)
    
    # 合约月份到列索引的映射
    contract_col_map = {
        1: 1,   # B列（索引1）：01合约
        3: 2,   # C列（索引2）：03合约
        5: 3,   # D列（索引3）：05合约
        7: 4,   # E列（索引4）：07合约
        9: 5,   # F列（索引5）：09合约
        11: 6   # G列（索引6）：11合约
    }
    
    # 按需求：01、03、05、07、09、11 共 6 个合约
    contract_months = [contract_month] if contract_month else [1, 3, 5, 7, 9, 11]
    
    all_series = []
    
    for month in contract_months:
        if month not in contract_col_map:
            continue
        
        col_idx = contract_col_map[month]
        
        # 从第4行开始读取数据（索引3）
        futures_data = []
        for row_idx in range(3, len(excel_data)):
            row = excel_data[row_idx]
            
            if len(row) <= col_idx:
                continue
            
            date_val = row[0] if len(row) > 0 else None  # A列（索引0）是日期
            futures_val = row[col_idx] if len(row) > col_idx else None
            
            if not date_val or futures_val is None or futures_val == "":
                continue
            
            date_obj = _parse_excel_date(date_val)
            if not date_obj:
                continue
            
            try:
                futures_price = float(futures_val)
                # 期货价格单位是元/吨，转换为元/公斤（除以1000）
                futures_price_per_kg = futures_price / 1000.0
                
                futures_data.append({
                    'date': date_obj,
                    'futures_settle': futures_price_per_kg
                })
            except (ValueError, TypeError):
                continue
        
        if not futures_data:
            continue
        
        # 使用预加载的现货价格计算升贴水（避免逐日查询导致超时）
        data_points = []
        for item in futures_data:
            trade_date = item['date']
            futures_settle = item['futures_settle']
            spot_price = spot_price_map.get(trade_date)
            
            # 计算升贴水和升贴水比率
            # 升贴水 = 期货价格 - 现货价格
            # 升贴水比率 = 升贴水 / 合约价格
            premium = None
            premium_ratio = None
            
            if futures_settle is not None and spot_price is not None:
                premium = futures_settle - spot_price
                # 升贴水比率 = 升贴水 / 合约价格（不是除以现货价格）
                if futures_settle > 0:
                    premium_ratio = (premium / futures_settle) * 100
            
            # 判断是否为当月（合约交割月），如果是当月则升贴水比率为空
            is_delivery_month = False
            if month == 1:
                # 01合约的交割月是1月
                is_delivery_month = trade_date.month == 1
            else:
                is_delivery_month = trade_date.month == month
            
            # 如果是当月，升贴水比率设为None
            if is_delivery_month:
                premium_ratio = None
            
            data_points.append(PremiumDataPointV2(
                date=trade_date.isoformat(),
                futures_settle=round(futures_settle, 2) if futures_settle else None,
                spot_price=round(spot_price, 2) if spot_price else None,
                premium=round(premium, 2) if premium else None,
                premium_ratio=round(premium_ratio, 2) if premium_ratio else None,
                year=trade_date.year
            ))
        
        # 根据view_type过滤数据
        if view_type == "季节性":
            # 季节性图：X月合约的季节性图为X+1月的1日至X-1月的最后一日，剔除假期和周末
            seasonal_data = []
            for point in data_points:
                point_date = datetime.strptime(point.date.split('T')[0], '%Y-%m-%d').date()
                
                # 检查是否在季节性时间范围内（按月份判断，跨年）
                if is_in_seasonal_range(point_date, month) and _is_trading_day(point_date):
                    seasonal_data.append(point)
            
            data_points = seasonal_data
        else:
            # 全部日期：仅保留在X合约时间轴内的点（(X+1)月1日～(X-1)月最后一日）
            data_points = [
                p for p in data_points
                if is_date_in_contract_range(datetime.strptime(p.date.split('T')[0], '%Y-%m-%d').date(), month)
            ]
        
        # 按日期排序
        data_points.sort(key=lambda x: x.date)
        
        if data_points:
            all_series.append(PremiumSeriesV2(
                contract_month=month,
                contract_name=f"{month:02d}合约",
                region=region,
                data=data_points
            ))
    
    if not all_series:
        raise HTTPException(
            status_code=404,
            detail="未找到升贴水数据"
        )
    
    return PremiumResponseV2(
        series=all_series,
        region_premiums={k: v for k, v in region_premiums.items() if k == region or region == "全国均价"},
        update_time=None
    )


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
    规则：X-Y价差，时间从 (Y+1)月1日 到 (X-1)月最后一日。
    - 03-05（近月03、远月05）：6月1日 ～ 次年2月最后一日（year 指近月所在年）
    - 05-07：8月1日 ～ 次年4月最后一日
    - 11-01（同年）：2月1日 ～ 10月最后一日

    Args:
        near_month: 近月月份（X），如 3
        far_month: 远月月份（Y），如 5
        year: 近月合约所在年份，不指定则用当前年

    Returns:
        (start_date, end_date)
    """
    if year is None:
        year = datetime.now().year

    # 开始：(Y+1)月1日
    start_month = far_month + 1
    if start_month > 12:
        start_month = 1
    # 结束：(X-1)月最后一日
    end_month = near_month - 1
    if end_month < 1:
        end_month = 12

    # 跨年：开始月 > 结束月（如 03-05：6月 > 2月）→ 开始在上一年，结束在当年
    if start_month > end_month:
        start_year = year - 1
        end_year = year
    else:
        # 同年（如 11-01：2月～10月；01-03：4月～12月）
        start_year = year
        end_year = year

    if end_month == 12:
        next_month, next_year = 1, end_year + 1
    else:
        next_month, next_year = end_month + 1, end_year
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
    获取月间价差数据（从Excel文件读取）
    
    数据来源：4.1、生猪期货升贴水数据（盘面结算价）.xlsx
    价差 = 远月合约结算价 - 近月合约结算价
    6个价差：03-05、05-07、07-09、09-11、11-01、01-03
    时间范围：X-Y价差，日期从Y的次月1日到X的前一月的最后一日
    例如：03-05价差，日期从6月1日到2月28日
    """
    # 获取Excel数据
    excel_data = _get_raw_table_data(db, "期货结算价(1月交割连续)_生猪", "4.1、生猪期货升贴水数据")
    
    if not excel_data or len(excel_data) < 4:
        raise HTTPException(status_code=404, detail="未找到期货结算价Excel数据")
    
    # 合约月份到列索引的映射
    contract_col_map = {
        1: 1,   # B列（索引1）：01合约
        3: 2,   # C列（索引2）：03合约
        5: 3,   # D列（索引3）：05合约
        7: 4,   # E列（索引4）：07合约
        9: 5,   # F列（索引5）：09合约
        11: 6   # G列（索引6）：11合约
    }
    
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
    
    all_series = []
    
    for near_month, far_month in spread_pairs:
        if near_month not in contract_col_map or far_month not in contract_col_map:
            continue
        
        near_col_idx = contract_col_map[near_month]
        far_col_idx = contract_col_map[far_month]
        
        # 从Excel读取两个合约的数据
        near_futures_data = {}
        far_futures_data = {}
        
        for row_idx in range(3, len(excel_data)):
            row = excel_data[row_idx]
            
            if len(row) <= max(near_col_idx, far_col_idx):
                continue
            
            date_val = row[0] if len(row) > 0 else None
            near_val = row[near_col_idx] if len(row) > near_col_idx else None
            far_val = row[far_col_idx] if len(row) > far_col_idx else None
            
            if not date_val:
                continue
            
            date_obj = _parse_excel_date(date_val)
            if not date_obj:
                continue
            
            # 检查日期是否在价差的时间范围内（X-Y 价差：Y 次月 1 日 ～ X 前一月最后一日，跨年）
            start_date, end_date = get_spread_date_range(near_month, far_month, date_obj.year)
            if date_obj < start_date or date_obj > end_date:
                start_date_next, end_date_next = get_spread_date_range(near_month, far_month, date_obj.year + 1)
                if date_obj < start_date_next or date_obj > end_date_next:
                    start_date_prev, end_date_prev = get_spread_date_range(near_month, far_month, date_obj.year - 1)
                    if date_obj < start_date_prev or date_obj > end_date_prev:
                        continue
            
            try:
                if near_val is not None and near_val != "":
                    near_price = float(near_val) / 1000.0  # 转换为元/公斤
                    near_futures_data[date_obj] = near_price
                
                if far_val is not None and far_val != "":
                    far_price = float(far_val) / 1000.0  # 转换为元/公斤
                    far_futures_data[date_obj] = far_price
            except (ValueError, TypeError):
                continue
        
        # 找出两个合约都存在的日期
        common_dates = sorted(set(near_futures_data.keys()) & set(far_futures_data.keys()))
        
        # 构建数据点（无数据也返回该价差，保证 6 个图表位格式一致）
        data_points = []
        for trade_date in common_dates:
            near_settle = near_futures_data.get(trade_date)
            far_settle = far_futures_data.get(trade_date)
            spread = None
            if near_settle is not None and far_settle is not None:
                spread = far_settle - near_settle
            data_points.append(CalendarSpreadDataPoint(
                date=trade_date.isoformat(),
                near_contract_settle=near_settle,
                far_contract_settle=far_settle,
                spread=spread
            ))
        near_month_str = f"{near_month:02d}"
        far_month_str = f"{far_month:02d}"
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
    close_price: Optional[float] = None  # 收盘价
    settle_price: Optional[float] = None  # 主力合约结算价
    open_interest: Optional[int] = None  # 持仓量
    volatility: Optional[float] = None  # 波动率（年化%）
    year: Optional[int] = None  # 年份，用于季节性图


class VolatilitySeries(BaseModel):
    """波动率数据系列"""
    contract_code: str
    contract_month: int
    data: List[VolatilityDataPoint]


class VolatilityResponse(BaseModel):
    """波动率响应"""
    series: List[VolatilitySeries]
    update_time: Optional[str] = None


def calculate_volatility(prices: List[float], current_idx: int, window_days: int = 10) -> Optional[float]:
    """
    计算波动率（以10日为例）：
    （1）从第11天开始，收益率 = ln(当日价格/10日前价格)
    （2）从第21天开始，计算过去10天收益率的标准差
    （3）波动率 = 标准差 * sqrt(252)
    """
    n = window_days
    # 第21天才有第一个波动率（需 2n 个价格：0..2n-1，即索引 2n-1 为第 2n 天）
    if current_idx < 2 * n:
        return None
    # 收益率：从第 n 天到当前，共 current_idx - n + 1 个
    returns = []
    for i in range(n, current_idx + 1):
        if i >= len(prices) or prices[i] is None or prices[i - n] is None:
            continue
        if prices[i - n] > 0 and prices[i] > 0:
            returns.append(math.log(prices[i] / prices[i - n]))
    if len(returns) < n:
        return None
    recent_returns = returns[-n:]
    if len(recent_returns) < 2:
        return None
    mean_return = sum(recent_returns) / len(recent_returns)
    variance = sum((r - mean_return) ** 2 for r in recent_returns) / (len(recent_returns) - 1)
    std_dev = math.sqrt(variance)
    return std_dev * math.sqrt(252) * 100


# 波动率与月间价差、升贴水 V2 同源：4.1、生猪期货升贴水数据（盘面结算价）.xlsx → sheet「期货结算价(1月交割连续)_生猪」
VOLATILITY_EXCEL_SHEET = "期货结算价(1月交割连续)_生猪"
VOLATILITY_EXCEL_FILENAME = "4.1、生猪期货升贴水数据"
VOLATILITY_CONTRACT_COL_MAP = {1: 1, 3: 2, 5: 3, 7: 4, 9: 5, 11: 6}  # B=01, C=03, D=05, E=07, F=09, G=11


def _date_to_contract_year(d: date, contract_month: int) -> int:
    """日期 d 在合约月份 contract_month 的季节区间内对应的合约年。"""
    start_month = (contract_month + 1) if contract_month < 12 else 1
    return d.year + 1 if d.month >= start_month else d.year


@router.get("/volatility", response_model=VolatilityResponse)
async def get_volatility(
    contract_month: Optional[int] = Query(None, description="合约月份，如 3, 5, 7, 9, 11, 1。不指定则返回所有6个合约"),
    window_days: int = Query(10, description="波动率窗口：5=5日波动率，10=10日波动率"),
    min_volatility: Optional[float] = Query(None, description="波动率最小值筛选"),
    max_volatility: Optional[float] = Query(None, description="波动率最大值筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取波动率数据。数据来源与升贴水、月间价差一致：4.1、生猪期货升贴水数据（盘面结算价）.xlsx。
    （1）收益率：从第11天起，收益率=ln(当日价格/10日前价格)
    （2）从第21天起，计算过去10天收益率的标准差
    （3）波动率=标准差*sqrt(252)
    按合约月份（03/05/07等）分年计算，返回季节性多曲线图所需数据。
    """
    excel_data = _get_raw_table_data(db, VOLATILITY_EXCEL_SHEET, VOLATILITY_EXCEL_FILENAME)
    if not excel_data or len(excel_data) < 4:
        raise HTTPException(status_code=404, detail="未找到波动率数据，请先导入 4.1、生猪期货升贴水数据（盘面结算价）.xlsx")

    contract_months = [contract_month] if contract_month else [1, 3, 5, 7, 9, 11]
    all_series = []
    min_required = 2 * window_days + 1

    for month in contract_months:
        if month not in VOLATILITY_CONTRACT_COL_MAP:
            continue
        col_idx = VOLATILITY_CONTRACT_COL_MAP[month]
        month_str = f"{month:02d}"
        # 从 Excel 读取该合约列：(日期, 价格)，并赋予合约年
        date_price_year: List[tuple] = []
        for row_idx in range(3, len(excel_data)):
            row = excel_data[row_idx]
            if len(row) <= col_idx:
                continue
            date_val = row[0] if len(row) > 0 else None
            price_val = row[col_idx] if len(row) > col_idx else None
            if not date_val:
                continue
            date_obj = _parse_excel_date(date_val)
            if not date_obj:
                continue
            if start_date and date_obj < start_date:
                continue
            if end_date and date_obj > end_date:
                continue
            if not is_in_seasonal_range(date_obj, month):
                continue
            try:
                if price_val is None or price_val == "":
                    continue
                price = float(price_val)
                if price <= 0:
                    continue
            except (ValueError, TypeError):
                continue
            cy = _date_to_contract_year(date_obj, month)
            date_price_year.append((date_obj, price, cy))

        if not date_price_year:
            continue
        date_price_year.sort(key=lambda x: x[0])

        # 按合约年分组，每组内按日期排序后计算波动率
        by_year: Dict[int, List[tuple]] = {}
        for d, p, cy in date_price_year:
            if cy not in by_year:
                by_year[cy] = []
            by_year[cy].append((d, p))
        for cy in by_year:
            by_year[cy].sort(key=lambda x: x[0])

        month_data_points: List[VolatilityDataPoint] = []
        for cy in sorted(by_year.keys()):
            points = by_year[cy]
            if len(points) < min_required:
                continue
            dates = [p[0] for p in points]
            prices = [p[1] for p in points]
            for i in range(len(prices)):
                if prices[i] is None or prices[i] <= 0:
                    continue
                trade_date = dates[i]
                vol = calculate_volatility(prices, i, window_days)
                if vol is None:
                    continue
                if min_volatility is not None and vol < min_volatility:
                    continue
                if max_volatility is not None and vol > max_volatility:
                    continue
                # Excel 列为元/吨，统一转为元/公斤（与升贴水一致）
                price_kg = round(prices[i] / 1000.0, 2)
                month_data_points.append(VolatilityDataPoint(
                    date=trade_date.isoformat(),
                    close_price=price_kg,
                    settle_price=price_kg,
                    open_interest=None,
                    volatility=round(vol, 2),
                    year=cy,
                ))

        if month_data_points:
            month_data_points.sort(key=lambda x: x.date)
            all_series.append(VolatilitySeries(
                contract_code=f"lh{month_str}",
                contract_month=month,
                data=month_data_points,
            ))

    return VolatilityResponse(series=all_series)


# ========== 仓单数据 ==========
# 钢联模板：仓单数据 sheet，列映射（0-based）: B=总量, C=德康, I=神农, L=富之源, M=扬翔, O=牧原, R=中粮
WAREHOUSE_RECEIPT_COLS = {
    "total": 1,    # B列 注册仓单总量
    "德康": 2,     # C列
    "神农": 8,     # I列
    "富之源": 11,  # L列
    "扬翔": 12,    # M列
    "牧原": 14,    # O列
    "中粮": 17,    # R列
}
ENTERPRISE_NAMES = ["德康", "牧原", "中粮", "神农", "富之源", "扬翔"]
# 图表折线显示的企业候选（不含扬翔，用中粮等）
CHART_ENTERPRISE_NAMES = ["德康", "牧原", "中粮", "神农", "富之源"]


class WarehouseReceiptChartPoint(BaseModel):
    date: str
    total: Optional[float] = None
    enterprises: Dict[str, Optional[float]] = {}


class WarehouseReceiptChartResponse(BaseModel):
    data: List[WarehouseReceiptChartPoint]
    date_range: Dict[str, Optional[str]]
    top2_enterprises: List[str]  # 用于折线图显示的最多2个企业


class WarehouseReceiptTableRow(BaseModel):
    enterprise: str
    total: Optional[float] = None
    warehouses: List[Dict[str, Any]] = []  # [{name, quantity}, ...]


class WarehouseReceiptTableResponse(BaseModel):
    data: List[WarehouseReceiptTableRow]
    enterprises: List[str]


# 企业名 -> 表头关键词与展示列名：(关键词, 展示名)，按顺序；首项一般为总量
# 例：DCE：猪：注册仓单：德康农牧库（日）-> 德康，常熟德康（德康农牧）库 -> 常熟
WAREHOUSE_ENTERPRISE_HEADERS = {
    "德康": [("德康农牧库", "德康"), ("常熟德康", "常熟"), ("江安德康", "江安"), ("泸州德康", "泸州"), ("泗阳德康", "泗阳"), ("渠县德康", "渠县")],
    "牧原": [("牧原", "牧原")],
    "中粮": [("中粮", "中粮")],
    "神农": [("神农", "神农")],
    "富之源": [("富之源", "富之源")],
    "扬翔": [("扬翔", "扬翔")],
}


class WarehouseReceiptRawRow(BaseModel):
    date: str
    values: Dict[str, Optional[float]] = {}  # 列展示名 -> 数值


class WarehouseReceiptRawResponse(BaseModel):
    enterprise: str
    columns: List[str]  # ['日期', '德康', '常熟', ...]
    rows: List[WarehouseReceiptRawRow]


def _parse_warehouse_receipt_value(v: Any) -> Optional[float]:
    """解析仓单数值"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and (v != v or v == float('inf')):
            return None
        return float(v)
    s = str(v).strip()
    if not s or s.lower() in ('nan', '-', '—', ''):
        return None
    try:
        return float(s.replace(',', ''))
    except ValueError:
        return None


@router.get("/warehouse-receipt/chart", response_model=WarehouseReceiptChartResponse)
async def get_warehouse_receipt_chart(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    注册仓单统计 - 图表数据
    钢联模板：仓单数据 sheet，B列=总量，德康C、牧原O、中粮R、神农I、富之源L、扬翔M
    """
    table_data = _get_raw_table_data(db, "仓单数据", "钢联")
    if not table_data or len(table_data) < 2:
        return WarehouseReceiptChartResponse(
            data=[],
            date_range={"start": None, "end": None},
            top2_enterprises=[]
        )
    # 假设第0行为表头，第1行起为数据；日期在第0列
    points = []
    for row in table_data[1:]:
        if not row or len(row) <= 1:
            continue
        dt = _parse_excel_date(row[0]) if len(row) > 0 else None
        if not dt:
            continue
        total_val = _parse_warehouse_receipt_value(row[WAREHOUSE_RECEIPT_COLS["total"]]) if len(row) > WAREHOUSE_RECEIPT_COLS["total"] else None
        enterprises_val = {}
        for name in ENTERPRISE_NAMES:
            col = WAREHOUSE_RECEIPT_COLS.get(name)
            if col is not None and len(row) > col:
                enterprises_val[name] = _parse_warehouse_receipt_value(row[col])
        points.append(WarehouseReceiptChartPoint(
            date=dt.isoformat(),
            total=total_val,
            enterprises=enterprises_val
        ))
    if not points:
        return WarehouseReceiptChartResponse(data=[], date_range={"start": None, "end": None}, top2_enterprises=[])
    # 按日期排序
    points.sort(key=lambda x: x.date)
    # 日期范围过滤
    if start_date:
        points = [p for p in points if p.date >= start_date.isoformat()]
    if end_date:
        points = [p for p in points if p.date <= end_date.isoformat()]
    if not points:
        return WarehouseReceiptChartResponse(data=[], date_range={"start": None, "end": None}, top2_enterprises=[])
    date_range = {"start": points[0].date, "end": points[-1].date}
    # 选择数值最大的2个企业作为折线图显示（不使用扬翔，使用中粮等）
    last_point = points[-1]
    ent_sums = [(name, last_point.enterprises.get(name) or 0) for name in CHART_ENTERPRISE_NAMES]
    ent_sums.sort(key=lambda x: x[1], reverse=True)
    top2 = [e[0] for e in ent_sums[:2] if e[1] > 0]
    return WarehouseReceiptChartResponse(data=points, date_range=date_range, top2_enterprises=top2)


@router.get("/warehouse-receipt/table", response_model=WarehouseReceiptTableResponse)
async def get_warehouse_receipt_table(
    enterprises: Optional[str] = Query(None, description="企业筛选，逗号分隔，如 德康,牧原,中粮"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    企业仓单统计 - 表格数据
    显示企业总量；交割库明细需 sheet 有对应结构时扩展
    """
    table_data = _get_raw_table_data(db, "仓单数据", "钢联")
    if not table_data or len(table_data) < 2:
        return WarehouseReceiptTableResponse(data=[], enterprises=ENTERPRISE_NAMES)
    filter_names = [s.strip() for s in (enterprises or "").split(",") if s.strip()] if enterprises else []
    if not filter_names:
        filter_names = ENTERPRISE_NAMES.copy()
    # 取最新日期的企业总量
    points = []
    for row in table_data[1:]:
        if not row or len(row) <= 1:
            continue
        dt = _parse_excel_date(row[0]) if len(row) > 0 else None
        if not dt:
            continue
        total_val = _parse_warehouse_receipt_value(row[WAREHOUSE_RECEIPT_COLS["total"]]) if len(row) > WAREHOUSE_RECEIPT_COLS["total"] else None
        enterprises_val = {}
        for name in ENTERPRISE_NAMES:
            col = WAREHOUSE_RECEIPT_COLS.get(name)
            if col is not None and len(row) > col:
                enterprises_val[name] = _parse_warehouse_receipt_value(row[col])
        points.append((dt, total_val, enterprises_val))
    if not points:
        return WarehouseReceiptTableResponse(data=[], enterprises=ENTERPRISE_NAMES)
    points.sort(key=lambda x: x[0], reverse=True)
    latest_date = points[0][0]
    latest_row = next((p for p in points if p[0] == latest_date), points[0])
    _, _, latest_ent = latest_row
    rows = []
    for name in filter_names:
        if name not in ENTERPRISE_NAMES:
            continue
        val = latest_ent.get(name)
        rows.append(WarehouseReceiptTableRow(enterprise=name, total=val, warehouses=[]))
    return WarehouseReceiptTableResponse(data=rows, enterprises=ENTERPRISE_NAMES)


def _short_label_from_header(header_str: str, enterprise: str) -> str:
    """
    从表头文案提取简短列名。如 常熟德康（德康农牧）库 -> 常熟；中粮华东库 -> 华东。
    """
    s = str(header_str).strip()
    for prefix in ("DCE：猪：注册仓单：", "注册仓单：", "DCE："):
        if s.startswith(prefix):
            s = s[len(prefix):]
    for suffix in ("（日）", "(日)", "（月）", "(月)"):
        if suffix in s:
            s = s.split(suffix)[0].strip()
    if "（" in s:
        s = s.split("（")[0].strip()
    if "(" in s:
        s = s.split("(")[0].strip()
    s = s.rstrip("库").strip()
    if enterprise in s:
        before = s.split(enterprise)[0].strip()
        after = s.split(enterprise)[-1].strip() if enterprise in s else ""
        if before and len(before) <= 4:
            return before
        if after and len(after) <= 4:
            return after
        if before:
            return before[:4]
        if after:
            return after[:4]
    return s[:6] if len(s) > 6 else (s or enterprise)


def _find_warehouse_columns_for_enterprise(header_row: List[Any], enterprise: str) -> List[tuple]:
    """
    根据表头行解析该企业对应的列：(列索引, 展示名)。
    先按 WAREHOUSE_ENTERPRISE_HEADERS 顺序匹配；再扫描所有含企业名的列补充分库（与德康道理一致）。
    """
    pairs = WAREHOUSE_ENTERPRISE_HEADERS.get(enterprise) or [(enterprise, enterprise)]
    result: List[tuple] = []
    matched_cols: set = set()
    for keyword, short_name in pairs:
        for col_idx in range(len(header_row)):
            cell = header_row[col_idx] if col_idx < len(header_row) else None
            if cell is None or col_idx in matched_cols:
                continue
            if keyword in str(cell).strip():
                result.append((col_idx, short_name))
                matched_cols.add(col_idx)
                break
    used_names = {n for _, n in result}
    for col_idx in range(len(header_row)):
        if col_idx in matched_cols:
            continue
        cell = header_row[col_idx] if col_idx < len(header_row) else None
        if cell is None:
            continue
        h = str(cell).strip()
        if enterprise in h:
            short = _short_label_from_header(h, enterprise)
            if short:
                base = short
                n = 1
                while short in used_names:
                    n += 1
                    short = f"{base}{n}"
                used_names.add(short)
                result.append((col_idx, short))
                matched_cols.add(col_idx)
    return result


@router.get("/warehouse-receipt/raw", response_model=WarehouseReceiptRawResponse)
async def get_warehouse_receipt_raw(
    enterprise: str = Query(..., description="企业名称，单选：德康/牧原/中粮/神农/富之源/扬翔"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    企业仓单原始数据：单选企业 + 日期范围，返回该企业总量及分库列（日期、德康、常熟、江安…）。
    表头需含关键词（如 德康农牧库、常熟德康）；若无则退回固定列企业总量。
    """
    if enterprise not in ENTERPRISE_NAMES:
        raise HTTPException(status_code=400, detail=f"企业须为: {', '.join(ENTERPRISE_NAMES)}")
    table_data = _get_raw_table_data(db, "仓单数据", "钢联")
    if not table_data or len(table_data) < 2:
        return WarehouseReceiptRawResponse(enterprise=enterprise, columns=["日期", "总仓单量", enterprise], rows=[])

    # 表头可能在首行或第二行（如 DCE：猪：注册仓单：德康农牧库（日）等）
    header_row = table_data[0] if table_data else []
    col_tuples = _find_warehouse_columns_for_enterprise(header_row, enterprise)
    data_start = 1
    if not col_tuples and len(table_data) > 2:
        header_row = table_data[1]
        col_tuples = _find_warehouse_columns_for_enterprise(header_row, enterprise)
        if col_tuples:
            data_start = 2
    if not col_tuples:
        fixed_col = WAREHOUSE_RECEIPT_COLS.get(enterprise)
        if fixed_col is not None:
            col_tuples = [(fixed_col, enterprise)]
        else:
            return WarehouseReceiptRawResponse(enterprise=enterprise, columns=["日期", "总仓单量", enterprise], rows=[])

    # 公共列：DCE：猪：注册仓单（日）总仓单量，放在日期后、企业分库列前
    total_col_name = "总仓单量"
    columns = ["日期", total_col_name] + [short for _, short in col_tuples]
    total_col_idx = WAREHOUSE_RECEIPT_COLS["total"]
    rows_out: List[WarehouseReceiptRawRow] = []
    for row in table_data[data_start:]:
        if not row or len(row) <= 0:
            continue
        dt = _parse_excel_date(row[0])
        if not dt:
            continue
        if start_date and dt < start_date:
            continue
        if end_date and dt > end_date:
            continue
        values = {}
        values[total_col_name] = _parse_warehouse_receipt_value(row[total_col_idx]) if len(row) > total_col_idx else None
        for col_idx, short_name in col_tuples:
            if col_idx < len(row):
                values[short_name] = _parse_warehouse_receipt_value(row[col_idx])
            else:
                values[short_name] = None
        rows_out.append(WarehouseReceiptRawRow(date=dt.isoformat(), values=values))
    rows_out.sort(key=lambda x: x.date, reverse=True)  # 日期倒序，最新在前
    return WarehouseReceiptRawResponse(enterprise=enterprise, columns=columns, rows=rows_out)
