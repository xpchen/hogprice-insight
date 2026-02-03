from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class DimContract(Base):
    __tablename__ = "dim_contract"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    instrument = Column(String(16), nullable=False)  # 品种代码，如 LH
    contract_code = Column(String(32), nullable=False, unique=True, index=True)  # 合约代码，如 lh2603
    maturity_year = Column(Integer, nullable=False)  # 到期年份，如 2026
    maturity_month = Column(Integer, nullable=False)  # 到期月份，如 3
    is_main = Column(Boolean, default=False)  # 是否主力合约
    main_rank = Column(Integer)  # 主力排名（可选）
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_dim_contract_code", "contract_code"),
        Index("idx_dim_contract_instrument", "instrument"),
        Index("idx_dim_contract_maturity", "maturity_year", "maturity_month"),
        Index("idx_dim_contract_main", "is_main"),
    )
