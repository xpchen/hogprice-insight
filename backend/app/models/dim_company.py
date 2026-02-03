from sqlalchemy import Column, BigInteger, String, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class DimCompany(Base):
    __tablename__ = "dim_company"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_name = Column(String(128), nullable=False, unique=True, index=True)
    province = Column(String(32))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
