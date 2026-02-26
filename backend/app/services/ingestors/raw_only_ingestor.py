"""Raw-only 导入器：仅保存到 raw_file/raw_sheet/raw_table，不解析到 fact_observation"""
from typing import Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from openpyxl import load_workbook
from io import BytesIO

from app.services.ingestors.raw_writer import save_raw_file, save_all_sheets_from_workbook


# 不同模板类型的 max_rows 配置（避免超大 sheet 影响性能）
RAW_ONLY_MAX_ROWS = {
    "INDUSTRY_DATA": 200,   # 生猪产业数据
    "PREMIUM_DATA": 1500,   # 升贴水数据（行数较多）
    "ENTERPRISE_MONTHLY": 200,
}


def import_raw_only(
    db: Session,
    file_content: bytes,
    filename: str,
    batch_id: int,
    source_code: str,
    on_progress: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    仅导入到 raw 层（raw_file + raw_sheet + raw_table），不解析到 fact_observation。
    适用于：生猪产业数据、升贴水数据、集团企业月度数据 等。
    
    Args:
        db: 数据库会话
        file_content: 文件内容（bytes）
        filename: 文件名
        batch_id: 导入批次 ID（已由调用方创建）
        source_code: 数据源代码（INDUSTRY_DATA / PREMIUM_DATA / ENTERPRISE_MONTHLY）
    
    Returns:
        { success: True, batch_id, inserted: 0, updated: sheet_count, errors: [] }
    """
    try:
        if on_progress:
            try:
                on_progress(f"正在写入 raw 层: {filename}")
            except Exception:
                pass
        workbook = load_workbook(BytesIO(file_content), data_only=True)
        max_rows = RAW_ONLY_MAX_ROWS.get(source_code, 200)

        raw_file = save_raw_file(
            db=db,
            batch_id=batch_id,
            filename=filename,
            file_content=file_content
        )
        
        raw_sheets = save_all_sheets_from_workbook(
            db=db,
            raw_file_id=raw_file.id,
            workbook_or_path=workbook,
            sparse=False,
            max_rows=max_rows
        )
        
        return {
            "success": True,
            "batch_id": batch_id,
            "inserted": 0,
            "updated": len(raw_sheets),
            "errors": []
        }
    except Exception as e:
        return {
            "success": False,
            "batch_id": batch_id,
            "inserted": 0,
            "updated": 0,
            "errors": [{"sheet": "", "row": 0, "reason": str(e)}]
        }
