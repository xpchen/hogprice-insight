"""期货查询接口 — hogprice_v3 版本

Tables:
    fact_futures_daily   日线行情（trade_date, contract_code, OHLC, settle, volume, open_interest）
    fact_futures_basis   升贴水/基差/月间价差/仓单（trade_date, indicator_code, region_code, source, value, unit）
    dim_contract         合约元数据（contract_code, instrument, delivery_month）
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import math

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.models.fact_futures_daily import FactFuturesDaily

router = APIRouter(prefix=f"{settings.API_V1_STR}/futures", tags=["futures"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class FuturesDailyResponse(BaseModel):
    contract_code: str
    series: List[dict]


class ContractCodeItem(BaseModel):
    contract_code: str
    delivery_month: Optional[str] = None
    listed_date: Optional[str] = None
    last_trade_date: Optional[str] = None


class ContractCodeListResponse(BaseModel):
    contracts: List[ContractCodeItem]
    total: int


class MainContractResponse(BaseModel):
    contract_code: Optional[str] = None
    date: Optional[str] = None
    close: Optional[float] = None
    settle: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    message: Optional[str] = None


class ContractAnalysisPoint(BaseModel):
    date: str
    value: Optional[float] = None
    unit: Optional[str] = None


class ContractAnalysisSeries(BaseModel):
    indicator_code: str
    label: str
    region_code: str
    data: List[ContractAnalysisPoint]


class ContractAnalysisResponse(BaseModel):
    series: List[ContractAnalysisSeries]
    update_time: Optional[str] = None


class MainContractAnalysisPoint(BaseModel):
    date: str
    close: Optional[float] = None
    settle: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    premium: Optional[float] = None
    basis: Optional[float] = None


class MainContractAnalysisResponse(BaseModel):
    contract_code: str
    data: List[MainContractAnalysisPoint]
    update_time: Optional[str] = None


class VolatilityDataPoint(BaseModel):
    date: str
    close_price: Optional[float] = None
    settle_price: Optional[float] = None
    open_interest: Optional[int] = None
    volatility: Optional[float] = None
    year: Optional[int] = None


class VolatilitySeries(BaseModel):
    contract_code: str
    contract_month: int
    data: List[VolatilityDataPoint]


class VolatilityResponse(BaseModel):
    series: List[VolatilitySeries]
    update_time: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    return float(v)


def _safe_int(v) -> Optional[int]:
    if v is None:
        return None
    return int(v)


def _iso(d) -> Optional[str]:
    if d is None:
        return None
    if hasattr(d, 'isoformat'):
        return d.isoformat()
    return str(d)


def _indicator_label(code: str) -> str:
    """Turn an indicator_code into a human-readable Chinese label."""
    if code.startswith("premium_"):
        return f"升贴水_{code.replace('premium_', '')}"
    if code.startswith("basis_"):
        return f"基差_{code.replace('basis_', '')}"
    if code.startswith("spread_"):
        parts = code.replace("spread_", "").split("_")
        if len(parts) == 2:
            return f"{parts[0]}-{parts[1]}月间价差"
        return f"月间价差_{code.replace('spread_', '')}"
    if code.startswith("warehouse_"):
        return f"仓单_{code.replace('warehouse_', '')}"
    return code


def calculate_volatility(prices: List[float], current_idx: int, window_days: int = 10) -> Optional[float]:
    """
    Calculate annualized volatility.
    (1) From day window_days+1 onward: return = ln(P[i] / P[i - window_days])
    (2) From day 2*window_days+1 onward: std of past window_days returns
    (3) volatility = std * sqrt(252) * 100
    """
    n = window_days
    if current_idx < 2 * n:
        return None
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


def is_in_seasonal_range(date_obj: date, contract_month: int) -> bool:
    """季节性范围：排除交割月。如 03 合约为 4月~次年2月。"""
    month = date_obj.month
    start_month = (contract_month + 1) % 12
    if start_month == 0:
        start_month = 12
    end_month = contract_month - 1
    if end_month == 0:
        end_month = 12
    if start_month > end_month:
        return month >= start_month or month <= end_month
    return start_month <= month <= end_month


# ---------------------------------------------------------------------------
# 1. /daily  -- single contract daily OHLCV
# ---------------------------------------------------------------------------

@router.get("/daily", response_model=FuturesDailyResponse)
async def get_futures_daily(
    contract: str = Query(..., description="合约代码，如 lh2503"),
    from_date: Optional[date] = Query(None, description="开始日期"),
    to_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """期货日线行情查询"""
    sql = """
        SELECT trade_date, `open` as open_price, `high` as high_price,
               `low` as low_price, `close` as close_price,
               settle as settle_price, volume, open_interest
        FROM fact_futures_daily
        WHERE contract_code = :contract
    """
    params: dict = {"contract": contract}
    if from_date:
        sql += " AND trade_date >= :from_date"
        params["from_date"] = from_date
    if to_date:
        sql += " AND trade_date <= :to_date"
        params["to_date"] = to_date
    sql += " ORDER BY trade_date"

    rows = db.execute(text(sql), params).fetchall()
    series = [
        {
            "date": r.trade_date.isoformat(),
            "open": _safe_float(r.open_price),
            "high": _safe_float(r.high_price),
            "low": _safe_float(r.low_price),
            "close": _safe_float(r.close_price),
            "settle": _safe_float(r.settle_price),
            "volume": _safe_int(r.volume),
            "open_interest": _safe_int(r.open_interest),
        }
        for r in rows
    ]
    return FuturesDailyResponse(contract_code=contract, series=series)


# ---------------------------------------------------------------------------
# 2. /main  -- main contract snapshot (highest open interest)
# ---------------------------------------------------------------------------

@router.get("/main", response_model=MainContractResponse)
async def get_main_contract(
    date: Optional[date] = Query(None, description="日期，默认最新交易日"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """主力合约快照：返回指定日期持仓量最大的合约"""
    if date is None:
        row = db.execute(text(
            "SELECT MAX(trade_date) AS d FROM fact_futures_daily"
        )).fetchone()
        date = row.d if row and row.d else datetime.now().date()

    row = db.execute(text("""
        SELECT contract_code, `close` as close_price, settle as settle_price, volume, open_interest
        FROM fact_futures_daily
        WHERE trade_date = :d
        ORDER BY open_interest DESC
        LIMIT 1
    """), {"d": date}).fetchone()

    if not row:
        return MainContractResponse(message="无数据")

    return MainContractResponse(
        contract_code=row.contract_code,
        date=date.isoformat(),
        close=_safe_float(row.close_price),
        settle=_safe_float(row.settle_price),
        volume=_safe_int(row.volume),
        open_interest=_safe_int(row.open_interest),
    )


# ---------------------------------------------------------------------------
# 3. /contract-code-list  -- contract metadata from dim_contract
# ---------------------------------------------------------------------------

@router.get("/contract-code-list", response_model=ContractCodeListResponse)
async def get_contract_code_list(
    month: Optional[int] = Query(None, description="交割月份筛选，如 1,3,5,7,9,11"),
    active_only: bool = Query(False, description="仅返回未到期合约"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询合约代码列表（dim_contract）"""
    sql = "SELECT contract_code, delivery_month, NULL as listed_date, NULL as last_trade_date FROM dim_contract WHERE 1=1"
    params: dict = {}

    if month is not None:
        sql += " AND MONTH(delivery_month) = :month"
        params["month"] = month

    if active_only:
        sql += " AND delivery_month >= :today"
        params["today"] = datetime.now().date()

    sql += " ORDER BY delivery_month DESC, contract_code"
    rows = db.execute(text(sql), params).fetchall()

    contracts = [
        ContractCodeItem(
            contract_code=r.contract_code,
            delivery_month=_iso(r.delivery_month),
            listed_date=_iso(r.listed_date),
            last_trade_date=_iso(r.last_trade_date),
        )
        for r in rows
    ]
    return ContractCodeListResponse(contracts=contracts, total=len(contracts))


