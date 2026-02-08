"""
检查所有市场的数据
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

def check_all_markets():
    """检查所有市场"""
    print("=" * 80)
    print("检查所有市场的数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找所有"白条市场"sheet的指标
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "白条市场"
        ).all()
        
        print(f"\n找到 {len(metrics)} 个指标")
        
        # 统计所有市场
        markets = set()
        for metric in metrics:
            # 查询该指标的所有数据，提取market
            obs_list = db.query(FactObservation.tags_json).filter(
                FactObservation.metric_id == metric.id
            ).distinct().all()
            
            for obs in obs_list:
                if obs.tags_json:
                    if isinstance(obs.tags_json, str):
                        tags = json.loads(obs.tags_json)
                    else:
                        tags = obs.tags_json
                    market = tags.get('market')
                    if market:
                        markets.add(market)
        
        print(f"\n找到的所有市场: {sorted(list(markets))}")
        
        # 检查每个市场的数据条数
        print(f"\n各市场数据统计:")
        for market in sorted(markets):
            count = db.query(FactObservation).filter(
                FactObservation.tags_json.like(f'%{market}%')
            ).count()
            print(f"  {market}: {count} 条")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_all_markets()
