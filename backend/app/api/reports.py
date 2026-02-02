from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
import os

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.models.report_template import ReportTemplate
from app.models.report_run import ReportRun
from app.services.report_service import generate_report

router = APIRouter(prefix=f"{settings.API_V1_STR}/reports", tags=["reports"])


class ReportTemplateInfo(BaseModel):
    id: int
    name: str
    is_public: bool
    owner_id: Optional[int]
    created_at: str
    
    class Config:
        from_attributes = True


class ReportRunInfo(BaseModel):
    id: int
    template_id: int
    status: str
    output_path: Optional[str]
    created_at: str
    finished_at: Optional[str]
    
    class Config:
        from_attributes = True


class ReportRunRequest(BaseModel):
    template_id: int
    params: Dict  # 报告生成参数


@router.get("/templates", response_model=List[ReportTemplateInfo])
async def get_report_templates(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取报告模板列表"""
    templates = db.query(ReportTemplate).filter(
        (ReportTemplate.is_public == True) | (ReportTemplate.owner_id == current_user.id)
    ).order_by(ReportTemplate.created_at.desc()).all()
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "is_public": t.is_public,
            "owner_id": t.owner_id,
            "created_at": t.created_at.isoformat()
        }
        for t in templates
    ]


@router.post("/run", response_model=ReportRunInfo)
async def create_report_run(
    request: ReportRunRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """生成报告"""
    # 验证模板存在
    template = db.query(ReportTemplate).filter(ReportTemplate.id == request.template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # 权限检查
    if not template.is_public and template.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # 生成报告（异步执行，实际应该使用后台任务）
        output_path = generate_report(
            db=db,
            template_id=request.template_id,
            params=request.params
        )
        
        # 查询运行记录
        report_run = db.query(ReportRun).filter(
            ReportRun.template_id == request.template_id
        ).order_by(ReportRun.created_at.desc()).first()
        
        return {
            "id": report_run.id,
            "template_id": report_run.template_id,
            "status": report_run.status,
            "output_path": report_run.output_path,
            "created_at": report_run.created_at.isoformat(),
            "finished_at": report_run.finished_at.isoformat() if report_run.finished_at else None
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("/run/{run_id}", response_model=ReportRunInfo)
async def get_report_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """查询报告运行状态"""
    report_run = db.query(ReportRun).filter(ReportRun.id == run_id).first()
    
    if not report_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report run not found"
        )
    
    # 权限检查：检查模板权限
    template = db.query(ReportTemplate).filter(ReportTemplate.id == report_run.template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    if not template.is_public and template.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return {
        "id": report_run.id,
        "template_id": report_run.template_id,
        "status": report_run.status,
        "output_path": report_run.output_path,
        "created_at": report_run.created_at.isoformat(),
        "finished_at": report_run.finished_at.isoformat() if report_run.finished_at else None
    }


@router.get("/run/{run_id}/download")
async def download_report(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """下载报告文件"""
    report_run = db.query(ReportRun).filter(ReportRun.id == run_id).first()
    
    if not report_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report run not found"
        )
    
    if report_run.status != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report not ready. Status: {report_run.status}"
        )
    
    if not report_run.output_path or not os.path.exists(report_run.output_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found"
        )
    
    # 权限检查
    template = db.query(ReportTemplate).filter(ReportTemplate.id == report_run.template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    if not template.is_public and template.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return FileResponse(
        report_run.output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"report_{run_id}.xlsx"
    )
