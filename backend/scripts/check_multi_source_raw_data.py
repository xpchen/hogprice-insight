"""
检查多渠道汇总raw_table数据
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
    print("检查多渠道汇总raw_table数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 1. 检查月度-猪料销量（涌益）
        print("\n1. 月度-猪料销量（涌益）:")
        sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "月度-猪料销量"
        ).first()
        
        if sheet:
            raw_table = db.query(RawTable).filter(
                RawTable.raw_sheet_id == sheet.id
            ).first()
            
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"  表格尺寸: {len(table_data)} 行 x {len(table_data[0]) if table_data else 0} 列")
                print(f"  前5行数据:")
                for idx, row in enumerate(table_data[:5]):
                    print(f"    行{idx+1}: {row[:10]}")
                
                # 查找C列（后备母猪料）、E列（教保料）、F列（育肥猪饲料）
                if len(table_data) > 1:
                    headers = table_data[1] if len(table_data) > 1 else []
                    print(f"  表头行: {headers[:15]}")
        
        # 2. 检查月度-能繁母猪存栏（2020年2月新增）
        print("\n\n2. 月度-能繁母猪存栏（2020年2月新增）:")
        sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "月度-能繁母猪存栏（2020年2月新增）"
        ).first()
        
        if sheet:
            raw_table = db.query(RawTable).filter(
                RawTable.raw_sheet_id == sheet.id
            ).first()
            
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"  表格尺寸: {len(table_data)} 行 x {len(table_data[0]) if table_data else 0} 列")
                if len(table_data) > 3:
                    print(f"  第4行（表头）: {table_data[3][:10]}")
                    print(f"  第5行（数据示例）: {table_data[4][:10]}")
        
        # 3. 检查月度-小猪存栏（2020年5月新增）
        print("\n\n3. 月度-小猪存栏（2020年5月新增）:")
        sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "月度-小猪存栏（2020年5月新增）"
        ).first()
        
        if sheet:
            raw_table = db.query(RawTable).filter(
                RawTable.raw_sheet_id == sheet.id
            ).first()
            
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"  表格尺寸: {len(table_data)} 行 x {len(table_data[0]) if table_data else 0} 列")
                if len(table_data) > 1:
                    print(f"  第2行（表头）: {table_data[1][:10]}")
        
        # 4. 检查月度-大猪存栏（2020年5月新增）
        print("\n\n4. 月度-大猪存栏（2020年5月新增）:")
        sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "月度-大猪存栏（2020年5月新增）"
        ).first()
        
        if sheet:
            raw_table = db.query(RawTable).filter(
                RawTable.raw_sheet_id == sheet.id
            ).first()
            
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"  表格尺寸: {len(table_data)} 行 x {len(table_data[0]) if table_data else 0} 列")
                if len(table_data) > 1:
                    print(f"  第2行（表头）: {table_data[1][:10]}")
        
        # 5. 检查月度-淘汰母猪屠宰厂宰杀量
        print("\n\n5. 月度-淘汰母猪屠宰厂宰杀量:")
        sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "月度-淘汰母猪屠宰厂宰杀量"
        ).first()
        
        if sheet:
            raw_table = db.query(RawTable).filter(
                RawTable.raw_sheet_id == sheet.id
            ).first()
            
            if raw_table:
                table_data = raw_table.table_json
                if isinstance(table_data, str):
                    table_data = json.loads(table_data)
                
                print(f"  表格尺寸: {len(table_data)} 行 x {len(table_data[0]) if table_data else 0} 列")
                if len(table_data) > 1:
                    print(f"  第2行（表头）: {table_data[1][:10]}")
                    if len(table_data) > 2:
                        print(f"  第3行（数据示例）: {table_data[2][:10]}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_raw_data()
