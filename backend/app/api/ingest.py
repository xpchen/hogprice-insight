"""新导入系统API"""
import asyncio
import json
import tempfile
from pathlib import Path

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user, get_current_user_from_request
from app.core.config import settings
from app.services.ingest_task_progress import (
    create_task,
    update_progress,
    get_progress,
    mark_task_done,
    mark_task_failed,
)
from app.services.ingest_service import (
    collect_excel_files_from_upload,
    _run_single_import,
)
from app.models.sys_user import SysUser
from app.models import ImportBatch, IngestError, IngestMapping
from app.services.ingest_template_detector import detect_template
from app.services.ingest_preview_service import preview_excel
from app.services.ingestors import import_lh_ftr, import_lh_opt, import_yongyi_daily, import_yongyi_weekly
from app.services.excel_import_service import calculate_file_hash

router = APIRouter(prefix=f"{settings.API_V1_STR}/ingest", tags=["ingest"])


class PreviewResponse(BaseModel):
    template_type: str
    sheets: List[dict]
    date_range: Optional[dict] = None
    sample_rows: List[dict] = []
    field_mappings: dict = {}
    
    class Config:
        # 允许任意类型，避免类型检查问题
        arbitrary_types_allowed = True


class ExecuteRequest(BaseModel):
    batch_id: Optional[int] = None
    template_type: Optional[str] = None


class BatchDetailResponse(BaseModel):
    id: int
    filename: str
    source_code: Optional[str]
    status: str
    total_rows: int
    success_rows: int
    failed_rows: int
    date_range: Optional[dict]
    created_at: str
    errors: List[dict]
    mapping: Optional[dict]


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传文件，返回batch_id"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持Excel文件 (.xlsx, .xls)"
        )
    
    file_content = await file.read()
    file_hash = calculate_file_hash(file_content)
    
    # 识别模板类型
    template_type = detect_template(file_content, file.filename)
    
    # 创建导入批次
    batch = ImportBatch(
        filename=file.filename,
        file_hash=file_hash,
        uploader_id=current_user.id,
        status="pending",
        source_code=template_type,
        total_rows=0,
        success_rows=0,
        failed_rows=0
    )
    db.add(batch)
    db.flush()
    
    return {
        "batch_id": batch.id,
        "template_type": template_type,
        "filename": file.filename
    }


@router.post("/preview", response_model=PreviewResponse)
async def preview_import(
    file: UploadFile = File(...),
    template_type: Optional[str] = None,
    current_user: SysUser = Depends(get_current_user)
):
    """预览导入结果（不实际入库）"""
    file_content = await file.read()
    
    if template_type is None:
        template_type = detect_template(file_content, file.filename)
    
    preview_result = preview_excel(file_content, template_type, file.filename)
    
    # 确保所有字段都存在
    if "error" in preview_result:
        # 如果有错误，返回错误信息
        return PreviewResponse(
            template_type=preview_result.get("template_type", "UNKNOWN"),
            sheets=preview_result.get("sheets", []),
            date_range=preview_result.get("date_range"),
            sample_rows=preview_result.get("sample_rows", []),
            field_mappings=preview_result.get("field_mappings", {})
        )
    
    return PreviewResponse(
        template_type=preview_result.get("template_type", "UNKNOWN"),
        sheets=preview_result.get("sheets", []),
        date_range=preview_result.get("date_range"),
        sample_rows=preview_result.get("sample_rows", []),
        field_mappings=preview_result.get("field_mappings", {})
    )


def _run_quick_chart_regenerate() -> None:
    """后台执行：清空快速图表缓存并按配置重新预计算（导入后调用）"""
    from app.services.quick_chart_service import regenerate_cache_sync
    db = SessionLocal()
    try:
        regenerate_cache_sync(db)
    finally:
        db.close()


