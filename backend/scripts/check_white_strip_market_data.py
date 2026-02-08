"""
检查白条市场数据
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
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

def check_white_strip_market_data():
    """检查白条市场数据"""
    print("=" * 80)
    print("检查白条市场数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"白条市场"sheet的所有指标
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "白条市场"
        ).all()
        
        print(f"\n找到 {len(metrics)} 个'白条市场'sheet的指标:")
        for m in metrics:
            print(f"  - ID: {m.id}, 名称: {m.metric_name}, 原始表头: {m.raw_header}")
            if m.parse_json:
                if isinstance(m.parse_json, str):
                    import json
                    parse_json = json.loads(m.parse_json)
                else:
                    parse_json = m.parse_json
                print(f"    metric_key: {parse_json.get('metric_key')}")
                print(f"    tags: {parse_json.get('tags')}")
                
                # 检查数据条数
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == m.id
                ).count()
                print(f"    数据条数: {count}")
                
                # 显示最近5条数据
                if count > 0:
                    recent_obs = db.query(
                        FactObservation.obs_date,
                        FactObservation.value
                    ).filter(
                        FactObservation.metric_id == m.id
                    ).order_by(FactObservation.obs_date.desc()).limit(5).all()
                    print(f"    最近5条数据:")
                    for obs in recent_obs:
                        print(f"      {obs.obs_date}: {obs.value}")
        
        # 检查到货量和价格指标
        print(f"\n检查到货量指标（ARRIVAL）:")
        arrival_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "白条市场",
            func.json_unquote(func.json_extract(DimMetric.parse_json, '$.metric_key')).like('%ARRIVAL%')
        ).all()
        print(f"  找到 {len(arrival_metrics)} 个到货量指标")
        
        print(f"\n检查价格指标（PRICE）:")
        price_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "白条市场",
            func.json_unquote(func.json_extract(DimMetric.parse_json, '$.metric_key')).like('%PRICE%')
        ).all()
        print(f"  找到 {len(price_metrics)} 个价格指标")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_white_strip_market_data()
