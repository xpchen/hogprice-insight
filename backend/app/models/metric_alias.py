from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class MetricAlias(Base):
    """指标别名映射表 - 将 Excel 表头映射到稳定的 metric_code"""
    __tablename__ = "metric_alias"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_code = Column(String(32), ForeignKey("dim_source.source_code", ondelete="CASCADE"), nullable=False)
    sheet_name = Column(String(128), nullable=False)  # 来源 sheet 名称
    alias_text = Column(String(500), nullable=False)  # 原始口径字符串（Excel 表头）
    metric_id = Column(BigInteger, ForeignKey("dim_metric.id", ondelete="SET NULL"), nullable=True, index=True)
    tags_patch_json = Column(JSON)  # 这个 alias 固定附带的 tags，如 {"scale": "规模场"}
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # 关联关系
    source = relationship("DimSource", backref="metric_aliases")
    metric = relationship("DimMetric", backref="aliases")

    __table_args__ = (
        UniqueConstraint("source_code", "sheet_name", "alias_text", name="uq_metric_alias_source_sheet_alias"),
        Index("ix_metric_alias_source_sheet_alias", "source_code", "sheet_name", "alias_text"),
        Index("ix_metric_alias_metric", "metric_id"),
        {'comment': '指标别名映射表'}
    )
