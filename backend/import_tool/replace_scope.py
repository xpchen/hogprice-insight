"""
Web 导入覆盖策略：
1) truncate_tables: 整表 TRUNCATE（仅独占单表模板）
2) delete_rules: 按 source 精准删除（共享表低风险覆盖）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class DeleteRule:
    table: str
    source: str
    extra_where_sql: str | None = None


@dataclass
class ReplaceSummary:
    mode: str
    template_type: str
    truncated_tables: list[str]
    deleted_rows_by_table: dict[str, int]


# template_type 与 ingest.TEMPLATE_MAP 键一致
REPLACE_TRUNCATE_TABLES: dict[str, list[str]] = {
    "ENTERPRISE_MONTHLY": ["fact_enterprise_monthly"],
    "LH_FTR": ["fact_futures_daily"],
}

# 按 source 删除（阶段二）
REPLACE_DELETE_RULES: dict[str, list[DeleteRule]] = {
    "YONGYI_DAILY": [
        DeleteRule("fact_price_daily", "YONGYI"),
        DeleteRule("fact_spread_daily", "YONGYI"),
        DeleteRule("fact_slaughter_daily", "YONGYI"),
    ],
    "YONGYI_WEEKLY": [
        DeleteRule("fact_weekly_indicator", "YONGYI"),
        DeleteRule("fact_monthly_indicator", "YONGYI"),
    ],
}


def supports_replace_tables(template_type: str) -> bool:
    return template_type in REPLACE_TRUNCATE_TABLES or template_type in REPLACE_DELETE_RULES


def get_replace_support_hint() -> str:
    return (
        "当前支持覆盖导入："
        "ENTERPRISE_MONTHLY→TRUNCATE fact_enterprise_monthly；"
        "LH_FTR→TRUNCATE fact_futures_daily；"
        "YONGYI_DAILY→DELETE source='YONGYI' (price/spread/slaughter)；"
        "YONGYI_WEEKLY→DELETE source='YONGYI' (weekly/monthly_indicator)。"
    )


def apply_replace_strategy(engine: Engine, template_type: str) -> ReplaceSummary:
    """
    统一执行覆盖策略，返回执行摘要。
    调用方需先用 supports_replace_tables 校验。
    """
    if template_type in REPLACE_TRUNCATE_TABLES:
        tables = REPLACE_TRUNCATE_TABLES[template_type]
        with engine.connect() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in tables:
                conn.execute(text(f"TRUNCATE TABLE `{table}`"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
        return ReplaceSummary(
            mode="truncate_tables",
            template_type=template_type,
            truncated_tables=list(tables),
            deleted_rows_by_table={},
        )

    rules = REPLACE_DELETE_RULES.get(template_type, [])
    deleted: dict[str, int] = {}
    with engine.connect() as conn:
        for rule in rules:
            sql = f"DELETE FROM `{rule.table}` WHERE source = :src"
            params: dict[str, Any] = {"src": rule.source}
            if rule.extra_where_sql:
                sql += f" AND ({rule.extra_where_sql})"
            res = conn.execute(text(sql), params)
            deleted[rule.table] = deleted.get(rule.table, 0) + (res.rowcount or 0)
        conn.commit()
    return ReplaceSummary(
        mode="delete_by_source",
        template_type=template_type,
        truncated_tables=[],
        deleted_rows_by_table=deleted,
    )
