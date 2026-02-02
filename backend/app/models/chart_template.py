from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ChartTemplate(Base):
    __tablename__ = "chart_template"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)  # 模板名称
    chart_type = Column(String(32))  # seasonality | timeseries
    spec_json = Column(JSON)  # ChartSpec配置（JSON格式）
    is_public = Column(Boolean, default=True)  # 是否公开
    owner_id = Column(BigInteger, ForeignKey("sys_user.id"))  # 创建者ID
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 关联关系
    owner = relationship("SysUser", backref="chart_templates")
