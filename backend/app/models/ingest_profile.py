from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class IngestProfile(Base):
    """导入配置模板表 - 存储数据源模板配置（如 YONGYI_DAILY_V1）"""
    __tablename__ = "ingest_profile"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    profile_code = Column(String(64), nullable=False, unique=True, index=True)  # YONGYI_DAILY_V1
    profile_name = Column(String(255), nullable=False)  # 配置名称
    source_code = Column(String(32), ForeignKey("dim_source.source_code", ondelete="CASCADE"), nullable=False, index=True)
    dataset_type = Column(String(64), nullable=False)  # YONGYI_DAILY / YONGYI_WEEKLY / GANGLIAN_DAILY
    file_pattern = Column(String(255), nullable=True)  # 文件匹配模式：*涌益咨询日度数据*.xlsx
    target = Column(String(64), nullable=False, default="fact_observation")  # 目标表：fact_observation
    defaults_json = Column(JSON, nullable=True)  # 默认配置（freq, period_type, geo_strategy 等）
    dispatch_rules_json = Column(JSON, nullable=True)  # 分发规则（周度文件用）
    version = Column(String(32), nullable=False, default="1.0")  # 配置版本
    is_active = Column(String(1), nullable=False, default="Y")  # Y/N
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # 关联关系
    source = relationship("DimSource", backref="ingest_profiles")
    sheets = relationship("IngestProfileSheet", back_populates="profile", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ingest_profile_profile_code", "profile_code"),
        Index("ix_ingest_profile_source", "source_code"),
        {'comment': '导入配置模板表'}
    )


class IngestProfileSheet(Base):
    """导入配置 Sheet 表 - 每个 sheet 的解析规则"""
    __tablename__ = "ingest_profile_sheet"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    profile_id = Column(BigInteger, ForeignKey("ingest_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    sheet_name = Column(String(128), nullable=False)  # sheet 名称
    parser = Column(String(64), nullable=True)  # 解析器类型：NARROW_DATE_ROWS / WIDE_DATE_GROUPED_SUBCOLS 等
    action = Column(String(32), nullable=True)  # SKIP_META / RAW_TABLE_STORE_ONLY
    config_json = Column(JSON, nullable=False)  # sheet 完整配置（header, date_col, metrics, geo 等）
    priority = Column(BigInteger, nullable=True, default=100)  # 优先级（用于 dispatch_rules）
    note = Column(String(512), nullable=True)  # 备注
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # 关联关系
    profile = relationship("IngestProfile", back_populates="sheets")

    __table_args__ = (
        Index("ix_ingest_profile_sheet_profile", "profile_id"),
        Index("ix_ingest_profile_sheet_sheet_name", "sheet_name"),
        {'comment': '导入配置 Sheet 表'}
    )
