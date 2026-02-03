"""create_yongyi_weekly_tables

为涌益周度数据创建独立的事实表（主要13个表）

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-02-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # ========================================
    # 涌益周度表（主要13个sheet）
    # ========================================
    
    # 1. yongyi_weekly_out_price（周度-商品猪出栏价）
    if not _table_exists('yongyi_weekly_out_price'):
        op.create_table(
            'yongyi_weekly_out_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False, comment='周期开始日期'),
            sa.Column('period_end', sa.Date(), nullable=False, comment='周期结束日期'),
            sa.Column('region_code', sa.String(32), nullable=False, comment='省份代码'),
            sa.Column('price', sa.Numeric(18, 6), nullable=True, comment='出栏价'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_out_price', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_out_price', ['period_end'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_out_price', ['region_code'], unique=False)
        op.create_unique_constraint('uk_period_region', 'yongyi_weekly_out_price', ['period_end', 'region_code'])
    
    # 2. yongyi_weekly_weight（周度-体重）
    if not _table_exists('yongyi_weekly_weight'):
        op.create_table(
            'yongyi_weekly_weight',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('indicator', sa.String(64), nullable=False, comment='指标名称'),
            sa.Column('region_code', sa.String(32), nullable=False, comment='省份代码'),
            sa.Column('weight_value', sa.Numeric(18, 6), nullable=True, comment='体重值'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_weight', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_weight', ['period_end'], unique=False)
        op.create_index('idx_indicator', 'yongyi_weekly_weight', ['indicator'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_weight', ['region_code'], unique=False)
        op.create_unique_constraint('uk_period_indicator_region', 'yongyi_weekly_weight', ['period_end', 'indicator', 'region_code'])
    
    # 3. yongyi_weekly_slaughter_prelive_weight（周度-屠宰厂宰前活猪重）
    if not _table_exists('yongyi_weekly_slaughter_prelive_weight'):
        op.create_table(
            'yongyi_weekly_slaughter_prelive_weight',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('indicator', sa.String(64), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=False),
            sa.Column('weight_value', sa.Numeric(18, 6), nullable=True, comment='重量值'),
            sa.Column('change_from_last_week', sa.Numeric(18, 6), nullable=True, comment='较上周变化'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_slaughter_prelive_weight', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_slaughter_prelive_weight', ['period_end'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_slaughter_prelive_weight', ['region_code'], unique=False)
        op.create_unique_constraint('uk_period_indicator_region', 'yongyi_weekly_slaughter_prelive_weight', ['period_end', 'indicator', 'region_code'])
    
    # 4. yongyi_weekly_weight_spread（周度-各体重段价差）
    if not _table_exists('yongyi_weekly_weight_spread'):
        op.create_table(
            'yongyi_weekly_weight_spread',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('indicator', sa.String(64), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=False),
            sa.Column('spread_value', sa.Numeric(18, 6), nullable=True, comment='价差值'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_weight_spread', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_weight_spread', ['period_end'], unique=False)
        op.create_index('idx_indicator', 'yongyi_weekly_weight_spread', ['indicator'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_weight_spread', ['region_code'], unique=False)
        op.create_unique_constraint('uk_period_indicator_region', 'yongyi_weekly_weight_spread', ['period_end', 'indicator', 'region_code'])
    
    # 5. yongyi_weekly_farm_profit_latest（周度-养殖利润最新）
    if not _table_exists('yongyi_weekly_farm_profit_latest'):
        op.create_table(
            'yongyi_weekly_farm_profit_latest',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('scale_type', sa.String(32), nullable=False, comment='规模段'),
            sa.Column('profit_mode', sa.String(32), nullable=False, comment='利润模式'),
            sa.Column('profit_value', sa.Numeric(18, 6), nullable=True, comment='利润值'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_farm_profit_latest', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_farm_profit_latest', ['period_end'], unique=False)
        op.create_unique_constraint('uk_period_scale_mode', 'yongyi_weekly_farm_profit_latest', ['period_end', 'scale_type', 'profit_mode'])
    
    # 6. yongyi_weekly_frozen_inventory（周度-冻品库存）
    if not _table_exists('yongyi_weekly_frozen_inventory'):
        op.create_table(
            'yongyi_weekly_frozen_inventory',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=True, comment='省份代码'),
            sa.Column('inventory_ratio', sa.Numeric(18, 6), nullable=True, comment='冻品库存库容率'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_frozen_inventory', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_frozen_inventory', ['period_end'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_frozen_inventory', ['region_code'], unique=False)
        op.create_unique_constraint('uk_period_region', 'yongyi_weekly_frozen_inventory', ['period_end', 'region_code'])
    
    # 7. yongyi_weekly_live_white_spread（周度-毛白价差）
    if not _table_exists('yongyi_weekly_live_white_spread'):
        op.create_table(
            'yongyi_weekly_live_white_spread',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_end', sa.Date(), nullable=False, comment='周期结束日期'),
            sa.Column('metric_name', sa.String(64), nullable=False, comment='指标名称'),
            sa.Column('spread_value', sa.Numeric(18, 6), nullable=True, comment='价差值'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_live_white_spread', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_live_white_spread', ['period_end'], unique=False)
        op.create_unique_constraint('uk_period_metric', 'yongyi_weekly_live_white_spread', ['period_end', 'metric_name'])
    
    # 8. yongyi_weekly_sow_50kg_price（周度-50公斤二元母猪价格）
    if not _table_exists('yongyi_weekly_sow_50kg_price'):
        op.create_table(
            'yongyi_weekly_sow_50kg_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=True),
            sa.Column('price', sa.Numeric(18, 6), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_sow_50kg_price', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_sow_50kg_price', ['period_end'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_sow_50kg_price', ['region_code'], unique=False)
        op.create_unique_constraint('uk_period_region', 'yongyi_weekly_sow_50kg_price', ['period_end', 'region_code'])
    
    # 9. yongyi_weekly_piglet_15kg_price（周度-规模场15公斤仔猪出栏价）
    if not _table_exists('yongyi_weekly_piglet_15kg_price'):
        op.create_table(
            'yongyi_weekly_piglet_15kg_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=True),
            sa.Column('price', sa.Numeric(18, 6), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_piglet_15kg_price', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_piglet_15kg_price', ['period_end'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_piglet_15kg_price', ['region_code'], unique=False)
        op.create_unique_constraint('uk_period_region', 'yongyi_weekly_piglet_15kg_price', ['period_end', 'region_code'])
    
    # 10. yongyi_weekly_cull_sow_price（周度-淘汰母猪价格）
    if not _table_exists('yongyi_weekly_cull_sow_price'):
        op.create_table(
            'yongyi_weekly_cull_sow_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=True),
            sa.Column('price', sa.Numeric(18, 6), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_cull_sow_price', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_cull_sow_price', ['period_end'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_cull_sow_price', ['region_code'], unique=False)
        op.create_unique_constraint('uk_period_region', 'yongyi_weekly_cull_sow_price', ['period_end', 'region_code'])
    
    # 11. yongyi_weekly_post_slaughter_settle_price（周度-宰后结算价）
    if not _table_exists('yongyi_weekly_post_slaughter_settle_price'):
        op.create_table(
            'yongyi_weekly_post_slaughter_settle_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=True),
            sa.Column('settle_price', sa.Numeric(18, 6), nullable=True, comment='结算价'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_post_slaughter_settle_price', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_post_slaughter_settle_price', ['period_end'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_post_slaughter_settle_price', ['region_code'], unique=False)
        op.create_unique_constraint('uk_period_region', 'yongyi_weekly_post_slaughter_settle_price', ['period_end', 'region_code'])
    
    # 12. yongyi_weekly_pork_price（周度-猪肉价（前三等级白条均价））
    if not _table_exists('yongyi_weekly_pork_price'):
        op.create_table(
            'yongyi_weekly_pork_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False),
            sa.Column('period_end', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=True),
            sa.Column('avg_price', sa.Numeric(18, 6), nullable=True, comment='均价'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_pork_price', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_pork_price', ['period_end'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_pork_price', ['region_code'], unique=False)
        op.create_unique_constraint('uk_period_region', 'yongyi_weekly_pork_price', ['period_end', 'region_code'])
    
    # 13. yongyi_weekly_slaughter_daily（周度-屠宰企业日度屠宰量）
    if not _table_exists('yongyi_weekly_slaughter_daily'):
        op.create_table(
            'yongyi_weekly_slaughter_daily',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日期（日度数据）'),
            sa.Column('region_code', sa.String(32), nullable=False, comment='省份代码'),
            sa.Column('slaughter_volume', sa.Integer(), nullable=True, comment='屠宰量'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_slaughter_daily', ['batch_id'], unique=False)
        op.create_index('idx_date', 'yongyi_weekly_slaughter_daily', ['trade_date'], unique=False)
        op.create_index('idx_region', 'yongyi_weekly_slaughter_daily', ['region_code'], unique=False)
        op.create_unique_constraint('uk_date_region', 'yongyi_weekly_slaughter_daily', ['trade_date', 'region_code'])
    
    # 14. yongyi_weekly_weight_split（周度-体重拆分）
    if not _table_exists('yongyi_weekly_weight_split'):
        op.create_table(
            'yongyi_weekly_weight_split',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_end', sa.Date(), nullable=False, comment='周期结束日期'),
            sa.Column('nation_avg_weight', sa.Numeric(18, 6), nullable=True, comment='全国均重'),
            sa.Column('group_weight', sa.Numeric(18, 6), nullable=True, comment='集团均重'),
            sa.Column('scatter_weight', sa.Numeric(18, 6), nullable=True, comment='散户均重'),
            sa.Column('group_ratio', sa.Numeric(18, 6), nullable=True, comment='集团占比'),
            sa.Column('scatter_ratio', sa.Numeric(18, 6), nullable=True, comment='散户占比'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_weekly_weight_split', ['batch_id'], unique=False)
        op.create_index('idx_period', 'yongyi_weekly_weight_split', ['period_end'], unique=False)
        op.create_unique_constraint('uk_period', 'yongyi_weekly_weight_split', ['period_end'])


def downgrade() -> None:
    # 删除所有表（按相反顺序）
    op.drop_table('yongyi_weekly_weight_split')
    op.drop_table('yongyi_weekly_slaughter_daily')
    op.drop_table('yongyi_weekly_pork_price')
    op.drop_table('yongyi_weekly_post_slaughter_settle_price')
    op.drop_table('yongyi_weekly_cull_sow_price')
    op.drop_table('yongyi_weekly_piglet_15kg_price')
    op.drop_table('yongyi_weekly_sow_50kg_price')
    op.drop_table('yongyi_weekly_live_white_spread')
    op.drop_table('yongyi_weekly_frozen_inventory')
    op.drop_table('yongyi_weekly_farm_profit_latest')
    op.drop_table('yongyi_weekly_weight_spread')
    op.drop_table('yongyi_weekly_slaughter_prelive_weight')
    op.drop_table('yongyi_weekly_weight')
    op.drop_table('yongyi_weekly_out_price')
