"""
检查涌益"月度-商品猪出栏量"sheet在数据库中的情况
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

def check_yongyi_monthly_output():
    """检查涌益月度-商品猪出栏量sheet"""
    print("=" * 80)
    print("检查涌益'月度-商品猪出栏量'sheet")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"月度-商品猪出栏量"sheet
        yongyi_sheet = db.query(RawSheet).join(RawFile).filter(
            RawFile.filename.like('%涌益%'),
            RawSheet.sheet_name == "月度-商品猪出栏量"
        ).first()
        
        if yongyi_sheet:
            print(f"\n找到sheet:")
            print(f"  - ID: {yongyi_sheet.id}")
            print(f"  - Sheet名称: {yongyi_sheet.sheet_name}")
            print(f"  - 文件: {yongyi_sheet.raw_file.filename if yongyi_sheet.raw_file else 'N/A'}")
            
            # 查找raw_table
            raw_table = db.query(RawTable).filter(
                RawTable.raw_sheet_id == yongyi_sheet.id
            ).first()
            
            if raw_table:
                print(f"\n找到raw_table数据:")
                print(f"  - ID: {raw_table.id}")
                
                if raw_table.table_json:
                    table_data = raw_table.table_json
                    print(f"  - 数据行数: {len(table_data)}")
                    print(f"\n前5行数据示例:")
                    for i, row in enumerate(table_data[:5]):
                        print(f"    行{i}: {row}")
                    
                    # 分析数据结构
                    if len(table_data) > 1:
                        print(f"\n数据结构分析:")
                        print(f"  - 第0行（标题）: {table_data[0] if len(table_data) > 0 else 'N/A'}")
                        print(f"  - 第1行（表头）: {table_data[1] if len(table_data) > 1 else 'N/A'}")
                        if len(table_data) > 2:
                            print(f"  - 第2行（数据）: {table_data[2] if len(table_data) > 2 else 'N/A'}")
                            # 检查B列和C列（索引1和2）
                            if isinstance(table_data[2], list) and len(table_data[2]) > 2:
                                print(f"    B列（出栏量，索引1）: {table_data[2][1]}")
                                print(f"    C列（环比，索引2）: {table_data[2][2]}")
            else:
                print("\n未找到raw_table数据")
        else:
            print("\n未找到'月度-商品猪出栏量'sheet")
            # 查找所有涌益相关的sheet
            all_sheets = db.query(RawSheet).join(RawFile).filter(
                RawFile.filename.like('%涌益%')
            ).all()
            print(f"\n找到 {len(all_sheets)} 个涌益相关的sheet:")
            for sheet in all_sheets[:10]:  # 只显示前10个
                print(f"  - {sheet.sheet_name}")
    finally:
        db.close()

if __name__ == "__main__":
    check_yongyi_monthly_output()
