from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batch"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64))
    uploader_id = Column(BigInteger, ForeignKey("sys_user.id"))
    status = Column(String(20), nullable=False, default="success")  # success/failed/partial
    total_rows = Column(BigInteger, default=0)
    success_rows = Column(BigInteger, default=0)
    failed_rows = Column(BigInteger, default=0)
    sheet_count = Column(BigInteger, default=0)  # Sheet数量
    metric_count = Column(BigInteger, default=0)  # 指标数量
    duration_ms = Column(BigInteger)  # 耗时（毫秒）
    inserted_count = Column(BigInteger, default=0)  # 插入记录数
    updated_count = Column(BigInteger, default=0)  # 更新记录数
    error_json = Column(JSON)  # MySQL使用JSON类型，包含error_summary
    # 新增字段：用于新导入系统
    source_code = Column(String(32))  # 数据源代码：LH_FTR/LH_OPT/YONGYI_DAILY/YONGYI_WEEKLY/LEGACY
    date_range = Column(JSON)  # 日期范围：{"start": "2026-01-01", "end": "2026-01-31"}
    mapping_json = Column(JSON)  # 映射结果：记录识别与映射，便于追溯和复用
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    uploader = relationship("SysUser", backref="import_batches")
