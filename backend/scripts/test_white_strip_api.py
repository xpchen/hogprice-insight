"""
测试白条市场API
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import date, timedelta
import json
import math

from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

def test_api_logic():
    """测试API逻辑"""
    print("=" * 80)
    print("测试白条市场API逻辑")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找白条市场相关的指标
        arrival_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "白条市场",
            func.json_unquote(func.json_extract(DimMetric.parse_json, '$.metric_key')).like('%ARRIVAL%')
        ).all()
        
        price_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "白条市场",
            func.json_unquote(func.json_extract(DimMetric.parse_json, '$.metric_key')).like('%PRICE%')
        ).all()
        
        print(f"\n找到 {len(arrival_metrics)} 个到货量指标")
        print(f"找到 {len(price_metrics)} 个价格指标")
        
        # 查询最近15天的数据
        end_date = date.today()
        start_date = end_date - timedelta(days=15)
        
        all_data = []
        markets = set()
        
        # 查询到货量数据
        for metric in arrival_metrics:
            obs_list = db.query(
                FactObservation.obs_date,
                FactObservation.value,
                FactObservation.tags_json
            ).filter(
                FactObservation.metric_id == metric.id,
                FactObservation.obs_date >= start_date,
                FactObservation.obs_date <= end_date
            ).order_by(desc(FactObservation.obs_date)).limit(15).all()
            
            print(f"\n到货量指标 {metric.id} ({metric.metric_name}): {len(obs_list)} 条数据")
            for obs in obs_list[:3]:  # 只显示前3条
                if obs.value is not None and not math.isnan(obs.value):
                    market = None
                    if obs.tags_json:
                        if isinstance(obs.tags_json, str):
                            tags = json.loads(obs.tags_json)
                        else:
                            tags = obs.tags_json
                        market = tags.get('market')
                    
                    if market:
                        markets.add(market)
                        print(f"  日期: {obs.obs_date}, 市场: {market}, 值: {obs.value}")
        
        # 查询价格数据
        for metric in price_metrics:
            obs_list = db.query(
                FactObservation.obs_date,
                FactObservation.value,
                FactObservation.tags_json
            ).filter(
                FactObservation.metric_id == metric.id,
                FactObservation.obs_date >= start_date,
                FactObservation.obs_date <= end_date
            ).order_by(desc(FactObservation.obs_date)).limit(15).all()
            
            print(f"\n价格指标 {metric.id} ({metric.metric_name}): {len(obs_list)} 条数据")
            for obs in obs_list[:3]:  # 只显示前3条
                if obs.value is not None and not math.isnan(obs.value):
                    market = None
                    if obs.tags_json:
                        if isinstance(obs.tags_json, str):
                            tags = json.loads(obs.tags_json)
                        else:
                            tags = obs.tags_json
                        market = tags.get('market')
                    
                    if market:
                        markets.add(market)
                        print(f"  日期: {obs.obs_date}, 市场: {market}, 值: {obs.value}")
        
        print(f"\n找到的市场: {sorted(list(markets))}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_api_logic()
