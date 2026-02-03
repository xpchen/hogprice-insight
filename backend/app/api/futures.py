"""期货查询接口"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.models import FactFuturesDaily

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
