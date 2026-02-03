from sqlalchemy import Column, BigInteger, String, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class DimRegion(Base):
    __tablename__ = "dim_region"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    region_code = Column(String(32), nullable=False, unique=True, index=True)  # 唯一标识，如 NATION/HEILONGJIANG/NORTHEAST
    region_name = Column(String(64), nullable=False)  # 展示名称，如 "全国"/"黑龙江"/"东北"
    region_level = Column(String(16), nullable=False)  # 0全国/1大区/2省
    parent_region_code = Column(String(32))  # 父级区域代码（可选，用于层级关系）
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_dim_region_code", "region_code"),
        Index("idx_dim_region_level", "region_level"),
        Index("idx_dim_region_parent", "parent_region_code"),
    )
