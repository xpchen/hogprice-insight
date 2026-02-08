"""
检查涌益和钢联的月度数据
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
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable

def check_data():
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("检查涌益和钢联的月度数据")
        print("=" * 80)
        
        # 1. 检查涌益月度计划出栏量
        print("\n1. 检查涌益月度计划出栏量数据")
        print("-" * 80)
        
        # 检查fact_observation
        yongyi_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "月度计划出栏量"
        ).all()
        
        if yongyi_metrics:
            print(f"找到 {len(yongyi_metrics)} 个指标（已导入到fact_observation）")
            for m in yongyi_metrics:
                metric_key = m.parse_json.get('metric_key') if m.parse_json else None
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == m.id
                ).count()
                print(f"  - {m.metric_name} ({metric_key}): {count} 条")
        else:
            print("  ⚠️ 未找到指标，检查raw_table")
            # 检查raw_sheet
            raw_sheets = db.query(RawSheet).filter(
                RawSheet.sheet_name == "月度计划出栏量"
            ).limit(5).all()
            
            if raw_sheets:
                print(f"  找到 {len(raw_sheets)} 个raw_sheet记录")
                for sheet in raw_sheets:
                    raw_table = db.query(RawTable).filter(
                        RawTable.raw_sheet_id == sheet.id
                    ).first()
                    if raw_table:
                        table_json = raw_table.table_json
                        if isinstance(table_json, list) and len(table_json) > 0:
                            print(f"    Sheet ID: {sheet.id}, 行数: {len(table_json)}, 列数: {len(table_json[0]) if table_json[0] else 0}")
                            # 显示前几行数据
                            print(f"    前3行数据:")
                            for i, row in enumerate(table_json[:3]):
                                print(f"      行{i}: {row[:20] if len(row) > 20 else row}")
            else:
                print("  ❌ 未找到raw_sheet记录")
        
        # 2. 检查钢联月度数据
        print("\n2. 检查钢联月度数据")
        print("-" * 80)
        
        ganglian_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "月度数据"
        ).all()
        
        if ganglian_metrics:
            print(f"找到 {len(ganglian_metrics)} 个指标（已导入到fact_observation）")
            for m in ganglian_metrics:
                metric_key = m.parse_json.get('metric_key') if m.parse_json else None
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == m.id
                ).count()
                print(f"  - {m.metric_name} ({metric_key}): {count} 条")
        else:
            print("  ⚠️ 未找到指标，检查raw_table")
            raw_sheets = db.query(RawSheet).filter(
                RawSheet.sheet_name == "月度数据"
            ).limit(5).all()
            
            if raw_sheets:
                print(f"  找到 {len(raw_sheets)} 个raw_sheet记录")
                for sheet in raw_sheets:
                    raw_table = db.query(RawTable).filter(
                        RawTable.raw_sheet_id == sheet.id
                    ).first()
                    if raw_table:
                        table_json = raw_table.table_json
                        if isinstance(table_json, list) and len(table_json) > 0:
                            print(f"    Sheet ID: {sheet.id}, 行数: {len(table_json)}, 列数: {len(table_json[0]) if table_json[0] else 0}")
                            # 显示前几行数据
                            print(f"    前3行数据:")
                            for i, row in enumerate(table_json[:3]):
                                print(f"      行{i}: {row[:15] if len(row) > 15 else row}")
            else:
                print("  ❌ 未找到raw_sheet记录")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
