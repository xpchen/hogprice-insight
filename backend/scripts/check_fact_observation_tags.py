"""
检查FactObservation的tags_json字段
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
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

def check_tags():
    """检查tags"""
    print("=" * 80)
    print("检查FactObservation的tags_json")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找"白条市场"sheet的指标
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "白条市场"
        ).all()
        
        for m in metrics:
            print(f"\n指标ID: {m.id}, 名称: {m.metric_name}")
            
            # 查询该指标的数据
            obs_list = db.query(FactObservation).filter(
                FactObservation.metric_id == m.id
            ).limit(5).all()
            
            print(f"  数据条数: {len(obs_list)}")
            for obs in obs_list:
                print(f"    日期: {obs.obs_date}, 值: {obs.value}")
                print(f"    tags_json类型: {type(obs.tags_json)}")
                print(f"    tags_json内容: {obs.tags_json}")
                if obs.tags_json:
                    if isinstance(obs.tags_json, str):
                        tags = json.loads(obs.tags_json)
                    else:
                        tags = obs.tags_json
                    print(f"    解析后的tags: {tags}")
                    print(f"    market: {tags.get('market')}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_tags()
