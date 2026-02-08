"""
调试涌益raw_table数据格式
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

def debug_raw_table():
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("调试涌益raw_table数据格式")
        print("=" * 80)
        
        # 查找最新的raw_sheet
        raw_sheet = db.query(RawSheet).filter(
            RawSheet.sheet_name == "月度计划出栏量"
        ).order_by(RawSheet.created_at.desc()).first()
        
        if not raw_sheet:
            print("未找到raw_sheet")
            return
        
        print(f"找到raw_sheet: ID={raw_sheet.id}, 创建时间={raw_sheet.created_at}")
        
        # 获取raw_table数据
        raw_table = db.query(RawTable).filter(
            RawTable.raw_sheet_id == raw_sheet.id
        ).first()
        
        if not raw_table:
            print("未找到raw_table")
            return
        
        table_json = raw_table.table_json
        print(f"\ntable_json类型: {type(table_json)}")
        print(f"table_json长度: {len(table_json) if isinstance(table_json, list) else 'N/A'}")
        
        if isinstance(table_json, list) and len(table_json) > 0:
            print(f"\n第一个元素类型: {type(table_json[0])}")
            print(f"第一个元素: {table_json[0]}")
            
            if isinstance(table_json[0], dict):
                print("\n这是稀疏格式")
                # 找到最大行和列
                max_row = max([item.get('row', 0) for item in table_json if isinstance(item, dict)])
                max_col = max([item.get('col', 0) for item in table_json if isinstance(item, dict)])
                
                print(f"最大行: {max_row}, 最大列: {max_col}")
                
                # 创建二维数组
                rows = [[None] * (max_col + 1) for _ in range(max_row + 1)]
                for item in table_json:
                    if isinstance(item, dict):
                        row_idx = item.get('row', 0) - 1  # row从1开始
                        col_idx = item.get('col', 0) - 1  # col从1开始
                        if 0 <= row_idx < len(rows) and 0 <= col_idx < len(rows[0]):
                            rows[row_idx][col_idx] = item.get('value')
                
                print(f"\n转换后的二维数组形状: {len(rows)} x {len(rows[0]) if rows else 0}")
                print(f"\n前3行数据（显示Q列和R列，索引16和17）:")
                for i in range(min(3, len(rows))):
                    row = rows[i]
                    q_val = row[16] if len(row) > 16 else None
                    r_val = row[17] if len(row) > 17 else None
                    print(f"  行{i}: Q列={q_val}, R列={r_val}")
                
                # 检查数据行（从第3行开始，索引2）
                print(f"\n数据行（从索引2开始）:")
                for i in range(2, min(10, len(rows))):
                    row = rows[i]
                    date_val = row[0] if len(row) > 0 else None
                    q_val = row[16] if len(row) > 16 else None
                    r_val = row[17] if len(row) > 17 else None
                    print(f"  行{i}: 日期={date_val}, Q列={q_val}, R列={r_val}")
            elif isinstance(table_json[0], list):
                print("\n这是二维数组格式")
                rows = table_json
                print(f"二维数组形状: {len(rows)} x {len(rows[0]) if rows else 0}")
                print(f"\n前3行数据（显示Q列和R列，索引16和17）:")
                for i in range(min(3, len(rows))):
                    row = rows[i]
                    q_val = row[16] if len(row) > 16 else None
                    r_val = row[17] if len(row) > 17 else None
                    print(f"  行{i}: Q列={q_val}, R列={r_val}")
                
                # 检查数据行（从第3行开始，索引2）
                print(f"\n数据行（从索引2开始）:")
                for i in range(2, min(10, len(rows))):
                    row = rows[i]
                    date_val = row[0] if len(row) > 0 else None
                    q_val = row[16] if len(row) > 16 else None
                    r_val = row[17] if len(row) > 17 else None
                    print(f"  行{i}: 日期={date_val}, Q列={q_val}, R列={r_val}")
        
    finally:
        db.close()

if __name__ == "__main__":
    debug_raw_table()
