"""add_dedup_key

Revision ID: 8a6049b65469
Revises: 0001_init
Create Date: 2026-02-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a6049b65469'
down_revision = '0001_init'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加dedup_key字段
    op.add_column('fact_observation', 
        sa.Column('dedup_key', sa.String(length=64), nullable=True)
    )
    
    # 创建唯一索引
    op.create_unique_constraint('uq_fact_observation_dedup_key', 'fact_observation', ['dedup_key'])
    
    # 创建普通索引（用于查询优化）
    op.create_index('ix_fact_observation_dedup_key', 'fact_observation', ['dedup_key'], unique=False)


def downgrade() -> None:
    # 删除索引和约束
    op.drop_index('ix_fact_observation_dedup_key', table_name='fact_observation')
    op.drop_constraint('uq_fact_observation_dedup_key', 'fact_observation', type_='unique')
    
    # 删除字段
    op.drop_column('fact_observation', 'dedup_key')
