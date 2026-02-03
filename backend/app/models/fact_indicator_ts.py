from sqlalchemy import Column, BigInteger, String, Date, Numeric, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class FactIndicatorTs(Base):
    __tablename__ = "fact_indicator_ts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    indicator_code = Column(String(64), nullable=False, index=True)  # 指标代码，外键到 dim_indicator.indicator_code
    region_code = Column(String(32), nullable=False, index=True)  # 区域代码，外键到 dim_region.region_code
    freq = Column(String(16), nullable=False)  # D/W (daily/weekly)
    
    # 日频字段
    trade_date = Column(Date, index=True)  # 交易日期（日频使用）
    
    # 周频字段
    week_start = Column(Date)  # 周开始日期（周频使用）
    week_end = Column(Date)  # 周结束日期（周频使用）
    
    value = Column(Numeric(18, 6))  # 指标值
    source_code = Column(String(32))  # 数据源代码
    ingest_batch_id = Column(BigInteger, ForeignKey("import_batch.id", ondelete="SET NULL"))  # 导入批次ID
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # 关联关系
    batch = relationship("ImportBatch", backref="indicator_ts_records")

    __table_args__ = (
        # 日频唯一键
        UniqueConstraint("indicator_code", "region_code", "freq", "trade_date", name="uq_fact_indicator_ts_daily"),
        # 周频唯一键
        UniqueConstraint("indicator_code", "region_code", "freq", "week_end", name="uq_fact_indicator_ts_weekly"),
        # 索引
        Index("idx_fact_indicator_ts_code_date", "indicator_code", "trade_date"),
        Index("idx_fact_indicator_ts_code_week", "indicator_code", "week_end"),
        Index("idx_fact_indicator_ts_region_date", "region_code", "trade_date"),
        Index("idx_fact_indicator_ts_batch", "ingest_batch_id"),
    )
