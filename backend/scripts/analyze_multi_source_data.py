"""
分析E2. 多渠道汇总数据源
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
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

def analyze_data_sources():
    """分析数据源"""
    print("=" * 80)
    print("分析E2. 多渠道汇总数据源")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 1. 涌益数据源
        print("\n1. 涌益数据源（涌益咨询周度数据）:")
        yongyi_sheets = [
            "月度-能繁母猪存栏（2020年2月新增）",
            "月度-小猪存栏（2020年5月新增）",
            "月度-大猪存栏（2020年5月新增）",
            "月度-猪料销量",
            "月度-淘汰母猪屠宰厂宰杀量"
        ]
        
        for sheet_name in yongyi_sheets:
            sheet = db.query(RawSheet).join(RawFile).filter(
                RawSheet.sheet_name == sheet_name
            ).first()
            
            if sheet:
                print(f"\n  ✓ {sheet_name}")
                print(f"    文件: {sheet.raw_file.filename if sheet.raw_file else 'N/A'}")
                
                # 检查是否有指标
                metrics = db.query(DimMetric).filter(
                    DimMetric.sheet_name == sheet_name
                ).limit(5).all()
                print(f"    指标数: {len(metrics)}")
                if metrics:
                    for m in metrics[:3]:
                        print(f"      - {m.metric_name} ({m.raw_header})")
            else:
                print(f"\n  ✗ {sheet_name} (未找到)")
        
        # 2. 钢联数据源
        print("\n\n2. 钢联数据源（钢联模板）:")
        ganglian_sheets = [
            "月度数据",
            "淘汰母猪屠宰"
        ]
        
        for sheet_name in ganglian_sheets:
            sheet = db.query(RawSheet).join(RawFile).filter(
                RawSheet.sheet_name == sheet_name
            ).first()
            
            if sheet:
                print(f"\n  ✓ {sheet_name}")
                print(f"    文件: {sheet.raw_file.filename if sheet.raw_file else 'N/A'}")
            else:
                print(f"\n  ✗ {sheet_name} (未找到)")
        
        # 3. 协会和NYB数据源
        print("\n\n3. 协会和NYB数据源（【生猪产业数据】）:")
        association_sheets = [
            "02.协会猪料",
            "NYB"
        ]
        
        for sheet_name in association_sheets:
            sheet = db.query(RawSheet).join(RawFile).filter(
                RawSheet.sheet_name.like(f"%{sheet_name}%")
            ).first()
            
            if sheet:
                print(f"\n  ✓ {sheet.sheet_name}")
                print(f"    文件: {sheet.raw_file.filename if sheet.raw_file else 'N/A'}")
            else:
                print(f"\n  ✗ {sheet_name} (未找到)")
        
    finally:
        db.close()

if __name__ == "__main__":
    analyze_data_sources()
