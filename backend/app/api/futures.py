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
# 6. /volatility-analysis  -- volatility from fact_futures_daily settle prices
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
    波动率分析：基于 fact_futures_daily 的结算价计算年化波动率。

    按合约月份分组，每组内按日期排序后计算滚动波动率。
    波动率 = stdev(ln(P[i]/P[i-n])) * sqrt(252) * 100
    """
    contract_months = [contract_month] if contract_month else [1, 3, 5, 7, 9, 11]
    all_series: List[VolatilitySeries] = []

    for month in contract_months:
        month_str = f"{month:02d}"
        # Fetch all contracts for this delivery month
        sql = """
            SELECT d.trade_date, d.contract_code, d.`close` as close_price, d.settle as settle_price, d.open_interest
            FROM fact_futures_daily d
            WHERE d.contract_code LIKE :pattern
        """
        params: dict = {"pattern": f"%{month_str}"}
        if from_date:
            sql += " AND d.trade_date >= :from_date"
            params["from_date"] = from_date
        if to_date:
            sql += " AND d.trade_date <= :to_date"
            params["to_date"] = to_date
        sql += " ORDER BY d.trade_date, d.open_interest DESC"

        rows = db.execute(text(sql), params).fetchall()
        if not rows:
            continue

        # For each trade_date pick the contract with the highest open_interest
        # (rows ordered by open_interest DESC so first per date wins)
        seen_dates: Dict[date, Any] = {}
        for r in rows:
            if r.trade_date not in seen_dates:
                seen_dates[r.trade_date] = r

        sorted_dates = sorted(seen_dates.keys())
        prices = []
        date_list = []
        for d in sorted_dates:
            r = seen_dates[d]
            p = _safe_float(r.settle_price) or _safe_float(r.close_price)
            prices.append(p)
            date_list.append(d)

        # Group by contract year for seasonal analysis
        by_year: Dict[int, List[int]] = {}
        for idx, d in enumerate(date_list):
            if d.month > month:
                cy = d.year + 1
            else:
                cy = d.year
            by_year.setdefault(cy, []).append(idx)

        data_points: List[VolatilityDataPoint] = []
        min_required = 2 * window_days + 1

        for cy in sorted(by_year.keys()):
            indices = by_year[cy]
            if len(indices) < min_required:
                continue
            year_prices = [prices[i] for i in indices]
            year_dates = [date_list[i] for i in indices]

            for local_idx in range(len(year_prices)):
                if year_prices[local_idx] is None or year_prices[local_idx] <= 0:
                    continue
                vol = calculate_volatility(year_prices, local_idx, window_days)
                if vol is None:
                    continue
                r = seen_dates[year_dates[local_idx]]
                data_points.append(VolatilityDataPoint(
                    date=year_dates[local_idx].isoformat(),
                    close_price=_safe_float(r.close_price),
                    settle_price=_safe_float(r.settle_price),
                    open_interest=_safe_int(r.open_interest),
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


def _get_contract_year(d: date, contract_month: int) -> int:
    """Determine the 'contract year' for a given date and delivery month."""
    if d.month > contract_month:
        return d.year + 1
    return d.year


@router.get("/premium/v2", response_model=PremiumResponseV2)
async def get_premium_v2(
    contract_month: Optional[int] = Query(None, description="合约月份"),
    region: Optional[str] = Query("全国均价", description="区域名称"),
    view_type: Optional[str] = Query("全部日期", description="季节性 或 全部日期"),
    format_type: Optional[str] = Query("全部格式"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """升贴水 V2 — 按合约月份返回期货结算价、现货均价、升贴水"""
    contract_months = [contract_month] if contract_month else [1, 3, 5, 7, 9, 11]
    is_seasonal = view_type == "季节性"

    all_series: List[PremiumSeriesV2] = []

    for cm in contract_months:
        month_str = f"{cm:02d}"

        # 1. Get settle prices from fact_futures_basis
        settle_sql = """
            SELECT trade_date, value FROM fact_futures_basis
            WHERE indicator_code = :settle_code AND region_code = 'NATION'
            ORDER BY trade_date
        """
        settle_rows = db.execute(text(settle_sql), {"settle_code": f"settle_{month_str}"}).fetchall()
        settle_map = {r[0]: float(r[1]) for r in settle_rows if r[1] is not None}

        # 2. Get spot avg prices from fact_futures_basis
        spot_sql = """
            SELECT trade_date, value FROM fact_futures_basis
            WHERE indicator_code = :spot_code AND region_code = 'NATION'
            ORDER BY trade_date
        """
        spot_rows = db.execute(text(spot_sql), {"spot_code": f"spot_avg_{month_str}"}).fetchall()
        spot_map = {r[0]: float(r[1]) for r in spot_rows if r[1] is not None}

        # Fallback: if no spot data from fact_futures_basis (e.g. LH01),
        # use national average hog price from fact_price_daily
        if not spot_map and settle_map:
            spot_fallback_sql = """
                SELECT trade_date, value FROM fact_price_daily
                WHERE price_type = 'hog_avg_price' AND region_code = 'NATION'
                  AND value IS NOT NULL
                ORDER BY trade_date
            """
            spot_fb_rows = db.execute(text(spot_fallback_sql)).fetchall()
            spot_map = {r[0]: float(r[1]) for r in spot_fb_rows if r[1] is not None}

        # 3. Get premium from fact_futures_basis
        premium_sql = """
            SELECT trade_date, value FROM fact_futures_basis
            WHERE indicator_code = :prem_code AND region_code = 'NATION'
            ORDER BY trade_date
        """
        premium_rows = db.execute(text(premium_sql), {"prem_code": f"premium_{month_str}"}).fetchall()
        premium_map = {r[0]: float(r[1]) for r in premium_rows if r[1] is not None}

        # Merge all dates
        all_dates = sorted(set(settle_map.keys()) | set(spot_map.keys()) | set(premium_map.keys()))
        if not all_dates:
            continue

        data_points: List[PremiumDataPointV2] = []
        for d in all_dates:
            settle_val = settle_map.get(d)
            spot_val = spot_map.get(d)
            prem_val = premium_map.get(d)

            # If we have settle & spot but no premium from DB, compute it
            if prem_val is None and settle_val is not None and spot_val is not None:
                prem_val = round(settle_val - spot_val, 2)

            # Calculate premium ratio if we have both settle and spot
            prem_ratio = None
            if settle_val and spot_val and spot_val != 0:
                prem_ratio = round((settle_val - spot_val) / spot_val * 100, 2)

            year = _get_contract_year(d, cm)
            data_points.append(PremiumDataPointV2(
                date=d.isoformat(),
                futures_settle=settle_val,
                spot_price=spot_val,
                premium=prem_val,
                premium_ratio=prem_ratio,
                year=year,
            ))

        all_series.append(PremiumSeriesV2(
            contract_month=cm,
            contract_name=f"LH{month_str}",
            region=region or "全国均价",
            data=data_points,
        ))

    # Region premiums (latest values)
    region_premiums: Dict[str, float] = {}
    for rname, rcode in REGION_MAP.items():
        if rname == "全国均价":
            continue
        # Use latest premium data for each region (from fact_futures_basis)
        # For simplicity, compute from spot_price_kg region differences
        pass  # Region premium data not available per region in current schema

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


@router.get("/calendar-spread", response_model=CalendarSpreadResponse)
async def get_calendar_spread(
    spread_pair: Optional[str] = Query(None, description="月间价差对，如 03_05"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """月间价差查询"""
    # Default spread pair
    if not spread_pair:
        spread_pair = "03_05"

    parts = spread_pair.split("_")
    if len(parts) != 2:
        raise HTTPException(400, "spread_pair 格式错误，应为 MM_MM 如 03_05")

    near_month = int(parts[0])
    far_month = int(parts[1])
    indicator_code = f"spread_{spread_pair}"

    sql = """
        SELECT trade_date, value FROM fact_futures_basis
        WHERE indicator_code = :code AND region_code = 'NATION'
        ORDER BY trade_date
    """
    rows = db.execute(text(sql), {"code": indicator_code}).fetchall()

    # Also get settle prices for near and far contracts
    near_sql = """SELECT trade_date, value FROM fact_futures_basis
        WHERE indicator_code = :code ORDER BY trade_date"""
    far_sql = """SELECT trade_date, value FROM fact_futures_basis
        WHERE indicator_code = :code ORDER BY trade_date"""
    near_rows = db.execute(text(near_sql), {"code": f"settle_{parts[0]}"}).fetchall()
    far_rows = db.execute(text(far_sql), {"code": f"settle_{parts[1]}"}).fetchall()

    near_map = {r[0]: float(r[1]) for r in near_rows if r[1] is not None}
    far_map = {r[0]: float(r[1]) for r in far_rows if r[1] is not None}

    data = []
    for r in rows:
        d = r[0]
        data.append(CalendarSpreadDataPoint(
            date=d.isoformat(),
            near_contract_settle=near_map.get(d),
            far_contract_settle=far_map.get(d),
            spread=float(r[1]) if r[1] is not None else None,
        ))

    update_time = data[-1].date if data else None

    return CalendarSpreadResponse(
        series=[CalendarSpreadSeries(
            spread_name=f"LH{parts[0]}-LH{parts[1]}",
            near_month=near_month,
            far_month=far_month,
            data=data,
        )] if data else [],
        update_time=update_time,
    )


# ---------------------------------------------------------------------------
# 11. /warehouse-receipt/*  -- warehouse receipt data
# ---------------------------------------------------------------------------

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

        # Track cumulative for top enterprises
        if ind != "warehouse_receipt_total":
            name = ind.replace("warehouse_receipt_", "")
            enterprise_totals[name] = enterprise_totals.get(name, 0) + val

    # Find top 2 enterprises
    sorted_ent = sorted(enterprise_totals.items(), key=lambda x: -x[1])
    top2 = [e[0] for e in sorted_ent[:2]]

    # Build response
    data = []
    sorted_dates = sorted(date_map.keys())
    for d in sorted_dates:
        entries = date_map[d]
        total = entries.get("warehouse_receipt_total")
        enterprises = {}
        for k, v in entries.items():
            if k != "warehouse_receipt_total":
                enterprises[k.replace("warehouse_receipt_", "")] = v
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


@router.get("/warehouse-receipt/raw", response_model=WarehouseReceiptRawResponse)
async def get_warehouse_receipt_raw(
    enterprise: str = Query(..., description="企业名"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """仓单原始数据 - 按企业名模糊匹配所有子仓库，每个仓库作为一列"""
    # Use LIKE to match all warehouses belonging to the enterprise
    like_pattern = f"warehouse_receipt_%{enterprise}%"
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

    # Collect all warehouse names and pivot into date → {warehouse: value}
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

    # Sort warehouse names for consistent column order
    warehouse_names = sorted(warehouse_names)

    # Build rows with per-warehouse values + 合计 column
    data = []
    for d in sorted(date_map.keys()):
        row_vals = date_map[d]
        total = sum(v for v in row_vals.values() if v is not None)
        values: Dict[str, Optional[float]] = {"合计": round(total, 2) if total else None}
        for wh in warehouse_names:
            values[wh] = row_vals.get(wh)
        data.append(WarehouseReceiptRawRow(date=d, values=values))

    # columns[0] = enterprise name (skipped by frontend's slice(1)), rest = data columns
    columns = [enterprise, "合计"] + warehouse_names
    return WarehouseReceiptRawResponse(
        enterprise=enterprise, columns=columns, rows=data,
    )
