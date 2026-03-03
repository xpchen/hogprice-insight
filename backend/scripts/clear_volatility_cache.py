# -*- coding: utf-8 -*-
"""
清除波动率接口的图表缓存。
当波动率 API 修复或数据更新后，若前端仍显示空，可运行此脚本清除旧缓存。
"""
import sys
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

from app.core.database import SessionLocal
from app.services.quick_chart_service import clear_cached_by_prefix

# 与 router prefix 一致：/api/futures，波动率路径为 /api/futures/volatility
PREFIX = "/api/futures/volatility"


def main():
    db = SessionLocal()
    try:
        n = clear_cached_by_prefix(db, PREFIX)
        print(f"已清除 {n} 条波动率缓存（前缀: {PREFIX}）")
    finally:
        db.close()


if __name__ == "__main__":
    main()
