"""extend_metric_metadata

Revision ID: f5823ac9a07e
Revises: 8a6049b65469
Create Date: 2026-02-01 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5823ac9a07e'
down_revision = '8a6049b65469'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加指标元数据字段
    op.add_column('dim_metric', 
        sa.Column('value_type', sa.String(length=16), nullable=True)
    )
    op.add_column('dim_metric',
        sa.Column('preferred_agg', sa.String(length=16), server_default='mean', nullable=True)
    )
    op.add_column('dim_metric',
        sa.Column('suggested_axis', sa.String(length=8), server_default='auto', nullable=True)
    )
    op.add_column('dim_metric',
        sa.Column('display_precision', sa.String(length=8), nullable=True)
    )
    op.add_column('dim_metric',
        sa.Column('seasonality_supported', sa.String(length=8), server_default='true', nullable=True)
    )


def downgrade() -> None:
    # 删除字段
    op.drop_column('dim_metric', 'seasonality_supported')
    op.drop_column('dim_metric', 'display_precision')
    op.drop_column('dim_metric', 'suggested_axis')
    op.drop_column('dim_metric', 'preferred_agg')
    op.drop_column('dim_metric', 'value_type')
