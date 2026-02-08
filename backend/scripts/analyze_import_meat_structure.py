"""
详细分析进口肉sheet结构
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

def analyze_structure():
    """分析结构"""
    print("=" * 80)
    print("详细分析进口肉sheet结构")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        sheet = db.query(RawSheet).filter(
            RawSheet.sheet_name == "进口肉"
        ).first()
        
        if not sheet:
            print("未找到'进口肉'sheet")
            return
        
        raw_table = db.query(RawTable).filter(
            RawTable.raw_sheet_id == sheet.id
        ).first()
        
        if not raw_table:
            print("未找到raw_table")
            return
        
        table_data = raw_table.table_json
        if isinstance(table_data, str):
            table_data = json.loads(table_data)
        
        print(f"\n表格尺寸: {len(table_data)} 行 x {len(table_data[0]) if table_data else 0} 列")
        
        # 显示前10行
        print("\n前10行数据:")
        for idx, row in enumerate(table_data[:10]):
            print(f"\n行{idx}:")
            for col_idx, cell in enumerate(row[:25]):
                if cell:
                    col_letter = chr(65 + col_idx) if col_idx < 26 else f"列{col_idx}"
                    print(f"  {col_letter}列: {cell}")
        
        # 分析列结构
        print("\n\n列结构分析:")
        if len(table_data) > 3:
            # 第3行是年份行（2016年-2025年）
            year_row = table_data[2]
            print(f"\n第3行（年份行）:")
            for col_idx, cell in enumerate(year_row[:15]):
                if cell:
                    col_letter = chr(65 + col_idx) if col_idx < 26 else f"列{col_idx}"
                    print(f"  {col_letter}列: {cell}")
            
            # 第4行是表头行（日期、猪肉、猪杂碎等）
            header_row = table_data[3]
            print(f"\n第4行（表头行）:")
            for col_idx, cell in enumerate(header_row[:25]):
                if cell:
                    col_letter = chr(65 + col_idx) if col_idx < 26 else f"列{col_idx}"
                    print(f"  {col_letter}列: {cell}")
            
            # 分析数据行（从第5行开始）
            print(f"\n数据行分析（第5-15行）:")
            for row_idx in range(4, min(15, len(table_data))):
                row = table_data[row_idx]
                month = row[0] if len(row) > 0 else None
                print(f"\n  行{row_idx+1} ({month}):")
                # 显示年份数据（B-K列，索引1-10）
                for col_idx in range(1, min(11, len(row))):
                    year_col = year_row[col_idx] if col_idx < len(year_row) else None
                    value = row[col_idx] if col_idx < len(row) else None
                    if value:
                        print(f"    {year_col}: {value}")
                
                # 显示日期列（M列，索引12）
                if len(row) > 12:
                    date_val = row[12]
                    print(f"    日期（M列）: {date_val}")
                
                # 显示猪肉总量（P列，索引15）
                if len(row) > 15:
                    total_val = row[15]
                    print(f"    猪总量（P列）: {total_val}")
        
    finally:
        db.close()

if __name__ == "__main__":
    analyze_structure()
