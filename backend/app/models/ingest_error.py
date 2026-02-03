from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class IngestError(Base):
    __tablename__ = "ingest_error"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(BigInteger, ForeignKey("import_batch.id", ondelete="CASCADE"), nullable=False, index=True)
    sheet_name = Column(String(128))  # Sheet名称
    row_no = Column(Integer)  # 行号（从1开始）
    col_name = Column(String(128))  # 列名
    error_type = Column(String(32))  # 错误类型：missing/duplicate/invalid_value/unit_mismatch/region_mismatch等
    message = Column(String(512))  # 错误消息
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 关联关系
    batch = relationship("ImportBatch", backref="errors")

    __table_args__ = (
        Index("idx_ingest_error_batch", "batch_id"),
        Index("idx_ingest_error_type", "error_type"),
    )
