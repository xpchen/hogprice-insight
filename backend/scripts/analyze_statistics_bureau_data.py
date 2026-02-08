"""
分析E4. 统计局数据汇总数据源
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
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

def analyze_data_sources():
    """分析数据源"""
    print("=" * 80)
    print("分析E4. 统计局数据汇总数据源")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 1. 查找"03.统计局季度数据"sheet
        print("\n1. 查找'03.统计局季度数据'sheet:")
        sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name.like("%统计局%")
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
                
                # 检查B列到Y列（索引1到24）
                if len(table_data) > 0:
                    print(f"\n    前5行数据（检查B-Y列）:")
                    for idx, row in enumerate(table_data[:5]):
                        b_to_y = row[1:25] if len(row) > 1 else []
                        print(f"      行{idx+1}: {b_to_y[:10]}...")
                    
                    # 检查J列（季度出栏量，索引9）和P列（定点屠宰量，索引15）
                    if len(table_data) > 1:
                        headers = table_data[0] if len(table_data) > 0 else []
                        print(f"\n    表头（B-Y列）:")
                        for col_idx in range(1, min(25, len(headers))):
                            col_letter = chr(64 + col_idx)  # A=65, B=66, etc.
                            print(f"      {col_letter}列（索引{col_idx}）: {headers[col_idx] if col_idx < len(headers) else None}")
        else:
            print("  ✗ 未找到'统计局'相关sheet")
        
        # 2. 查找"猪肉进口"sheet（钢联模板）
        print("\n\n2. 查找'猪肉进口'sheet（钢联模板）:")
        sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "猪肉进口"
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
                
                if len(table_data) > 0:
                    print(f"\n    前5行数据:")
                    for idx, row in enumerate(table_data[:5]):
                        print(f"      行{idx+1}: {row[:15]}")
                    
                    # 分析列结构，找出国家列
                    if len(table_data) > 0:
                        headers = table_data[0] if len(table_data) > 0 else []
                        print(f"\n    表头分析（查找国家列）:")
                        for col_idx, header in enumerate(headers[:20]):
                            if header and isinstance(header, str):
                                print(f"      列{col_idx}: {header}")
        else:
            print("  ✗ 未找到'猪肉进口'sheet")
        
        # 3. 查找是否有其他统计局相关数据
        print("\n\n3. 查找所有包含'统计局'的sheet:")
        sheets = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name.like("%统计局%")
        ).all()
        
        print(f"  找到 {len(sheets)} 个相关sheet")
        for s in sheets:
            print(f"    - {s.sheet_name} (文件: {s.raw_file.filename if s.raw_file else 'N/A'})")
        
    finally:
        db.close()

if __name__ == "__main__":
    analyze_data_sources()
