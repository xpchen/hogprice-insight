"""数据对账API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.services.data_reconciliation_service import (
    check_missing_dates,
    check_duplicates,
    check_anomalies
)

router = APIRouter(prefix=f"{settings.API_V1_STR}/reconciliation", tags=["reconciliation"])


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


@router.get("/missing", response_model=MissingDatesResponse)
async def get_missing_dates(
    indicator_code: str = Query(..., description="指标代码"),
    region_code: Optional[str] = Query(None, description="区域代码"),
    freq: str = Query("D", description="频率（D/W）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取缺失日期列表"""
    missing = check_missing_dates(
        db=db,
        indicator_code=indicator_code,
        region_code=region_code,
        freq=freq,
        start_date=start_date,
        end_date=end_date
    )
    
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
    freq: str = Query("D", description="频率（D/W）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取重复记录"""
    date_range = None
    if start_date and end_date:
        date_range = {"start": start_date, "end": end_date}
    
    duplicates = check_duplicates(
        db=db,
        indicator_code=indicator_code,
        region_code=region_code,
        freq=freq,
        date_range=date_range
    )
    
    return DuplicatesResponse(
        indicator_code=indicator_code,
        duplicates=duplicates
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
    """获取异常值"""
    threshold_config = {}
    if min_value is not None:
        threshold_config["min"] = min_value
    if max_value is not None:
        threshold_config["max"] = max_value
    threshold_config["std_multiplier"] = std_multiplier
    
    anomalies = check_anomalies(
        db=db,
        indicator_code=indicator_code,
        region_code=region_code,
        threshold_config=threshold_config
    )
    
    return AnomaliesResponse(
        indicator_code=indicator_code,
        anomalies=anomalies,
        threshold_config=threshold_config
    )
