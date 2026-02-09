"""
测试表格API接口的返回数据
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path
import json

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.api.structure_analysis import get_structure_analysis_table
import asyncio

async def test_api():
    """测试API接口"""
    print("=" * 80)
    print("测试结构分析表格API接口")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        response = await get_structure_analysis_table(db)
        
        print(f"\n返回数据条数: {len(response.data)}")
        print(f"最新月份: {response.latest_month}")
        
        if response.data:
            # 显示最新10条数据
            print("\n最新10条数据:")
            for i, row in enumerate(response.data[-10:]):
                print(f"\n第{len(response.data)-9+i}条 ({row.month}):")
                print(f"  CR20: {row.cr20}")
                print(f"  涌益: {row.yongyi}")
                print(f"  钢联: {row.ganglian}")
                print(f"  农业部规模场: {row.ministry_scale}")
                print(f"  农业部散户: {row.ministry_scattered}")
                print(f"  定点屠宰: {row.slaughter}")
            
            # 统计有数据的列（只统计最新20条）
            print("\n\n最新20条数据统计:")
            recent_data = response.data[-20:]
            cr20_count = sum(1 for row in recent_data if row.cr20 is not None)
            yongyi_count = sum(1 for row in recent_data if row.yongyi is not None)
            ganglian_count = sum(1 for row in recent_data if row.ganglian is not None)
            ministry_scale_count = sum(1 for row in recent_data if row.ministry_scale is not None)
            ministry_scattered_count = sum(1 for row in recent_data if row.ministry_scattered is not None)
            slaughter_count = sum(1 for row in recent_data if row.slaughter is not None)
            
            print(f"  CR20: {cr20_count}/20")
            print(f"  涌益: {yongyi_count}/20")
            print(f"  钢联: {ganglian_count}/20")
            print(f"  农业部规模场: {ministry_scale_count}/20")
            print(f"  农业部散户: {ministry_scattered_count}/20")
            print(f"  定点屠宰: {slaughter_count}/20")
            
            # 检查是否有2025年的数据
            print("\n\n2025年的数据:")
            data_2025 = [row for row in response.data if row.month.startswith('2025')]
            print(f"  2025年数据条数: {len(data_2025)}")
            if data_2025:
                print(f"  前5条:")
                for row in data_2025[:5]:
                    print(f"    {row.month}: CR20={row.cr20}, 规模场={row.ministry_scale}, 散户={row.ministry_scattered}, 屠宰={row.slaughter}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_api())
