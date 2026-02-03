from sqlalchemy import Column, BigInteger, String, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class DimIndicator(Base):
    __tablename__ = "dim_indicator"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    indicator_code = Column(String(64), nullable=False, unique=True, index=True)  # 唯一标识，如 hog_price_nation
    indicator_name = Column(String(128), nullable=False)  # 展示名称，如 "全国出栏均价"
    freq = Column(String(16), nullable=False)  # D/W (daily/weekly)
    unit = Column(String(32))  # 单位，如 "元/公斤"
    topic = Column(String(32))  # 主题分类：价格/屠宰/均重/价差/冻品/产业链/期货/期权
    source_code = Column(String(32))  # 数据源代码：YONGYI/DCE/LEGACY等
    calc_method = Column(String(16), nullable=False, default="RAW")  # RAW/DERIVED (原始/衍生)
    description = Column(String(512))  # 指标描述
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_dim_indicator_code", "indicator_code"),
        Index("idx_dim_indicator_topic_freq", "topic", "freq"),
        Index("idx_dim_indicator_source", "source_code"),
    )
