"""通用查询 API（hogprice_v3 精简版）
原 query_service / seasonality_service / topn_service 已废弃。
保留端点定义避免前端 404。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser

router = APIRouter(prefix=f"{settings.API_V1_STR}/query", tags=["query"])


class TimeSeriesRequest(BaseModel):
    date_range: Optional[Dict[str, date]] = None
    metric_ids: Optional[List[int]] = None
    geo_ids: Optional[List[int]] = None
    company_ids: Optional[List[int]] = None
    warehouse_ids: Optional[List[int]] = None
    tags_filter: Optional[Dict] = None
    group_by: Optional[List[str]] = None
    time_dimension: str = "daily"


class SeasonalityRequest(BaseModel):
    metric_id: int
    years: List[int]
    geo_ids: Optional[List[int]] = None
    company_ids: Optional[List[int]] = None
    warehouse_ids: Optional[List[int]] = None
    tags_filter: Optional[Dict] = None
    x_mode: str = "week_of_year"
    agg: str = "mean"


class TopNRequest(BaseModel):
    metric_id: int
    dimension: str
    window_days: int = 7
    rank_by: str = "delta"
    filters: Optional[Dict] = None
    topk: int = 10


@router.post("/timeseries")
async def query_timeseries_data(
    request: TimeSeriesRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """时间序列查询（已迁移 → /v1/ts）"""
    raise HTTPException(
        status_code=501,
        detail="此接口已迁移，请使用 /api/v1/ts 统一时序接口"
    )


@router.post("/seasonality")
async def query_seasonality_data(
    request: SeasonalityRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """季节性查询（已迁移 → /v1/price-display）"""
    raise HTTPException(
        status_code=501,
        detail="此接口已迁移，请使用 /api/v1/price-display 下的季节性接口"
    )


@router.post("/topn")
async def query_topn_data(
    request: TopNRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """TopN排名查询（暂未迁移）"""
    raise HTTPException(
        status_code=501,
        detail="此接口暂未迁移到 hogprice_v3"
    )
