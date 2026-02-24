from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class QuickChartCache(Base):
    """快速图表缓存：预计算的图表 API 响应，key=path+query 归一化"""
    __tablename__ = "quick_chart_cache"

    cache_key = Column(String(512), primary_key=True)
    response_body = Column(Text, nullable=False)  # JSON；MySQL 上通过迁移为 MEDIUMTEXT(16MB) 以支持大响应
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
