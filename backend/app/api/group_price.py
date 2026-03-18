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


class GroupPriceTableResponse(BaseModel):
    """集团价格表格响应（含表格一 + 表格二白条到货量&价格，旧版单接口）"""
    data: List[GroupPriceDataPoint]
    companies: List[str]  # 企业列表
    date_range: Dict[str, str]  # 日期范围 {start: "YYYY-MM-DD", end: "YYYY-MM-DD"}
    latest_date: Optional[str] = None
    white_strip_market: Optional[WhiteStripMarketResponse] = None  # 表格二：重点市场白条到货量&价格


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

# 华宝/牧原白条：fact_carcass_market (source, region_code) -> 前端列名（与 r05 HUABAO_MUYUAN_COLS 一致）
WHITE_STRIP_DISPLAY = {
    ("HUABAO", "NATION"): "华宝白条",
    ("MUYUAN", "EAST"): "华东",
    ("MUYUAN", "HENAN_SHANDONG"): "河南山东",
    ("MUYUAN", "HUBEI_SHAANXI"): "湖北陕西",
    ("MUYUAN", "BEIJING_TIANJIN_HEBEI"): "京津冀",
    ("MUYUAN", "NORTHEAST"): "东北",
}
# 表格1 白条列顺序：华宝白条 + 牧原五区域（与前端 MUYUAN_WHITE_STRIP_REGIONS 一致）
WHITE_STRIP_COLUMN_ORDER = ["华宝白条", "华东", "河南山东", "湖北陕西", "京津冀", "东北"]

# 旧版表格1 企业列顺序（省份+企业名）：吉林中粮、河南牧原、山东新希望、广东温氏、湖南唐人神、江西温氏、四川德康、贵州富之源
FLAT_ENTERPRISE_ORDER = [
    "吉林中粮", "河南牧原", "山东新希望", "广东温氏",
    "湖南唐人神", "江西温氏", "四川德康", "贵州富之源",
]


def _parse_company_display(company_code: str) -> str:
    """MUYUAN_HN -> 河南牧原（旧版列名：省份+企业名）"""
    parts = company_code.split("_", 1)
    prefix = parts[0]
    suffix = parts[1] if len(parts) > 1 else ""
    name = COMPANY_PREFIX_DISPLAY.get(prefix, prefix)
    prov = PROVINCE_SUFFIX.get(suffix, "")
    return f"{prov}{name}" if prov else name


def _get_national_price_by_date(db: Session, start_date: date, end_date: date) -> Dict[date, float]:
    """全国现货均价（元/公斤）按日期。优先钢联中国，缺日用涌益全国均价/标猪均价填补。"""
    result: Dict[date, float] = {}
    rows = db.execute(text("""
        SELECT trade_date, value FROM fact_price_daily
        WHERE price_type = 'hog_avg_price' AND region_code = 'NATION' AND source = 'GANGLIAN'
          AND trade_date >= :sd AND trade_date <= :ed AND value IS NOT NULL
        ORDER BY trade_date
    """), {"sd": start_date, "ed": end_date}).fetchall()
    for r in rows:
        result[r[0]] = float(r[1])
    for pt, src in [("全国均价", "YONGYI"), ("标猪均价", "YONGYI")]:
        rows = db.execute(text("""
            SELECT trade_date, value FROM fact_price_daily
            WHERE price_type = :pt AND region_code = 'NATION' AND source = :src
              AND trade_date >= :sd AND trade_date <= :ed AND value IS NOT NULL
            ORDER BY trade_date
        """), {"pt": pt, "src": src, "sd": start_date, "ed": end_date}).fetchall()
        for r in rows:
            if r[0] not in result:
                result[r[0]] = float(r[1])
    if result:
        return result
    rows = db.execute(text("""
        SELECT trade_date, value FROM fact_price_daily
        WHERE region_code = 'NATION' AND trade_date >= :sd AND trade_date <= :ed AND value IS NOT NULL
        ORDER BY trade_date
    """), {"sd": start_date, "ed": end_date}).fetchall()
    return {r[0]: float(r[1]) for r in rows} if rows else {}


