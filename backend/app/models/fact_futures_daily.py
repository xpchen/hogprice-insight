from sqlalchemy import Column, BigInteger, String, Date, Numeric, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class FactFuturesDaily(Base):
    __tablename__ = "fact_futures_daily"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    instrument = Column(String(16), nullable=False, index=True)  # 品种代码，如 LH
    contract_code = Column(String(32), nullable=False, index=True)  # 合约代码，如 lh2603
    trade_date = Column(Date, nullable=False, index=True)  # 交易日期
    
    # 价格字段
    open = Column(Numeric(10, 2))  # 开盘价
    high = Column(Numeric(10, 2))  # 最高价
    low = Column(Numeric(10, 2))  # 最低价
    close = Column(Numeric(10, 2))  # 收盘价
    pre_settle = Column(Numeric(10, 2))  # 前结算价
    settle = Column(Numeric(10, 2))  # 结算价
    
    # 涨跌
    chg = Column(Numeric(10, 2))  # 涨跌
    chg1 = Column(Numeric(10, 2))  # 涨跌1
    
    # 成交持仓
    volume = Column(BigInteger)  # 成交量
    open_interest = Column(BigInteger)  # 持仓量
    oi_chg = Column(BigInteger)  # 持仓量变化
    turnover = Column(Numeric(18, 2))  # 成交额
    
    ingest_batch_id = Column(BigInteger)  # 导入批次ID
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("contract_code", "trade_date", name="uq_fact_futures_daily"),
        Index("idx_fact_futures_contract_date", "contract_code", "trade_date"),
        Index("idx_fact_futures_instrument_date", "instrument", "trade_date"),
        Index("idx_fact_futures_date", "trade_date"),
    )
