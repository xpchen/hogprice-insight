"""
检查CR20数据和钢联月度出栏raw_table数据
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.core.database import SessionLocal
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_cr20_data():
    """检查汇总sheet中是否有CR20数据"""
    print("=" * 80)
    print("1. 检查'汇总'sheet中的CR20数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找PROVINCE_ACTUAL指标
        actual_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总",
            func.json_unquote(func.json_extract(DimMetric.parse_json, '$.metric_key')) == 'PROVINCE_ACTUAL'
        ).first()
        
        if actual_metric:
            print(f"\n找到指标: {actual_metric.metric_name} (ID: {actual_metric.id})")
            
            # 查询所有region值
            regions = db.query(
                func.json_unquote(func.json_extract(FactObservation.tags_json, '$.region')).distinct()
            ).filter(
                FactObservation.metric_id == actual_metric.id
            ).distinct().all()
            
            print(f"\n找到的region值:")
            for r in regions:
                region_val = r[0] if isinstance(r, tuple) else r
                if region_val:
                    print(f"  - {region_val}")
                    
                    # 检查是否有CR20相关的region
                    if 'CR20' in str(region_val) or '20' in str(region_val):
                        count = db.query(FactObservation).filter(
                            FactObservation.metric_id == actual_metric.id,
                            func.json_unquote(func.json_extract(FactObservation.tags_json, '$.region')) == region_val
                        ).count()
                        print(f"    CR20相关数据条数: {count}")
        else:
            print("\n未找到PROVINCE_ACTUAL指标")
    finally:
        db.close()

def check_ganglian_monthly_output_raw():
    """检查钢联月度出栏raw_table数据"""
    print("\n" + "=" * 80)
    print("2. 检查钢联'月度出栏'sheet的raw_table数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找钢联文件的raw_sheet
        ganglian_sheets = db.query(RawSheet).join(RawFile).filter(
            RawFile.filename.like('%钢联%'),
            RawSheet.sheet_name.like('%月度%出栏%')
        ).all()
        
        if ganglian_sheets:
            print(f"\n找到 {len(ganglian_sheets)} 个相关sheet:")
            for sheet in ganglian_sheets:
                file_name = sheet.raw_file.file_name if sheet.raw_file else "N/A"
                print(f"  - 文件: {file_name}, Sheet: {sheet.sheet_name}, ID: {sheet.id}")
                
                # 查找对应的raw_table
                raw_table = db.query(RawTable).filter(
                    RawTable.sheet_id == sheet.id
                ).first()
                
                if raw_table:
                    print(f"    找到raw_table数据")
                    # 检查table_json的结构
                    if raw_table.table_json:
                        if isinstance(raw_table.table_json, list) and len(raw_table.table_json) > 0:
                            print(f"    数据行数: {len(raw_table.table_json)}")
                            print(f"    前3行示例:")
                            for i, row in enumerate(raw_table.table_json[:3]):
                                print(f"      行{i}: {row}")
        else:
            print("\n未找到相关sheet，检查是否有'月度数据'sheet:")
            monthly_sheets = db.query(RawSheet).join(RawFile).filter(
                RawFile.filename.like('%钢联%'),
                RawSheet.sheet_name == "月度数据"
            ).all()
            
            if monthly_sheets:
                print(f"找到 {len(monthly_sheets)} 个'月度数据'sheet")
                for sheet in monthly_sheets:
                    file_name = sheet.raw_file.file_name if sheet.raw_file else "N/A"
                    print(f"  - 文件: {file_name}, Sheet: {sheet.sheet_name}, ID: {sheet.id}")
    finally:
        db.close()

if __name__ == "__main__":
    check_cr20_data()
    check_ganglian_monthly_output_raw()
