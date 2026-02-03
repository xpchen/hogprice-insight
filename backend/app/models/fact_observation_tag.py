from sqlalchemy import Column, BigInteger, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class FactObservationTag(Base):
    """观测值标签表 - 高性能维度筛选，将 tags_json 拆分为可索引的键值对"""
    __tablename__ = "fact_observation_tag"

    observation_id = Column(BigInteger, ForeignKey("fact_observation.id", ondelete="CASCADE"), primary_key=True)
    tag_key = Column(String(64), primary_key=True)  # 标签键：scale/weight_band/mode/sentiment 等
    tag_value = Column(String(128), nullable=False)  # 标签值：规模场/150kg/自繁自养/平稳 等

    # 关联关系
    observation = relationship("FactObservation", backref="tags")

    __table_args__ = (
        Index("idx_tag_kv", "tag_key", "tag_value"),
        Index("idx_tag_kv_obs", "tag_key", "tag_value", "observation_id"),
        {'comment': '观测值标签表'}
    )
