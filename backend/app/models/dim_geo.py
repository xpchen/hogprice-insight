from sqlalchemy import Column, BigInteger, String, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class DimGeo(Base):
    __tablename__ = "dim_geo"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    province = Column(String(32), nullable=False, unique=True, index=True)
    region = Column(String(32))  # 东北/华北/华东...
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
