from sqlalchemy import Column, BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class RawTable(Base):
    """原始表格快照表 - 存储sheet的完整表格数据（JSON格式），保证任何sheet都可查看"""
    __tablename__ = "raw_table"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_sheet_id = Column(BigInteger, ForeignKey("raw_sheet.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    table_json = Column(JSON, nullable=False)  # 表格数据（二维数组或稀疏格式）
    merged_cells_json = Column(JSON, nullable=True)  # 合并单元格信息（用于前端还原）
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 关联关系
    sheet = relationship("RawSheet", back_populates="raw_table")

    __table_args__ = (
        Index("ix_raw_table_sheet", "raw_sheet_id"),
        {'comment': '原始表格快照表'}
    )
