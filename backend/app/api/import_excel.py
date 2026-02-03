from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.sys_user import SysUser
from app.models.import_batch import ImportBatch
from app.services.excel_import_service import import_excel

router = APIRouter(prefix=f"{settings.API_V1_STR}/data", tags=["import"])


class ImportResponse(BaseModel):
    batch_id: int
    summary: dict
    errors: List[dict]


class BatchInfo(BaseModel):
    id: int
    filename: str
    status: str
    total_rows: int
    success_rows: int
    failed_rows: int
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/import-excel", response_model=ImportResponse)
async def import_excel_file(
    file: UploadFile = File(...),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传Excel并导入"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel files (.xlsx, .xls) are allowed"
        )
    
    file_content = await file.read()
    
    result = import_excel(
        db=db,
        file_content=file_content,
        filename=file.filename,
        uploader_id=current_user.id
    )
    
    return result


@router.get("/batches", response_model=List[BatchInfo])
async def get_batches(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取导入批次列表"""
    batches = db.query(ImportBatch).order_by(ImportBatch.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": batch.id,
            "filename": batch.filename,
            "status": batch.status,
            "total_rows": batch.total_rows,
            "success_rows": batch.success_rows,
            "failed_rows": batch.failed_rows,
            "created_at": batch.created_at.isoformat()
        }
        for batch in batches
    ]


@router.get("/batches/{batch_id}")
async def get_batch_detail(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取批次详情"""
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found"
        )
    
    return {
        "id": batch.id,
        "filename": batch.filename,
        "file_hash": batch.file_hash,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "success_rows": batch.success_rows,
        "failed_rows": batch.failed_rows,
        "error_json": batch.error_json,
        "created_at": batch.created_at.isoformat()
    }
