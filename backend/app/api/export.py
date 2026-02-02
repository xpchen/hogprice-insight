from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.services.export_service import export_excel

router = APIRouter(prefix=f"{settings.API_V1_STR}/export", tags=["export"])


class ExportRequest(BaseModel):
    date_range: Optional[Dict[str, date]] = None
    metric_ids: Optional[List[int]] = None
    geo_ids: Optional[List[int]] = None
    company_ids: Optional[List[int]] = None
    warehouse_ids: Optional[List[int]] = None
    tags_filter: Optional[Dict] = None
    group_by: Optional[List[str]] = None
    time_dimension: str = "daily"  # daily/weekly/monthly/quarterly/yearly
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
    """导出Excel文件"""
    excel_file = export_excel(
        db=db,
        date_range=request.date_range,
        metric_ids=request.metric_ids,
        geo_ids=request.geo_ids,
        company_ids=request.company_ids,
        warehouse_ids=request.warehouse_ids,
        tags_filter=request.tags_filter,
        group_by=request.group_by,
        time_dimension=request.time_dimension,
        include_detail=request.include_detail,
        include_summary=request.include_summary,
        include_chart=request.include_chart,
        include_cover=request.include_cover
    )
    
    return Response(
        content=excel_file.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=hogprice_export.xlsx"
        }
    )
