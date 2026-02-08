"""
检查D3. 销售计划功能所需的数据
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from app.models.raw_table import RawTable
from datetime import date

def check_data():
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("检查D3. 销售计划功能所需的数据")
        print("=" * 80)
        
        # 1. 检查集团企业汇总数据（全国CR20、全国CR5、广东、四川、贵州）
        print("\n1. 检查集团企业汇总数据")
        print("-" * 80)
        
        enterprise_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总"
        ).all()
        
        print(f"找到 {len(enterprise_metrics)} 个指标")
        for m in enterprise_metrics[:5]:
            metric_key = m.parse_json.get('metric_key') if m.parse_json else None
            print(f"  - {m.metric_name} ({metric_key})")
        
        if enterprise_metrics:
            metric_ids = [m.id for m in enterprise_metrics]
            # 检查各区域的数据
            regions = ['全国CR20', '全国CR5', '广东', '四川', '贵州']
            for region in regions:
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id.in_(metric_ids),
                    func.json_unquote(
                        func.json_extract(FactObservation.tags_json, '$.region')
                    ) == region
                ).count()
                print(f"  {region}: {count} 条数据")
        
        # 2. 检查涌益月度计划出栏量数据
        print("\n2. 检查涌益月度计划出栏量数据")
        print("-" * 80)
        
        yongyi_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "月度计划出栏量"
        ).all()
        
        if yongyi_metrics:
            print(f"找到 {len(yongyi_metrics)} 个指标")
            for m in yongyi_metrics[:5]:
                metric_key = m.parse_json.get('metric_key') if m.parse_json else None
                print(f"  - {m.metric_name} ({metric_key})")
        else:
            print("  ⚠️ 未找到指标，检查raw_table")
            raw_tables = db.query(RawTable).filter(
                RawTable.sheet_name == "月度计划出栏量"
            ).limit(5).all()
            print(f"  找到 {len(raw_tables)} 条raw_table记录")
        
        # 3. 检查钢联月度数据
        print("\n3. 检查钢联月度数据")
        print("-" * 80)
        
        ganglian_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "月度数据"
        ).all()
        
        if ganglian_metrics:
            print(f"找到 {len(ganglian_metrics)} 个指标")
            for m in ganglian_metrics[:5]:
                metric_key = m.parse_json.get('metric_key') if m.parse_json else None
                print(f"  - {m.metric_name} ({metric_key})")
        else:
            print("  ⚠️ 未找到指标，检查raw_table")
            raw_tables = db.query(RawTable).filter(
                RawTable.sheet_name == "月度数据"
            ).limit(5).all()
            print(f"  找到 {len(raw_tables)} 条raw_table记录")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
