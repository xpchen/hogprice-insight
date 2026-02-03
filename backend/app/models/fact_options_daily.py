from sqlalchemy import Column, BigInteger, String, Date, Numeric, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class FactOptionsDaily(Base):
    __tablename__ = "fact_options_daily"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    instrument = Column(String(16), nullable=False, index=True)  # 品种代码，如 LH
    underlying_contract = Column(String(32), nullable=False, index=True)  # 标的合约，如 lh2603
    option_type = Column(String(1), nullable=False)  # C/P
    strike = Column(Numeric(10, 2), nullable=False)  # 行权价
    option_code = Column(String(64), nullable=False, index=True)  # 期权代码，如 lh2603-C-10000
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
    
    # 期权特有字段
    delta = Column(Numeric(8, 4))  # Delta值
    iv = Column(Numeric(8, 4))  # 隐含波动率（百分比数值，如 23.18）
    
    # 成交持仓
    volume = Column(BigInteger)  # 成交量
    open_interest = Column(BigInteger)  # 持仓量
    oi_chg = Column(BigInteger)  # 持仓量变化
    turnover = Column(Numeric(18, 2))  # 成交额
    exercise_volume = Column(BigInteger)  # 行权量
    
    ingest_batch_id = Column(BigInteger)  # 导入批次ID
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("option_code", "trade_date", name="uq_fact_options_daily"),
        Index("idx_fact_options_code_date", "option_code", "trade_date"),
        Index("idx_fact_options_underlying_date", "underlying_contract", "trade_date"),
        Index("idx_fact_options_date", "trade_date"),
    )
