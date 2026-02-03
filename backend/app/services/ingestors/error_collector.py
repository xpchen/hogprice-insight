"""ErrorCollector - 统一错误收集和记录"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.ingest_error import IngestError


class ErrorCollector:
    """统一错误收集器"""
    
    def __init__(self, db: Session, batch_id: int):
        """
        初始化错误收集器
        
        Args:
            db: 数据库会话
            batch_id: 导入批次ID
        """
        self.db = db
        self.batch_id = batch_id
        self.errors = []  # 内存中的错误列表（用于批量写入）
    
    def record_error(
        self,
        error_type: str,
        message: str,
        sheet_name: Optional[str] = None,
        row_no: Optional[int] = None,
        col_name: Optional[str] = None,
        immediate: bool = False
    ):
        """
        记录错误
        
        Args:
            error_type: 错误类型（missing_required/invalid_value/date_parse_failed/duplicate_key/out_of_range）
            message: 错误消息
            sheet_name: Sheet名称
            row_no: 行号（从1开始）
            col_name: 列名
            immediate: 是否立即写入数据库（False则批量写入）
        """
        error_data = {
            "batch_id": self.batch_id,
            "sheet_name": sheet_name,
            "row_no": row_no,
            "col_name": col_name,
            "error_type": error_type,
            "message": message[:512] if len(message) > 512 else message  # 限制长度
        }
        
        if immediate:
            # 立即写入数据库
            error_record = IngestError(**error_data)
            self.db.add(error_record)
            self.db.flush()
        else:
            # 添加到内存列表，稍后批量写入
            self.errors.append(error_data)
    
    def record_missing_required(
        self,
        field_name: str,
        sheet_name: Optional[str] = None,
        row_no: Optional[int] = None,
        immediate: bool = False
    ):
        """记录必填字段缺失错误"""
        message = f"必填字段缺失: {field_name}"
        self.record_error(
            error_type="missing_required",
            message=message,
            sheet_name=sheet_name,
            row_no=row_no,
            immediate=immediate
        )
    
    def record_invalid_value(
        self,
        field_name: str,
        value: Any,
        reason: str,
        sheet_name: Optional[str] = None,
        row_no: Optional[int] = None,
        col_name: Optional[str] = None,
        immediate: bool = False
    ):
        """记录无效值错误"""
        value_str = str(value)[:100] if value is not None else "None"
        message = f"无效值: {field_name}={value_str}, 原因: {reason}"
        self.record_error(
            error_type="invalid_value",
            message=message,
            sheet_name=sheet_name,
            row_no=row_no,
            col_name=col_name,
            immediate=immediate
        )
    
    def record_date_parse_failed(
        self,
        date_value: Any,
        sheet_name: Optional[str] = None,
        row_no: Optional[int] = None,
        col_name: Optional[str] = None,
        immediate: bool = False
    ):
        """记录日期解析失败错误"""
        value_str = str(date_value)[:100] if date_value is not None else "None"
        message = f"日期解析失败: {value_str}"
        self.record_error(
            error_type="date_parse_failed",
            message=message,
            sheet_name=sheet_name,
            row_no=row_no,
            col_name=col_name,
            immediate=immediate
        )
    
    def record_duplicate_key(
        self,
        dedup_key: str,
        sheet_name: Optional[str] = None,
        row_no: Optional[int] = None,
        immediate: bool = False
    ):
        """记录重复键错误"""
        message = f"重复键: {dedup_key[:100]}"
        self.record_error(
            error_type="duplicate_key",
            message=message,
            sheet_name=sheet_name,
            row_no=row_no,
            immediate=immediate
        )
    
    def record_out_of_range(
        self,
        field_name: str,
        value: Any,
        valid_range: str,
        sheet_name: Optional[str] = None,
        row_no: Optional[int] = None,
        immediate: bool = False
    ):
        """记录超出范围错误（warning级别，不阻断）"""
        value_str = str(value)[:100] if value is not None else "None"
        message = f"超出范围: {field_name}={value_str}, 有效范围: {valid_range}"
        self.record_error(
            error_type="out_of_range",
            message=message,
            sheet_name=sheet_name,
            row_no=row_no,
            immediate=immediate
        )
    
    def flush(self):
        """批量写入所有错误到数据库"""
        if not self.errors:
            return
        
        # 批量插入
        error_records = [IngestError(**error_data) for error_data in self.errors]
        self.db.bulk_save_objects(error_records)
        self.db.flush()
        
        # 清空内存列表
        self.errors = []
    
    def get_error_count(self) -> int:
        """获取错误总数（包括内存中的）"""
        # 查询数据库中的错误数
        db_count = self.db.query(IngestError).filter(
            IngestError.batch_id == self.batch_id
        ).count()
        
        # 加上内存中的错误数
        return db_count + len(self.errors)
