"""add_chart_template

Revision ID: ad2a34220bb7
Revises: f5823ac9a07e
Create Date: 2026-02-01 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'ad2a34220bb7'
down_revision = 'f5823ac9a07e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建chart_template表
    op.create_table(
        'chart_template',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('chart_type', sa.String(length=32), nullable=True),
        sa.Column('spec_json', mysql.JSON, nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('owner_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['owner_id'], ['sys_user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('chart_template')
