from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReportRun(Base):
    __tablename__ = "report_run"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    template_id = Column(BigInteger, ForeignKey("report_template.id"), nullable=False)
    params_json = Column(JSON)  # 报告生成参数（年份/区间/地区等）
    status = Column(String(20), nullable=False, default="pending")  # pending/running/success/failed
    output_path = Column(String(512))  # 输出文件路径
    error_json = Column(JSON)  # 错误信息（如果失败）
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True))  # 完成时间

    # 关联关系
    template = relationship("ReportTemplate", backref="runs")
