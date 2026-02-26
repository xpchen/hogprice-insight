# -*- coding: utf-8 -*-
"""
清除统计局数据汇总相关的图表缓存。
当导入新的 Excel 数据后，若表1仍显示"暂无数据"，可运行此脚本清除旧缓存。
"""
import sys
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

from app.core.database import SessionLocal
from app.services.quick_chart_service import clear_cached_by_prefix

PREFIX = "/api/v1/statistics-bureau"


def main():
    db = SessionLocal()
    try:
        n = clear_cached_by_prefix(db, PREFIX)
        print(f"Cleared {n} cache entries for {PREFIX}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
