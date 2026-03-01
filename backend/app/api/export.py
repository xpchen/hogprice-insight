"""导出 API（hogprice_v3 精简版）
原 export_service 已废弃。保留端点定义避免前端 404。
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

router = APIRouter(prefix=f"{settings.API_V1_STR}/export", tags=["export"])


class ExportRequest(BaseModel):
    date_range: Optional[Dict[str, date]] = None
    metric_ids: Optional[List[int]] = None
    geo_ids: Optional[List[int]] = None
    company_ids: Optional[List[int]] = None
    warehouse_ids: Optional[List[int]] = None
    tags_filter: Optional[Dict] = None
    group_by: Optional[List[str]] = None
    time_dimension: str = "daily"
    include_detail: bool = True
    include_summary: bool = True
    include_chart: bool = True
    include_cover: bool = True


@router.post("/excel")
async def export_excel_file(
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """导出Excel文件（暂未迁移到 hogprice_v3）"""
    raise HTTPException(
        status_code=501,
        detail="导出功能暂未迁移到 hogprice_v3，敬请期待"
    )
