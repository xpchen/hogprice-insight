from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class IngestMapping(Base):
    __tablename__ = "ingest_mapping"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(BigInteger, ForeignKey("import_batch.id", ondelete="CASCADE"), nullable=False, index=True)
    mapping_json = Column(JSON, nullable=False)  # 映射结果JSON：记录识别与映射，便于追溯和复用
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 关联关系
    batch = relationship("ImportBatch", backref="mappings")

    __table_args__ = (
        UniqueConstraint("batch_id", name="uq_ingest_mapping_batch"),
        Index("idx_ingest_mapping_batch", "batch_id"),
    )
