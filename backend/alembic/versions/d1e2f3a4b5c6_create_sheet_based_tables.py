"""create_sheet_based_tables

为每个主要sheet创建独立的事实表

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-02-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================
    # 涌益日度表（8个sheet）
    # ========================================
    
    # 1. yongyi_daily_price_slaughter（价格+宰量）
    op.create_table(
        'yongyi_daily_price_slaughter',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('nation_avg_price', sa.Numeric(18, 6), nullable=True, comment='全国均价'),
        sa.Column('slaughter_total_1', sa.Integer(), nullable=True, comment='日屠宰量合计1'),
        sa.Column('slaughter_total_2', sa.Integer(), nullable=True, comment='日度屠宰量合计2'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch', 'yongyi_daily_price_slaughter', ['batch_id'], unique=False)
    op.create_index('idx_date', 'yongyi_daily_price_slaughter', ['trade_date'], unique=False)
    op.create_unique_constraint('uk_date', 'yongyi_daily_price_slaughter', ['trade_date'])
    
    # 2. yongyi_daily_province_avg（各省份均价）
    op.create_table(
        'yongyi_daily_province_avg',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('region_code', sa.String(32), nullable=False),
        sa.Column('avg_price', sa.Numeric(18, 6), nullable=True, comment='商品猪出栏均价'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch', 'yongyi_daily_province_avg', ['batch_id'], unique=False)
    op.create_index('idx_date', 'yongyi_daily_province_avg', ['trade_date'], unique=False)
    op.create_index('idx_region', 'yongyi_daily_province_avg', ['region_code'], unique=False)
    op.create_unique_constraint('uk_date_region', 'yongyi_daily_province_avg', ['trade_date', 'region_code'])
    
    # 3. yongyi_daily_slaughter_vol（屠宰企业日度屠宰量）
    op.create_table(
        'yongyi_daily_slaughter_vol',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('region_code', sa.String(32), nullable=False),
        sa.Column('slaughter_volume', sa.Integer(), nullable=True, comment='屠宰量（头）'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch', 'yongyi_daily_slaughter_vol', ['batch_id'], unique=False)
    op.create_index('idx_date', 'yongyi_daily_slaughter_vol', ['trade_date'], unique=False)
    op.create_index('idx_region', 'yongyi_daily_slaughter_vol', ['region_code'], unique=False)
    op.create_unique_constraint('uk_date_region', 'yongyi_daily_slaughter_vol', ['trade_date', 'region_code'])
    
    # 4. yongyi_daily_out_price（出栏价）
    op.create_table(
        'yongyi_daily_out_price',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('region_code', sa.String(32), nullable=False),
        sa.Column('scale', sa.String(16), nullable=False, comment='规模场/小散户/均价'),
        sa.Column('price', sa.Numeric(18, 6), nullable=True, comment='价格'),
        sa.Column('change_amount', sa.Numeric(18, 6), nullable=True, comment='涨跌'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch', 'yongyi_daily_out_price', ['batch_id'], unique=False)
    op.create_index('idx_date', 'yongyi_daily_out_price', ['trade_date'], unique=False)
    op.create_index('idx_region', 'yongyi_daily_out_price', ['region_code'], unique=False)
    op.create_index('idx_scale', 'yongyi_daily_out_price', ['scale'], unique=False)
    op.create_unique_constraint('uk_date_region_scale', 'yongyi_daily_out_price', ['trade_date', 'region_code', 'scale'])
    
    # 5. yongyi_daily_scatter_fat_spread（散户标肥价差）
    op.create_table(
        'yongyi_daily_scatter_fat_spread',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('region_code', sa.String(32), nullable=False),
        sa.Column('scatter_std_price', sa.Numeric(18, 6), nullable=True, comment='市场散户标重猪价格'),
        sa.Column('spread_150_vs_std', sa.Numeric(18, 6), nullable=True, comment='150kg较标猪价差'),
        sa.Column('spread_175_vs_std', sa.Numeric(18, 6), nullable=True, comment='175kg较标猪价差'),
        sa.Column('sentiment', sa.String(64), nullable=True, comment='二育采购情绪'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch', 'yongyi_daily_scatter_fat_spread', ['batch_id'], unique=False)
    op.create_index('idx_date', 'yongyi_daily_scatter_fat_spread', ['trade_date'], unique=False)
    op.create_index('idx_region', 'yongyi_daily_scatter_fat_spread', ['region_code'], unique=False)
    op.create_unique_constraint('uk_date_region', 'yongyi_daily_scatter_fat_spread', ['trade_date', 'region_code'])
    
    # 6. yongyi_daily_market_std_fat_price（市场主流标猪肥猪价格）
    op.create_table(
        'yongyi_daily_market_std_fat_price',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('region_code', sa.String(32), nullable=False),
        sa.Column('std_pig_avg_price', sa.Numeric(18, 6), nullable=True, comment='标猪均价'),
        sa.Column('std_pig_weight_band', sa.String(32), nullable=True, comment='标猪体重段'),
        sa.Column('price_90_100', sa.Numeric(18, 6), nullable=True, comment='90-100kg均价'),
        sa.Column('price_130_140', sa.Numeric(18, 6), nullable=True, comment='130-140kg均价'),
        sa.Column('price_150_around', sa.Numeric(18, 6), nullable=True, comment='150kg左右均价'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch', 'yongyi_daily_market_std_fat_price', ['batch_id'], unique=False)
    op.create_index('idx_date', 'yongyi_daily_market_std_fat_price', ['trade_date'], unique=False)
    op.create_index('idx_region', 'yongyi_daily_market_std_fat_price', ['region_code'], unique=False)
    op.create_unique_constraint('uk_date_region', 'yongyi_daily_market_std_fat_price', ['trade_date', 'region_code'])
    
    # 7. yongyi_daily_market_avg_convenient（市场主流标猪肥猪均价方便作图）
    op.create_table(
        'yongyi_daily_market_avg_convenient',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('nation_avg_price', sa.Numeric(18, 6), nullable=True, comment='全国均价'),
        sa.Column('price_90_100', sa.Numeric(18, 6), nullable=True, comment='90-100kg均价'),
        sa.Column('price_130_140', sa.Numeric(18, 6), nullable=True, comment='130-140kg均价'),
        sa.Column('price_150_170', sa.Numeric(18, 6), nullable=True, comment='150-170kg均价'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch', 'yongyi_daily_market_avg_convenient', ['batch_id'], unique=False)
    op.create_index('idx_date', 'yongyi_daily_market_avg_convenient', ['trade_date'], unique=False)
    op.create_unique_constraint('uk_date', 'yongyi_daily_market_avg_convenient', ['trade_date'])
    
    # 8. yongyi_daily_delivery_city_price（交割地市出栏价）
    op.create_table(
        'yongyi_daily_delivery_city_price',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('region_code', sa.String(32), nullable=False, comment='省份'),
        sa.Column('location_code', sa.String(32), nullable=False, comment='城市'),
        sa.Column('city_price', sa.Numeric(18, 6), nullable=True, comment='城市出栏价'),
        sa.Column('premium_lh2505_plus', sa.Numeric(18, 6), nullable=True, comment='升贴水（LH2505及以后）'),
        sa.Column('premium_lh2409_lh2503', sa.Numeric(18, 6), nullable=True, comment='升贴水（LH2409-LH2503）'),
        sa.Column('weight_band', sa.String(64), nullable=True, comment='交易均重'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch', 'yongyi_daily_delivery_city_price', ['batch_id'], unique=False)
    op.create_index('idx_date', 'yongyi_daily_delivery_city_price', ['trade_date'], unique=False)
    op.create_index('idx_region', 'yongyi_daily_delivery_city_price', ['region_code'], unique=False)
    op.create_index('idx_location', 'yongyi_daily_delivery_city_price', ['location_code'], unique=False)
    op.create_unique_constraint('uk_date_city', 'yongyi_daily_delivery_city_price', ['trade_date', 'location_code'])
    
    # ========================================
    # 涌益周度表（主要sheet，约10-15个）
    # ========================================
    
    # 9. yongyi_weekly_out_price（商品猪出栏价）
    op.create_table(
        'yongyi_weekly_out_price',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('region_code', sa.String(32), nullable=False),
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
    
    # 10. yongyi_weekly_frozen_inventory（冻品库存）
    op.create_table(
        'yongyi_weekly_frozen_inventory',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('region_code', sa.String(32), nullable=True, comment='省份或大区'),
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
    
    # 11. yongyi_weekly_farm_profit_latest（养殖利润最新）
    op.create_table(
        'yongyi_weekly_farm_profit_latest',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('mode', sa.String(32), nullable=False, comment='自繁自养/外购仔猪/合同农户'),
        sa.Column('scale_band', sa.String(64), nullable=True, comment='规模段'),
        sa.Column('profit', sa.Numeric(18, 6), nullable=True, comment='利润（元/头）'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch', 'yongyi_weekly_farm_profit_latest', ['batch_id'], unique=False)
    op.create_index('idx_period', 'yongyi_weekly_farm_profit_latest', ['period_end'], unique=False)
    op.create_index('idx_mode', 'yongyi_weekly_farm_profit_latest', ['mode'], unique=False)
    op.create_unique_constraint('uk_period_mode_scale', 'yongyi_weekly_farm_profit_latest', ['period_end', 'mode', 'scale_band'])
    
    # ========================================
    # 钢联日度表
    # ========================================
    
    # 12. ganglian_daily_price_template（价格模板）
    op.create_table(
        'ganglian_daily_price_template',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('indicator_code', sa.String(64), nullable=False, comment='指标代码'),
        sa.Column('region_code', sa.String(32), nullable=False, comment='区域代码'),
        sa.Column('value', sa.Numeric(18, 6), nullable=True, comment='指标值'),
        sa.Column('unit', sa.String(32), nullable=True, comment='单位'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_batch', 'ganglian_daily_price_template', ['batch_id'], unique=False)
    op.create_index('idx_date', 'ganglian_daily_price_template', ['trade_date'], unique=False)
    op.create_index('idx_indicator', 'ganglian_daily_price_template', ['indicator_code'], unique=False)
    op.create_index('idx_region', 'ganglian_daily_price_template', ['region_code'], unique=False)
    op.create_unique_constraint('uk_date_indicator_region', 'ganglian_daily_price_template', ['trade_date', 'indicator_code', 'region_code'])


def downgrade() -> None:
    # 删除所有sheet表
    tables = [
        'yongyi_daily_price_slaughter',
        'yongyi_daily_province_avg',
        'yongyi_daily_slaughter_vol',
        'yongyi_daily_out_price',
        'yongyi_daily_scatter_fat_spread',
        'yongyi_daily_market_std_fat_price',
        'yongyi_daily_market_avg_convenient',
        'yongyi_daily_delivery_city_price',
        'yongyi_weekly_out_price',
        'yongyi_weekly_frozen_inventory',
        'yongyi_weekly_farm_profit_latest',
        'ganglian_daily_price_template',
    ]
    
    for table_name in tables:
        op.drop_table(table_name)
