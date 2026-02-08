"""
检查集团企业月度数据跟踪中的CR20数据
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_cr20_enterprise_monthly():
    """检查集团企业月度数据跟踪中的CR20数据"""
    print("=" * 80)
    print("检查集团企业月度数据跟踪中的CR20数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"集团企业月度数据跟踪"文件中的"集团企业全国"sheet
        enterprise_sheet = db.query(RawSheet).join(RawFile).filter(
            RawFile.filename.like('%集团企业月度数据跟踪%'),
            RawSheet.sheet_name == "集团企业全国"
        ).first()
        
        if enterprise_sheet:
            print(f"\n找到sheet:")
            print(f"  - ID: {enterprise_sheet.id}")
            print(f"  - Sheet名称: {enterprise_sheet.sheet_name}")
            print(f"  - 文件: {enterprise_sheet.raw_file.filename if enterprise_sheet.raw_file else 'N/A'}")
            
            # 查找raw_table
            raw_table = db.query(RawTable).filter(
                RawTable.raw_sheet_id == enterprise_sheet.id
            ).first()
            
            if raw_table:
                print(f"\n找到raw_table数据:")
                print(f"  - ID: {raw_table.id}")
                
                if raw_table.table_json:
                    table_data = raw_table.table_json
                    print(f"  - 数据行数: {len(table_data)}")
                    
                    # 显示前10行数据
                    print(f"\n前10行数据:")
                    for i, row in enumerate(table_data[:10]):
                        print(f"    行{i}: {row}")
                    
                    # 查找B1为"实际出栏量"的行
                    print(f"\n查找B1为'实际出栏量'的行:")
                    for i, row in enumerate(table_data):
                        if isinstance(row, list) and len(row) > 1:
                            # B列是索引1
                            if row[1] == "实际出栏量":
                                print(f"  找到在第{i}行: {row}")
                                # 显示这一行的所有数据
                                print(f"    完整行数据: {row}")
                                
                                # 查找CR20列（需要找到列名包含CR20的列）
                                if i > 0 and len(table_data) > i:
                                    # 检查表头行（通常是第0行或第1行）
                                    header_row = None
                                    for h_idx in range(max(0, i-2), min(len(table_data), i+3)):
                                        if isinstance(table_data[h_idx], list):
                                            for col_idx, col_val in enumerate(table_data[h_idx]):
                                                if col_val and 'CR20' in str(col_val):
                                                    print(f"    找到CR20列在索引{col_idx}: {col_val}")
                                                    header_row = h_idx
                                                    break
                                            if header_row is not None:
                                                break
                                
                                # 显示后续几行数据，看看CR20列的数据
                                print(f"\n    后续5行数据（查看CR20列）:")
                                for j in range(i+1, min(len(table_data), i+6)):
                                    if isinstance(table_data[j], list):
                                        print(f"      行{j}: {table_data[j]}")
                                break
        else:
            print("\n未找到'集团企业全国'sheet")
            # 查找所有集团企业月度数据跟踪相关的sheet
            all_sheets = db.query(RawSheet).join(RawFile).filter(
                RawFile.filename.like('%集团企业月度数据跟踪%')
            ).all()
            print(f"\n找到 {len(all_sheets)} 个相关sheet:")
            for sheet in all_sheets:
                print(f"  - {sheet.sheet_name}")
    finally:
        db.close()

if __name__ == "__main__":
    check_cr20_enterprise_monthly()
