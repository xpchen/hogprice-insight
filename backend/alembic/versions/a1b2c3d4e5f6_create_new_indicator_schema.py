"""create_new_indicator_schema

Revision ID: a1b2c3d4e5f6
Revises: 82f6707485cf
Create Date: 2026-02-01 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '82f6707485cf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 扩展 import_batch 表
    op.add_column('import_batch', sa.Column('source_code', sa.String(length=32), nullable=True))
    op.add_column('import_batch', sa.Column('date_range', mysql.JSON, nullable=True))
    op.add_column('import_batch', sa.Column('mapping_json', mysql.JSON, nullable=True))
    
    # 2. 创建 dim_indicator 表
    op.create_table(
        'dim_indicator',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('indicator_code', sa.String(length=64), nullable=False),
        sa.Column('indicator_name', sa.String(length=128), nullable=False),
        sa.Column('freq', sa.String(length=16), nullable=False),
        sa.Column('unit', sa.String(length=32), nullable=True),
        sa.Column('topic', sa.String(length=32), nullable=True),
        sa.Column('source_code', sa.String(length=32), nullable=True),
        sa.Column('calc_method', sa.String(length=16), nullable=False, server_default='RAW'),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('indicator_code', name='uq_dim_indicator_code')
    )
    op.create_index('idx_dim_indicator_code', 'dim_indicator', ['indicator_code'], unique=False)
    op.create_index('idx_dim_indicator_topic_freq', 'dim_indicator', ['topic', 'freq'], unique=False)
    op.create_index('idx_dim_indicator_source', 'dim_indicator', ['source_code'], unique=False)
    
    # 3. 创建 dim_region 表
    op.create_table(
        'dim_region',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('region_code', sa.String(length=32), nullable=False),
        sa.Column('region_name', sa.String(length=64), nullable=False),
        sa.Column('region_level', sa.String(length=16), nullable=False),
        sa.Column('parent_region_code', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('region_code', name='uq_dim_region_code')
    )
    op.create_index('idx_dim_region_code', 'dim_region', ['region_code'], unique=False)
    op.create_index('idx_dim_region_level', 'dim_region', ['region_level'], unique=False)
    op.create_index('idx_dim_region_parent', 'dim_region', ['parent_region_code'], unique=False)
    
    # 4. 创建 dim_contract 表
    op.create_table(
        'dim_contract',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('instrument', sa.String(length=16), nullable=False),
        sa.Column('contract_code', sa.String(length=32), nullable=False),
        sa.Column('maturity_year', sa.Integer(), nullable=False),
        sa.Column('maturity_month', sa.Integer(), nullable=False),
        sa.Column('is_main', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('main_rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contract_code', name='uq_dim_contract_code')
    )
    op.create_index('idx_dim_contract_code', 'dim_contract', ['contract_code'], unique=False)
    op.create_index('idx_dim_contract_instrument', 'dim_contract', ['instrument'], unique=False)
    op.create_index('idx_dim_contract_maturity', 'dim_contract', ['maturity_year', 'maturity_month'], unique=False)
    op.create_index('idx_dim_contract_main', 'dim_contract', ['is_main'], unique=False)
    
    # 5. 创建 dim_option 表
    op.create_table(
        'dim_option',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('underlying_contract', sa.String(length=32), nullable=False),
        sa.Column('option_type', sa.String(length=1), nullable=False),
        sa.Column('strike', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('option_code', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('option_code', name='uq_dim_option_code')
    )
    op.create_index('idx_dim_option_code', 'dim_option', ['option_code'], unique=False)
    op.create_index('idx_dim_option_underlying', 'dim_option', ['underlying_contract'], unique=False)
    op.create_index('idx_dim_option_type_strike', 'dim_option', ['option_type', 'strike'], unique=False)
    
    # 6. 创建 fact_indicator_ts 表
    op.create_table(
        'fact_indicator_ts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('indicator_code', sa.String(length=64), nullable=False),
        sa.Column('region_code', sa.String(length=32), nullable=False),
        sa.Column('freq', sa.String(length=16), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=True),
        sa.Column('week_start', sa.Date(), nullable=True),
        sa.Column('week_end', sa.Date(), nullable=True),
        sa.Column('value', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('source_code', sa.String(length=32), nullable=True),
        sa.Column('ingest_batch_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['ingest_batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('indicator_code', 'region_code', 'freq', 'trade_date', name='uq_fact_indicator_ts_daily'),
        sa.UniqueConstraint('indicator_code', 'region_code', 'freq', 'week_end', name='uq_fact_indicator_ts_weekly')
    )
    op.create_index('idx_fact_indicator_ts_code_date', 'fact_indicator_ts', ['indicator_code', 'trade_date'], unique=False)
    op.create_index('idx_fact_indicator_ts_code_week', 'fact_indicator_ts', ['indicator_code', 'week_end'], unique=False)
    op.create_index('idx_fact_indicator_ts_region_date', 'fact_indicator_ts', ['region_code', 'trade_date'], unique=False)
    op.create_index('idx_fact_indicator_ts_batch', 'fact_indicator_ts', ['ingest_batch_id'], unique=False)
    op.create_index('ix_fact_indicator_ts_indicator_code', 'fact_indicator_ts', ['indicator_code'], unique=False)
    op.create_index('ix_fact_indicator_ts_region_code', 'fact_indicator_ts', ['region_code'], unique=False)
    op.create_index('ix_fact_indicator_ts_trade_date', 'fact_indicator_ts', ['trade_date'], unique=False)
    
    # 7. 创建 fact_indicator_metrics 表
    op.create_table(
        'fact_indicator_metrics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('indicator_code', sa.String(length=64), nullable=False),
        sa.Column('region_code', sa.String(length=32), nullable=False),
        sa.Column('freq', sa.String(length=16), nullable=False),
        sa.Column('date_key', sa.Date(), nullable=False),
        sa.Column('value', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('chg_1', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('chg_5', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('chg_10', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('chg_30', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('mom', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('yoy', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('update_time', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('indicator_code', 'region_code', 'freq', 'date_key', name='uq_fact_indicator_metrics')
    )
    op.create_index('idx_fact_indicator_metrics_code_date', 'fact_indicator_metrics', ['indicator_code', 'date_key'], unique=False)
    op.create_index('idx_fact_indicator_metrics_region_date', 'fact_indicator_metrics', ['region_code', 'date_key'], unique=False)
    op.create_index('ix_fact_indicator_metrics_indicator_code', 'fact_indicator_metrics', ['indicator_code'], unique=False)
    op.create_index('ix_fact_indicator_metrics_region_code', 'fact_indicator_metrics', ['region_code'], unique=False)
    op.create_index('ix_fact_indicator_metrics_date_key', 'fact_indicator_metrics', ['date_key'], unique=False)
    
    # 8. 创建 fact_futures_daily 表
    op.create_table(
        'fact_futures_daily',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('instrument', sa.String(length=16), nullable=False),
        sa.Column('contract_code', sa.String(length=32), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('high', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('low', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('close', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('pre_settle', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('settle', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('chg', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('chg1', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        sa.Column('open_interest', sa.BigInteger(), nullable=True),
        sa.Column('oi_chg', sa.BigInteger(), nullable=True),
        sa.Column('turnover', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('ingest_batch_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contract_code', 'trade_date', name='uq_fact_futures_daily')
    )
    op.create_index('idx_fact_futures_contract_date', 'fact_futures_daily', ['contract_code', 'trade_date'], unique=False)
    op.create_index('idx_fact_futures_instrument_date', 'fact_futures_daily', ['instrument', 'trade_date'], unique=False)
    op.create_index('idx_fact_futures_date', 'fact_futures_daily', ['trade_date'], unique=False)
    op.create_index('ix_fact_futures_daily_instrument', 'fact_futures_daily', ['instrument'], unique=False)
    op.create_index('ix_fact_futures_daily_contract_code', 'fact_futures_daily', ['contract_code'], unique=False)
    op.create_index('ix_fact_futures_daily_trade_date', 'fact_futures_daily', ['trade_date'], unique=False)
    
    # 9. 创建 fact_options_daily 表
    op.create_table(
        'fact_options_daily',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('instrument', sa.String(length=16), nullable=False),
        sa.Column('underlying_contract', sa.String(length=32), nullable=False),
        sa.Column('option_type', sa.String(length=1), nullable=False),
        sa.Column('strike', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('option_code', sa.String(length=64), nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('high', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('low', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('close', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('pre_settle', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('settle', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('chg', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('chg1', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('delta', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('iv', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        sa.Column('open_interest', sa.BigInteger(), nullable=True),
        sa.Column('oi_chg', sa.BigInteger(), nullable=True),
        sa.Column('turnover', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('exercise_volume', sa.BigInteger(), nullable=True),
        sa.Column('ingest_batch_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('option_code', 'trade_date', name='uq_fact_options_daily')
    )
    op.create_index('idx_fact_options_code_date', 'fact_options_daily', ['option_code', 'trade_date'], unique=False)
    op.create_index('idx_fact_options_underlying_date', 'fact_options_daily', ['underlying_contract', 'trade_date'], unique=False)
    op.create_index('idx_fact_options_date', 'fact_options_daily', ['trade_date'], unique=False)
    op.create_index('ix_fact_options_daily_instrument', 'fact_options_daily', ['instrument'], unique=False)
    op.create_index('ix_fact_options_daily_option_code', 'fact_options_daily', ['option_code'], unique=False)
    op.create_index('ix_fact_options_daily_trade_date', 'fact_options_daily', ['trade_date'], unique=False)
    
    # 10. 创建 ingest_error 表
    op.create_table(
        'ingest_error',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=False),
        sa.Column('sheet_name', sa.String(length=128), nullable=True),
        sa.Column('row_no', sa.Integer(), nullable=True),
        sa.Column('col_name', sa.String(length=128), nullable=True),
        sa.Column('error_type', sa.String(length=32), nullable=True),
        sa.Column('message', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ingest_error_batch', 'ingest_error', ['batch_id'], unique=False)
    op.create_index('idx_ingest_error_type', 'ingest_error', ['error_type'], unique=False)
    
    # 11. 创建 ingest_mapping 表
    op.create_table(
        'ingest_mapping',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=False),
        sa.Column('mapping_json', mysql.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id', name='uq_ingest_mapping_batch')
    )
    op.create_index('idx_ingest_mapping_batch', 'ingest_mapping', ['batch_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_ingest_mapping_batch', table_name='ingest_mapping')
    op.drop_table('ingest_mapping')
    op.drop_index('idx_ingest_error_type', table_name='ingest_error')
    op.drop_index('idx_ingest_error_batch', table_name='ingest_error')
    op.drop_table('ingest_error')
    op.drop_index('ix_fact_options_daily_trade_date', table_name='fact_options_daily')
    op.drop_index('ix_fact_options_daily_option_code', table_name='fact_options_daily')
    op.drop_index('ix_fact_options_daily_instrument', table_name='fact_options_daily')
    op.drop_index('idx_fact_options_date', table_name='fact_options_daily')
    op.drop_index('idx_fact_options_underlying_date', table_name='fact_options_daily')
    op.drop_index('idx_fact_options_code_date', table_name='fact_options_daily')
    op.drop_table('fact_options_daily')
    op.drop_index('ix_fact_futures_daily_trade_date', table_name='fact_futures_daily')
    op.drop_index('ix_fact_futures_daily_contract_code', table_name='fact_futures_daily')
    op.drop_index('ix_fact_futures_daily_instrument', table_name='fact_futures_daily')
    op.drop_index('idx_fact_futures_date', table_name='fact_futures_daily')
    op.drop_index('idx_fact_futures_instrument_date', table_name='fact_futures_daily')
    op.drop_index('idx_fact_futures_contract_date', table_name='fact_futures_daily')
    op.drop_table('fact_futures_daily')
    op.drop_index('ix_fact_indicator_metrics_date_key', table_name='fact_indicator_metrics')
    op.drop_index('ix_fact_indicator_metrics_region_code', table_name='fact_indicator_metrics')
    op.drop_index('ix_fact_indicator_metrics_indicator_code', table_name='fact_indicator_metrics')
    op.drop_index('idx_fact_indicator_metrics_region_date', table_name='fact_indicator_metrics')
    op.drop_index('idx_fact_indicator_metrics_code_date', table_name='fact_indicator_metrics')
    op.drop_table('fact_indicator_metrics')
    op.drop_index('ix_fact_indicator_ts_trade_date', table_name='fact_indicator_ts')
    op.drop_index('ix_fact_indicator_ts_region_code', table_name='fact_indicator_ts')
    op.drop_index('ix_fact_indicator_ts_indicator_code', table_name='fact_indicator_ts')
    op.drop_index('idx_fact_indicator_ts_batch', table_name='fact_indicator_ts')
    op.drop_index('idx_fact_indicator_ts_region_date', table_name='fact_indicator_ts')
    op.drop_index('idx_fact_indicator_ts_code_week', table_name='fact_indicator_ts')
    op.drop_index('idx_fact_indicator_ts_code_date', table_name='fact_indicator_ts')
    op.drop_table('fact_indicator_ts')
    op.drop_index('idx_dim_option_type_strike', table_name='dim_option')
    op.drop_index('idx_dim_option_underlying', table_name='dim_option')
    op.drop_index('idx_dim_option_code', table_name='dim_option')
    op.drop_table('dim_option')
    op.drop_index('idx_dim_contract_main', table_name='dim_contract')
    op.drop_index('idx_dim_contract_maturity', table_name='dim_contract')
    op.drop_index('idx_dim_contract_instrument', table_name='dim_contract')
    op.drop_index('idx_dim_contract_code', table_name='dim_contract')
    op.drop_table('dim_contract')
    op.drop_index('idx_dim_region_parent', table_name='dim_region')
    op.drop_index('idx_dim_region_level', table_name='dim_region')
    op.drop_index('idx_dim_region_code', table_name='dim_region')
    op.drop_table('dim_region')
    op.drop_index('idx_dim_indicator_source', table_name='dim_indicator')
    op.drop_index('idx_dim_indicator_topic_freq', table_name='dim_indicator')
    op.drop_index('idx_dim_indicator_code', table_name='dim_indicator')
    op.drop_table('dim_indicator')
    op.drop_column('import_batch', 'mapping_json')
    op.drop_column('import_batch', 'date_range')
    op.drop_column('import_batch', 'source_code')