def _run_import_task(task_id: str, file_paths: list, user_id: int, temp_dir: Path = None) -> None:
    """后台执行：遍历文件并导入"""
    import shutil
    db = SessionLocal()
    regenerate_called = False
    try:
        for i, (path, filename) in enumerate(file_paths):
            update_progress(
                task_id,
                current_file=i + 1,
                total_files=len(file_paths),
                message=f"正在导入 {filename}",
            )
            try:
                file_content = path.read_bytes()
                _run_single_import(
                    db=db,
                    file_content=file_content,
                    filename=filename,
                    uploader_id=user_id,
                    template_type=None,
                    task_id=task_id,
                    current_file=i + 1,
                    total_files=len(file_paths),
                )
                if i == len(file_paths) - 1:
                    from app.services.quick_chart_service import regenerate_cache_sync
                    regenerate_cache_sync(db)
                    regenerate_called = True
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 300:
                    error_msg = error_msg[:297] + "..."
                mark_task_failed(task_id, f"导入 {filename} 失败: {error_msg}")
                return
            finally:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
        mark_task_done(task_id, success=True)
    except Exception as e:
        mark_task_failed(task_id, str(e)[:300])
    finally:
        db.close()
        if not regenerate_called and file_paths:
            try:
                _run_quick_chart_regenerate()
            except Exception:
                pass
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


