"""
Web 导入「覆盖」时可安全整表 TRUNCATE 的范围。

仅包含当前确认只有单一 Reader 写入的 fact 表；共表模板不得加入，避免误删其他数据源。
"""
from __future__ import annotations

from typing import List

from sqlalchemy import text
from sqlalchemy.engine import Engine

# template_type 与 ingest.TEMPLATE_MAP 键一致
REPLACEABLE_TABLES_BY_TEMPLATE: dict[str, list[str]] = {
    "ENTERPRISE_MONTHLY": ["fact_enterprise_monthly"],
    "LH_FTR": ["fact_futures_daily"],
}


def truncate_tables_for_template(engine: Engine, template_type: str) -> List[str]:
    """
    对 template_type 在白名单内的表执行 TRUNCATE。
    返回实际执行 TRUNCATE 的表名列表；若不在白名单返回空列表（调用方应提前校验）。
    """
    tables = REPLACEABLE_TABLES_BY_TEMPLATE.get(template_type)
    if not tables:
        return []
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for t in tables:
            conn.execute(text(f"TRUNCATE TABLE `{t}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()
    return list(tables)


def supports_replace_tables(template_type: str) -> bool:
    return template_type in REPLACEABLE_TABLES_BY_TEMPLATE
