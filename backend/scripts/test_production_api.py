"""
测试规模场数据汇总API
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.api.production_indicators import _get_raw_table_data
from app.core.database import SessionLocal

def test_api():
    """测试API"""
    print("=" * 80)
    print("测试规模场数据汇总API")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        data = _get_raw_table_data(db, "月度-生产指标（2021.5.7新增）")
        print(f"\n数据行数: {len(data) if data else 0}")
        if data:
            print(f"前3行数据:")
            for idx, row in enumerate(data[:3]):
                print(f"  行{idx+1}: {row[:10]}")
    finally:
        db.close()

if __name__ == "__main__":
    test_api()
