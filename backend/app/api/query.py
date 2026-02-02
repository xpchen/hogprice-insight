from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.services.query_service import query_timeseries
from app.services.seasonality_service import query_seasonality
from app.services.topn_service import query_topn

router = APIRouter(prefix=f"{settings.API_V1_STR}/query", tags=["query"])


class TimeSeriesRequest(BaseModel):
    date_range: Optional[Dict[str, date]] = None
    metric_ids: Optional[List[int]] = None
    geo_ids: Optional[List[int]] = None
    company_ids: Optional[List[int]] = None
    warehouse_ids: Optional[List[int]] = None
    tags_filter: Optional[Dict] = None
    group_by: Optional[List[str]] = None
    time_dimension: str = "daily"  # daily/weekly/monthly/quarterly/yearly


@router.post("/timeseries")
async def query_timeseries_data(
    request: TimeSeriesRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """时间序列查询"""
    result = query_timeseries(
        db=db,
        date_range=request.date_range,
        metric_ids=request.metric_ids,
        geo_ids=request.geo_ids,
        company_ids=request.company_ids,
        warehouse_ids=request.warehouse_ids,
        tags_filter=request.tags_filter,
        group_by=request.group_by,
        time_dimension=request.time_dimension
    )
    
    return result


class SeasonalityRequest(BaseModel):
    metric_id: int
    years: List[int]
    geo_ids: Optional[List[int]] = None
    company_ids: Optional[List[int]] = None
    warehouse_ids: Optional[List[int]] = None
    tags_filter: Optional[Dict] = None
    x_mode: str = "week_of_year"  # week_of_year | month_day
    agg: str = "mean"  # mean | last


@router.post("/seasonality")
async def query_seasonality_data(
    request: SeasonalityRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """季节性查询（多年叠线）"""
    filters = {
        "geo_ids": request.geo_ids,
        "company_ids": request.company_ids,
        "warehouse_ids": request.warehouse_ids,
        "tags_filter": request.tags_filter
    }
    
    result = query_seasonality(
        db=db,
        metric_id=request.metric_id,
        years=request.years,
        filters=filters,
        x_mode=request.x_mode,
        agg=request.agg
    )
    
    return result


class TopNRequest(BaseModel):
    metric_id: int
    dimension: str  # geo | company | warehouse
    window_days: int = 7
    rank_by: str = "delta"  # delta | pct_change | seasonal_percentile | streak
    filters: Optional[Dict] = None
    topk: int = 10


@router.post("/topn")
async def query_topn_data(
    request: TopNRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """TopN排名查询"""
    result = query_topn(
        db=db,
        metric_id=request.metric_id,
        dimension=request.dimension,
        window_days=request.window_days,
        rank_by=request.rank_by,
        filters=request.filters,
        topk=request.topk
    )
    
    return result
