from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReportTemplate(Base):
    __tablename__ = "report_template"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)  # 报告模板名称
    template_json = Column(JSON)  # 报告模板配置（JSON格式）
    is_public = Column(Boolean, default=False)  # 是否公开
    owner_id = Column(BigInteger, ForeignKey("sys_user.id"))  # 创建者ID
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 关联关系
    owner = relationship("SysUser", backref="report_templates")
