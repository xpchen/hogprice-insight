"""create_raw_sheet_table

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-02-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 创建 raw_sheet 表（Sheet级元信息）
    op.create_table(
        'raw_sheet',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('raw_file_id', sa.BigInteger(), nullable=False),
        sa.Column('sheet_name', sa.String(length=128), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('col_count', sa.Integer(), nullable=True),
        sa.Column('header_signature', sa.String(length=512), nullable=True),
        sa.Column('parse_status', sa.String(length=32), nullable=True, server_default='pending'),
        sa.Column('parser_type', sa.String(length=64), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('observation_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['raw_file_id'], ['raw_file.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_raw_sheet_file', 'raw_sheet', ['raw_file_id'], unique=False)
    op.create_index('ix_raw_sheet_name', 'raw_sheet', ['sheet_name'], unique=False)
    op.create_index('ix_raw_sheet_status', 'raw_sheet', ['parse_status'], unique=False)
    
    # 2. 创建 raw_table 表（表格快照）
    op.create_table(
        'raw_table',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('raw_sheet_id', sa.BigInteger(), nullable=False),
        sa.Column('table_json', mysql.JSON, nullable=False),
        sa.Column('merged_cells_json', mysql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['raw_sheet_id'], ['raw_sheet.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_raw_table_sheet', 'raw_table', ['raw_sheet_id'], unique=True)


def downgrade() -> None:
    # 删除表（按创建顺序反向）
    op.drop_index('ix_raw_table_sheet', table_name='raw_table')
    op.drop_table('raw_table')
    
    op.drop_index('ix_raw_sheet_status', table_name='raw_sheet')
    op.drop_index('ix_raw_sheet_name', table_name='raw_sheet')
    op.drop_index('ix_raw_sheet_file', table_name='raw_sheet')
    op.drop_table('raw_sheet')
