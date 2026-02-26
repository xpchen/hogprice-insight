"""导入服务 - 封装单文件导入逻辑，供 execute 和后台任务复用"""
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import zipfile
import tempfile
import os

from sqlalchemy.orm import Session

from app.models import ImportBatch, IngestError
from app.services.excel_import_service import calculate_file_hash
from app.services.ingest_template_detector import detect_template
from app.services.ingest_task_progress import update_progress


def _run_single_import(
    db: Session,
    file_content: bytes,
    filename: str,
    uploader_id: int,
    template_type: Optional[str] = None,
    task_id: Optional[str] = None,
    current_file: int = 1,
    total_files: int = 1,
) -> Dict[str, Any]:
    """执行单个文件导入，返回 result 字典"""
    if not template_type:
        template_type = detect_template(file_content, filename)

    file_hash = calculate_file_hash(file_content)
    unified_types = ("YONGYI_DAILY", "YONGYI_WEEKLY", "GANGLIAN_DAILY", "ENTERPRISE_DAILY", "WHITE_STRIP_MARKET")

    # unified_import 会创建自己的 batch，此处不预创建，避免主键冲突
    if template_type not in unified_types:
        batch = ImportBatch(
            filename=filename,
            file_hash=file_hash,
            uploader_id=uploader_id,
            status="processing",
            source_code=template_type,
            total_rows=0,
            success_rows=0,
            failed_rows=0,
        )
        db.add(batch)
        db.flush()
    else:
        batch = None

    def _on_progress(sheet_idx: int, total_sheets: int, sheet_name: str) -> None:
        if task_id:
            update_progress(
                task_id,
                current_file=current_file,
                total_files=total_files,
                current_sheet=sheet_idx,
                total_sheets=total_sheets,
                message=f"正在导入 {filename} - Sheet {sheet_name}",
                batch_id=batch.id if batch else None,
            )

    try:
        if template_type == "LH_FTR":
            from app.services.ingestors import import_lh_ftr
            result = import_lh_ftr(db, file_content, batch.id)
        elif template_type == "LH_OPT":
            from app.services.ingestors import import_lh_opt
            result = import_lh_opt(db, file_content, batch.id)
        elif template_type in unified_types:
            from app.services.ingestors.unified_ingestor import unified_import
            dataset_map = {
                "YONGYI_DAILY": ("YONGYI_DAILY", "YONGYI"),
                "YONGYI_WEEKLY": ("YONGYI_WEEKLY", "YONGYI"),
                "GANGLIAN_DAILY": ("GANGLIAN_DAILY", "GANGLIAN"),
                "ENTERPRISE_DAILY": ("ENTERPRISE_DAILY", "ENTERPRISE"),
                "WHITE_STRIP_MARKET": ("WHITE_STRIP_MARKET", "WHITE_STRIP_MARKET"),
            }
            dataset_type, source_code = dataset_map[template_type]
            result = unified_import(
                db=db,
                file_content=file_content,
                filename=filename,
                uploader_id=uploader_id,
                dataset_type=dataset_type,
                source_code=source_code,
                on_sheet_progress=_on_progress,
            )
            # 使用 unified_import 创建的 batch，不要修改主键
            if result.get("success") and result.get("batch_id"):
                batch = db.query(ImportBatch).filter(ImportBatch.id == result["batch_id"]).first()
        elif template_type in ("INDUSTRY_DATA", "PREMIUM_DATA", "ENTERPRISE_MONTHLY"):
            from app.services.ingestors.raw_only_ingestor import import_raw_only
            source_map = {
                "INDUSTRY_DATA": "INDUSTRY_DATA",
                "PREMIUM_DATA": "PREMIUM_DATA",
                "ENTERPRISE_MONTHLY": "ENTERPRISE_MONTHLY",
            }
            result = import_raw_only(
                db=db,
                file_content=file_content,
                filename=filename,
                batch_id=batch.id,
                source_code=source_map[template_type],
                on_progress=lambda msg: update_progress(task_id, message=msg) if task_id else None,
            )
        else:
            raise ValueError(f"不支持的模板类型: {template_type}")

        err_val = result.get("errors")
        error_count_val = len(err_val) if isinstance(err_val, (list, tuple)) else (err_val if isinstance(err_val, int) else 0)
        has_errors = error_count_val > 0
        if batch:
            batch.status = "success" if (result.get("success") and not has_errors) else "partial"
            batch.inserted_count = result.get("inserted", 0)
            batch.updated_count = result.get("updated", 0)
            batch.success_rows = result.get("inserted", 0) + result.get("updated", 0)
            batch.failed_rows = error_count_val
            batch.total_rows = batch.success_rows + batch.failed_rows
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        if batch:
            batch.status = "failed"
            db.commit()
        raise


async def collect_excel_files_from_upload(
    files: list,
    temp_dir: Path,
) -> list[tuple[Path, str]]:
    """
    从上传的文件（可能是多个 Excel 或 zip）收集 Excel 文件路径。
    返回 [(Path, original_filename), ...]
    """
    results = []
    for f in files:
        filename = getattr(f, "filename", "unknown")
        content = await f.read()

        if filename.lower().endswith(".zip"):
            zip_path = temp_dir / filename.replace("/", "_").replace("\\", "_")
            zip_path.write_bytes(content)
            with zipfile.ZipFile(zip_path, "r") as z:
                for name in z.namelist():
                    if name.lower().endswith((".xlsx", ".xls")) and not name.startswith("__"):
                        base_name = name.split("/")[-1].split("\\")[-1]
                        extract_path = temp_dir / f"zip_{len(results)}_{base_name}"
                        with z.open(name) as src:
                            extract_path.write_bytes(src.read())
                        results.append((extract_path, base_name))
            zip_path.unlink(missing_ok=True)
        elif filename.lower().endswith((".xlsx", ".xls")):
            path = temp_dir / f"file_{len(results)}_{filename.replace('/', '_').replace(chr(92), '_')}"
            path.write_bytes(content)
            results.append((path, filename))
    return results
