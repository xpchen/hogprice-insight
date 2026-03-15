"""数据导入 API（hogprice_v3）
简化版：调用 import_tool 的 reader 进行 Excel 导入。
保留前端 DataIngest.vue 所需的上传、执行、批次查询端点。
"""
import asyncio
import hashlib
import json
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user, get_current_user_from_request
from app.core.config import settings
from app.models.sys_user import SysUser

router = APIRouter(prefix=f"{settings.API_V1_STR}/ingest", tags=["ingest"])

# ---------- 文件名 → reader 映射 ----------
TEMPLATE_MAP = {
    "GANGLIAN_DAILY": "r01_ganglian_daily",
    "INDUSTRY_DATA": "r02_industry_data",
    "ENTERPRISE_DAILY": "r03_enterprise_province",
    "ENTERPRISE_MONTHLY": "r04_enterprise_monthly",
    "WHITE_STRIP_MARKET": "r05_carcass_market",
    "LH_FTR": "r06_futures_premium",
    "FUTURES_BASIS": "r07_futures_basis",
    "YONGYI_DAILY": "r08_yongyi_daily",
    "YONGYI_WEEKLY": "r09_yongyi_weekly",
}

# 文件名关键词 → template_type（按匹配顺序，更具体的放前）
# 集团企业两类 Excel 区分：3.1 分省区 → fact_enterprise_daily(r03)；3.2 月度数据跟踪 → fact_enterprise_monthly(r04)
# - 3.2、集团企业月度数据跟踪.xlsx → 仅含「集团企业月度」，用 ENTERPRISE_MONTHLY
# - 3.1、集团企业出栏跟踪【分省区】.xlsx → 含「集团企业出栏跟踪」，用 ENTERPRISE_DAILY
FILENAME_HINTS = [
    ("钢联", "GANGLIAN_DAILY"),
    ("产业数据", "INDUSTRY_DATA"),
    ("集团企业月度", "ENTERPRISE_MONTHLY"),  # 先匹配 3.2 月度，再匹配 3.1 分省区
    ("集团企业出栏跟踪", "ENTERPRISE_DAILY"),
    ("白条市场", "WHITE_STRIP_MARKET"),
    ("升贴水", "LH_FTR"),
    ("基差", "FUTURES_BASIS"),
    ("月间价差", "FUTURES_BASIS"),
    ("周度", "YONGYI_WEEKLY"),
    ("涌益", "YONGYI_DAILY"),  # 默认日度
]

# 简化的任务进度存储（内存中）
_progress_store: dict = {}


def _detect_template(filename: str) -> str:
    """根据文件名推断模板类型"""
    for keyword, ttype in FILENAME_HINTS:
        if keyword in filename:
            return ttype
    return "UNKNOWN"


