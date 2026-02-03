from sqlalchemy import Column, BigInteger, String, DateTime, Index
from sqlalchemy.sql import func
from app.core.database import Base


class DimLocation(Base):
    """地理位置维度表 - 支持省/市/县三级地理层级"""
    __tablename__ = "dim_location"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    location_code = Column(String(32), nullable=False, unique=True, index=True)  # 地理位置代码
    level = Column(String(16), nullable=False, index=True)  # province/city/county
    parent_code = Column(String(32), nullable=True, index=True)  # 父级代码
    name_cn = Column(String(128), nullable=False)  # 中文名称
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_dim_location_location_code", "location_code"),
        Index("ix_dim_location_level", "level"),
        Index("ix_dim_location_parent", "parent_code"),
        {'comment': '地理位置维度表'}
    )
