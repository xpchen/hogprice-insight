"""数据对账API - 查询 hogprice_v3 fact 表"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import date, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser

router = APIRouter(prefix=f"{settings.API_V1_STR}/reconciliation", tags=["reconciliation"])

# 表 → (日期列, 主键维度列) 映射
TABLE_META = {
    "fact_price_daily": ("trade_date", ["region_code", "price_type", "source"]),
    "fact_spread_daily": ("trade_date", ["region_code", "spread_type", "source"]),
    "fact_slaughter_daily": ("trade_date", ["region_code", "source"]),
    "fact_weekly_indicator": ("week_end", ["region_code", "indicator_code", "source"]),
    "fact_monthly_indicator": ("month_date", ["region_code", "indicator_code", "source"]),
    "fact_enterprise_daily": ("trade_date", ["company_code", "region_code", "metric_type"]),
    "fact_futures_daily": ("trade_date", ["contract_code"]),
}


class MissingDatesResponse(BaseModel):
    indicator_code: str
    region_code: Optional[str]
    freq: str
    missing_dates: List[str]
    total_missing: int


class DuplicatesResponse(BaseModel):
    indicator_code: str
    duplicates: List[dict]


class AnomaliesResponse(BaseModel):
    indicator_code: str
    anomalies: List[dict]
    threshold_config: dict


def _guess_table(indicator_code: str, freq: str) -> str:
    """根据 indicator_code 和 freq 猜测所在表"""
    if freq == "W":
        return "fact_weekly_indicator"
    if freq == "M":
        return "fact_monthly_indicator"
    # 日度：按指标名猜
    if "price" in indicator_code or "hog_price" in indicator_code:
        return "fact_price_daily"
    if "spread" in indicator_code:
        return "fact_spread_daily"
    if "slaughter" in indicator_code:
        return "fact_slaughter_daily"
    return "fact_price_daily"


@router.get("/missing", response_model=MissingDatesResponse)
async def get_missing_dates(
    indicator_code: str = Query(..., description="指标代码"),
    region_code: Optional[str] = Query(None, description="区域代码"),
    freq: str = Query("D", description="频率（D/W/M）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取缺失日期列表"""
    table = _guess_table(indicator_code, freq)
    date_col = TABLE_META[table][0]
    region = region_code or "NATION"
    end_d = end_date or date.today()
    start_d = start_date or (end_d - timedelta(days=90))

    # 查询已有日期
    sql = f"SELECT DISTINCT `{date_col}` FROM `{table}` WHERE `{date_col}` BETWEEN :s AND :e"
    params: dict = {"s": start_d, "e": end_d}

    if "indicator_code" in [c for c in TABLE_META[table][1]]:
        sql += " AND indicator_code = :code"
        params["code"] = indicator_code
    if "region_code" in [c for c in TABLE_META[table][1]]:
        sql += " AND region_code = :region"
        params["region"] = region

    rows = db.execute(text(sql), params).fetchall()
    existing = {r[0] for r in rows}

    # 生成预期日期序列
    expected: list[date] = []
    if freq == "D":
        d = start_d
        while d <= end_d:
            if d.weekday() < 5:  # 工作日
                expected.append(d)
            d += timedelta(days=1)
    elif freq == "W":
        d = start_d
        while d <= end_d:
            expected.append(d)
            d += timedelta(weeks=1)
    elif freq == "M":
        from datetime import date as dt
        y, m = start_d.year, start_d.month
        while dt(y, m, 1) <= end_d:
            expected.append(dt(y, m, 1))
            m += 1
            if m > 12:
                m = 1
                y += 1

    missing = sorted(set(expected) - existing)

    return MissingDatesResponse(
        indicator_code=indicator_code,
        region_code=region_code,
        freq=freq,
        missing_dates=[d.isoformat() for d in missing],
        total_missing=len(missing)
    )


@router.get("/duplicates", response_model=DuplicatesResponse)
async def get_duplicates(
    indicator_code: str = Query(..., description="指标代码"),
    region_code: Optional[str] = Query(None, description="区域代码"),
    freq: str = Query("D", description="频率（D/W/M）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取重复记录（由于 UNIQUE KEY，新库不应有重复）"""
    return DuplicatesResponse(
        indicator_code=indicator_code,
        duplicates=[]
    )


@router.get("/anomalies", response_model=AnomaliesResponse)
async def get_anomalies(
    indicator_code: str = Query(..., description="指标代码"),
    region_code: Optional[str] = Query(None, description="区域代码"),
    min_value: Optional[float] = Query(None, description="最小值阈值"),
    max_value: Optional[float] = Query(None, description="最大值阈值"),
    std_multiplier: float = Query(3.0, description="标准差倍数"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取异常值（3σ 法则）"""
    threshold_config = {"std_multiplier": std_multiplier}
    if min_value is not None:
        threshold_config["min"] = min_value
    if max_value is not None:
        threshold_config["max"] = max_value

    # 在周度/月度表中查
    for tbl, dcol in [("fact_weekly_indicator", "week_end"), ("fact_monthly_indicator", "month_date")]:
        stat = db.execute(text(
            f"SELECT AVG(value), STDDEV(value), COUNT(*) FROM `{tbl}` "
            f"WHERE indicator_code = :code AND region_code = :region AND value IS NOT NULL"
        ), {"code": indicator_code, "region": region_code or "NATION"}).fetchone()
        if stat and stat[2] and stat[2] > 10:
            avg_val, std_val = float(stat[0]), float(stat[1]) if stat[1] else 0
            lo = avg_val - std_multiplier * std_val
            hi = avg_val + std_multiplier * std_val
            rows = db.execute(text(
                f"SELECT `{dcol}`, value FROM `{tbl}` "
                f"WHERE indicator_code = :code AND region_code = :region "
                f"AND value IS NOT NULL AND (value < :lo OR value > :hi) "
                f"ORDER BY `{dcol}` DESC LIMIT 50"
            ), {"code": indicator_code, "region": region_code or "NATION", "lo": lo, "hi": hi}).fetchall()
            anomalies = [{"date": r[0].isoformat(), "value": float(r[1]),
                          "avg": round(avg_val, 4), "std": round(std_val, 4)} for r in rows]
            return AnomaliesResponse(
                indicator_code=indicator_code,
                anomalies=anomalies,
                threshold_config=threshold_config
            )

    return AnomaliesResponse(
        indicator_code=indicator_code, anomalies=[], threshold_config=threshold_config
    )
