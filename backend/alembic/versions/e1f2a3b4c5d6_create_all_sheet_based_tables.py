"""create_all_sheet_based_tables

为所有sheet创建独立的事实表（钢联7个 + 涌益日度8个）

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-02-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd1e2f3a4b5c6'
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
    # 钢联日度表（7个sheet）
    # ========================================
    
    # 1. ganglian_daily_province_price（分省区猪价）
    if not _table_exists('ganglian_daily_province_price'):
        op.create_table(
            'ganglian_daily_province_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=False, comment='省份代码'),
            sa.Column('indicator_name', sa.String(128), nullable=True, comment='指标名称'),
            sa.Column('value', sa.Numeric(18, 6), nullable=True, comment='价格值'),
            sa.Column('unit', sa.String(32), nullable=True, comment='单位'),
            sa.Column('updated_at_time', sa.DateTime(), nullable=True, comment='更新时间'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'ganglian_daily_province_price', ['batch_id'], unique=False)
        op.create_index('idx_date', 'ganglian_daily_province_price', ['trade_date'], unique=False)
        op.create_index('idx_region', 'ganglian_daily_province_price', ['region_code'], unique=False)
        op.create_unique_constraint('uk_date_region_indicator', 'ganglian_daily_province_price', ['trade_date', 'region_code', 'indicator_name'])
    
    # 2. ganglian_daily_group_enterprise_price（集团企业出栏价）
    if not _table_exists('ganglian_daily_group_enterprise_price'):
        op.create_table(
            'ganglian_daily_group_enterprise_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=True, comment='省份代码'),
            sa.Column('enterprise_name', sa.String(128), nullable=False, comment='集团企业名称'),
            sa.Column('value', sa.Numeric(18, 6), nullable=True, comment='出栏价'),
            sa.Column('unit', sa.String(32), nullable=True, comment='单位'),
            sa.Column('updated_at_time', sa.DateTime(), nullable=True, comment='更新时间'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'ganglian_daily_group_enterprise_price', ['batch_id'], unique=False)
        op.create_index('idx_date', 'ganglian_daily_group_enterprise_price', ['trade_date'], unique=False)
        op.create_index('idx_enterprise', 'ganglian_daily_group_enterprise_price', ['enterprise_name'], unique=False)
        op.create_unique_constraint('uk_date_enterprise', 'ganglian_daily_group_enterprise_price', ['trade_date', 'enterprise_name', 'region_code'])
    
    # 3. ganglian_daily_delivery_warehouse_price（交割库出栏价）
    if not _table_exists('ganglian_daily_delivery_warehouse_price'):
        op.create_table(
            'ganglian_daily_delivery_warehouse_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=True, comment='省份代码'),
            sa.Column('warehouse_name', sa.String(128), nullable=False, comment='交割库名称'),
            sa.Column('value', sa.Numeric(18, 6), nullable=True, comment='出栏价'),
            sa.Column('unit', sa.String(32), nullable=True, comment='单位'),
            sa.Column('updated_at_time', sa.DateTime(), nullable=True, comment='更新时间'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'ganglian_daily_delivery_warehouse_price', ['batch_id'], unique=False)
        op.create_index('idx_date', 'ganglian_daily_delivery_warehouse_price', ['trade_date'], unique=False)
        op.create_index('idx_warehouse', 'ganglian_daily_delivery_warehouse_price', ['warehouse_name'], unique=False)
        op.create_unique_constraint('uk_date_warehouse', 'ganglian_daily_delivery_warehouse_price', ['trade_date', 'warehouse_name', 'region_code'])
    
    # 4. ganglian_daily_region_spread（区域价差）
    if not _table_exists('ganglian_daily_region_spread'):
        op.create_table(
            'ganglian_daily_region_spread',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('spread_type', sa.String(64), nullable=False, comment='价差类型'),
            sa.Column('value', sa.Numeric(18, 6), nullable=True, comment='价差值'),
            sa.Column('unit', sa.String(32), nullable=True, comment='单位'),
            sa.Column('updated_at_time', sa.DateTime(), nullable=True, comment='更新时间'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'ganglian_daily_region_spread', ['batch_id'], unique=False)
        op.create_index('idx_date', 'ganglian_daily_region_spread', ['trade_date'], unique=False)
        op.create_unique_constraint('uk_date_spread_type', 'ganglian_daily_region_spread', ['trade_date', 'spread_type'])
    
    # 5. ganglian_daily_fat_std_spread（肥标价差）
    if not _table_exists('ganglian_daily_fat_std_spread'):
        op.create_table(
            'ganglian_daily_fat_std_spread',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=True, comment='区域代码'),
            sa.Column('value', sa.Numeric(18, 6), nullable=True, comment='肥标价差'),
            sa.Column('unit', sa.String(32), nullable=True, comment='单位'),
            sa.Column('updated_at_time', sa.DateTime(), nullable=True, comment='更新时间'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'ganglian_daily_fat_std_spread', ['batch_id'], unique=False)
        op.create_index('idx_date', 'ganglian_daily_fat_std_spread', ['trade_date'], unique=False)
        op.create_unique_constraint('uk_date_region', 'ganglian_daily_fat_std_spread', ['trade_date', 'region_code'])
    
    # 6. ganglian_daily_live_white_spread（毛白价差）
    if not _table_exists('ganglian_daily_live_white_spread'):
        op.create_table(
            'ganglian_daily_live_white_spread',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=True, comment='区域代码'),
            sa.Column('value', sa.Numeric(18, 6), nullable=True, comment='毛白价差'),
            sa.Column('unit', sa.String(32), nullable=True, comment='单位'),
            sa.Column('updated_at_time', sa.DateTime(), nullable=True, comment='更新时间'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'ganglian_daily_live_white_spread', ['batch_id'], unique=False)
        op.create_index('idx_date', 'ganglian_daily_live_white_spread', ['trade_date'], unique=False)
        op.create_unique_constraint('uk_date_region', 'ganglian_daily_live_white_spread', ['trade_date', 'region_code'])
    
    # 7. ganglian_weekly_farm_profit（养殖利润周度）
    if not _table_exists('ganglian_weekly_farm_profit'):
        op.create_table(
            'ganglian_weekly_farm_profit',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('period_start', sa.Date(), nullable=False, comment='周期开始日期'),
            sa.Column('period_end', sa.Date(), nullable=False, comment='周期结束日期'),
            sa.Column('profit_type', sa.String(64), nullable=False, comment='利润类型'),
            sa.Column('value', sa.Numeric(18, 6), nullable=True, comment='利润值（元/头）'),
            sa.Column('unit', sa.String(32), nullable=True, comment='单位'),
            sa.Column('updated_at_time', sa.DateTime(), nullable=True, comment='更新时间'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'ganglian_weekly_farm_profit', ['batch_id'], unique=False)
        op.create_index('idx_period', 'ganglian_weekly_farm_profit', ['period_end'], unique=False)
        op.create_unique_constraint('uk_period_profit_type', 'ganglian_weekly_farm_profit', ['period_end', 'profit_type'])
    
    # ========================================
    # 涌益日度表（8个sheet）
    # ========================================
    
    # 8. yongyi_daily_out_price（出栏价）
    if not _table_exists('yongyi_daily_out_price'):
        op.create_table(
            'yongyi_daily_out_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=False, comment='省份代码'),
            sa.Column('scale', sa.String(16), nullable=False, comment='规模场/小散户/均价'),
            sa.Column('price', sa.Numeric(18, 6), nullable=True, comment='价格'),
            sa.Column('change_amount', sa.Numeric(18, 6), nullable=True, comment='较昨日涨跌'),
            sa.Column('last_year_price', sa.Numeric(18, 6), nullable=True, comment='去年同期'),
            sa.Column('yoy_ratio', sa.Numeric(18, 6), nullable=True, comment='同比'),
            sa.Column('tomorrow_forecast', sa.Numeric(18, 6), nullable=True, comment='明日预计'),
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
    
    # 9. yongyi_daily_price_slaughter（价格+宰量）
    if not _table_exists('yongyi_daily_price_slaughter'):
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
    
    # 10. yongyi_daily_scatter_fat_spread（散户标肥价差）
    if not _table_exists('yongyi_daily_scatter_fat_spread'):
        op.create_table(
            'yongyi_daily_scatter_fat_spread',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=False, comment='省份代码'),
            sa.Column('scatter_std_price', sa.Numeric(18, 6), nullable=True, comment='市场散户标重猪价格'),
            sa.Column('spread_150_vs_std', sa.Numeric(18, 6), nullable=True, comment='150公斤左右较标猪价差'),
            sa.Column('spread_175_vs_std', sa.Numeric(18, 6), nullable=True, comment='175公斤左右较标猪价差'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_batch', 'yongyi_daily_scatter_fat_spread', ['batch_id'], unique=False)
        op.create_index('idx_date', 'yongyi_daily_scatter_fat_spread', ['trade_date'], unique=False)
        op.create_index('idx_region', 'yongyi_daily_scatter_fat_spread', ['region_code'], unique=False)
        op.create_unique_constraint('uk_date_region', 'yongyi_daily_scatter_fat_spread', ['trade_date', 'region_code'])
    
    # 11. yongyi_daily_province_avg（各省份均价）
    if not _table_exists('yongyi_daily_province_avg'):
        op.create_table(
            'yongyi_daily_province_avg',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=False, comment='省份代码'),
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
    
    # 12. yongyi_daily_market_std_fat_price（市场主流标猪肥猪价格）
    if not _table_exists('yongyi_daily_market_std_fat_price'):
        op.create_table(
            'yongyi_daily_market_std_fat_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=False, comment='省份代码'),
            sa.Column('std_pig_avg_price', sa.Numeric(18, 6), nullable=True, comment='标猪均价'),
            sa.Column('std_pig_weight_band', sa.String(32), nullable=True, comment='标猪体重段（文本）'),
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
    
    # 13. yongyi_daily_slaughter_vol（屠宰企业日度屠宰量）
    if not _table_exists('yongyi_daily_slaughter_vol'):
        op.create_table(
            'yongyi_daily_slaughter_vol',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=False, comment='省份代码'),
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
    
    # 14. yongyi_daily_market_avg_convenient（市场主流标猪肥猪均价方便作图）
    if not _table_exists('yongyi_daily_market_avg_convenient'):
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
    
    # 15. yongyi_daily_delivery_city_price（交割地市出栏价）
    if not _table_exists('yongyi_daily_delivery_city_price'):
        op.create_table(
            'yongyi_daily_delivery_city_price',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('batch_id', sa.BigInteger(), nullable=True),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('region_code', sa.String(32), nullable=False, comment='省份代码'),
            sa.Column('location_code', sa.String(32), nullable=False, comment='城市代码'),
            sa.Column('city_price', sa.Numeric(18, 6), nullable=True, comment='城市出栏价'),
            sa.Column('premium_lh2505_plus', sa.Numeric(18, 6), nullable=True, comment='升贴水（LH2505及以后）'),
            sa.Column('premium_lh2409_lh2503', sa.Numeric(18, 6), nullable=True, comment='升贴水（LH2409-LH2503）'),
            sa.Column('weight_band', sa.String(64), nullable=True, comment='交易均重（文本）'),
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


def downgrade() -> None:
    # 删除所有表（按相反顺序）
    op.drop_table('yongyi_daily_delivery_city_price')
    op.drop_table('yongyi_daily_market_avg_convenient')
    op.drop_table('yongyi_daily_slaughter_vol')
    op.drop_table('yongyi_daily_market_std_fat_price')
    op.drop_table('yongyi_daily_province_avg')
    op.drop_table('yongyi_daily_scatter_fat_spread')
    op.drop_table('yongyi_daily_price_slaughter')
    op.drop_table('yongyi_daily_out_price')
    op.drop_table('ganglian_weekly_farm_profit')
    op.drop_table('ganglian_daily_live_white_spread')
    op.drop_table('ganglian_daily_fat_std_spread')
    op.drop_table('ganglian_daily_region_spread')
    op.drop_table('ganglian_daily_delivery_warehouse_price')
    op.drop_table('ganglian_daily_group_enterprise_price')
    op.drop_table('ganglian_daily_province_price')
