from sqlalchemy import Column, BigInteger, Date, Numeric, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class FactObservation(Base):
    __tablename__ = "fact_observation"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(BigInteger, ForeignKey("import_batch.id", ondelete="SET NULL"))
    metric_id = Column(BigInteger, ForeignKey("dim_metric.id", ondelete="CASCADE"), nullable=False, index=True)
    obs_date = Column(Date, nullable=False, index=True)
    period_type = Column(String(10), nullable=True)  # day/week/month - 周期类型
    period_start = Column(Date, nullable=True)  # 周期开始日期（周度/月度必需）
    period_end = Column(Date, nullable=True)  # 周期结束日期（周度/月度必需）
    value = Column(Numeric(18, 6))  # 价格/价差/比例/利润等统一numeric
    geo_id = Column(BigInteger, ForeignKey("dim_geo.id"), index=True)
    company_id = Column(BigInteger, ForeignKey("dim_company.id"), index=True)
    warehouse_id = Column(BigInteger, ForeignKey("dim_warehouse.id"), index=True)
    tags_json = Column(JSON)  # pig_type/weight_range/ma/window/price_type...
    raw_value = Column(String(64))  # 可选：保留原始字符串（异常时排查）
    dedup_key = Column(String(64), unique=True, index=True)  # 去重键，用于批量upsert
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 关联关系
    batch = relationship("ImportBatch", backref="observations")
    metric = relationship("DimMetric", backref="observations")
    geo = relationship("DimGeo", backref="observations")
    company = relationship("DimCompany", backref="observations")
    warehouse = relationship("DimWarehouse", backref="observations")

    __table_args__ = (
        # 注意：MySQL中NULL值在唯一约束中被视为不同值
        # 实际去重逻辑在导入服务中处理
        Index("idx_fact_metric_date", "metric_id", "obs_date"),
        Index("idx_fact_geo_date", "geo_id", "obs_date"),
        Index("idx_fact_company_date", "company_id", "obs_date"),
        Index("idx_fact_warehouse_date", "warehouse_id", "obs_date"),
        Index("idx_obs_period", "period_type", "period_end"),  # 周期查询索引
    )
