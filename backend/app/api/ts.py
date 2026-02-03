"""统一时序接口"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.services.indicator_query_service import query_indicator_ts, query_indicator_metrics

router = APIRouter(prefix=f"{settings.API_V1_STR}/ts", tags=["timeseries"])


class TimeSeriesResponse(BaseModel):
    indicator_code: str
    indicator_name: str
    unit: Optional[str]
    series: List[dict]
    update_time: Optional[str]
    metrics: Optional[dict] = None


@router.get("", response_model=TimeSeriesResponse)
async def get_timeseries(
    indicator_code: str = Query(..., description="指标代码"),
    region_code: Optional[str] = Query(None, description="区域代码"),
    freq: str = Query("D", description="频率（D/W）"),
    from_date: Optional[date] = Query(None, description="开始日期"),
    to_date: Optional[date] = Query(None, description="结束日期"),
    include_metrics: bool = Query(False, description="是否包含预计算metrics"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """统一时序查询接口"""
    # 查询时序数据
    result = query_indicator_ts(
        db=db,
        indicator_code=indicator_code,
        region_code=region_code,
        freq=freq,
        from_date=from_date,
        to_date=to_date
    )
    
    # 如果需要metrics，查询最新日期的metrics
    metrics = None
    if include_metrics and result.get("series"):
        latest_date_str = result["series"][-1]["date"]
        if latest_date_str:
            latest_date = date.fromisoformat(latest_date_str)
            metrics = query_indicator_metrics(
                db=db,
                indicator_code=indicator_code,
                region_code=region_code,
                date_key=latest_date
            )
    
    result["metrics"] = metrics
    
    return TimeSeriesResponse(**result)
