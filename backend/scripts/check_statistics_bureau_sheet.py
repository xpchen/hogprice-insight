"""
检查"03.统计局季度数据"sheet是否已导入到数据库
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
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable

def check_sheet():
    """检查sheet是否存在"""
    db: Session = SessionLocal()
    try:
        sheet = db.query(RawSheet).filter(
            RawSheet.sheet_name == "03.统计局季度数据"
        ).first()
        
        if sheet:
            print(f"✓ 找到'03.统计局季度数据'sheet")
            print(f"  Sheet ID: {sheet.id}")
            print(f"  文件ID: {sheet.raw_file_id}")
            print(f"  文件名: {sheet.raw_file.filename if sheet.raw_file else 'N/A'}")
            
            raw_table = db.query(RawTable).filter(
                RawTable.raw_sheet_id == sheet.id
            ).first()
            
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"  ✓ 有数据表")
                print(f"  数据行数: {len(table_data)}")
                
                # 显示前5行数据
                print(f"\n  前5行数据:")
                for row_idx, row in enumerate(table_data[:5], 1):
                    print(f"    行{row_idx} (前10列): {row[:10]}")
                
                # 检查表头
                if len(table_data) > 0:
                    print(f"\n  第1行（表头）:")
                    header_row = table_data[0]
                    for col_idx, cell in enumerate(header_row[:30], 1):
                        if cell:
                            col_letter = chr(64 + col_idx) if col_idx <= 26 else f"列{col_idx}"
                            print(f"    {col_letter}列 ({col_idx}): {cell}")
                
                # 检查第2行（子表头）
                if len(table_data) > 1:
                    print(f"\n  第2行（子表头）:")
                    sub_header_row = table_data[1]
                    for col_idx, cell in enumerate(sub_header_row[:30], 1):
                        if cell:
                            col_letter = chr(64 + col_idx) if col_idx <= 26 else f"列{col_idx}"
                            print(f"    {col_letter}列 ({col_idx}): {cell}")
                
                # 检查第3行数据
                if len(table_data) > 2:
                    print(f"\n  第3行数据（前15列）:")
                    data_row = table_data[2]
                    for col_idx, cell in enumerate(data_row[:15], 1):
                        col_letter = chr(64 + col_idx) if col_idx <= 26 else f"列{col_idx}"
                        print(f"    {col_letter}列 ({col_idx}): {cell}")
            else:
                print(f"  ✗ 没有数据表")
        else:
            print(f"✗ 未找到'03.统计局季度数据'sheet")
            print(f"\n需要运行导入脚本:")
            print(f"  python scripts/import_industry_data.py")
    
    finally:
        db.close()

if __name__ == "__main__":
    check_sheet()
