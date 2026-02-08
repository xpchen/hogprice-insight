"""
检查月度-生产指标raw_table数据
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

def check_raw_data():
    """检查raw数据"""
    print("=" * 80)
    print("检查月度-生产指标raw_table数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找sheet
        sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name.like("%生产指标%")
        ).first()
        
        if not sheet:
            print("\n未找到sheet")
            return
        
        print(f"\n找到sheet: {sheet.sheet_name}")
        print(f"文件: {sheet.raw_file.filename if sheet.raw_file else 'N/A'}")
        
        # 读取raw_table数据
        raw_table = db.query(RawTable).filter(
            RawTable.raw_sheet_id == sheet.id
        ).first()
        
        if not raw_table:
            print("\n未找到raw_table数据")
            return
        
        table_data = raw_table.table_json
        if isinstance(table_data, str):
            table_data = json.loads(table_data)
        
        print(f"\n表格尺寸: {len(table_data)} 行")
        if table_data:
            print(f"列数: {len(table_data[0]) if table_data[0] else 0}")
        
        print(f"\n前10行数据:")
        for idx, row in enumerate(table_data[:10]):
            print(f"  行{idx+1}: {row[:15]}")
        
        # 分析列结构
        print(f"\n分析列结构（F列和N列）:")
        # F列是第6列（索引5），N列是第14列（索引13）
        f_col_data = []
        n_col_data = []
        
        for row_idx, row in enumerate(table_data):
            if len(row) > 5:
                f_val = row[5] if len(row) > 5 else None  # F列（索引5）
                n_val = row[13] if len(row) > 13 else None  # N列（索引13）
                
                if row_idx < 3:
                    print(f"  行{row_idx+1}: F列={f_val}, N列={n_val}")
                
                if row_idx >= 2:  # 跳过表头（前2行）
                    date_val = row[0] if len(row) > 0 else None
                    if f_val and f_val != "":
                        f_col_data.append((row_idx+1, date_val, f_val))
                    if n_val and n_val != "":
                        n_col_data.append((row_idx+1, date_val, n_val))
        
        print(f"\nF列数据条数: {len(f_col_data)}")
        print(f"N列数据条数: {len(n_col_data)}")
        
        if f_col_data:
            print(f"\nF列前5条数据:")
            for item in f_col_data[:5]:
                print(f"  {item}")
        
        if n_col_data:
            print(f"\nN列前5条数据:")
            for item in n_col_data[:5]:
                print(f"  {item}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_raw_data()
