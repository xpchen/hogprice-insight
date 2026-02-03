"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2026-02-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # sys_user
    op.create_table(
        'sys_user',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username', name='uq_sys_user_username')
    )
    op.create_index(op.f('ix_sys_user_username'), 'sys_user', ['username'], unique=False)

    # sys_role
    op.create_table(
        'sys_role',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_sys_role_code')
    )
    op.create_index(op.f('ix_sys_role_code'), 'sys_role', ['code'], unique=False)

    # sys_user_role
    op.create_table(
        'sys_user_role',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('role_id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['sys_user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['sys_role.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )

    # import_batch
    op.create_table(
        'import_batch',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('uploader_id', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        sa.Column('total_rows', sa.BigInteger(), server_default='0'),
        sa.Column('success_rows', sa.BigInteger(), server_default='0'),
        sa.Column('failed_rows', sa.BigInteger(), server_default='0'),
        sa.Column('error_json', mysql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['uploader_id'], ['sys_user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_import_batch_created_at', 'import_batch', ['created_at'], unique=False)

    # dim_metric
    op.create_table(
        'dim_metric',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('metric_group', sa.String(length=32), nullable=False),
        sa.Column('metric_name', sa.String(length=64), nullable=False),
        sa.Column('unit', sa.String(length=32), nullable=True),
        sa.Column('freq', sa.String(length=16), nullable=False),
        sa.Column('raw_header', sa.String(length=500), nullable=False),
        sa.Column('sheet_name', sa.String(length=64), nullable=True),
        sa.Column('source_updated_at', sa.String(length=64), nullable=True),
        sa.Column('parse_json', mysql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('raw_header', 'sheet_name', name='uq_dim_metric_raw_sheet')
    )
    op.create_index('idx_dim_metric_group_freq', 'dim_metric', ['metric_group', 'freq'], unique=False)
    op.create_index(op.f('ix_dim_metric_metric_group'), 'dim_metric', ['metric_group'], unique=False)
    op.create_index(op.f('ix_dim_metric_metric_name'), 'dim_metric', ['metric_name'], unique=False)

    # dim_geo
    op.create_table(
        'dim_geo',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('province', sa.String(length=32), nullable=False),
        sa.Column('region', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('province', name='uq_dim_geo_province')
    )
    op.create_index(op.f('ix_dim_geo_province'), 'dim_geo', ['province'], unique=False)

    # dim_company
    op.create_table(
        'dim_company',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('company_name', sa.String(length=128), nullable=False),
        sa.Column('province', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_name', name='uq_dim_company_name')
    )
    op.create_index(op.f('ix_dim_company_company_name'), 'dim_company', ['company_name'], unique=False)

    # dim_warehouse
    op.create_table(
        'dim_warehouse',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('warehouse_name', sa.String(length=128), nullable=False),
        sa.Column('province', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('warehouse_name', name='uq_dim_warehouse_name')
    )
    op.create_index(op.f('ix_dim_warehouse_warehouse_name'), 'dim_warehouse', ['warehouse_name'], unique=False)

    # fact_observation
    op.create_table(
        'fact_observation',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.BigInteger(), nullable=True),
        sa.Column('metric_id', sa.BigInteger(), nullable=False),
        sa.Column('obs_date', sa.Date(), nullable=False),
        sa.Column('value', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('geo_id', sa.BigInteger(), nullable=True),
        sa.Column('company_id', sa.BigInteger(), nullable=True),
        sa.Column('warehouse_id', sa.BigInteger(), nullable=True),
        sa.Column('tags_json', mysql.JSON, nullable=True),
        sa.Column('raw_value', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['company_id'], ['dim_company.id'], ),
        sa.ForeignKeyConstraint(['geo_id'], ['dim_geo.id'], ),
        sa.ForeignKeyConstraint(['metric_id'], ['dim_metric.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['dim_warehouse.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_fact_warehouse_date', 'fact_observation', ['warehouse_id', 'obs_date'], unique=False)
    op.create_index('idx_fact_metric_date', 'fact_observation', ['metric_id', 'obs_date'], unique=False)
    op.create_index('idx_fact_geo_date', 'fact_observation', ['geo_id', 'obs_date'], unique=False)
    op.create_index('idx_fact_company_date', 'fact_observation', ['company_id', 'obs_date'], unique=False)
    op.create_index(op.f('ix_fact_observation_company_id'), 'fact_observation', ['company_id'], unique=False)
    op.create_index(op.f('ix_fact_observation_geo_id'), 'fact_observation', ['geo_id'], unique=False)
    op.create_index(op.f('ix_fact_observation_metric_id'), 'fact_observation', ['metric_id'], unique=False)
    op.create_index(op.f('ix_fact_observation_obs_date'), 'fact_observation', ['obs_date'], unique=False)
    op.create_index(op.f('ix_fact_observation_warehouse_id'), 'fact_observation', ['warehouse_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_fact_observation_warehouse_id'), table_name='fact_observation')
    op.drop_index(op.f('ix_fact_observation_obs_date'), table_name='fact_observation')
    op.drop_index(op.f('ix_fact_observation_metric_id'), table_name='fact_observation')
    op.drop_index(op.f('ix_fact_observation_geo_id'), table_name='fact_observation')
    op.drop_index(op.f('ix_fact_observation_company_id'), table_name='fact_observation')
    op.drop_index('idx_fact_company_date', table_name='fact_observation')
    op.drop_index('idx_fact_geo_date', table_name='fact_observation')
    op.drop_index('idx_fact_metric_date', table_name='fact_observation')
    op.drop_index('idx_fact_warehouse_date', table_name='fact_observation')
    op.drop_table('fact_observation')
    op.drop_index(op.f('ix_dim_warehouse_warehouse_name'), table_name='dim_warehouse')
    op.drop_table('dim_warehouse')
    op.drop_index(op.f('ix_dim_company_company_name'), table_name='dim_company')
    op.drop_table('dim_company')
    op.drop_index(op.f('ix_dim_geo_province'), table_name='dim_geo')
    op.drop_table('dim_geo')
    op.drop_index(op.f('ix_dim_metric_metric_name'), table_name='dim_metric')
    op.drop_index(op.f('ix_dim_metric_metric_group'), table_name='dim_metric')
    op.drop_index('idx_dim_metric_group_freq', table_name='dim_metric')
    op.drop_table('dim_metric')
    op.drop_index('idx_import_batch_created_at', table_name='import_batch')
    op.drop_table('import_batch')
    op.drop_table('sys_user_role')
    op.drop_index(op.f('ix_sys_role_code'), table_name='sys_role')
    op.drop_table('sys_role')
    op.drop_index(op.f('ix_sys_user_username'), table_name='sys_user')
    op.drop_table('sys_user')