# ---------------------------------------------------------------------------
# 4. /contract-analysis  -- premium / basis / spread / warehouse from fact_futures_basis
# ---------------------------------------------------------------------------

@router.get("/contract-analysis", response_model=ContractAnalysisResponse)
async def get_contract_analysis(
    indicator: Optional[str] = Query(None, description="indicator_code 精确匹配，如 premium_2505"),
    indicator_prefix: Optional[str] = Query(None, description="indicator_code 前缀匹配，如 premium / basis / spread / warehouse"),
    region_code: Optional[str] = Query(None, description="区域代码，默认 NATION"),
    source: Optional[str] = Query(None, description="数据来源，如 GANGLIAN"),
    from_date: Optional[date] = Query(None, description="开始日期"),
    to_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    通用合约分析查询 - 从 fact_futures_basis 读取升贴水、基差、月间价差、仓单等指标。

    indicator_code 命名约定:
      - premium_XXXX       升贴水（XXXX 为合约后缀，如 2503）
      - basis_XXXX         基差
      - spread_XXXX_YYYY   月间价差
      - warehouse_CITYNAME 仓单
    """
    if not indicator and not indicator_prefix:
        raise HTTPException(status_code=400, detail="indicator 或 indicator_prefix 至少提供一个")

    sql = "SELECT trade_date, indicator_code, region_code, value, unit FROM fact_futures_basis WHERE 1=1"
    params: dict = {}

    if indicator:
        sql += " AND indicator_code = :indicator"
        params["indicator"] = indicator
    elif indicator_prefix:
        sql += " AND indicator_code LIKE :prefix"
        params["prefix"] = f"{indicator_prefix}%"

    if region_code:
        sql += " AND region_code = :region_code"
        params["region_code"] = region_code

    if source:
        sql += " AND source = :source"
        params["source"] = source

    if from_date:
        sql += " AND trade_date >= :from_date"
        params["from_date"] = from_date
    if to_date:
        sql += " AND trade_date <= :to_date"
        params["to_date"] = to_date

    sql += " ORDER BY indicator_code, trade_date"
    rows = db.execute(text(sql), params).fetchall()

    # Group by (indicator_code, region_code)
    groups: Dict[tuple, List] = {}
    for r in rows:
        key = (r.indicator_code, r.region_code)
        groups.setdefault(key, []).append(r)

    series_list = []
    for (ind_code, reg_code), items in groups.items():
        data_points = [
            ContractAnalysisPoint(
                date=item.trade_date.isoformat(),
                value=_safe_float(item.value),
                unit=item.unit,
            )
            for item in items
        ]
        series_list.append(ContractAnalysisSeries(
            indicator_code=ind_code,
            label=_indicator_label(ind_code),
            region_code=reg_code,
            data=data_points,
        ))

    return ContractAnalysisResponse(series=series_list)


# ---------------------------------------------------------------------------
# 5. /main-contract-analysis  -- main contract daily + premium/basis
# ---------------------------------------------------------------------------

@router.get("/main-contract-analysis", response_model=MainContractAnalysisResponse)
async def get_main_contract_analysis(
    contract: Optional[str] = Query(None, description="合约代码，如 lh2509。不传则自动取主力合约"),
    from_date: Optional[date] = Query(None, description="开始日期"),
    to_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    主力合约综合分析：日线行情 + 对应升贴水/基差。

    若未指定合约，自动取最新交易日持仓量最大的合约。
    升贴水/基差通过合约后缀（如 2509）与 fact_futures_basis 的 indicator_code 关联。
    """
    # Resolve contract code
    if not contract:
        row = db.execute(text("""
            SELECT contract_code FROM fact_futures_daily
            WHERE trade_date = (SELECT MAX(trade_date) FROM fact_futures_daily)
            ORDER BY open_interest DESC LIMIT 1
        """)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="无期货数据")
        contract = row.contract_code

    # Extract contract suffix for basis lookup (e.g. lh2509 -> 2509)
    contract_suffix = contract.replace("lh", "").replace("LH", "")

    # Fetch daily bars
    daily_sql = """
        SELECT trade_date, `close` as close_price, settle as settle_price, volume, open_interest
        FROM fact_futures_daily
        WHERE contract_code = :contract
    """
    params: dict = {"contract": contract}
    if from_date:
        daily_sql += " AND trade_date >= :from_date"
        params["from_date"] = from_date
    if to_date:
        daily_sql += " AND trade_date <= :to_date"
        params["to_date"] = to_date
    daily_sql += " ORDER BY trade_date"
    daily_rows = db.execute(text(daily_sql), params).fetchall()

    if not daily_rows:
        raise HTTPException(status_code=404, detail=f"合约 {contract} 无日线数据")

    # Fetch premium & basis from fact_futures_basis for same date range
    basis_sql = """
        SELECT trade_date, indicator_code, value
        FROM fact_futures_basis
        WHERE indicator_code IN (:premium_code, :basis_code)
    """
    basis_params: dict = {
        "premium_code": f"premium_{contract_suffix}",
        "basis_code": f"basis_{contract_suffix}",
    }
    if from_date:
        basis_sql += " AND trade_date >= :from_date"
        basis_params["from_date"] = from_date
    if to_date:
        basis_sql += " AND trade_date <= :to_date"
        basis_params["to_date"] = to_date

    basis_rows = db.execute(text(basis_sql), basis_params).fetchall()

    # Build lookup maps: date -> value
    premium_map: Dict[date, float] = {}
    basis_map: Dict[date, float] = {}
    for br in basis_rows:
        if br.indicator_code == f"premium_{contract_suffix}":
            premium_map[br.trade_date] = _safe_float(br.value)
        elif br.indicator_code == f"basis_{contract_suffix}":
            basis_map[br.trade_date] = _safe_float(br.value)

    data = []
    for r in daily_rows:
        data.append(MainContractAnalysisPoint(
            date=r.trade_date.isoformat(),
            close=_safe_float(r.close_price),
            settle=_safe_float(r.settle_price),
            volume=_safe_int(r.volume),
            open_interest=_safe_int(r.open_interest),
            premium=premium_map.get(r.trade_date),
            basis=basis_map.get(r.trade_date),
        ))

    return MainContractAnalysisResponse(contract_code=contract, data=data)


# ---------------------------------------------------------------------------
# 6. /volatility-analysis  -- volatility，数据源与升贴水/月间价差一致
# ---------------------------------------------------------------------------

@router.get("/volatility-analysis", response_model=VolatilityResponse)
async def get_volatility_analysis(
    contract_month: Optional[int] = Query(None, description="合约月份，如 1,3,5,7,9,11。不指定返回全部"),
    window_days: int = Query(10, description="波动率窗口天数，默认10"),
    from_date: Optional[date] = Query(None, description="开始日期"),
    to_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    波动率分析：从 fact_futures_daily 取数（raw SQL 避免表缺 instrument 等列导致 ORM 报错）。
    - contract_code LIKE "%{月}"，按交易日分组取 open_interest 最大主力；价格用 settle（4.1 盘面仅有 settle）。
    - 全序列连续，按 is_in_seasonal_range 排除交割月；波动率 = stdev(ln(P[i]/P[i-n])) * sqrt(252) * 100。
    """
    contract_months = [contract_month] if contract_month else [1, 3, 5, 7, 9, 11]
    all_series: List[VolatilitySeries] = []

    for month in contract_months:
        month_str = f"{month:02d}"
        # 仅查存在的列，不依赖 instrument（部分环境表结构可能与 model 不一致）
        sql = """
            SELECT trade_date, contract_code, `close`, settle, open_interest
            FROM fact_futures_daily
            WHERE contract_code LIKE :pattern
        """
        params: dict = {"pattern": f"%{month_str}"}
        if from_date:
            sql += " AND trade_date >= :from_date"
            params["from_date"] = from_date
        if to_date:
            sql += " AND trade_date <= :to_date"
            params["to_date"] = to_date
        sql += " ORDER BY trade_date"
        rows = db.execute(text(sql), params).fetchall()

        if not rows:
            continue

        # 按交易日分组，取 open_interest 最大的主力；价格用 settle（4.1 盘面 close 为空）
        date_dict: Dict[date, List[Any]] = {}
        for r in rows:
            td = r[0]
            if td not in date_dict:
                date_dict[td] = []
            date_dict[td].append(r)

        sorted_dates = sorted(date_dict.keys())
        prices: List[Optional[float]] = []
        date_list: List[date] = []
        best_per_date: Dict[date, Any] = {}

        for trade_date in sorted_dates:
            best = max(date_dict[trade_date], key=lambda x: (x[4] or 0))
            best_per_date[trade_date] = best
            # 优先 close，无则 settle（4.1 盘面只有 settle）
            raw = best[2] if (best[2] is not None and float(best[2] or 0) > 0) else best[3]
            p = _safe_float(raw)
            prices.append(p)
            date_list.append(trade_date)

        # 全序列连续，按 is_in_seasonal_range 排除交割月后计算年化波动率
        data_points: List[VolatilityDataPoint] = []
        for i in range(len(prices)):
            if prices[i] is None or prices[i] <= 0:
                continue
            if not is_in_seasonal_range(date_list[i], month):
                continue
            vol = calculate_volatility(prices, i, window_days)
            if vol is None:
                continue
            r = best_per_date[date_list[i]]
            d = date_list[i]
            cy = d.year + 1 if d.month > month else d.year
            _price = _safe_float(r[2] if (r[2] is not None and float(r[2] or 0) > 0) else r[3])
            data_points.append(VolatilityDataPoint(
                date=d.isoformat(),
                close_price=_price,
                settle_price=_safe_float(r[3]),
                open_interest=_safe_int(r[4]),
                volatility=round(vol, 2),
                year=cy,
            ))

        if data_points:
            data_points.sort(key=lambda x: x.date)
            all_series.append(VolatilitySeries(
                contract_code=f"lh{month_str}",
                contract_month=month,
                data=data_points,
            ))

    return VolatilityResponse(series=all_series)


# ---------------------------------------------------------------------------
# 6b. /volatility  -- alias for /volatility-analysis (frontend uses this path)
# ---------------------------------------------------------------------------

@router.get("/volatility", response_model=VolatilityResponse)
async def get_volatility(
    contract_month: Optional[int] = Query(None),
    window_days: int = Query(10),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await get_volatility_analysis(
        contract_month=contract_month, window_days=window_days,
        from_date=start_date, to_date=end_date,
        current_user=current_user, db=db,
    )


# ---------------------------------------------------------------------------
# Response models for premium endpoints
# ---------------------------------------------------------------------------

class PremiumDataPointV2(BaseModel):
    date: str
    futures_settle: Optional[float] = None
    spot_price: Optional[float] = None
    premium: Optional[float] = None
    premium_ratio: Optional[float] = None
    year: Optional[int] = None


class PremiumSeriesV2(BaseModel):
    contract_month: int
    contract_name: str
    region: str
    data: List[PremiumDataPointV2]


class PremiumResponseV2(BaseModel):
    series: List[PremiumSeriesV2]
    region_premiums: Dict[str, float] = {}
    update_time: Optional[str] = None


class PremiumDataPoint(BaseModel):
    date: str
    futures_settle: Optional[float] = None
    spot_price: Optional[float] = None
    premium: Optional[float] = None


class PremiumSeries(BaseModel):
    contract_month: int
    contract_name: str
    data: List[PremiumDataPoint]


class PremiumResponse(BaseModel):
    series: List[PremiumSeries]
    update_time: Optional[str] = None


# ---------------------------------------------------------------------------
# 7. /premium/v2  -- premium with seasonal view & region support
# ---------------------------------------------------------------------------

# Region name mapping for spot_avg price lookup
REGION_MAP = {
    "全国均价": "NATION",
    "贵州": "GUIZHOU",
    "四川": "SICHUAN",
    "云南": "YUNNAN",
    "广东": "GUANGDONG",
    "广西": "GUANGXI",
    "江苏": "JIANGSU",
    "内蒙": "NEIMENGGU",
}

# 全国均价区域升贴水（元/吨，交割地市升贴水，来源于大商所交割规则/交割地市出栏价sheet）
# 全国均价为基准0，各省相对全国的升贴水调整值
REGION_PREMIUM_ADJUSTMENTS: Dict[str, float] = {
    "全国均价": 0,
    "贵州": -300,
    "四川": -100,
    "内蒙": -300,
    "广西": -200,
    "云南": -600,
    "江苏": 500,
    "广东": 500,
}


def _get_contract_year(d: date, contract_month: int) -> int:
    """Determine the 'contract year' for a given date and delivery month."""
    if d.month > contract_month:
        return d.year + 1
    return d.year


def _get_national_spot_map(db: Session) -> Dict[date, float]:
    """获取全国现货均价（元/公斤）。与旧版一致：优先钢联分省区猪价中国；缺日用涌益填补以保障整年覆盖。
    优先级：hog_avg_price(GANGLIAN)=钢联中国 > 全国均价(YONGYI)=涌益日度汇总。"""
    result: Dict[date, float] = {}
    # 1. 钢联分省区猪价中国（与旧版 fact_observation 分省区猪价 中国列一致）
    rows = db.execute(text("""
        SELECT trade_date, value FROM fact_price_daily
        WHERE price_type = 'hog_avg_price' AND region_code = 'NATION' AND source = 'GANGLIAN' AND value IS NOT NULL
        ORDER BY trade_date
    """)).fetchall()
    for r in rows:
        result[r[0]] = float(r[1])
    # 2. 涌益全国均价填补钢联缺失的日期（确保 2022 等整年有数据）
    for pt, src in [("全国均价", "YONGYI"), ("标猪均价", "YONGYI")]:
        rows = db.execute(text("""
            SELECT trade_date, value FROM fact_price_daily
            WHERE price_type = :pt AND region_code = 'NATION' AND source = :src AND value IS NOT NULL
            ORDER BY trade_date
        """), {"pt": pt, "src": src}).fetchall()
        for r in rows:
            if r[0] not in result:
                result[r[0]] = float(r[1])
    if result:
        return result
    rows = db.execute(text("""
        SELECT trade_date, value FROM fact_price_daily
        WHERE region_code = 'NATION' AND value IS NOT NULL ORDER BY trade_date
    """)).fetchall()
    return {r[0]: float(r[1]) for r in rows} if rows else {}


@router.get("/premium/v2", response_model=PremiumResponseV2)
async def get_premium_v2(
    contract_month: Optional[int] = Query(None, description="合约月份"),
    region: Optional[str] = Query("全国均价", description="区域名称"),
    view_type: Optional[str] = Query("全部日期", description="季节性 或 全部日期"),
    format_type: Optional[str] = Query("全部格式"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """升贴水 V2 — fact_futures_daily(4.1盘面结算价) + fact_price_daily(优先钢联分省区猪价中国，缺日用涌益填补) 实时计算"""
    contract_months = [contract_month] if contract_month else [1, 3, 5, 7, 9, 11]
    is_seasonal = view_type == "季节性"

    # 现货：优先钢联分省区猪价中国，缺日用涌益全国均价填补（保障整年覆盖）
    spot_map = _get_national_spot_map(db)
    if not spot_map:
        return PremiumResponseV2(series=[], region_premiums=dict(REGION_PREMIUM_ADJUSTMENTS), update_time=None)

    all_series: List[PremiumSeriesV2] = []

    for cm in contract_months:
        month_str = f"{cm:02d}"

        # 期货结算价：fact_futures_daily（4.1 盘面结算价.xlsx），元/吨，按持仓量最大选合约
        settle_sql = """
            SELECT trade_date, contract_code, settle, open_interest
            FROM fact_futures_daily WHERE contract_code LIKE :pat ORDER BY trade_date
        """
        settle_rows = db.execute(text(settle_sql), {"pat": f"%{month_str}"}).fetchall()
        date_best: Dict[date, tuple] = {}
        for r in settle_rows:
            td, cc, settle_val, oi = r[0], r[1], r[2], r[3] or 0
            if settle_val is None:
                continue
            if td not in date_best or oi > date_best[td][1]:
                date_best[td] = (float(settle_val), oi)
        # settle 元/吨 → 元/公斤 用于计算
        settle_map = {td: v[0] / 1000.0 for td, v in date_best.items()}

        all_dates = sorted(set(settle_map.keys()) | set(spot_map.keys()))
        if not all_dates:
            continue

        data_points: List[PremiumDataPointV2] = []
        for d in all_dates:
            settle_kg = settle_map.get(d)
            spot_val = spot_map.get(d)
            # 升贴水 = 期货(元/公斤) - 现货(元/公斤)，实时计算
            prem_val = round(settle_kg - spot_val, 2) if (settle_kg is not None and spot_val is not None) else None
            # 升贴水比率 = 升贴水/现货×100%（行业标准，与参考站一致）
            prem_ratio = round(prem_val / spot_val * 100, 2) if (spot_val and spot_val != 0 and prem_val is not None) else None
            year = _get_contract_year(d, cm)
            data_points.append(PremiumDataPointV2(
                date=d.isoformat(),
                futures_settle=settle_kg,
                spot_price=spot_val,
                premium=prem_val,
                premium_ratio=prem_ratio,
                year=year,
            ))

        all_series.append(PremiumSeriesV2(
            contract_month=cm,
            contract_name=f"{month_str}合约",
            region=region or "全国均价",
            data=data_points,
        ))

    # 全国均价区域升贴水（交割地市升贴水，用于展示各省相对全国的调整值）
    region_premiums: Dict[str, float] = dict(REGION_PREMIUM_ADJUSTMENTS)

    update_time = None
    if all_series and all_series[0].data:
        update_time = all_series[0].data[-1].date

    return PremiumResponseV2(
        series=all_series,
        region_premiums=region_premiums,
        update_time=update_time,
    )


# ---------------------------------------------------------------------------
# 8. /premium  -- simpler version
# ---------------------------------------------------------------------------

@router.get("/premium", response_model=PremiumResponse)
async def get_premium(
    contract_month: Optional[int] = Query(None),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """升贴水查询（简版）"""
    result = await get_premium_v2(
        contract_month=contract_month, region="全国均价", view_type="全部日期",
        current_user=current_user, db=db,
    )
    series = [
        PremiumSeries(
            contract_month=s.contract_month,
            contract_name=s.contract_name,
            data=[PremiumDataPoint(
                date=p.date, futures_settle=p.futures_settle,
                spot_price=p.spot_price, premium=p.premium,
            ) for p in s.data],
        )
        for s in result.series
    ]
    return PremiumResponse(series=series, update_time=result.update_time)


# ---------------------------------------------------------------------------
# 9. /region-premium  -- per-region premium snapshot
# ---------------------------------------------------------------------------

class RegionPremiumData(BaseModel):
    region: str
    contract_month: int
    contract_name: str
    spot_price: Optional[float] = None
    futures_settle: Optional[float] = None
    premium: Optional[float] = None
    date: Optional[str] = None


class RegionPremiumResponse(BaseModel):
    data: List[RegionPremiumData]
    update_time: Optional[str] = None


@router.get("/region-premium", response_model=RegionPremiumResponse)
async def get_region_premium(
    contract_month: int = Query(9),
    regions: Optional[str] = Query(None),
    trade_date: Optional[date] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """区域升贴水数据"""
    return RegionPremiumResponse(data=[], update_time=None)


# ---------------------------------------------------------------------------
# 10. /calendar-spread  -- month-to-month spread
# ---------------------------------------------------------------------------

class CalendarSpreadDataPoint(BaseModel):
    date: str
    near_contract_settle: Optional[float] = None
    far_contract_settle: Optional[float] = None
    spread: Optional[float] = None


class CalendarSpreadSeries(BaseModel):
    spread_name: str
    near_month: int
    far_month: int
    data: List[CalendarSpreadDataPoint]


class CalendarSpreadResponse(BaseModel):
    series: List[CalendarSpreadSeries]
    update_time: Optional[str] = None


# 月间价差对列表（与前端展示一致：03-05、05-07、07-09、09-11、11-01、01-03）
_CALENDAR_SPREAD_PAIRS = ["03_05", "05_07", "07_09", "09_11", "11_01", "01_03"]


def _get_spread_date_range(near_month: int, far_month: int, year: int) -> tuple[date, date]:
    """获取月间价差的时间范围（与旧版 101e563 一致）。
    X-Y 价差，时间从 (Y+1)月1日 至 (X-1)月最后日。如 03-05：6月1日～次年2月末。
    """
    start_month = (far_month % 12) + 1  # Y+1 月
    end_month = near_month - 1 if near_month > 1 else 12  # X-1 月
    cross_year = start_month > end_month
    if cross_year:
        start_year = year - 1
        end_year = year
    else:
        start_year = end_year = year
    start_date = date(start_year, start_month, 1)
    if end_month == 12:
        end_date = date(end_year, 12, 31)
    else:
        end_date = date(end_year, end_month + 1, 1) - timedelta(days=1)
    return start_date, end_date


def _in_spread_range(td: date, near_month: int, far_month: int) -> bool:
    """判断日期是否落在任意年份的价差时间范围内（跨年周期之间自然断开）。"""
    start_month = (far_month % 12) + 1
    end_month = near_month - 1 if near_month > 1 else 12
    cross_year = start_month > end_month
    y, m = td.year, td.month
    if cross_year:
        if m >= start_month:
            return True  # 6-12 月
        if m <= end_month:
            return True  # 1-2 月
        return False  # 3-5 月为 gap
    return start_month <= m <= end_month


def _parse_contract_ym(cc: str) -> int:
    """解析合约代码为 year*12+month，如 LH2303 -> 2023*12+3"""
    if not cc or not cc.upper().startswith("LH") or len(cc) < 6:
        return 999999
    try:
        yy = int(cc[2:4])
        mm = int(cc[4:6])
        return (2000 + yy if yy >= 22 else 1900 + yy) * 12 + mm
    except (ValueError, IndexError):
        return 999999


def _far_contract_for_spread(near_cc: str, near_month: int, far_month: int) -> str:
    """根据近月合约推导对应的远月合约（形成有效价差对）。"""
    ym = _parse_contract_ym(near_cc)
    if ym >= 999999:
        return ""
    y = ym // 12
    if far_month < near_month:  # 跨年如 11-01
        yy = y + 1
    else:
        yy = y
    return f"LH{str(yy)[2:4]}{far_month:02d}"


def _build_one_spread_series(
    db: Session,
    spread_pair: str,
    region_code: str,
) -> tuple[list, Optional[str]]:
    """月间价差：全部用 fact_futures_daily，价差 = 远月 - 近月（元/公斤），与服务器一致。
    按持仓量最大选合约，按 get_spread_date_range 过滤，跨年周期之间自然断开。"""
    parts = spread_pair.split("_")
    if len(parts) != 2:
        return [], None
    near_month = int(parts[0])
    far_month = int(parts[1])
    near_str = f"{near_month:02d}"
    far_str = f"{far_month:02d}"

    # 全部用 fact_futures_daily（03-05 与其它价差对一致）
    near_sql = """
        SELECT trade_date, settle, open_interest FROM fact_futures_daily
        WHERE contract_code LIKE :pat
        ORDER BY trade_date
    """
    far_sql = """
        SELECT trade_date, settle, open_interest FROM fact_futures_daily
        WHERE contract_code LIKE :pat
        ORDER BY trade_date
    """
    near_rows = db.execute(text(near_sql), {"pat": f"%{near_str}"}).fetchall()
    far_rows = db.execute(text(far_sql), {"pat": f"%{far_str}"}).fetchall()

    date_dict_near: dict = {}
    for r in near_rows:
        td = r[0]
        if not _in_spread_range(td, near_month, far_month):
            continue
        if td not in date_dict_near:
            date_dict_near[td] = []
        date_dict_near[td].append({"settle": r[1], "oi": r[2] or 0})

    date_dict_far: dict = {}
    for r in far_rows:
        td = r[0]
        if not _in_spread_range(td, near_month, far_month):
            continue
        if td not in date_dict_far:
            date_dict_far[td] = []
        date_dict_far[td].append({"settle": r[1], "oi": r[2] or 0})

    common_dates = sorted(set(date_dict_near.keys()) & set(date_dict_far.keys()))
    data = []
    for td in common_dates:
        near_best = max(date_dict_near[td], key=lambda x: x["oi"])
        far_best = max(date_dict_far[td], key=lambda x: x["oi"])
        ns = float(near_best["settle"]) if near_best["settle"] else None
        fs = float(far_best["settle"]) if far_best["settle"] else None
        near_kg = ns / 1000.0 if ns is not None else None
        far_kg = fs / 1000.0 if fs is not None else None
        spread = (far_kg - near_kg) if (near_kg is not None and far_kg is not None) else None
        data.append(CalendarSpreadDataPoint(
            date=td.isoformat(),
            near_contract_settle=near_kg,
            far_contract_settle=far_kg,
            spread=spread,
        ))
    return data, data[-1].date if data else None


@router.get("/calendar-spread", response_model=CalendarSpreadResponse)
async def get_calendar_spread(
    spread_pair: Optional[str] = Query(None, description="月间价差对，如 03_05；为空则返回全部"),
    region: Optional[str] = Query("全国均价", description="区域名称"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """月间价差查询：无 spread_pair 时返回全部价差对（03-05、05-07 等），供前端全部日期/季节性图使用"""
    region_code = REGION_MAP.get(region or "全国均价", "NATION")

    if spread_pair:
        spread_pair = spread_pair.replace("-", "_")
        parts = spread_pair.split("_")
        if len(parts) != 2:
            raise HTTPException(400, "spread_pair 格式错误，应为 MM_MM 或 MM-MM 如 03_05")
        pairs_to_fetch = [spread_pair]
    else:
        pairs_to_fetch = _CALENDAR_SPREAD_PAIRS

    series_list: list = []
    latest_update: Optional[str] = None

    for pair in pairs_to_fetch:
        data, update_time = _build_one_spread_series(db, pair, region_code)
        if not data:
            continue
        parts = pair.split("_")
        near_month = int(parts[0])
        far_month = int(parts[1])
        series_list.append(CalendarSpreadSeries(
            spread_name=f"{parts[0]}-{parts[1]}价差",
            near_month=near_month,
            far_month=far_month,
            data=data,
        ))
        if update_time and (latest_update is None or update_time > latest_update):
            latest_update = update_time

    return CalendarSpreadResponse(series=series_list, update_time=latest_update)


# ---------------------------------------------------------------------------
# 11. /warehouse-receipt/*  -- warehouse receipt data
# ---------------------------------------------------------------------------

# 注册仓单图例显示名：原始仓库名 -> 前端图例显示名
WAREHOUSE_LEGEND_DISPLAY = {
    "粮肉食库": "中粮",
    "中粮肉食库": "中粮",
    "德康农牧库": "德康",
}


def _warehouse_display_name(raw_name: str) -> str:
    return WAREHOUSE_LEGEND_DISPLAY.get(raw_name, raw_name)


class WarehouseReceiptChartPoint(BaseModel):
    date: str
    total: Optional[float] = None
    enterprises: Dict[str, Optional[float]] = {}


class WarehouseReceiptChartResponse(BaseModel):
    data: List[WarehouseReceiptChartPoint]
    date_range: Dict[str, Optional[str]] = {}
    top2_enterprises: List[str] = []


@router.get("/warehouse-receipt/chart", response_model=WarehouseReceiptChartResponse)
async def get_warehouse_receipt_chart(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """仓单数据图表"""
    sql = """
        SELECT trade_date, indicator_code, value FROM fact_futures_basis
        WHERE indicator_code LIKE 'warehouse_receipt%%'
        ORDER BY trade_date
    """
    params: dict = {}
    conditions = []
    if start_date:
        conditions.append("trade_date >= :sd")
        params["sd"] = start_date
    if end_date:
        conditions.append("trade_date <= :ed")
        params["ed"] = end_date

    if conditions:
        sql = f"""
            SELECT trade_date, indicator_code, value FROM fact_futures_basis
            WHERE indicator_code LIKE 'warehouse_receipt%%' AND {' AND '.join(conditions)}
            ORDER BY trade_date
        """

    rows = db.execute(text(sql), params).fetchall()

    # Build date -> {indicator: value} map
    date_map: Dict[date, Dict[str, float]] = {}
    enterprise_totals: Dict[str, float] = {}
    for r in rows:
        d = r[0]
        ind = r[1]
        val = float(r[2]) if r[2] is not None else None
        if val is None:
            continue
        if d not in date_map:
            date_map[d] = {}
        date_map[d][ind] = val

        # Track cumulative for top enterprises (by raw name)
        if ind != "warehouse_receipt_total":
            name = ind.replace("warehouse_receipt_", "")
            enterprise_totals[name] = enterprise_totals.get(name, 0) + val

    # Find top 2 enterprises, 返回图例显示名（粮肉食库->中粮, 德康农牧库->德康）
    sorted_ent = sorted(enterprise_totals.items(), key=lambda x: -x[1])
    top2 = [_warehouse_display_name(e[0]) for e in sorted_ent[:2]]

    # Build response：enterprises 使用显示名作为 key，便于图例一致
    data = []
    sorted_dates = sorted(date_map.keys())
    for d in sorted_dates:
        entries = date_map[d]
        total = entries.get("warehouse_receipt_total")
        enterprises = {}
        for k, v in entries.items():
            if k != "warehouse_receipt_total":
                raw_name = k.replace("warehouse_receipt_", "")
                enterprises[_warehouse_display_name(raw_name)] = v
        data.append(WarehouseReceiptChartPoint(
            date=d.isoformat(), total=total, enterprises=enterprises,
        ))

    return WarehouseReceiptChartResponse(
        data=data,
        date_range={
            "start": sorted_dates[0].isoformat() if sorted_dates else None,
            "end": sorted_dates[-1].isoformat() if sorted_dates else None,
        },
        top2_enterprises=top2,
    )


class WarehouseReceiptTableRow(BaseModel):
    enterprise: str
    total: Optional[float] = None
    warehouses: List[Dict[str, Any]] = []


class WarehouseReceiptTableResponse(BaseModel):
    data: List[WarehouseReceiptTableRow]
    enterprises: List[str] = []


@router.get("/warehouse-receipt/table", response_model=WarehouseReceiptTableResponse)
async def get_warehouse_receipt_table(
    enterprises: Optional[str] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """仓单数据表格"""
    # Get latest date's warehouse data
    sql = """
        SELECT indicator_code, value FROM fact_futures_basis
        WHERE indicator_code LIKE 'warehouse_receipt%%'
          AND indicator_code != 'warehouse_receipt_total'
          AND trade_date = (SELECT MAX(trade_date) FROM fact_futures_basis WHERE indicator_code LIKE 'warehouse_receipt%%')
        ORDER BY value DESC
    """
    rows = db.execute(text(sql)).fetchall()

    data = []
    ent_names = []
    for r in rows:
        name = r[0].replace("warehouse_receipt_", "")
        val = float(r[1]) if r[1] is not None else None
        data.append(WarehouseReceiptTableRow(
            enterprise=name, total=val, warehouses=[{"name": name, "quantity": val}],
        ))
        ent_names.append(name)

    return WarehouseReceiptTableResponse(data=data, enterprises=ent_names)


class WarehouseReceiptRawRow(BaseModel):
    date: str
    values: Dict[str, Optional[float]] = {}


class WarehouseReceiptRawResponse(BaseModel):
    enterprise: str
    columns: List[str] = []
    rows: List[WarehouseReceiptRawRow] = []


# 企业 -> 集团汇总仓在 DB 中的名称（用于企业仓单统计「企业」列）
ENTERPRISE_GROUP_WAREHOUSE = {
    "德康": "德康农牧库",
    "中粮": "粮肉食库",
}
# 中粮集团仓可能出现的名称（图例/数据源命名不一）
COFCO_GROUP_NAMES = ("粮肉食库", "中粮肉食库")


def _is_group_warehouse(wh_name: str, enterprise: str) -> bool:
    """是否为该企业的集团汇总仓（如 德康农牧库、粮肉食库/中粮肉食库）"""
    if not wh_name or not enterprise:
        return False
    if enterprise == "中粮":
        return wh_name in COFCO_GROUP_NAMES
    if enterprise in ENTERPRISE_GROUP_WAREHOUSE:
        return wh_name == ENTERPRISE_GROUP_WAREHOUSE[enterprise]
    return wh_name == f"{enterprise}农牧库" or wh_name == f"{enterprise}库"


def _sub_warehouse_short_name(wh_name: str, enterprise: str) -> str:
    """子仓库简称：常熟德康库 -> 常熟，江安德康库 -> 江安（按企业显示名截取地名）"""
    if not wh_name:
        return ""
    # 用企业名分割，取前半作为地名；若企业名在原始名中不存在则用原始名
    for sep in (enterprise, "德康", "中粮"):
        if sep in wh_name:
            before = wh_name.split(sep)[0].strip()
            return before.rstrip("库").strip() or wh_name
    return wh_name


@router.get("/warehouse-receipt/raw", response_model=WarehouseReceiptRawResponse)
async def get_warehouse_receipt_raw(
    enterprise: str = Query(..., description="企业名"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """仓单原始数据 - 按企业名模糊匹配，列顺序：总仓单量、企业名(集团汇总)、子仓库简称(常熟/江安/泸州等)"""
    # 德康：匹配 德康农牧库、常熟德康库 等；中粮：匹配 粮肉食库、中粮肉食库
    like_search = "德康" if enterprise == "德康" else ("粮肉食" if enterprise == "中粮" else (ENTERPRISE_GROUP_WAREHOUSE.get(enterprise) or enterprise))
    like_pattern = f"warehouse_receipt_%{like_search}%"
    sql = "SELECT trade_date, indicator_code, value FROM fact_futures_basis WHERE indicator_code LIKE :pat"
    params: dict = {"pat": like_pattern}
    if start_date:
        sql += " AND trade_date >= :sd"
        params["sd"] = start_date
    if end_date:
        sql += " AND trade_date <= :ed"
        params["ed"] = end_date
    sql += " ORDER BY trade_date, indicator_code"

    rows = db.execute(text(sql), params).fetchall()

    date_map: Dict[str, Dict[str, Optional[float]]] = {}
    warehouse_names: list = []
    for r in rows:
        d = r[0].isoformat()
        wh_name = r[1].replace("warehouse_receipt_", "")
        val = float(r[2]) if r[2] is not None else None
        if wh_name not in warehouse_names:
            warehouse_names.append(wh_name)
        if d not in date_map:
            date_map[d] = {}
        date_map[d][wh_name] = val

    # 区分集团汇总仓与子仓库；子仓库按简称排序。中粮优先取「中粮肉食库」为集团仓
    group_wh = None
    sub_list: List[tuple] = []  # (full_name, short_name)
    for wh in warehouse_names:
        if _is_group_warehouse(wh, enterprise):
            group_wh = wh
        else:
            short = _sub_warehouse_short_name(wh, enterprise)
            if not short:
                short = wh
            sub_list.append((wh, short))
    if enterprise == "中粮" and "中粮肉食库" in warehouse_names:
        group_wh = "中粮肉食库"
    sub_list.sort(key=lambda x: x[1])

    # 列顺序：总仓单量、企业名、子仓库简称...
    columns = ["总仓单量", enterprise] + [s[1] for s in sub_list]

    data = []
    for d in sorted(date_map.keys(), reverse=True):
        row_vals = date_map[d]
        total = sum(v for v in row_vals.values() if v is not None)
        values: Dict[str, Optional[float]] = {"总仓单量": round(total, 2) if total else None}
        values[enterprise] = float(row_vals[group_wh]) if group_wh and row_vals.get(group_wh) is not None else None
        for full_wh, short_wh in sub_list:
            values[short_wh] = row_vals.get(full_wh)
        data.append(WarehouseReceiptRawRow(date=d, values=values))

    return WarehouseReceiptRawResponse(
        enterprise=enterprise, columns=columns, rows=data,
    )
