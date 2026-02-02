from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class SysRole(Base):
    __tablename__ = "sys_role"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
