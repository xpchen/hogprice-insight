"""
详细测试E2 API数据提取
"""
# -*- coding: utf-8 -*-
import sys
import io
import asyncio
from pathlib import Path
from collections import Counter

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.core.database import SessionLocal
from app.api.multi_source import get_multi_source_data

async def test_api():
    """测试API"""
    db = SessionLocal()
    try:
        result = await get_multi_source_data(months=999, db=db)
        
        print("=" * 80)
        print("E2 API详细测试结果")
        print("=" * 80)
        print(f"\n总数据点数: {len(result.data)}")
        print(f"最新月份: {result.latest_month}")
        
        # 统计有数据的字段
        field_counts = Counter()
        for point in result.data:
            for field_name, field_value in point.dict().items():
                if field_name != 'month' and field_value is not None:
                    field_counts[field_name] += 1
        
        print(f"\n各字段有数据的月份数:")
        for field, count in sorted(field_counts.items(), key=lambda x: -x[1]):
            print(f"  {field}: {count}个月")
        
        # 显示最近10个月的数据
        print(f"\n最近10个月的数据:")
        for point in result.data[-10:]:
            print(f"\n  {point.month}:")
            has_data = False
            if point.breeding_inventory_yongyi is not None:
                print(f"    能繁母猪存栏环比-涌益: {point.breeding_inventory_yongyi}%")
                has_data = True
            if point.breeding_inventory_ganglian_nation is not None:
                print(f"    能繁母猪存栏环比-钢联-全国: {point.breeding_inventory_ganglian_nation}%")
                has_data = True
            if point.breeding_inventory_nyb is not None:
                print(f"    能繁母猪存栏环比-NYB: {point.breeding_inventory_nyb}%")
                has_data = True
            if point.breeding_feed_association is not None:
                print(f"    能繁母猪饲料环比-协会: {point.breeding_feed_association}%")
                has_data = True
            if point.breeding_feed_ganglian is not None:
                print(f"    能繁母猪饲料环比-钢联: {point.breeding_feed_ganglian}%")
                has_data = True
            if point.piglet_inventory_yongyi is not None:
                print(f"    新生仔猪存栏环比-涌益: {point.piglet_inventory_yongyi}%")
                has_data = True
            if point.piglet_inventory_ganglian_nation is not None:
                print(f"    新生仔猪存栏环比-钢联-全国: {point.piglet_inventory_ganglian_nation}%")
                has_data = True
            if point.piglet_inventory_nyb is not None:
                print(f"    新生仔猪存栏环比-NYB: {point.piglet_inventory_nyb}%")
                has_data = True
            if point.piglet_feed_association is not None:
                print(f"    仔猪饲料环比-协会: {point.piglet_feed_association}%")
                has_data = True
            if point.piglet_feed_ganglian is not None:
                print(f"    仔猪饲料环比-钢联: {point.piglet_feed_ganglian}%")
                has_data = True
            if point.hog_inventory_yongyi is not None:
                print(f"    生猪存栏环比-涌益: {point.hog_inventory_yongyi}%")
                has_data = True
            if point.hog_inventory_ganglian_nation is not None:
                print(f"    生猪存栏环比-钢联-全国: {point.hog_inventory_ganglian_nation}%")
                has_data = True
            if point.hog_inventory_nyb is not None:
                print(f"    生猪存栏环比-NYB: {point.hog_inventory_nyb}%")
                has_data = True
            if point.hog_feed_association is not None:
                print(f"    育肥猪饲料环比-协会: {point.hog_feed_association}%")
                has_data = True
            if point.hog_feed_ganglian is not None:
                print(f"    育肥猪饲料环比-钢联: {point.hog_feed_ganglian}%")
                has_data = True
            if not has_data:
                print(f"    (无数据)")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_api())
