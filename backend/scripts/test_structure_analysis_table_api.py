"""
测试结构分析表格API接口
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

def test_table_api():
    """测试表格API"""
    print("=" * 80)
    print("测试结构分析表格API")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        response = await get_structure_analysis_table(db)
        
        print(f"\n返回数据条数: {len(response.data)}")
        print(f"最新月份: {response.latest_month}")
        
        if response.data:
            print("\n前10条数据:")
            for i, row in enumerate(response.data[:10]):
                print(f"\n第{i+1}条:")
                print(f"  月份: {row.month}")
                print(f"  CR20: {row.cr20}")
                print(f"  涌益: {row.yongyi}")
                print(f"  钢联: {row.ganglian}")
                print(f"  农业部规模场: {row.ministry_scale}")
                print(f"  农业部散户: {row.ministry_scattered}")
                print(f"  定点屠宰: {row.slaughter}")
            
            # 统计有数据的列
            print("\n\n数据统计:")
            cr20_count = sum(1 for row in response.data if row.cr20 is not None)
            yongyi_count = sum(1 for row in response.data if row.yongyi is not None)
            ganglian_count = sum(1 for row in response.data if row.ganglian is not None)
            ministry_scale_count = sum(1 for row in response.data if row.ministry_scale is not None)
            ministry_scattered_count = sum(1 for row in response.data if row.ministry_scattered is not None)
            slaughter_count = sum(1 for row in response.data if row.slaughter is not None)
            
            print(f"  CR20: {cr20_count}/{len(response.data)}")
            print(f"  涌益: {yongyi_count}/{len(response.data)}")
            print(f"  钢联: {ganglian_count}/{len(response.data)}")
            print(f"  农业部规模场: {ministry_scale_count}/{len(response.data)}")
            print(f"  农业部散户: {ministry_scattered_count}/{len(response.data)}")
            print(f"  定点屠宰: {slaughter_count}/{len(response.data)}")
    finally:
        db.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_table_api())
