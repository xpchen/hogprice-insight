"""add_import_batch_audit_fields

Revision ID: 4d389fc6ab66
Revises: ad2a34220bb7
Create Date: 2026-02-01 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d389fc6ab66'
down_revision = 'ad2a34220bb7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加导入批次审计字段
    op.add_column('import_batch', 
        sa.Column('sheet_count', sa.BigInteger(), server_default='0', nullable=True)
    )
    op.add_column('import_batch',
        sa.Column('metric_count', sa.BigInteger(), server_default='0', nullable=True)
    )
    op.add_column('import_batch',
        sa.Column('duration_ms', sa.BigInteger(), nullable=True)
    )
    op.add_column('import_batch',
        sa.Column('inserted_count', sa.BigInteger(), server_default='0', nullable=True)
    )
    op.add_column('import_batch',
        sa.Column('updated_count', sa.BigInteger(), server_default='0', nullable=True)
    )


def downgrade() -> None:
    # 删除字段
    op.drop_column('import_batch', 'updated_count')
    op.drop_column('import_batch', 'inserted_count')
    op.drop_column('import_batch', 'duration_ms')
    op.drop_column('import_batch', 'metric_count')
    op.drop_column('import_batch', 'sheet_count')
