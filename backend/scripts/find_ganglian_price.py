"""
查找钢联价格数据
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
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

def find_price():
    """查找价格数据"""
    print("=" * 80)
    print("查找钢联价格数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 1. 通过metric_key查找
        print("\n1. 通过metric_key查找（GL_D_PRICE_NATION）:")
        metrics = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, '$.metric_key') == 'GL_D_PRICE_NATION'
        ).all()
        
        print(f"  找到 {len(metrics)} 个指标")
        for m in metrics:
            print(f"    - ID: {m.id}, 名称: {m.metric_name}, 表头: {m.raw_header}, sheet: {m.sheet_name}")
            count = db.query(FactObservation).filter(
                FactObservation.metric_id == m.id
            ).count()
            print(f"      数据条数: {count}")
        
        # 2. 查找所有包含"价格"的指标
        print("\n\n2. 查找所有包含'价格'的指标（钢联相关）:")
        metrics = db.query(DimMetric).filter(
            DimMetric.raw_header.like('%价%'),
            DimMetric.freq == "D"
        ).limit(20).all()
        
        print(f"  找到 {len(metrics)} 个价格指标（显示前20个）:")
        for m in metrics:
            print(f"    - ID: {m.id}, 名称: {m.metric_name}, 表头: {m.raw_header}, sheet: {m.sheet_name}, freq: {m.freq}")
            if m.parse_json:
                if isinstance(m.parse_json, str):
                    parse_json = json.loads(m.parse_json)
                else:
                    parse_json = m.parse_json
                metric_key = parse_json.get('metric_key')
                if metric_key:
                    print(f"      metric_key: {metric_key}")
        
        # 3. 查找"分省区猪价"sheet
        print("\n\n3. 查找'分省区猪价'sheet的指标:")
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价"
        ).limit(10).all()
        
        print(f"  找到 {len(metrics)} 个指标")
        for m in metrics:
            print(f"    - ID: {m.id}, 名称: {m.metric_name}, 表头: {m.raw_header}")
            if "中国" in str(m.raw_header) or "全国" in str(m.raw_header):
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == m.id,
                    FactObservation.period_type == 'day'
                ).count()
                print(f"      *** 可能是全国价格数据，数据条数: {count} ***")
        
    finally:
        db.close()

if __name__ == "__main__":
    find_price()