@router.post("/execute")
async def execute_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    template_type: Optional[str] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    执行导入（上传文件并立即导入）
    
    注意：大文件导入可能需要较长时间，请耐心等待
    """
    file_content = await file.read()
    
    # 识别模板类型
    if not template_type:
        template_type = detect_template(file_content, file.filename)

    # 创建导入批次
    file_hash = calculate_file_hash(file_content)
    
    batch = ImportBatch(
        filename=file.filename,
        file_hash=file_hash,
        uploader_id=current_user.id,
        status="processing",
        source_code=template_type,  # 保留模板类型用于路由
        total_rows=0,
        success_rows=0,
        failed_rows=0
    )
    db.add(batch)
    db.flush()
    
    try:
        # 根据模板类型调用对应的导入器
        result = None
        try:
            if template_type == "LH_FTR":
                result = import_lh_ftr(db, file_content, batch.id)
            elif template_type == "LH_OPT":
                result = import_lh_opt(db, file_content, batch.id)
            elif template_type == "YONGYI_DAILY":
                from app.services.ingestors.unified_ingestor import unified_import
                result = unified_import(
                    db=db,
                    file_content=file_content,
                    filename=file.filename,
                    uploader_id=current_user.id,
                    dataset_type="YONGYI_DAILY",
                    source_code="YONGYI"
                )
                if result.get("success") and result.get("batch_id"):
                    db.delete(batch)
                    db.flush()
                    batch = db.query(ImportBatch).filter(ImportBatch.id == result["batch_id"]).first()
            elif template_type == "YONGYI_WEEKLY":
                from app.services.ingestors.unified_ingestor import unified_import
                result = unified_import(
                    db=db,
                    file_content=file_content,
                    filename=file.filename,
                    uploader_id=current_user.id,
                    dataset_type="YONGYI_WEEKLY",
                    source_code="YONGYI"
                )
                if result.get("success") and result.get("batch_id"):
                    db.delete(batch)
                    db.flush()
                    batch = db.query(ImportBatch).filter(ImportBatch.id == result["batch_id"]).first()
            elif template_type == "GANGLIAN_DAILY":
                from app.services.ingestors.unified_ingestor import unified_import
                result = unified_import(
                    db=db,
                    file_content=file_content,
                    filename=file.filename,
                    uploader_id=current_user.id,
                    dataset_type="GANGLIAN_DAILY",
                    source_code="GANGLIAN"
                )
                if result.get("success") and result.get("batch_id"):
                    db.delete(batch)
                    db.flush()
                    batch = db.query(ImportBatch).filter(ImportBatch.id == result["batch_id"]).first()
            elif template_type == "INDUSTRY_DATA":
                # 生猪产业数据（协会、NYB、统计局、供需曲线等）：仅导入 raw 层
                from app.services.ingestors.raw_only_ingestor import import_raw_only
                result = import_raw_only(
                    db=db,
                    file_content=file_content,
                    filename=file.filename,
                    batch_id=batch.id,
                    source_code="INDUSTRY_DATA"
                )
            elif template_type == "PREMIUM_DATA":
                # 生猪期货升贴水（盘面结算价）：仅导入 raw 层
                from app.services.ingestors.raw_only_ingestor import import_raw_only
                result = import_raw_only(
                    db=db,
                    file_content=file_content,
                    filename=file.filename,
                    batch_id=batch.id,
                    source_code="PREMIUM_DATA"
                )
            elif template_type == "ENTERPRISE_MONTHLY":
                # 集团企业月度数据：仅导入 raw 层
                from app.services.ingestors.raw_only_ingestor import import_raw_only
                result = import_raw_only(
                    db=db,
                    file_content=file_content,
                    filename=file.filename,
                    batch_id=batch.id,
                    source_code="ENTERPRISE_MONTHLY"
                )
            elif template_type == "ENTERPRISE_DAILY":
                from app.services.ingestors.unified_ingestor import unified_import
                result = unified_import(
                    db=db,
                    file_content=file_content,
                    filename=file.filename,
                    uploader_id=current_user.id,
                    dataset_type="ENTERPRISE_DAILY",
                    source_code="ENTERPRISE"
                )
                if result.get("success") and result.get("batch_id"):
                    db.delete(batch)
                    db.flush()
                    batch = db.query(ImportBatch).filter(ImportBatch.id == result["batch_id"]).first()
            elif template_type == "WHITE_STRIP_MARKET":
                from app.services.ingestors.unified_ingestor import unified_import
                result = unified_import(
                    db=db,
                    file_content=file_content,
                    filename=file.filename,
                    uploader_id=current_user.id,
                    dataset_type="WHITE_STRIP_MARKET",
                    source_code="WHITE_STRIP_MARKET"
                )
                if result.get("success") and result.get("batch_id"):
                    db.delete(batch)
                    db.flush()
                    batch = db.query(ImportBatch).filter(ImportBatch.id == result["batch_id"]).first()
            else:
                raise ValueError(f"不支持的模板类型: {template_type}")
        except Exception as import_error:
            # 捕获导入过程中的错误，提供更详细的错误信息
            error_msg = str(import_error)
            if len(error_msg) > 500:
                error_msg = error_msg[:497] + "..."
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"导入过程出错: {error_msg}"
            ) from import_error
        
        # 更新批次状态（result["errors"]可能是int或list）
        err_val = result.get("errors")
        error_count_val = len(err_val) if isinstance(err_val, (list, tuple)) else (err_val if isinstance(err_val, int) else 0)
        has_errors = error_count_val > 0
        batch.status = "success" if (result.get("success") and not has_errors) else "failed"
        batch.inserted_count = result.get("inserted", 0)
        batch.updated_count = result.get("updated", 0)
        batch.success_rows = result.get("inserted", 0) + result.get("updated", 0)
        batch.failed_rows = error_count_val
        batch.total_rows = batch.success_rows + batch.failed_rows
        
        # 记录错误（先更新批次状态，再记录错误）
        try:
            # 先提交批次状态更新
            db.commit()
            
            # 然后记录错误（使用新会话避免事务冲突）
            if has_errors:
                err_list = result.get("errors") if isinstance(result.get("errors"), (list, tuple)) else []
                from app.core.database import SessionLocal
                error_db = SessionLocal()
                try:
                    for error in err_list:
                        # 截断过长的错误消息（限制为500字符，留一些余量）
                        error_message = error.get("reason", "") or error.get("message", "")
                        if error_message:
                            # 清理错误消息：移除SQL语句等冗余信息
                            if "[SQL:" in error_message:
                                # 提取关键错误信息
                                if "Duplicate entry" in error_message:
                                    import re
                                    match = re.search(r"Duplicate entry '([^']+)'", error_message)
                                    if match:
                                        error_message = f"数据重复: {match.group(1)}"
                                    else:
                                        error_message = "数据重复错误"
                                elif "Data too long" in error_message:
                                    error_message = "数据格式错误：字段值过长"
                                else:
                                    # 提取错误类型
                                    if "IntegrityError" in error_message:
                                        error_message = "数据完整性错误"
                                    elif "DataError" in error_message:
                                        error_message = "数据格式错误"
                                    else:
                                        # 只保留错误消息的前200字符
                                        error_message = error_message[:200]
                            
                            # 确保消息不超过500字符
                            if len(error_message) > 500:
                                error_message = error_message[:497] + "..."
                            
                            error_record = IngestError(
                                batch_id=batch.id,
                                sheet_name=error.get("sheet"),
                                row_no=error.get("row"),
                                col_name=error.get("col"),
                                error_type=error.get("error_type", "unknown"),
                                message=error_message
                            )
                            error_db.add(error_record)
                    
                    error_db.commit()
                finally:
                    error_db.close()
        except Exception as commit_error:
            # 如果记录错误时失败，忽略（避免二次错误）
            # 批次状态已经更新，不影响主流程
            pass
        
        if batch.status == "success":
            background_tasks.add_task(_run_quick_chart_regenerate)
        
        return {
            "success": batch.status == "success",
            "batch_id": batch.id,
            "inserted": result.get("inserted", 0),
            "updated": result.get("updated", 0),
            "errors_count": error_count_val,
            "message": "导入完成" if batch.status == "success" else f"导入完成，但有 {error_count_val} 个错误"
        }
        
    except Exception as e:
        # 先回滚事务
        db.rollback()
        
        # 更新批次状态
        try:
            batch.status = "failed"
            db.commit()
        except:
            db.rollback()
        
        # 提取关键错误信息，避免包含完整的SQL语句
        error_message = str(e)
        if "IntegrityError" in error_message:
            # 提取重复键信息
            if "Duplicate entry" in error_message:
                import re
                match = re.search(r"Duplicate entry '([^']+)'", error_message)
                if match:
                    error_message = f"数据重复: {match.group(1)}"
                else:
                    error_message = "数据重复错误"
            else:
                error_message = "数据完整性错误"
        elif "DataError" in error_message:
            error_message = "数据格式错误"
        else:
            # 截断过长的错误消息
            if len(error_message) > 200:
                error_message = error_message[:197] + "..."
        
        # 确保不超过500字符
        if len(error_message) > 500:
            error_message = error_message[:497] + "..."
        
        # 尝试记录异常到错误表（使用新会话避免事务冲突）
        try:
            from app.core.database import SessionLocal
            error_db = SessionLocal()
            try:
                error_record = IngestError(
                    batch_id=batch.id,
                    error_type="system_error",
                    message=error_message
                )
                error_db.add(error_record)
                error_db.commit()
            finally:
                error_db.close()
        except:
            # 如果记录错误失败，忽略（避免二次错误）
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入失败: {error_message}"
        )


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_import(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Excel 文件或 zip 压缩包，可多选"),
    current_user: SysUser = Depends(get_current_user),
):
    """
    提交导入任务（后台执行）
    支持多个 .xlsx/.xls 或 .zip（解压后导入其中的 Excel）
    立即返回 task_id，通过 SSE /ingest/sse/{task_id} 获取进度
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请至少上传一个文件")

    valid = []
    for f in files:
        fn = getattr(f, "filename", "") or ""
        if fn.lower().endswith((".xlsx", ".xls", ".zip")):
            valid.append(f)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 .xlsx、.xls、.zip 格式",
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="ingest_"))
    try:
        file_list = await collect_excel_files_from_upload(valid, temp_dir)
    except Exception as e:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"解析文件失败: {str(e)[:200]}",
        )

    if not file_list:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未找到可导入的 Excel 文件（zip 内需包含 .xlsx 或 .xls）",
        )

    task_id = create_task(total_files=len(file_list))
    background_tasks.add_task(
        _run_import_task,
        task_id=task_id,
        file_paths=file_list,
        user_id=current_user.id,
        temp_dir=temp_dir,
    )
    return {
        "task_id": task_id,
        "total_files": len(file_list),
        "message": "任务已提交，请通过 SSE 接口获取进度",
    }


