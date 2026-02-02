from sqlalchemy import Column, BigInteger, String, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from app.core.database import Base


class DimMetric(Base):
    __tablename__ = "dim_metric"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    metric_group = Column(String(32), nullable=False, index=True)  # province/group/warehouse/spread/profit
    metric_name = Column(String(64), nullable=False, index=True)  # 出栏价/出栏均价/区域价差/利润/猪粮比...
    unit = Column(String(32))
    freq = Column(String(16), nullable=False)  # daily/weekly
    raw_header = Column(String(500), nullable=False)  # 原始"指标名称"（改为VARCHAR以支持唯一约束）
    sheet_name = Column(String(64))  # 来源sheet
    source_updated_at = Column(String(64))  # 原表"更新时间"行字符串
    parse_json = Column(JSON)  # 解析结果（pig_type, weight_range, geo, company...）
    # 扩展元数据字段
    value_type = Column(String(16))  # price/spread/profit/ratio
    preferred_agg = Column(String(16), default="mean")  # mean/last/sum
    suggested_axis = Column(String(8), default="auto")  # left/right/auto
    display_precision = Column(String(8))  # 小数位数，如 "2" 表示保留2位小数
    seasonality_supported = Column(String(8), default="true")  # true/false，是否支持季节性分析
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("raw_header", "sheet_name", name="uq_dim_metric_raw_sheet"),
        Index("idx_dim_metric_group_freq", "metric_group", "freq"),
        Index("ix_dim_metric_metric_group", "metric_group"),
        Index("ix_dim_metric_metric_name", "metric_name"),
    )
