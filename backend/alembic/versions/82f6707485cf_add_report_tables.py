"""add_report_tables

Revision ID: 82f6707485cf
Revises: 4d389fc6ab66
Create Date: 2026-02-01 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '82f6707485cf'
down_revision = '4d389fc6ab66'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建report_template表
    op.create_table(
        'report_template',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('template_json', mysql.JSON, nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default='0', nullable=True),
        sa.Column('owner_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['owner_id'], ['sys_user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建report_run表
    op.create_table(
        'report_run',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('template_id', sa.BigInteger(), nullable=False),
        sa.Column('params_json', mysql.JSON, nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('output_path', sa.String(length=512), nullable=True),
        sa.Column('error_json', mysql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['report_template.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('ix_report_run_template_id', 'report_run', ['template_id'], unique=False)
    op.create_index('ix_report_run_status', 'report_run', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_report_run_status', table_name='report_run')
    op.drop_index('ix_report_run_template_id', table_name='report_run')
    op.drop_table('report_run')
    op.drop_table('report_template')
