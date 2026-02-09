"""
直接测试表格API的数据合并逻辑
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
from app.api.structure_analysis import (
    _get_cr20_month_on_month,
    _get_yongyi_month_on_month,
    _get_ganglian_month_on_month,
    _get_ministry_agriculture_month_on_month,
    _get_slaughter_month_on_month
)
from datetime import datetime

def test_data_merge():
    """测试数据合并逻辑"""
    print("=" * 80)
    print("测试数据合并逻辑")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 获取所有数据源的数据
        print("\n1. 获取各数据源数据:")
        cr20_data = _get_cr20_month_on_month(db)
        print(f"  CR20: {len(cr20_data)}条")
        if cr20_data:
            print(f"    示例: {cr20_data[0]}")
        
        yongyi_data = _get_yongyi_month_on_month(db)
        print(f"  涌益: {len(yongyi_data)}条")
        if yongyi_data:
            print(f"    示例: {yongyi_data[0]}")
        
        ganglian_data = _get_ganglian_month_on_month(db, "全国")
        print(f"  钢联: {len(ganglian_data)}条")
        if ganglian_data:
            print(f"    示例: {ganglian_data[0]}")
        
        ministry_scale_data = _get_ministry_agriculture_month_on_month(db, "规模场")
        print(f"  农业部规模场: {len(ministry_scale_data)}条")
        if ministry_scale_data:
            print(f"    示例: {ministry_scale_data[0]}")
        
        ministry_scattered_data = _get_ministry_agriculture_month_on_month(db, "散户")
        print(f"  农业部散户: {len(ministry_scattered_data)}条")
        if ministry_scattered_data:
            print(f"    示例: {ministry_scattered_data[0]}")
        
        slaughter_data = _get_slaughter_month_on_month(db)
        print(f"  定点屠宰: {len(slaughter_data)}条")
        if slaughter_data:
            print(f"    示例: {slaughter_data[0]}")
        
        # 模拟数据合并逻辑
        print("\n2. 模拟数据合并:")
        def date_to_month(date_str: str) -> str:
            """将日期字符串转换为月份字符串 YYYY-MM"""
            try:
                date_obj = datetime.strptime(date_str.split('T')[0], '%Y-%m-%d').date()
                return date_obj.strftime('%Y-%m')
            except:
                return date_str[:7] if len(date_str) >= 7 else date_str
        
        data_map = {}
        
        for item in cr20_data:
            month = date_to_month(item.date)
            if month not in data_map:
                data_map[month] = {}
            data_map[month]['cr20'] = item.value
        
        for item in yongyi_data:
            month = date_to_month(item.date)
            if month not in data_map:
                data_map[month] = {}
            data_map[month]['yongyi'] = item.value
        
        for item in ganglian_data:
            month = date_to_month(item.date)
            if month not in data_map:
                data_map[month] = {}
            data_map[month]['ganglian'] = item.value
        
        for item in ministry_scale_data:
            month = date_to_month(item.date)
            if month not in data_map:
                data_map[month] = {}
            data_map[month]['ministry_scale'] = item.value
        
        for item in ministry_scattered_data:
            month = date_to_month(item.date)
            if month not in data_map:
                data_map[month] = {}
            data_map[month]['ministry_scattered'] = item.value
        
        for item in slaughter_data:
            month = date_to_month(item.date)
            if month not in data_map:
                data_map[month] = {}
            data_map[month]['slaughter'] = item.value
        
        print(f"\n合并后的月份数: {len(data_map)}")
        
        # 显示前10个月的数据
        print("\n前10个月的数据:")
        sorted_months = sorted(data_map.keys())
        for month in sorted_months[:10]:
            row_data = data_map[month]
            print(f"\n  {month}:")
            print(f"    CR20: {row_data.get('cr20')}")
            print(f"    涌益: {row_data.get('yongyi')}")
            print(f"    钢联: {row_data.get('ganglian')}")
            print(f"    农业部规模场: {row_data.get('ministry_scale')}")
            print(f"    农业部散户: {row_data.get('ministry_scattered')}")
            print(f"    定点屠宰: {row_data.get('slaughter')}")
        
        # 统计有数据的列
        print("\n\n数据统计:")
        cr20_count = sum(1 for month in sorted_months if data_map[month].get('cr20') is not None)
        yongyi_count = sum(1 for month in sorted_months if data_map[month].get('yongyi') is not None)
        ganglian_count = sum(1 for month in sorted_months if data_map[month].get('ganglian') is not None)
        ministry_scale_count = sum(1 for month in sorted_months if data_map[month].get('ministry_scale') is not None)
        ministry_scattered_count = sum(1 for month in sorted_months if data_map[month].get('ministry_scattered') is not None)
        slaughter_count = sum(1 for month in sorted_months if data_map[month].get('slaughter') is not None)
        
        print(f"  CR20: {cr20_count}/{len(sorted_months)}")
        print(f"  涌益: {yongyi_count}/{len(sorted_months)}")
        print(f"  钢联: {ganglian_count}/{len(sorted_months)}")
        print(f"  农业部规模场: {ministry_scale_count}/{len(sorted_months)}")
        print(f"  农业部散户: {ministry_scattered_count}/{len(sorted_months)}")
        print(f"  定点屠宰: {slaughter_count}/{len(sorted_months)}")
    
    finally:
        db.close()

if __name__ == "__main__":
    test_data_merge()