@router.get("/sse/{task_id}")
async def sse_progress(
    task_id: str,
    request: Request,
    current_user: SysUser = Depends(get_current_user_from_request),
):
    """SSE 流：推送导入进度"""
    progress = get_progress(task_id)
    if not progress:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在或已过期")

    async def event_generator():
        last_sent = None
        while True:
            p = get_progress(task_id)
            if not p:
                break
            key = (
                p.get("status"),
                p.get("current_file"),
                p.get("message"),
                p.get("current_sheet"),
            )
            if key != last_sent:
                last_sent = key
                yield f"data: {json.dumps(p, ensure_ascii=False)}\n\n"
            if p.get("status") == "done":
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/replay/{batch_id}")
async def replay_batch(
    batch_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    重跑批次（重新解析覆盖）
    
    从raw_file重新读取数据，重新执行解析和导入流程
    """
    from app.models.import_batch import ImportBatch
    from app.models.raw_file import RawFile
    from app.services.ingestors.unified_ingestor import unified_import
    import os
    
    # 查找batch
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    
    # 查找raw_file
    raw_file = db.query(RawFile).filter(RawFile.batch_id == batch_id).first()
    if not raw_file:
        raise HTTPException(status_code=404, detail="原始文件不存在")
    
    # 检查文件是否存在
    if not raw_file.storage_path or not os.path.exists(raw_file.storage_path):
        raise HTTPException(status_code=404, detail="原始文件路径不存在")
    
    # 读取文件内容
    with open(raw_file.storage_path, 'rb') as f:
        file_content = f.read()
    
    # 推断dataset_type
    dataset_type = batch.source_code or "YONGYI_DAILY"
    
    # 调用统一导入工作流
    result = unified_import(
        db=db,
        file_content=file_content,
        filename=raw_file.filename,
        uploader_id=current_user.id,
        dataset_type=dataset_type,
        source_code=batch.source_code
    )
    
    return {
        "success": result.get("success", False),
        "new_batch_id": result.get("batch_id"),
        "inserted": result.get("inserted", 0),
        "updated": result.get("updated", 0),
        "errors": result.get("errors", 0)
    }


@router.get("/batches")
async def get_batches(
    skip: int = 0,
    limit: int = 20,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取批次列表"""
    batches = db.query(ImportBatch).order_by(ImportBatch.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": b.id,
            "filename": b.filename,
            "source_code": b.source_code,
            "status": b.status,
            "total_rows": b.total_rows,
            "success_rows": b.success_rows,
            "failed_rows": b.failed_rows,
            "created_at": b.created_at.isoformat() if b.created_at else None
        }
        for b in batches
    ]


@router.get("/batches/{batch_id}", response_model=BatchDetailResponse)
async def get_batch_detail(
    batch_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取批次详情（含错误列表）"""
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="批次不存在"
        )
    
    # 获取错误列表
    errors = db.query(IngestError).filter(
        IngestError.batch_id == batch_id
    ).all()
    
    errors_list = [
        {
            "sheet": e.sheet_name,
            "row": e.row_no,
            "col": e.col_name,
            "error_type": e.error_type,
            "message": e.message
        }
        for e in errors
    ]
    
    # 获取映射信息
    mapping = db.query(IngestMapping).filter(
        IngestMapping.batch_id == batch_id
    ).first()
    
    mapping_dict = mapping.mapping_json if mapping else None
    
    return BatchDetailResponse(
        id=batch.id,
        filename=batch.filename,
        source_code=batch.source_code,
        status=batch.status,
        total_rows=batch.total_rows,
        success_rows=batch.success_rows,
        failed_rows=batch.failed_rows,
        date_range=batch.date_range,
        created_at=batch.created_at.isoformat() if batch.created_at else "",
        errors=errors_list,
        mapping=mapping_dict
    )
