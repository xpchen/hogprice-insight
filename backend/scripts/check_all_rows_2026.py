"""
检查所有2026年的行，看看是否有"实际出栏量"
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

def check_all_rows_2026():
    """检查所有2026年的行"""
    print("=" * 80)
    print("检查所有2026年的行")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"集团企业全国"sheet
        enterprise_sheet = db.query(RawSheet).join(RawFile).filter(
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
        
        # 查找所有2026年的行
        print(f"\n所有2026年的行:")
        for row_idx in sorted(grid.keys()):
            row_data = grid[row_idx]
            date_val = row_data.get(1)  # col=1是日期
            
            if date_val and isinstance(date_val, str) and '2026' in str(date_val):
                col2_val = row_data.get(2)  # col=2是类型
                col24_val = row_data.get(24)  # col=24是CR20
                
                print(f"\n  row={row_idx}:")
                print(f"    日期: {date_val}")
                print(f"    类型(col=2): {col2_val}")
                print(f"    CR20(col=24): {col24_val}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_all_rows_2026()
