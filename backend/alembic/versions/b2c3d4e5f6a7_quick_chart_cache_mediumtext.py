"""quick_chart_cache response_body MEDIUMTEXT

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-02-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = 'b2c3d4e5f6a7'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MySQL TEXT = 64KB; 季节性与屠宰量等大 JSON 超限导致按需预热写入失败，改为 MEDIUMTEXT(16MB)
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.alter_column(
            "quick_chart_cache",
            "response_body",
            existing_type=sa.Text(),
            type_=mysql.MEDIUMTEXT(),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.alter_column(
            "quick_chart_cache",
            "response_body",
            existing_type=mysql.MEDIUMTEXT(),
            type_=sa.Text(),
            existing_nullable=False,
        )
