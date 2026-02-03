from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class DimSource(Base):
    """数据源维度表 - 统一管理 DCE / MYSTEEL / YONGYI 等数据源"""
    __tablename__ = "dim_source"

    source_code = Column(String(32), primary_key=True)  # DCE / MYSTEEL / YONGYI
    source_name = Column(String(128), nullable=False)  # 数据源名称
    update_freq = Column(String(32))  # 更新频率：daily/weekly/monthly
    source_type = Column(String(32))  # 数据源类型：exchange/vendor/legacy
    license_note = Column(String(512))  # 授权说明
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        {'comment': '数据源维度表'}
    )
