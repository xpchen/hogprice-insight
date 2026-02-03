from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class DimOption(Base):
    __tablename__ = "dim_option"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    underlying_contract = Column(String(32), nullable=False, index=True)  # 标的合约，如 lh2603
    option_type = Column(String(1), nullable=False)  # C/P (看涨/看跌)
    strike = Column(Numeric(10, 2), nullable=False)  # 行权价，如 10000
    option_code = Column(String(64), nullable=False, unique=True, index=True)  # 期权代码，如 lh2603-C-10000
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_dim_option_code", "option_code"),
        Index("idx_dim_option_underlying", "underlying_contract"),
        Index("idx_dim_option_type_strike", "option_type", "strike"),
    )
