"""
D4. 集团价格 API
显示重点集团企业生猪出栏价格和白条价格，以及重点市场白条到货量&价格
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional, Dict
from datetime import date, timedelta, datetime
from pydantic import BaseModel
import math
import json

from app.core.database import get_db
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

router = APIRouter(prefix="/api/v1/group-price", tags=["group-price"])


class GroupPriceDataPoint(BaseModel):
    """集团价格数据点"""
    date: str  # 日期 YYYY-MM-DD
    company: str  # 企业名称
    price: Optional[float] = None  # 价格
    premium_discount: Optional[float] = None  # 升贴水


class GroupPriceTableResponse(BaseModel):
    """集团价格表格响应"""
    data: List[GroupPriceDataPoint]
    companies: List[str]  # 企业列表
    date_range: Dict[str, str]  # 日期范围 {start: "YYYY-MM-DD", end: "YYYY-MM-DD"}
    latest_date: Optional[str] = None


class WhiteStripMarketDataPoint(BaseModel):
    """白条市场数据点"""
    date: str  # 日期 YYYY-MM-DD
    market: str  # 市场名称
    arrival_volume: Optional[float] = None  # 到货量
    price: Optional[float] = None  # 价格


class WhiteStripMarketResponse(BaseModel):
    """白条市场响应"""
    data: List[WhiteStripMarketDataPoint]
    markets: List[str]  # 市场列表
    latest_date: Optional[str] = None


# 企业名称映射（从数据库指标名称到显示名称）
COMPANY_MAPPING = {
    "中粮家佳康（吉林）": "吉林中粮",
    "河南牧原": "河南牧原",
    "山东新希望": "山东新希望",
    "广东温氏": "广东温氏",
    "湖南唐人神": "湖南唐人神",
    "江西温氏": "江西温氏",
    "四川德康": "四川德康",
    "贵州富之源": "贵州富之源",
}

# 升贴水映射
PREMIUM_DISCOUNT_MAPPING = {
    "吉林中粮": -300,
    "河南牧原": 0,
    "山东新希望": 200,
    "广东温氏": 500,
    "湖南唐人神": 100,
    "江西温氏": 100,
    "四川德康": -100,
    "贵州富之源": -300,
}


def _extract_company_name(raw_header: str) -> Optional[str]:
    """从原始表头提取企业名称"""
    # 示例：外三元猪：每头重110-125kg：出栏价：吉林：中粮家佳康（吉林）（日）
    if "中粮家佳康（吉林）" in raw_header or "吉林" in raw_header and "中粮" in raw_header:
        return "吉林中粮"
    elif "河南牧原" in raw_header:
        return "河南牧原"
    elif "山东新希望" in raw_header:
        return "山东新希望"
    elif "广东温氏" in raw_header:
        return "广东温氏"
    elif "湖南唐人神" in raw_header:
        return "湖南唐人神"
    elif "江西温氏" in raw_header:
        return "江西温氏"
    elif "四川德康" in raw_header:
        return "四川德康"
    elif "贵州富之源" in raw_header:
        return "贵州富之源"
    return None


@router.get("/group-enterprise-price", response_model=GroupPriceTableResponse)
async def get_group_enterprise_price(
    days: int = Query(15, description="显示最近N天的数据"),
    db: Session = Depends(get_db)
):
    """
    获取重点集团企业生猪出栏价格和白条价格
    包括：吉林中粮、河南牧原、山东新希望、广东温氏、湖南唐人神、江西温氏、四川德康、贵州富之源
    以及：华宝白条、牧原白条、华东、河南山东、湖北陕西、京津冀、东北
    """
    # 查找"集团企业出栏价"sheet的所有指标
    metrics = db.query(DimMetric).filter(
        DimMetric.sheet_name == "集团企业出栏价"
    ).all()
    
    # 提取企业名称并过滤
    company_metrics = {}
    for metric in metrics:
        company_name = _extract_company_name(metric.raw_header)
        if company_name and company_name in COMPANY_MAPPING.values():
            company_metrics[company_name] = metric
    
    # 查找华宝白条和牧原白条数据（从"华宝和牧原白条"sheet）
    huabao_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "华宝和牧原白条",
        func.json_unquote(func.json_extract(DimMetric.parse_json, '$.metric_key')) == 'WHITE_STRIP_PRICE_HUABAO'
    ).first()
    
    muyuan_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "华宝和牧原白条",
        func.json_unquote(func.json_extract(DimMetric.parse_json, '$.metric_key')) == 'WHITE_STRIP_PRICE_MUYUAN'
    ).first()
    
    if huabao_metric:
        company_metrics["华宝白条"] = huabao_metric
    
    if muyuan_metric:
        company_metrics["牧原白条"] = muyuan_metric
    
    # 查找区域数据（华东、河南山东、湖北陕西、京津冀、东北）
    region_mapping = {
        "华东": "WHITE_STRIP_PRICE_EAST_CHINA",
        "河南山东": "WHITE_STRIP_PRICE_HENAN_SHANDONG",
        "湖北陕西": "WHITE_STRIP_PRICE_HUBEI_SHANXI",
        "京津冀": "WHITE_STRIP_PRICE_JINGJINJI",
        "东北": "WHITE_STRIP_PRICE_NORTHEAST",
    }
    
    for region_name, metric_key in region_mapping.items():
        region_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "华宝和牧原白条",
            func.json_unquote(func.json_extract(DimMetric.parse_json, '$.metric_key')) == metric_key
        ).first()
        
        if region_metric:
            company_metrics[region_name] = region_metric
    
    if not company_metrics:
        return GroupPriceTableResponse(
            data=[],
            companies=[],
            date_range={"start": "", "end": ""},
            latest_date=None
        )
    
    # 查询最近N天的数据
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    all_data = []
    
    for company_name, metric in company_metrics.items():
        # 查询该企业的价格数据
        obs_list = db.query(
            FactObservation.obs_date,
            FactObservation.value
        ).filter(
            FactObservation.metric_id == metric.id,
            FactObservation.obs_date >= start_date,
            FactObservation.obs_date <= end_date
        ).order_by(desc(FactObservation.obs_date)).limit(days).all()
        
        for obs in obs_list:
            if obs.value is not None and not math.isnan(obs.value):
                # 对于华宝白条、牧原白条和区域数据，升贴水为None
                premium_discount = PREMIUM_DISCOUNT_MAPPING.get(company_name) if company_name in PREMIUM_DISCOUNT_MAPPING else None
                all_data.append(GroupPriceDataPoint(
                    date=obs.obs_date.isoformat(),
                    company=company_name,
                    price=round(float(obs.value), 2),
                    premium_discount=premium_discount
                ))
    
    # 按日期排序
    all_data.sort(key=lambda x: x.date, reverse=True)
    
    # 获取最新日期
    latest_date = all_data[0].date if all_data else None
    
    # 获取企业列表
    companies = list(company_metrics.keys())
    
    return GroupPriceTableResponse(
        data=all_data,
        companies=companies,
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        latest_date=latest_date
    )


@router.get("/white-strip-market", response_model=WhiteStripMarketResponse)
async def get_white_strip_market(
    days: int = Query(15, description="显示最近N天的数据"),
    db: Session = Depends(get_db)
):
    """
    获取重点市场白条到货量&价格
    数据来源：白条市场跟踪 -> 白条市场 sheet
    """
    # 查找白条市场相关的指标
    # 到货量指标：metric_key包含ARRIVAL
    # 价格指标：metric_key包含PRICE
    arrival_metrics = db.query(DimMetric).filter(
        DimMetric.sheet_name == "白条市场",
        func.json_unquote(func.json_extract(DimMetric.parse_json, '$.metric_key')).like('%ARRIVAL%')
    ).all()
    
    price_metrics = db.query(DimMetric).filter(
        DimMetric.sheet_name == "白条市场",
        func.json_unquote(func.json_extract(DimMetric.parse_json, '$.metric_key')).like('%PRICE%')
    ).all()
    
    if not arrival_metrics and not price_metrics:
        return WhiteStripMarketResponse(
            data=[],
            markets=[],
            latest_date=None
        )
    
    # 查询最近N天的数据
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    all_data = []
    markets = set()
    
    # 查询到货量数据，从FactObservation的tags_json中获取market
    for metric in arrival_metrics:
        obs_list = db.query(
            FactObservation.obs_date,
            FactObservation.value,
            FactObservation.tags_json
        ).filter(
            FactObservation.metric_id == metric.id,
            FactObservation.obs_date >= start_date,
            FactObservation.obs_date <= end_date
        ).order_by(desc(FactObservation.obs_date)).limit(days).all()
        
        for obs in obs_list:
            if obs.value is not None and not math.isnan(obs.value):
                # 从tags_json中提取market
                market = None
                if obs.tags_json:
                    if isinstance(obs.tags_json, str):
                        tags = json.loads(obs.tags_json)
                    else:
                        tags = obs.tags_json
                    market = tags.get('market')
                
                if market:
                    markets.add(market)
                    all_data.append(WhiteStripMarketDataPoint(
                        date=obs.obs_date.isoformat(),
                        market=market,
                        arrival_volume=round(float(obs.value), 2),
                        price=None
                    ))
    
    # 查询价格数据，从FactObservation的tags_json中获取market
    for metric in price_metrics:
        obs_list = db.query(
            FactObservation.obs_date,
            FactObservation.value,
            FactObservation.tags_json
        ).filter(
            FactObservation.metric_id == metric.id,
            FactObservation.obs_date >= start_date,
            FactObservation.obs_date <= end_date
        ).order_by(desc(FactObservation.obs_date)).limit(days).all()
        
        # 合并到现有数据点或创建新数据点
        for obs in obs_list:
            if obs.value is not None and not math.isnan(obs.value):
                # 从tags_json中提取market
                market = None
                if obs.tags_json:
                    if isinstance(obs.tags_json, str):
                        tags = json.loads(obs.tags_json)
                    else:
                        tags = obs.tags_json
                    market = tags.get('market')
                
                if market:
                    markets.add(market)
                    # 查找是否已有该日期和市场的数据点
                    existing = next(
                        (d for d in all_data if d.date == obs.obs_date.isoformat() and d.market == market),
                        None
                    )
                    if existing:
                        existing.price = round(float(obs.value), 2)
                    else:
                        all_data.append(WhiteStripMarketDataPoint(
                            date=obs.obs_date.isoformat(),
                            market=market,
                            arrival_volume=None,
                            price=round(float(obs.value), 2)
                        ))
    
    # 按日期排序
    all_data.sort(key=lambda x: x.date, reverse=True)
    
    # 获取最新日期
    latest_date = all_data[0].date if all_data else None
    
    return WhiteStripMarketResponse(
        data=all_data,
        markets=sorted(list(markets)),
        latest_date=latest_date
    )
