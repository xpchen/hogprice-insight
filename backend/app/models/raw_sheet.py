from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class RawSheet(Base):
    """原始Sheet元信息表 - 记录每个sheet的元信息，用于识别和匹配"""
    __tablename__ = "raw_sheet"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_file_id = Column(BigInteger, ForeignKey("raw_file.id", ondelete="CASCADE"), nullable=False, index=True)
    sheet_name = Column(String(128), nullable=False)  # Sheet名称
    row_count = Column(Integer, nullable=True)  # 行数
    col_count = Column(Integer, nullable=True)  # 列数
    header_signature = Column(String(512), nullable=True)  # 表头签名（用于sheet识别和匹配）
    parse_status = Column(String(32), nullable=True, default="pending")  # pending/parsed/failed/skipped
    parser_type = Column(String(64), nullable=True)  # 使用的解析器类型
    error_count = Column(Integer, nullable=True, default=0)  # 错误数量
    observation_count = Column(Integer, nullable=True, default=0)  # 生成的observation数量
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # 关联关系
    raw_file = relationship("RawFile", backref="sheets")
    raw_table = relationship("RawTable", back_populates="sheet", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_raw_sheet_file", "raw_file_id"),
        Index("ix_raw_sheet_name", "sheet_name"),
        Index("ix_raw_sheet_status", "parse_status"),
        {'comment': '原始Sheet元信息表'}
    )
