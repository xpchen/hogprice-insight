"""
测试E2 API
"""
# -*- coding: utf-8 -*-
import sys
import io
import asyncio
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal
from app.api.multi_source import get_multi_source_data

async def test_api():
    """测试API"""
    db = SessionLocal()
    try:
        result = await get_multi_source_data(months=10, db=db)
        
        print("=" * 80)
        print("E2 API测试结果")
        print("=" * 80)
        print(f"\n数据点数: {len(result.data)}")
        print(f"最新月份: {result.latest_month}")
        
        if result.data:
            print(f"\n前5条数据:")
            for point in result.data[:5]:
                print(f"\n  {point.month}:")
                if point.breeding_inventory_yongyi:
                    print(f"    能繁母猪存栏环比-涌益: {point.breeding_inventory_yongyi}")
                if point.breeding_inventory_nyb:
                    print(f"    能繁母猪存栏环比-NYB: {point.breeding_inventory_nyb}")
                if point.breeding_feed_association:
                    print(f"    能繁母猪饲料环比-协会: {point.breeding_feed_association}")
                if point.piglet_inventory_yongyi:
                    print(f"    新生仔猪存栏环比-涌益: {point.piglet_inventory_yongyi}")
                if point.piglet_feed_association:
                    print(f"    仔猪饲料环比-协会: {point.piglet_feed_association}")
                if point.hog_inventory_yongyi:
                    print(f"    生猪存栏环比-涌益: {point.hog_inventory_yongyi}")
                if point.hog_feed_association:
                    print(f"    育肥猪饲料环比-协会: {point.hog_feed_association}")
        else:
            print("\n没有数据")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_api())
