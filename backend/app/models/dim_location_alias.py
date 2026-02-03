from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class DimLocationAlias(Base):
    """地理位置别名映射表 - 将 Excel 中的别名映射到标准 location_code"""
    __tablename__ = "dim_location_alias"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    alias = Column(String(128), nullable=False)  # 别名（Excel 中的名称）
    source_code = Column(String(32), ForeignKey("dim_source.source_code", ondelete="CASCADE"), nullable=False)
    location_code = Column(String(32), ForeignKey("dim_location.location_code", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 关联关系
    source = relationship("DimSource", backref="location_aliases")
    location = relationship("DimLocation", backref="aliases")

    __table_args__ = (
        UniqueConstraint("alias", "source_code", name="uq_dim_location_alias_alias_source"),
        Index("ix_dim_location_alias_alias_source", "alias", "source_code"),
        Index("ix_dim_location_alias_location", "location_code"),
        {'comment': '地理位置别名映射表'}
    )
