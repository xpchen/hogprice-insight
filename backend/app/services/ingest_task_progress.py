"""任务进度存储 - 用于 SSE 推送导入进度（单进程内存，多 worker 时需改用 Redis）"""
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

TASK_PROGRESS: Dict[str, dict] = {}


def create_task(total_files: int = 1) -> str:
    """创建任务，返回 task_id"""
    task_id = str(uuid.uuid4())
    TASK_PROGRESS[task_id] = {
        "status": "processing",
        "current_file": 0,
        "total_files": total_files,
        "current_sheet": 0,
        "total_sheets": 0,
        "message": "等待开始",
        "batches": [],
        "completed_at": None,
        "success": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
    }
    return task_id


def update_progress(
    task_id: str,
    *,
    current_file: Optional[int] = None,
    total_files: Optional[int] = None,
    current_sheet: Optional[int] = None,
    total_sheets: Optional[int] = None,
    message: Optional[str] = None,
    batch_id: Optional[int] = None,
) -> None:
    """更新任务进度"""
    if task_id not in TASK_PROGRESS:
        return
    p = TASK_PROGRESS[task_id]
    if current_file is not None:
        p["current_file"] = current_file
    if total_files is not None:
        p["total_files"] = total_files
    if current_sheet is not None:
        p["current_sheet"] = current_sheet
    if total_sheets is not None:
        p["total_sheets"] = total_sheets
    if message is not None:
        p["message"] = message
    if batch_id is not None and batch_id not in p["batches"]:
        p["batches"].append(batch_id)


def get_progress(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务进度"""
    return TASK_PROGRESS.get(task_id)


def mark_task_done(task_id: str, success: bool = True, error: Optional[str] = None) -> None:
    """标记任务完成"""
    if task_id not in TASK_PROGRESS:
        return
    p = TASK_PROGRESS[task_id]
    p["status"] = "done"
    p["success"] = success
    p["error"] = error
    p["completed_at"] = datetime.now().isoformat()
    p["message"] = "导入完成" if success else (error or "导入失败")


def mark_task_failed(task_id: str, error: str) -> None:
    """标记任务失败"""
    mark_task_done(task_id, success=False, error=error)
