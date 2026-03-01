"""
D4. 集团价格 API
显示重点集团企业生猪出栏价格和白条市场数据

数据来源：hogprice_v3
- fact_enterprise_daily: 企业日度出栏价 (metric_type='output_price')
- fact_carcass_market: 白条市场数据 (carcass_price, carcass_arrival, muyuan_spread等)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict
from datetime import date, timedelta
from pydantic import BaseModel

from app.core.database import get_db

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


# company_code prefix -> 显示名称 映射（output_price公司码带省份后缀如MUYUAN_HN）
COMPANY_PREFIX_DISPLAY = {
    "MUYUAN": "牧原",
    "WENS": "温氏",
    "DEKANG": "德康",
    "NEWHOPE": "新希望",
    "TANGRENSHEN": "唐人神",
    "DABEINONG": "大北农",
    "COFCO": "中粮",
    "XINHAO": "新豪",
    "SHENNONG": "神农",
    "FUZHIYUAN": "富之源",
}

# 省份后缀 -> 中文
PROVINCE_SUFFIX = {
    "HN": "河南", "GD": "广东", "SD": "山东", "SC": "四川",
    "JS": "江苏", "JX": "江西", "HB": "河北", "LN": "辽宁",
    "JL": "吉林", "HLJ": "黑龙江", "HUN": "湖南", "HUB": "湖北",
    "AH": "安徽", "YN": "云南", "SAX": "陕西", "NMG": "内蒙古",
    "GZ": "贵州",
}


def _parse_company_display(company_code: str) -> str:
    """MUYUAN_HN -> 牧原(河南)"""
    parts = company_code.split("_", 1)
    prefix = parts[0]
    suffix = parts[1] if len(parts) > 1 else ""
    name = COMPANY_PREFIX_DISPLAY.get(prefix, prefix)
    prov = PROVINCE_SUFFIX.get(suffix, "")
    return f"{name}({prov})" if prov else name


@router.get("/group-enterprise-price", response_model=GroupPriceTableResponse)
async def get_group_enterprise_price(
    days: int = Query(15, description="显示最近N天的数据"),
    db: Session = Depends(get_db)
):
    """
    获取重点集团企业生猪出栏价格

    数据来源: fact_enterprise_daily (metric_type='output_price')
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    all_data: List[GroupPriceDataPoint] = []
    found_companies: set = set()

    # 查询企业出栏价 — 数据按省份存储（公司码如MUYUAN_HN）
    enterprise_sql = text("""
        SELECT trade_date, company_code, value
        FROM fact_enterprise_daily
        WHERE metric_type = 'output_price'
          AND trade_date >= :start_date
          AND trade_date <= :end_date
          AND value IS NOT NULL
        ORDER BY trade_date DESC
    """)

    rows = db.execute(enterprise_sql, {
        "start_date": start_date,
        "end_date": end_date,
    }).fetchall()

    for row in rows:
        trade_date, company_code, value = row
        company_name = _parse_company_display(company_code)
        found_companies.add(company_name)

        all_data.append(GroupPriceDataPoint(
            date=trade_date.isoformat(),
            company=company_name,
            price=round(float(value), 2),
        ))

    # 按日期降序排序
    all_data.sort(key=lambda x: x.date, reverse=True)

    latest_date = all_data[0].date if all_data else None
    companies = sorted(found_companies)

    return GroupPriceTableResponse(
        data=all_data,
        companies=companies,
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        latest_date=latest_date,
    )


@router.get("/white-strip-market", response_model=WhiteStripMarketResponse)
async def get_white_strip_market(
    days: int = Query(15, description="显示最近N天的数据"),
    db: Session = Depends(get_db)
):
    """
    获取重点市场白条到货量&价格

    数据来源: fact_carcass_market
    - metric_type='carcass_arrival': 到货量
    - metric_type='carcass_price': 白条均价
    source 字段为市场名（如 上海西郊、杭州五和 等）
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    sql = text("""
        SELECT trade_date, source, metric_type, value
        FROM fact_carcass_market
        WHERE metric_type IN ('carcass_arrival', 'carcass_price')
          AND trade_date >= :start_date
          AND trade_date <= :end_date
          AND value IS NOT NULL
        ORDER BY trade_date DESC, source
    """)

    rows = db.execute(sql, {
        "start_date": start_date,
        "end_date": end_date,
    }).fetchall()

    # 按 (date, market) 分组
    grouped: Dict[str, Dict[str, object]] = {}
    markets_set: set = set()

    for row in rows:
        trade_date, source, metric_type, value = row
        date_str = trade_date.isoformat()
        market_name = source  # source字段就是市场名称
        markets_set.add(market_name)

        key = f"{date_str}|{market_name}"
        if key not in grouped:
            grouped[key] = {"date": date_str, "market": market_name}

        if metric_type == "carcass_arrival":
            grouped[key]["arrival_volume"] = round(float(value), 2)
        elif metric_type == "carcass_price":
            grouped[key]["price"] = round(float(value), 2)

    all_data = [
        WhiteStripMarketDataPoint(
            date=v["date"],
            market=v["market"],
            arrival_volume=v.get("arrival_volume"),
            price=v.get("price"),
        )
        for v in grouped.values()
    ]

    # 按日期降序
    all_data.sort(key=lambda x: x.date, reverse=True)

    latest_date = all_data[0].date if all_data else None

    return WhiteStripMarketResponse(
        data=all_data,
        markets=sorted(list(markets_set)),
        latest_date=latest_date,
    )
