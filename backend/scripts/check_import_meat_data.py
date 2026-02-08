"""
检查进口肉数据
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

def check_data():
    """检查数据"""
    print("=" * 80)
    print("检查进口肉和统计局数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 1. 查找"进口肉"sheet
        print("\n1. 查找'进口肉'sheet:")
        sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "进口肉"
        ).first()
        
        if sheet:
            print(f"  找到sheet: {sheet.sheet_name}")
            print(f"    文件: {sheet.raw_file.filename if sheet.raw_file else 'N/A'}")
            
            raw_table = db.query(RawTable).filter(
                RawTable.raw_sheet_id == sheet.id
            ).first()
            
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"    表格尺寸: {len(table_data)} 行 x {len(table_data[0]) if table_data else 0} 列")
                
                if len(table_data) > 3:
                    print(f"\n    第4行（表头）: {table_data[3][:15]}")
                    print(f"    第5行（数据示例）: {table_data[4][:15]}")
                    
                    # 分析列结构，找出国家列和总量列
                    if len(table_data) > 3:
                        headers = table_data[3]
                        print(f"\n    列结构分析:")
                        for col_idx, header in enumerate(headers[:25]):
                            if header:
                                col_letter = chr(65 + col_idx) if col_idx < 26 else f"列{col_idx}"
                                print(f"      {col_letter}列（索引{col_idx}）: {header}")
        else:
            print("  ✗ 未找到'进口肉'sheet")
        
        # 2. 查找所有sheet，看看是否有相关的
        print("\n\n2. 查找所有sheet（包含'进口'或'统计局'）:")
        sheets = db.query(RawSheet).join(RawFile).filter(
            or_(
                RawSheet.sheet_name.like("%进口%"),
                RawSheet.sheet_name.like("%统计局%"),
                RawSheet.sheet_name.like("%季度%")
            )
        ).all()
        
        print(f"  找到 {len(sheets)} 个相关sheet")
        for s in sheets:
            print(f"    - {s.sheet_name} (文件: {s.raw_file.filename if s.raw_file else 'N/A'})")
        
        # 3. 列出所有文件，看看是否有统计局相关文件
        print("\n\n3. 列出所有raw_file:")
        files = db.query(RawFile).limit(20).all()
        print(f"  找到 {len(files)} 个文件（显示前20个）:")
        for f in files:
            print(f"    - {f.filename}")
        
    finally:
        db.close()

if __name__ == "__main__":
    from sqlalchemy import or_
    check_data()
