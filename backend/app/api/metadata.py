from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.models.dim_metric import DimMetric
from app.models.dim_geo import DimGeo
from app.models.dim_company import DimCompany
from app.models.dim_warehouse import DimWarehouse
from app.services.completeness_service import get_metrics_completeness

router = APIRouter(prefix=f"{settings.API_V1_STR}/dim", tags=["metadata"])


class MetricInfo(BaseModel):
    id: int
    metric_group: str
    metric_name: str
    unit: Optional[str]
    freq: str
    raw_header: str
    
    class Config:
        from_attributes = True


class GeoInfo(BaseModel):
    id: int
    province: str
    region: Optional[str]
    
    class Config:
        from_attributes = True


class CompanyInfo(BaseModel):
    id: int
    company_name: str
    province: Optional[str]
    
    class Config:
        from_attributes = True


class WarehouseInfo(BaseModel):
    id: int
    warehouse_name: str
    province: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/metrics", response_model=List[MetricInfo])
async def get_metrics(
    group: Optional[str] = Query(None, description="指标组筛选（支持多个，用逗号分隔）"),
    freq: Optional[str] = Query(None, description="频率筛选"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取指标列表"""
    query = db.query(DimMetric)
    
    if group:
        # 支持多指标组：如果包含逗号，则使用IN查询
        groups = [g.strip() for g in group.split(',') if g.strip()]
        if len(groups) == 1:
            query = query.filter(DimMetric.metric_group == groups[0])
        elif len(groups) > 1:
            query = query.filter(DimMetric.metric_group.in_(groups))
    
    if freq:
        query = query.filter(DimMetric.freq == freq)
    
    metrics = query.all()
    
    return [
        {
            "id": m.id,
            "metric_group": m.metric_group,
            "metric_name": m.metric_name,
            "unit": m.unit,
            "freq": m.freq,
            "raw_header": m.raw_header
        }
        for m in metrics
    ]


@router.get("/geo", response_model=List[GeoInfo])
async def get_geo(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取地区列表"""
    geos = db.query(DimGeo).all()
    
    return [
        {
            "id": g.id,
            "province": g.province,
            "region": g.region
        }
        for g in geos
    ]


@router.get("/company", response_model=List[CompanyInfo])
async def get_company(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取企业列表"""
    companies = db.query(DimCompany).all()
    
    return [
        {
            "id": c.id,
            "company_name": c.company_name,
            "province": c.province
        }
        for c in companies
    ]


@router.get("/warehouse", response_model=List[WarehouseInfo])
async def get_warehouse(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取交割库列表"""
    warehouses = db.query(DimWarehouse).all()
    
    return [
        {
            "id": w.id,
            "warehouse_name": w.warehouse_name,
            "province": w.province
        }
        for w in warehouses
    ]


@router.get("/metrics/completeness")
async def get_metrics_completeness_api(
    as_of: Optional[str] = Query(None, description="基准日期 YYYY-MM-DD"),
    window: int = Query(7, description="窗口天数"),
    metric_group: Optional[str] = Query(None, description="指标组过滤"),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取指标完成度统计"""
    from datetime import datetime
    
    # 解析日期
    as_of_date = None
    if as_of:
        try:
            as_of_date = datetime.strptime(as_of, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    result = get_metrics_completeness(
        db=db,
        as_of=as_of_date,
        window=window,
        metric_group=metric_group
    )
    
    return result