@router.get("/group-enterprise-price", response_model=GroupPriceTableResponse)
async def get_group_enterprise_price(
    days: int = Query(15, description="显示最近N天的数据"),
    db: Session = Depends(get_db)
):
    """
    获取重点集团企业生猪出栏价格 + 华宝/牧原白条。升贴水 = 企业价格 - 全国均价（元/公斤）。

    数据来源:
    - fact_enterprise_daily (metric_type='output_price')：企业出栏价
    - fact_carcass_market (metric_type in huabao_spread/muyuan_spread)：华宝白条、牧原白条区域列
    - fact_price_daily：全国均价（用于计算升贴水）
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    national_by_date = _get_national_price_by_date(db, start_date, end_date)

    all_data: List[GroupPriceDataPoint] = []
    found_companies: set = set()

    # 1. 查询企业出栏价 — 数据按省份存储（公司码如MUYUAN_HN）
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
        if company_name not in FLAT_ENTERPRISE_ORDER:
            continue
        found_companies.add(company_name)
        price_val = round(float(value), 2)
        nation = national_by_date.get(trade_date)
        prem = round(price_val - nation, 2) if nation is not None else None
        all_data.append(GroupPriceDataPoint(
            date=trade_date.isoformat(),
            company=company_name,
            price=price_val,
            premium_discount=prem,
        ))

    # 2. 查询华宝/牧原白条 — 来自 3.3、白条市场跟踪.xlsx 华宝和牧原白条 sheet（r05 写入 fact_carcass_market）
    white_strip_sql = text("""
        SELECT trade_date, source, region_code, value
        FROM fact_carcass_market
        WHERE metric_type IN ('huabao_spread', 'muyuan_spread')
          AND trade_date >= :start_date
          AND trade_date <= :end_date
          AND value IS NOT NULL
        ORDER BY trade_date DESC
    """)
    ws_rows = db.execute(white_strip_sql, {
        "start_date": start_date,
        "end_date": end_date,
    }).fetchall()
    # 华宝/牧原白条在 fact_carcass_market 中存的是 元/头 的价差(spread)，不是 元/公斤 的绝对价格，不能与全国均价(元/公斤)做差算升贴水
    for row in ws_rows:
        trade_date, source, region_code, value = row
        display_name = WHITE_STRIP_DISPLAY.get((source, region_code))
        if display_name:
            found_companies.add(display_name)
            price_val = round(float(value), 2)
            prem = None  # 白条列为 元/头 价差，不计算升贴水
            all_data.append(GroupPriceDataPoint(
                date=trade_date.isoformat(),
                company=display_name,
                price=price_val,
                premium_discount=prem,
            ))

    # 按日期正序（与源数据一致）
    all_data.sort(key=lambda x: x.date, reverse=False)

    latest_date = all_data[0].date if all_data else None
    # 只展示旧版列：8 个企业 + 华宝白条 + 牧原五区域，不再带其它企业
    enterprise_in_order = [c for c in FLAT_ENTERPRISE_ORDER if c in found_companies]
    white_strip_ordered = [c for c in WHITE_STRIP_COLUMN_ORDER if c in found_companies]
    companies = enterprise_in_order + white_strip_ordered

    # 表格二：同一接口返回重点市场白条到货量&价格（旧版单接口 /group-enterprise-price?days=90）
    white_strip_market = _fetch_white_strip_market(db, start_date, end_date)

    return GroupPriceTableResponse(
        data=all_data,
        companies=companies,
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        latest_date=latest_date,
        white_strip_market=white_strip_market,
    )


# 表格2 只展示「白条市场」sheet 的 8 个重点市场（与 r05 MARKET_COLUMNS、旧版/ingest 配置一致），不含 ML到货/SDY到货/BZY到货
WHITE_STRIP_MARKET_SOURCES = [
    "北京石门", "上海西郊", "成都点杀", "山西太原",
    "杭州五和", "无锡天鹏", "南京众彩", "广西桂林",
]


def _fetch_white_strip_market(
    db: Session, start_date: date, end_date: date
) -> WhiteStripMarketResponse:
    """查询表格二：重点市场白条到货量&价格（与 white-strip-market 接口同逻辑、同数据源）。"""
    in_placeholders = ", ".join([f":src_{i}" for i in range(len(WHITE_STRIP_MARKET_SOURCES))])
    sql = text(f"""
        SELECT trade_date, source, metric_type, value
        FROM fact_carcass_market
        WHERE metric_type IN ('carcass_arrival', 'carcass_price')
          AND trade_date >= :start_date
          AND trade_date <= :end_date
          AND value IS NOT NULL
          AND source IN ({in_placeholders})
        ORDER BY trade_date DESC, source
    """)
    params: dict = {"start_date": start_date, "end_date": end_date}
    for i, name in enumerate(WHITE_STRIP_MARKET_SOURCES):
        params[f"src_{i}"] = name
    rows = db.execute(sql, params).fetchall()

    grouped: Dict[str, Dict[str, object]] = {}
    markets_set: set = set()
    for row in rows:
        trade_date, source, metric_type, value = row
        date_str = trade_date.isoformat()
        market_name = source
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
    all_data.sort(key=lambda x: (x.market, x.date))
    latest_date = max((x.date for x in all_data), default=None)
    return WhiteStripMarketResponse(
        data=all_data,
        markets=sorted(list(markets_set)),
        latest_date=latest_date,
    )


@router.get("/white-strip-market", response_model=WhiteStripMarketResponse)
async def get_white_strip_market(
    days: int = Query(15, description="显示最近N天的数据"),
    db: Session = Depends(get_db)
):
    """
    获取重点市场白条到货量&价格（仅 8 个重点市场，与旧版一致）

    数据来源: fact_carcass_market（同 r05 白条市场 sheet）
    - metric_type='carcass_arrival': 到货量
    - metric_type='carcass_price': 白条均价
    - 仅返回 source 在 WHITE_STRIP_MARKET_SOURCES 的 8 个市场，不包含 ML到货/SDY到货/BZY到货
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # SQLAlchemy text() 的 IN 用占位符拼接（与 production_indicators 一致）
    in_placeholders = ", ".join([f":src_{i}" for i in range(len(WHITE_STRIP_MARKET_SOURCES))])
    sql = text(f"""
        SELECT trade_date, source, metric_type, value
        FROM fact_carcass_market
        WHERE metric_type IN ('carcass_arrival', 'carcass_price')
          AND trade_date >= :start_date
          AND trade_date <= :end_date
          AND value IS NOT NULL
          AND source IN ({in_placeholders})
        ORDER BY trade_date DESC, source
    """)
    params: dict = {
        "start_date": start_date,
        "end_date": end_date,
    }
    for i, name in enumerate(WHITE_STRIP_MARKET_SOURCES):
        params[f"src_{i}"] = name

    rows = db.execute(sql, params).fetchall()

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
