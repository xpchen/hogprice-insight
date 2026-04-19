"""
Web 导入覆盖策略：
1) truncate_tables: 整表 TRUNCATE（仅独占单表模板）
2) delete_rules: 按 source 精准删除（共享表低风险覆盖）

注意：即使不使用覆盖导入，bulk_insert 也会通过 INSERT ... ON DUPLICATE KEY UPDATE
自动更新已存在的重复记录，因此覆盖策略仅影响「旧批次中有但新批次中已删除」的行。
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
    "ENTERPRISE_DAILY": ["fact_enterprise_daily"],
    "WHITE_STRIP_MARKET": ["fact_carcass_market"],
    "FUTURES_BASIS": ["fact_futures_basis"],
    "INDUSTRY_DATA": ["fact_quarterly_stats"],
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
    "GANGLIAN_DAILY": [
        DeleteRule("fact_price_daily", "GANGLIAN"),
        # fact_enterprise_daily / fact_futures_basis 没有 source 列，不能按source删除
        # 由 upsert 自动覆盖相同唯一键的数据
        DeleteRule("fact_spread_daily", "GANGLIAN"),
        DeleteRule("fact_weekly_indicator", "GANGLIAN"),
        DeleteRule("fact_monthly_indicator", "GANGLIAN"),
    ],
    "INDUSTRY_DATA": [
        # fact_quarterly_stats 没有 source 列，改用 TRUNCATE
        DeleteRule("fact_monthly_indicator", "A1"),
        DeleteRule("fact_monthly_indicator", "NYB"),
        DeleteRule("fact_monthly_indicator", "ASSOCIATION"),
        DeleteRule("fact_monthly_indicator", "CUSTOMS"),
    ],
}


def supports_replace_tables(template_type: str) -> bool:
    return template_type in REPLACE_TRUNCATE_TABLES or template_type in REPLACE_DELETE_RULES


def get_replace_support_hint() -> str:
    return "当前所有模板均支持覆盖导入。"


def apply_replace_strategy(engine: Engine, template_type: str) -> ReplaceSummary:
    """
    统一执行覆盖策略，返回执行摘要。
    支持同一模板同时 TRUNCATE 部分表 + 按 source DELETE 其他表。
    调用方需先用 supports_replace_tables 校验。
    """
    truncated: list[str] = []
    deleted: dict[str, int] = {}

    # 阶段一：TRUNCATE 无 source 列的独占表
    tables = REPLACE_TRUNCATE_TABLES.get(template_type, [])
    if tables:
        with engine.connect() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in tables:
                conn.execute(text(f"TRUNCATE TABLE `{table}`"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
        truncated = list(tables)

    # 阶段二：按 source 精准删除共享表中本模板的数据
    rules = REPLACE_DELETE_RULES.get(template_type, [])
    if rules:
        with engine.connect() as conn:
            for rule in rules:
                sql = f"DELETE FROM `{rule.table}` WHERE source = :src"
                params: dict[str, Any] = {"src": rule.source}
                if rule.extra_where_sql:
                    sql += f" AND ({rule.extra_where_sql})"
                res = conn.execute(text(sql), params)
                deleted[rule.table] = deleted.get(rule.table, 0) + (res.rowcount or 0)
            conn.commit()

    mode = "truncate_and_delete" if truncated and deleted else (
        "truncate_tables" if truncated else "delete_by_source"
    )
    return ReplaceSummary(
        mode=mode,
        template_type=template_type,
        truncated_tables=truncated,
        deleted_rows_by_table=deleted,
    )