def _calculate_hash(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


def _get_reader_class(template_type: str):
    """动态加载对应的 reader 类"""
    import inspect
    reader_module_name = TEMPLATE_MAP.get(template_type)
    if not reader_module_name:
        return None
    mod = __import__(f"import_tool.readers.{reader_module_name}", fromlist=["Reader"])
    # 优先找名为 Reader 的类
    ReaderClass = getattr(mod, "Reader", None)
    if ReaderClass is None:
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if name != "BaseSheetReader" and hasattr(obj, "read_file"):
                ReaderClass = obj
                break
    return ReaderClass


# ---------- 端点 ----------

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: SysUser = Depends(get_current_user),
):
    """上传文件，返回识别的模板类型"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 Excel 文件 (.xlsx, .xls)")

    template_type = _detect_template(file.filename)
    return {
        "template_type": template_type,
        "filename": file.filename,
    }


@router.post("/execute")
async def execute_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    template_type: Optional[str] = Query(None),
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传 Excel 并立即执行导入"""
    import time

    file_content = await file.read()
    if not template_type:
        template_type = _detect_template(file.filename)

    if template_type not in TEMPLATE_MAP:
        raise HTTPException(status_code=400, detail=f"不支持的模板类型: {template_type}，已知类型: {list(TEMPLATE_MAP.keys())}")

    ReaderClass = _get_reader_class(template_type)
    if not ReaderClass:
        raise HTTPException(status_code=500, detail=f"无法加载 Reader: {template_type}")

    file_hash = _calculate_hash(file_content)
    start_ms = time.time()

    # 写临时文件（reader 需要文件路径）
    tmp = Path(tempfile.mktemp(suffix=".xlsx"))
    tmp.write_bytes(file_content)

    try:
        reader = ReaderClass()
        result = reader.read_file(str(tmp))

        total_rows = 0
        for table_name, records in result.items():
            inserted = reader.bulk_insert(table_name, records)
            total_rows += inserted

        duration_ms = int((time.time() - start_ms) * 1000)

        # 记录 import_batch
        db.execute(text("""
            INSERT INTO import_batch (filename, file_hash, mode, status, row_count, duration_ms)
            VALUES (:fn, :fh, 'incremental', 'success', :rc, :dm)
        """), {"fn": file.filename, "fh": file_hash, "rc": total_rows, "dm": duration_ms})
        db.commit()

        return {
            "success": True,
            "inserted": total_rows,
            "updated": 0,
            "errors_count": 0,
            "message": f"导入完成，共 {total_rows} 行，耗时 {duration_ms}ms",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        error_msg = str(e)[:300]
        raise HTTPException(status_code=500, detail=f"导入失败: {error_msg}")
    finally:
        tmp.unlink(missing_ok=True)


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_import(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Excel 文件，可多选"),
    current_user: SysUser = Depends(get_current_user),
):
    """提交多文件后台导入任务"""
    import uuid

    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一个文件")

    valid_files = [(f, f.filename) for f in files if f.filename and f.filename.lower().endswith(('.xlsx', '.xls'))]
    if not valid_files:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx, .xls 格式")

    task_id = str(uuid.uuid4())[:8]
    _progress_store[task_id] = {
        "status": "processing",
        "total_files": len(valid_files),
        "current_file": 0,
        "message": "准备中...",
    }

    # 保存文件到临时目录
    tmp_dir = Path(tempfile.mkdtemp(prefix="ingest_"))
    file_paths = []
    for f, fname in valid_files:
        content = await f.read()
        p = tmp_dir / fname
        p.write_bytes(content)
        file_paths.append((str(p), fname))

    background_tasks.add_task(_run_bg_import, task_id, file_paths, tmp_dir)

    return {
        "task_id": task_id,
        "total_files": len(valid_files),
        "message": "任务已提交",
    }


def _run_bg_import(task_id: str, file_paths: list, tmp_dir: Path):
    """后台执行导入"""
    import time, shutil

    db = SessionLocal()
    try:
        for i, (fpath, fname) in enumerate(file_paths):
            _progress_store[task_id] = {
                "status": "processing",
                "total_files": len(file_paths),
                "current_file": i + 1,
                "message": f"正在导入 {fname}",
            }
            try:
                ttype = _detect_template(fname)
                ReaderClass = _get_reader_class(ttype)
                if ReaderClass is None:
                    continue

                start_ms = time.time()
                reader = ReaderClass()
                result = reader.read_file(fpath)
                total_rows = 0
                for table_name, records in result.items():
                    total_rows += reader.bulk_insert(table_name, records)
                duration_ms = int((time.time() - start_ms) * 1000)

                db.execute(text("""
                    INSERT INTO import_batch (filename, file_hash, mode, status, row_count, duration_ms)
                    VALUES (:fn, '', 'incremental', 'success', :rc, :dm)
                """), {"fn": fname, "rc": total_rows, "dm": duration_ms})
                db.commit()
            except Exception as e:
                _progress_store[task_id] = {
                    "status": "done",
                    "success": False,
                    "message": f"导入 {fname} 失败: {str(e)[:200]}",
                }
                return

        _progress_store[task_id] = {
            "status": "done",
            "success": True,
            "total_files": len(file_paths),
            "current_file": len(file_paths),
            "message": "全部导入完成",
        }
    finally:
        db.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/sse/{task_id}")
async def sse_progress(
    task_id: str,
    request: Request,
    current_user: SysUser = Depends(get_current_user_from_request),
):
    """SSE 流：推送导入进度"""
    if task_id not in _progress_store:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    async def event_generator():
        last_sent = None
        while True:
            p = _progress_store.get(task_id)
            if not p:
                break
            key = json.dumps(p, ensure_ascii=False)
            if key != last_sent:
                last_sent = key
                yield f"data: {key}\n\n"
            if p.get("status") == "done":
                _progress_store.pop(task_id, None)
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/batches")
async def get_batches(
    skip: int = 0,
    limit: int = 20,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取导入批次列表"""
    rows = db.execute(text("""
        SELECT id, filename, file_hash, mode, status, row_count, duration_ms, created_at
        FROM import_batch ORDER BY created_at DESC LIMIT :lim OFFSET :off
    """), {"lim": limit, "off": skip}).fetchall()

    return [
        {
            "id": r[0], "filename": r[1], "source_code": r[3],
            "status": r[4], "total_rows": r[5] or 0,
            "success_rows": r[5] or 0, "failed_rows": 0,
            "created_at": r[7].isoformat() if r[7] else None,
        }
        for r in rows
    ]


@router.get("/batches/{batch_id}")
async def get_batch_detail(
    batch_id: int,
    current_user: SysUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取批次详情"""
    row = db.execute(text("""
        SELECT id, filename, file_hash, mode, status, row_count, duration_ms, error_msg, created_at
        FROM import_batch WHERE id = :bid
    """), {"bid": batch_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="批次不存在")

    return {
        "id": row[0], "filename": row[1], "source_code": row[3],
        "status": row[4], "total_rows": row[5] or 0,
        "success_rows": row[5] or 0, "failed_rows": 0,
        "date_range": None,
        "created_at": row[8].isoformat() if row[8] else "",
        "errors": [],
        "mapping": None,
    }
