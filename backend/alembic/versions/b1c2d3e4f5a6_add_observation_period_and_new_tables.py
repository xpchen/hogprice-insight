"""add_observation_period_and_new_tables

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-02-01 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 为 fact_observation 添加周期字段（支持周度/月度）
    op.add_column('fact_observation', 
        sa.Column('period_type', sa.String(length=10), nullable=True)
    )
    op.add_column('fact_observation', 
        sa.Column('period_start', sa.Date(), nullable=True)
    )
    op.add_column('fact_observation', 
        sa.Column('period_end', sa.Date(), nullable=True)
    )
    op.create_index('idx_obs_period', 'fact_observation', ['period_type', 'period_end'], unique=False)
    
    # 2. 创建 dim_source 表（统一数据源管理）
    op.create_table(
        'dim_source',
        sa.Column('source_code', sa.String(length=32), nullable=False),
        sa.Column('source_name', sa.String(length=128), nullable=False),
        sa.Column('update_freq', sa.String(length=32), nullable=True),
        sa.Column('source_type', sa.String(length=32), nullable=True),
        sa.Column('license_note', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('source_code')
    )
    op.create_index('ix_dim_source_source_code', 'dim_source', ['source_code'], unique=True)
    
    # 3. 创建 dim_location 表（城市级地理层）
    op.create_table(
        'dim_location',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('location_code', sa.String(length=32), nullable=False),
        sa.Column('level', sa.String(length=16), nullable=False),  # province/city/county
        sa.Column('parent_code', sa.String(length=32), nullable=True),
        sa.Column('name_cn', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_dim_location_location_code', 'dim_location', ['location_code'], unique=True)
    op.create_index('ix_dim_location_level', 'dim_location', ['level'], unique=False)
    op.create_index('ix_dim_location_parent', 'dim_location', ['parent_code'], unique=False)
    
    # 4. 创建 dim_location_alias 表（地理位置别名映射）
    op.create_table(
        'dim_location_alias',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('alias', sa.String(length=128), nullable=False),
        sa.Column('source_code', sa.String(length=32), nullable=False),
        sa.Column('location_code', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['source_code'], ['dim_source.source_code'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['location_code'], ['dim_location.location_code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_dim_location_alias_alias_source', 'dim_location_alias', ['alias', 'source_code'], unique=True)
    op.create_index('ix_dim_location_alias_location', 'dim_location_alias', ['location_code'], unique=False)
    
    # 5. 创建 metric_alias 表（指标别名映射）
    op.create_table(
        'metric_alias',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('source_code', sa.String(length=32), nullable=False),
        sa.Column('sheet_name', sa.String(length=128), nullable=False),
        sa.Column('alias_text', sa.String(length=500), nullable=False),
        sa.Column('metric_id', sa.BigInteger(), nullable=True),
        sa.Column('tags_patch_json', mysql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['source_code'], ['dim_source.source_code'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['metric_id'], ['dim_metric.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_metric_alias_source_sheet_alias', 'metric_alias', ['source_code', 'sheet_name', 'alias_text'], unique=True)
    op.create_index('ix_metric_alias_metric', 'metric_alias', ['metric_id'], unique=False)
    
    # 6. 创建 fact_observation_tag 表（高性能维度筛选）
    op.create_table(
        'fact_observation_tag',
        sa.Column('observation_id', sa.BigInteger(), nullable=False),
        sa.Column('tag_key', sa.String(length=64), nullable=False),
        sa.Column('tag_value', sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(['observation_id'], ['fact_observation.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('observation_id', 'tag_key')
    )
    op.create_index('idx_tag_kv', 'fact_observation_tag', ['tag_key', 'tag_value'], unique=False)
    op.create_index('idx_tag_kv_obs', 'fact_observation_tag', ['tag_key', 'tag_value', 'observation_id'], unique=False)
    
    # 7. 创建 raw_file 表（原始文件溯源）
    op.create_table(
        'raw_file',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('report_date', sa.Date(), nullable=True),
        sa.Column('date_range_start', sa.Date(), nullable=True),
        sa.Column('date_range_end', sa.Date(), nullable=True),
        sa.Column('parser_version', sa.String(length=32), nullable=True),
        sa.Column('storage_path', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_raw_file_batch', 'raw_file', ['batch_id'], unique=False)
    op.create_index('ix_raw_file_hash', 'raw_file', ['file_hash'], unique=False)
    op.create_index('ix_raw_file_date_range', 'raw_file', ['date_range_start', 'date_range_end'], unique=False)
    
    # 8. 创建 ingest_profile 表（导入配置模板）
    op.create_table(
        'ingest_profile',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('profile_code', sa.String(length=64), nullable=False),
        sa.Column('profile_name', sa.String(length=255), nullable=False),
        sa.Column('source_code', sa.String(length=32), nullable=False),
        sa.Column('dataset_type', sa.String(length=64), nullable=False),
        sa.Column('file_pattern', sa.String(length=255), nullable=True),
        sa.Column('target', sa.String(length=64), nullable=False, server_default='fact_observation'),
        sa.Column('defaults_json', mysql.JSON, nullable=True),
        sa.Column('dispatch_rules_json', mysql.JSON, nullable=True),
        sa.Column('version', sa.String(length=32), nullable=False, server_default='1.0'),
        sa.Column('is_active', sa.String(length=1), nullable=False, server_default='Y'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['source_code'], ['dim_source.source_code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ingest_profile_profile_code', 'ingest_profile', ['profile_code'], unique=True)
    op.create_index('ix_ingest_profile_source', 'ingest_profile', ['source_code'], unique=False)
    
    # 9. 创建 ingest_profile_sheet 表（导入配置 Sheet）
    op.create_table(
        'ingest_profile_sheet',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('profile_id', sa.BigInteger(), nullable=False),
        sa.Column('sheet_name', sa.String(length=128), nullable=False),
        sa.Column('parser', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=32), nullable=True),
        sa.Column('config_json', mysql.JSON, nullable=False),
        sa.Column('priority', sa.BigInteger(), nullable=True, server_default='100'),
        sa.Column('note', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['ingest_profile.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ingest_profile_sheet_profile', 'ingest_profile_sheet', ['profile_id'], unique=False)
    op.create_index('ix_ingest_profile_sheet_sheet_name', 'ingest_profile_sheet', ['sheet_name'], unique=False)


def downgrade() -> None:
    # 删除表（按创建顺序反向）
    op.drop_index('ix_ingest_profile_sheet_sheet_name', table_name='ingest_profile_sheet')
    op.drop_index('ix_ingest_profile_sheet_profile', table_name='ingest_profile_sheet')
    op.drop_table('ingest_profile_sheet')
    
    op.drop_index('ix_ingest_profile_source', table_name='ingest_profile')
    op.drop_index('ix_ingest_profile_profile_code', table_name='ingest_profile')
    op.drop_table('ingest_profile')
    
    op.drop_index('ix_raw_file_date_range', table_name='raw_file')
    op.drop_index('ix_raw_file_hash', table_name='raw_file')
    op.drop_index('ix_raw_file_batch', table_name='raw_file')
    op.drop_table('raw_file')
    
    op.drop_index('idx_tag_kv_obs', table_name='fact_observation_tag')
    op.drop_index('idx_tag_kv', table_name='fact_observation_tag')
    op.drop_table('fact_observation_tag')
    
    op.drop_index('ix_metric_alias_metric', table_name='metric_alias')
    op.drop_index('ix_metric_alias_source_sheet_alias', table_name='metric_alias')
    op.drop_table('metric_alias')
    
    op.drop_index('ix_dim_location_alias_location', table_name='dim_location_alias')
    op.drop_index('ix_dim_location_alias_alias_source', table_name='dim_location_alias')
    op.drop_table('dim_location_alias')
    
    op.drop_index('ix_dim_location_parent', table_name='dim_location')
    op.drop_index('ix_dim_location_level', table_name='dim_location')
    op.drop_index('ix_dim_location_location_code', table_name='dim_location')
    op.drop_table('dim_location')
    
    op.drop_index('ix_dim_source_source_code', table_name='dim_source')
    op.drop_table('dim_source')
    
    # 删除 fact_observation 的周期字段
    op.drop_index('idx_obs_period', table_name='fact_observation')
    op.drop_column('fact_observation', 'period_end')
    op.drop_column('fact_observation', 'period_start')
    op.drop_column('fact_observation', 'period_type')
