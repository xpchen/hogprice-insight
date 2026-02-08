"""
测试销售计划API的数据查询
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.api.sales_plan import _get_enterprise_data, _get_yongyi_data, _get_ganglian_data

def test_api():
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("测试销售计划API的数据查询")
        print("=" * 80)
        
        # 1. 测试集团企业数据
        print("\n1. 测试集团企业数据")
        print("-" * 80)
        enterprise_regions = ['全国CR20', '全国CR5', '广东', '四川', '贵州']
        enterprise_data = _get_enterprise_data(db, enterprise_regions)
        print(f"找到 {len(enterprise_data)} 条数据")
        if enterprise_data:
            print("前5条数据:")
            for item in enterprise_data[:5]:
                print(f"  {item.date}, {item.region}, 出栏: {item.actual_output}, 计划: {item.plan_output}, 环比: {item.month_on_month}, 达成率: {item.plan_completion_rate}")
        
        # 2. 测试涌益数据
        print("\n2. 测试涌益数据")
        print("-" * 80)
        yongyi_data = _get_yongyi_data(db)
        print(f"找到 {len(yongyi_data)} 条数据")
        if yongyi_data:
            print("前5条数据:")
            for item in yongyi_data[:5]:
                print(f"  {item.date}, {item.region}, 出栏: {item.actual_output}, 计划: {item.plan_output}, 环比: {item.month_on_month}, 达成率: {item.plan_completion_rate}")
        else:
            print("  ⚠️ 未找到数据")
        
        # 3. 测试钢联数据
        print("\n3. 测试钢联数据")
        print("-" * 80)
        ganglian_data = _get_ganglian_data(db)
        print(f"找到 {len(ganglian_data)} 条数据")
        if ganglian_data:
            print("前5条数据:")
            for item in ganglian_data[:5]:
                print(f"  {item.date}, {item.region}, 出栏: {item.actual_output}, 计划: {item.plan_output}, 环比: {item.month_on_month}, 达成率: {item.plan_completion_rate}")
        else:
            print("  ⚠️ 未找到数据")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_api()
