"""
检查CR20数据中是否有2026年02月的数据
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
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile
from datetime import datetime, date

def check_cr20_feb_2026():
    """检查CR20数据中是否有2026年02月的数据"""
    print("=" * 80)
    print("检查CR20数据中是否有2026年02月的数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"集团企业全国"sheet
        enterprise_sheet = db.query(RawSheet).join(RawFile).filter(
            RawFile.filename.like('%集团企业月度数据跟踪%'),
            RawSheet.sheet_name == "集团企业全国"
        ).first()
        
        if not enterprise_sheet:
            print("\n未找到'集团企业全国'sheet")
            return
        
        # 查找raw_table
        raw_table = db.query(RawTable).filter(
            RawTable.raw_sheet_id == enterprise_sheet.id
        ).first()
        
        if not raw_table or not raw_table.table_json:
            print("\n未找到raw_table数据")
            return
        
        table_data = raw_table.table_json
        
        # 构建二维数组
        grid = {}
        for row in table_data:
            if isinstance(row, list):
                for cell in row:
                    if isinstance(cell, dict):
                        r = cell.get('row', 0)
                        c = cell.get('col', 0)
                        if r not in grid:
                            grid[r] = {}
                        grid[r][c] = cell.get('value')
        
        # 提取所有"实际出栏量"行的数据
        print(f"\n所有'实际出栏量'行的数据:")
        all_data = []
        for row_idx in sorted(grid.keys()):
            row_data = grid[row_idx]
            if row_data.get(2) == "实际出栏量":
                date_val = row_data.get(1)
                cr20_val = row_data.get(24)
                
                # 解析日期
                date_obj = None
                if isinstance(date_val, str):
                    try:
                        if 'T' in date_val:
                            date_str = date_val.split('T')[0]
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        else:
                            date_str = date_val.split()[0] if ' ' in date_val else date_val
                            try:
                                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                            except:
                                try:
                                    date_obj = datetime.strptime(date_str, '%Y/%m/%d').date()
                                except:
                                    try:
                                        parts = date_str.split('/')
                                        if len(parts) == 3:
                                            year = int(parts[0])
                                            month = int(parts[1])
                                            day = int(parts[2])
                                            date_obj = date(year, month, day)
                                    except:
                                        pass
                    except:
                        pass
                elif isinstance(date_val, date):
                    date_obj = date_val
                elif hasattr(date_val, 'date'):
                    date_obj = date_val.date()
                
                if date_obj:
                    all_data.append({
                        'row': row_idx,
                        'date': date_obj,
                        'date_raw': date_val,
                        'cr20': cr20_val
                    })
                    print(f"  行{row_idx}: 日期={date_obj} (原始={date_val}), CR20={cr20_val}")
        
        # 检查2026年02月的数据
        print(f"\n2026年02月的数据:")
        feb_2026_data = [d for d in all_data if d['date'].year == 2026 and d['date'].month == 2]
        if feb_2026_data:
            for d in feb_2026_data:
                print(f"  找到: 日期={d['date']}, CR20={d['cr20']}")
        else:
            print("  未找到2026年02月的数据")
            print(f"\n所有数据的日期范围:")
            if all_data:
                dates = [d['date'] for d in all_data]
                print(f"  最早: {min(dates)}")
                print(f"  最晚: {max(dates)}")
                print(f"\n所有日期:")
                for d in sorted(all_data, key=lambda x: x['date']):
                    print(f"    {d['date']} (原始: {d['date_raw']})")
        
        # 检查是否有2026年01月的数据（用于计算环比）
        print(f"\n2026年01月的数据:")
        jan_2026_data = [d for d in all_data if d['date'].year == 2026 and d['date'].month == 1]
        if jan_2026_data:
            for d in jan_2026_data:
                print(f"  找到: 日期={d['date']}, CR20={d['cr20']}")
        else:
            print("  未找到2026年01月的数据")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_cr20_feb_2026()
