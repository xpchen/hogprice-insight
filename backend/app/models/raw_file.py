from sqlalchemy import Column, BigInteger, String, Date, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class RawFile(Base):
    """原始文件溯源表 - 记录导入的原始文件信息，用于回放、对比、重跑解析、审计追溯"""
    __tablename__ = "raw_file"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(BigInteger, ForeignKey("import_batch.id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)  # 文件名
    file_hash = Column(String(64), nullable=True, index=True)  # 文件哈希（SHA256）
    report_date = Column(Date, nullable=True)  # 报告日期
    date_range_start = Column(Date, nullable=True)  # 数据日期范围开始
    date_range_end = Column(Date, nullable=True)  # 数据日期范围结束
    parser_version = Column(String(32), nullable=True)  # 解析器版本
    storage_path = Column(String(512), nullable=True)  # 存储路径（如果文件被保存）
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 关联关系
    batch = relationship("ImportBatch", backref="raw_files")

    __table_args__ = (
        Index("ix_raw_file_batch", "batch_id"),
        Index("ix_raw_file_hash", "file_hash"),
        Index("ix_raw_file_date_range", "date_range_start", "date_range_end"),
        {'comment': '原始文件溯源表'}
    )
