"""
检查各数据源的时间范围
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
from app.api.structure_analysis import (
    _get_cr20_month_on_month,
    _get_yongyi_month_on_month,
    _get_ganglian_month_on_month,
    _get_ministry_agriculture_month_on_month,
    _get_slaughter_month_on_month
)

def check_time_range():
    """检查各数据源的时间范围"""
    print("=" * 80)
    print("检查各数据源的时间范围")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # CR20
        cr20_data = _get_cr20_month_on_month(db)
        if cr20_data:
            print(f"\nCR20: {len(cr20_data)}条")
            print(f"  最早: {cr20_data[0].date}")
            print(f"  最晚: {cr20_data[-1].date}")
            print(f"  最新5条:")
            for item in cr20_data[-5:]:
                print(f"    {item.date}: {item.value}")
        
        # 农业部规模场
        ministry_scale_data = _get_ministry_agriculture_month_on_month(db, "规模场")
        if ministry_scale_data:
            print(f"\n农业部规模场: {len(ministry_scale_data)}条")
            print(f"  最早: {ministry_scale_data[0].date}")
            print(f"  最晚: {ministry_scale_data[-1].date}")
            print(f"  最新5条:")
            for item in ministry_scale_data[-5:]:
                print(f"    {item.date}: {item.value}")
        
        # 农业部散户
        ministry_scattered_data = _get_ministry_agriculture_month_on_month(db, "散户")
        if ministry_scattered_data:
            print(f"\n农业部散户: {len(ministry_scattered_data)}条")
            print(f"  最早: {ministry_scattered_data[0].date}")
            print(f"  最晚: {ministry_scattered_data[-1].date}")
            print(f"  最新5条:")
            for item in ministry_scattered_data[-5:]:
                print(f"    {item.date}: {item.value}")
        
        # 定点屠宰
        slaughter_data = _get_slaughter_month_on_month(db)
        if slaughter_data:
            print(f"\n定点屠宰: {len(slaughter_data)}条")
            print(f"  最早: {slaughter_data[0].date}")
            print(f"  最晚: {slaughter_data[-1].date}")
            print(f"  最新5条:")
            for item in slaughter_data[-5:]:
                print(f"    {item.date}: {item.value}")
    
    finally:
        db.close()

if __name__ == "__main__":
    check_time_range()
