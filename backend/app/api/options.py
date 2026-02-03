"""期权查询接口"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.models import FactOptionsDaily

router = APIRouter(prefix=f"{settings.API_V1_STR}/options", tags=["options"])


class OptionsDailyResponse(BaseModel):
    option_code: str
    series: List[dict]


@router.get("/daily", response_model=OptionsDailyResponse)
async def get_options_daily(
    underlying: str = Query(..., description="标的合约，如 lh2603"),
    type: Optional[str] = Query(None, description="期权类型（C/P）"),
    strike: Optional[float] = Query(None, description="行权价"),
    from_date: Optional[date] = Query(None, description="开始日期"),
    to_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """期权日线查询"""
    query = db.query(FactOptionsDaily).filter(
        FactOptionsDaily.underlying_contract == underlying
    )
    
    if type:
        query = query.filter(FactOptionsDaily.option_type == type.upper())
    if strike:
        query = query.filter(FactOptionsDaily.strike == strike)
    if from_date:
        query = query.filter(FactOptionsDaily.trade_date >= from_date)
    if to_date:
        query = query.filter(FactOptionsDaily.trade_date <= to_date)
    
    results = query.order_by(FactOptionsDaily.trade_date).all()
    
    series = []
    for r in results:
        series.append({
            "date": r.trade_date.isoformat(),
            "option_code": r.option_code,
            "close": float(r.close) if r.close else None,
            "settle": float(r.settle) if r.settle else None,
            "delta": float(r.delta) if r.delta else None,
            "iv": float(r.iv) if r.iv else None,
            "volume": int(r.volume) if r.volume else None,
            "open_interest": int(r.open_interest) if r.open_interest else None
        })
    
    return OptionsDailyResponse(
        option_code=results[0].option_code if results else "",
        series=series
    )
