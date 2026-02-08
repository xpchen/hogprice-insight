"""
检查row=13和row=16的完整数据
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

def check_row_13_16():
    """检查row=13和row=16的完整数据"""
    print("=" * 80)
    print("检查row=13和row=16的完整数据")
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
        
        # 检查row=13和row=16
        for row_idx in [13, 16]:
            if row_idx in grid:
                row_data = grid[row_idx]
                print(f"\nrow={row_idx}的完整数据:")
                for col_idx in sorted(row_data.keys()):
                    print(f"  col={col_idx}: {row_data[col_idx]}")
                
                # 检查col=2的值
                col2_val = row_data.get(2)
                print(f"\n  col=2的值: {col2_val}")
                print(f"  是否为'实际出栏量': {col2_val == '实际出栏量'}")
                
                # 检查col=24的值（CR20）
                col24_val = row_data.get(24)
                print(f"  col=24的值（CR20）: {col24_val}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_row_13_16()
