"""
详细检查A1供给预测sheet的AG列（定点屠宰）和CR20相关列
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
from app.models.raw_file import RawFile

def _get_raw_table_data(db: Session, sheet_name: str, filename_pattern: str = None):
    """获取raw_table数据"""
    query = db.query(RawSheet).join(RawFile)
    
    if filename_pattern:
        query = query.filter(RawFile.filename.like(f'%{filename_pattern}%'))
    
    sheet = query.filter(RawSheet.sheet_name == sheet_name).first()
    
    if not sheet:
        return None
    
    raw_table = db.query(RawTable).filter(
        RawTable.raw_sheet_id == sheet.id
    ).first()
    
    if not raw_table:
        return None
    
    table_data = raw_table.table_json
    if isinstance(table_data, str):
        table_data = json.loads(table_data)
    
    return table_data

def check_a1_detailed():
    """详细检查A1供给预测sheet"""
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("详细检查A1供给预测sheet（AG列定点屠宰和CR20相关列）")
        print("=" * 80)
        
        a1_data = _get_raw_table_data(db, "A1供给预测", "2、【生猪产业数据】")
        
        if not a1_data:
            print("未找到A1供给预测数据")
            return
        
        print(f"\n找到A1供给预测数据，共{len(a1_data)}行")
        
        # 查看AG列（索引32）定点屠宰的表头结构
        print("\n\n查看AG列（索引32）定点屠宰的表头结构:")
        if len(a1_data) > 1:
            # 查看前3行的AG列及其周围列
            for i in range(min(3, len(a1_data))):
                row = a1_data[i]
                print(f"\n第{i+1}行（索引{i}）:")
                # 查看AG列及其前后5列
                for j in range(max(0, 32-5), min(len(row), 32+10)):
                    cell = row[j] if j < len(row) else None
                    if cell is not None and cell != "":
                        col_letter = chr(ord('A') + j) if j < 26 else f"A{chr(ord('A') + j - 26)}"
                        print(f"  {col_letter}列（索引{j}）: {cell}")
        
        # 查看AG列的数据示例（前20行）
        print("\n\nAG列（索引32）定点屠宰数据示例（前20行）:")
        for i in range(2, min(22, len(a1_data))):
            row = a1_data[i]
            if len(row) > 32:
                date_val = row[1] if len(row) > 1 else None
                ag_val = row[32]
                print(f"  行{i+1}: 日期={date_val}, AG列={ag_val}")
        
        # 查找CR20相关的列
        print("\n\n查找CR20相关的列:")
        for i in range(min(5, len(a1_data))):
            row = a1_data[i]
            for j, cell in enumerate(row):
                if cell and isinstance(cell, str):
                    if 'CR20' in cell or 'CR' in cell:
                        col_letter = chr(ord('A') + j) if j < 26 else f"A{chr(ord('A') + j - 26)}"
                        print(f"  第{i+1}行，{col_letter}列（索引{j}）: {cell}")
    
    finally:
        db.close()

if __name__ == "__main__":
    check_a1_detailed()
