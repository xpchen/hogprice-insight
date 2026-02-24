#!/usr/bin/env python3
"""
将 quick_chart_cache.response_body 改为 MEDIUMTEXT，解决大响应写入失败 (1406 Data too long)。
可直接运行：python -m app.scripts.fix_quick_chart_cache_mediumtext（在 backend 目录下）
或：cd backend && python scripts/fix_quick_chart_cache_mediumtext.py
"""
import os
import sys

# 确保 backend 在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings


def main():
    url = getattr(settings, "DATABASE_URL", None) or os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set")
        sys.exit(1)
    if "mysql" not in url.lower() and "mariadb" not in url.lower():
        print("Skip: only MySQL/MariaDB supported")
        sys.exit(0)
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE quick_chart_cache MODIFY response_body MEDIUMTEXT NOT NULL"))
    print("OK: quick_chart_cache.response_body -> MEDIUMTEXT")


if __name__ == "__main__":
    main()
