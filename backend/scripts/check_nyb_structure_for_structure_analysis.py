"""
检查NYB sheet的结构，查找规模场和散户的出栏环比列
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

def check_nyb_structure():
    """检查NYB sheet结构"""
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("检查NYB sheet结构（查找规模场和散户的出栏环比列）")
        print("=" * 80)
        
        nyb_data = _get_raw_table_data(db, "NYB", "2、【生猪产业数据】")
        
        if not nyb_data:
            print("未找到NYB数据")
            return
        
        print(f"\n找到NYB数据，共{len(nyb_data)}行")
        
        # 显示前5行数据，查看表头结构
        print("\n前5行数据:")
        for i, row in enumerate(nyb_data[:5]):
            print(f"\n第{i+1}行（索引{i}）:")
            for j, cell in enumerate(row[:30]):  # 只显示前30列
                if cell is not None and cell != "":
                    col_letter = chr(ord('A') + j) if j < 26 else f"A{chr(ord('A') + j - 26)}"
                    print(f"  {col_letter}列（索引{j}）: {cell}")
        
        # 查找包含"规模场"、"散户"、"出栏"的列
        print("\n\n查找包含'规模场'、'散户'、'出栏'的列:")
        if len(nyb_data) > 1:
            header_row = nyb_data[1] if len(nyb_data) > 1 else nyb_data[0]
            for j, cell in enumerate(header_row):
                if cell and isinstance(cell, str):
                    if '规模场' in cell or '散户' in cell or '出栏' in cell:
                        col_letter = chr(ord('A') + j) if j < 26 else f"A{chr(ord('A') + j - 26)}"
                        print(f"  {col_letter}列（索引{j}）: {cell}")
        
        # 查找主表头（第1行）
        print("\n\n主表头（第1行，索引0）:")
        if len(nyb_data) > 0:
            main_header = nyb_data[0]
            for j, cell in enumerate(main_header[:30]):
                if cell and isinstance(cell, str):
                    col_letter = chr(ord('A') + j) if j < 26 else f"A{chr(ord('A') + j - 26)}"
                    print(f"  {col_letter}列（索引{j}）: {cell}")
    
    finally:
        db.close()

if __name__ == "__main__":
    check_nyb_structure()
