from sqlalchemy import Column, BigInteger, String, Date, Numeric, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class FactIndicatorMetrics(Base):
    __tablename__ = "fact_indicator_metrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    indicator_code = Column(String(64), nullable=False, index=True)  # 指标代码
    region_code = Column(String(32), nullable=False, index=True)  # 区域代码
    freq = Column(String(16), nullable=False)  # D/W
    date_key = Column(Date, nullable=False, index=True)  # 日期键（trade_date 或 week_end）
    
    # 基础值
    value = Column(Numeric(18, 6))  # 当前值
    
    # 变化量（预计算）
    chg_1 = Column(Numeric(18, 6))  # 较上期变化（日频：较昨日，周频：较上周）
    chg_5 = Column(Numeric(18, 6))  # 5日/周变化（价差类常用）
    chg_10 = Column(Numeric(18, 6))  # 10日/周变化
    chg_30 = Column(Numeric(18, 6))  # 30日/周变化
    
    # 同比环比
    mom = Column(Numeric(18, 6))  # 环比（Month-over-Month）
    yoy = Column(Numeric(18, 6))  # 同比（Year-over-Year）
    
    update_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("indicator_code", "region_code", "freq", "date_key", name="uq_fact_indicator_metrics"),
        Index("idx_fact_indicator_metrics_code_date", "indicator_code", "date_key"),
        Index("idx_fact_indicator_metrics_region_date", "region_code", "date_key"),
    )
