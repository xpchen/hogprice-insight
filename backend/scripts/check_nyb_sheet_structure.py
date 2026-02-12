"""
检查NYB sheet的数据结构
用于E3. 供需曲线 - 图表2和图表3
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

def check_nyb_structure():
    """检查NYB sheet结构"""
    db: Session = SessionLocal()
    try:
        sheet = db.query(RawSheet).filter(
            RawSheet.sheet_name == "NYB"
        ).first()
        
        if not sheet:
            print("✗ 未找到'NYB'sheet")
            return
        
        print(f"✓ 找到'NYB'sheet")
        print(f"  Sheet ID: {sheet.id}")
        print(f"  文件ID: {sheet.raw_file_id}")
        print(f"  文件名: {sheet.raw_file.filename if sheet.raw_file else 'N/A'}")
        
        raw_table = db.query(RawTable).filter(
            RawTable.raw_sheet_id == sheet.id
        ).first()
        
        if not raw_table:
            print(f"  ✗ 没有数据表")
            return
        
        table_data = raw_table.table_json
        if isinstance(table_data, str):
            table_data = json.loads(table_data)
        
        print(f"  ✓ 有数据表")
        print(f"  数据行数: {len(table_data)}")
        
        # 显示表头
        if len(table_data) > 0:
            print(f"\n  第1行（表头）:")
            header_row = table_data[0]
            for col_idx, cell in enumerate(header_row[:20], 1):
                if cell:
                    col_letter = chr(64 + col_idx) if col_idx <= 26 else f"列{col_idx}"
                    print(f"    {col_letter}列 ({col_idx}): {cell}")
        
        # 显示第2行（可能是子表头）
        if len(table_data) > 1:
            print(f"\n  第2行（子表头）:")
            sub_header_row = table_data[1]
            for col_idx, cell in enumerate(sub_header_row[:20], 1):
                if cell:
                    col_letter = chr(64 + col_idx) if col_idx <= 26 else f"列{col_idx}"
                    print(f"    {col_letter}列 ({col_idx}): {cell}")
        
        # 显示前10行数据（重点关注B列日期、C列能繁、G列新生仔猪）
        print(f"\n  前10行数据（B列日期、C列能繁、G列新生仔猪）:")
        for row_idx, row in enumerate(table_data[:10], 1):
            b_val = row[1] if len(row) > 1 else None  # B列（索引1）
            c_val = row[2] if len(row) > 2 else None  # C列（索引2）
            g_val = row[6] if len(row) > 6 else None  # G列（索引6）
            print(f"    行{row_idx}: B列={b_val}, C列={c_val}, G列={g_val}")
        
        # 查找2020年1月的数据
        print(f"\n  查找2020年1月的数据:")
        for row_idx, row in enumerate(table_data, 1):
            b_val = row[1] if len(row) > 1 else None
            c_val = row[2] if len(row) > 2 else None
            g_val = row[6] if len(row) > 6 else None
            
            if b_val:
                b_str = str(b_val)
                if '2020-01' in b_str or '2020/01' in b_str:
                    print(f"    行{row_idx}: B列={b_val}, C列={c_val}, G列={g_val}")
                    break
    
    finally:
        db.close()

if __name__ == "__main__":
    check_nyb_structure()
