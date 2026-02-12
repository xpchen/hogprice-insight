"""
检查"供需曲线"sheet是否已导入到数据库
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

def check_sheet():
    """检查sheet是否存在"""
    db: Session = SessionLocal()
    try:
        sheet = db.query(RawSheet).filter(
            RawSheet.sheet_name == "供需曲线"
        ).first()
        
        if sheet:
            print(f"✓ 找到'供需曲线'sheet")
            print(f"  Sheet ID: {sheet.id}")
            print(f"  文件ID: {sheet.raw_file_id}")
            print(f"  文件名: {sheet.raw_file.filename if sheet.raw_file else 'N/A'}")
            
            raw_table = db.query(RawTable).filter(
                RawTable.raw_sheet_id == sheet.id
            ).first()
            
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    import json
                    table_data = json.loads(table_data)
                
                print(f"  ✓ 有数据表")
                print(f"  数据行数: {len(table_data)}")
                
                # 检查第31行数据
                if len(table_data) > 30:
                    row_31 = table_data[30]  # 索引30是第31行
                    print(f"\n  第31行数据（前10列）:")
                    for col_idx, cell in enumerate(row_31[:10], 1):
                        if cell is not None:
                            print(f"    列{col_idx}: {cell}")
            else:
                print(f"  ✗ 没有数据表")
        else:
            print(f"✗ 未找到'供需曲线'sheet")
            print(f"\n需要运行导入脚本:")
            print(f"  python scripts/import_industry_data.py")
    
    finally:
        db.close()

if __name__ == "__main__":
    check_sheet()
