"""企业集团数据导入器"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from openpyxl import load_workbook
from io import BytesIO

from app.services.ingestors.unified_ingestor import unified_import


def import_enterprise_data(
    db: Session,
    file_content: bytes,
    filename: str,
    uploader_id: int,
    source_code: str = "ENTERPRISE"
) -> Dict[str, Any]:
    """
    导入企业集团数据
    
    Args:
        db: 数据库会话
        file_content: Excel文件内容（bytes）
        filename: 文件名
        uploader_id: 上传者ID
        source_code: 数据源代码（默认：ENTERPRISE）
    
    Returns:
        导入结果字典
    """
    return unified_import(
        db=db,
        file_content=file_content,
        filename=filename,
        uploader_id=uploader_id,
        dataset_type="ENTERPRISE_DAILY",
        source_code=source_code
    )
