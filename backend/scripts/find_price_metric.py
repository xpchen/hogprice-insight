"""
查找猪价指标
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from sqlalchemy import func, or_

def find_price_metric():
    """查找猪价指标"""
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("查找猪价指标")
        print("=" * 80)
        
        # 1. 查找"分省区猪价"sheet
        print("\n1. 查找'分省区猪价'sheet:")
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价"
        ).all()
        
        print(f"  找到 {len(metrics)} 个指标")
        for m in metrics[:10]:
            metric_key = None
            if m.parse_json:
                import json
                parse_data = json.loads(m.parse_json) if isinstance(m.parse_json, str) else m.parse_json
                metric_key = parse_data.get('metric_key')
            print(f"    - {m.metric_name} ({m.raw_header}), freq={m.freq}, metric_key={metric_key}")
        
        # 2. 查找包含"中国"或"全国"的指标
        print("\n2. 查找包含'中国'或'全国'的指标:")
        china_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价",
            or_(
                DimMetric.raw_header.like('%中国%'),
                DimMetric.raw_header.like('%全国%')
            )
        ).all()
        
        print(f"  找到 {len(china_metrics)} 个指标")
        for m in china_metrics:
            metric_key = None
            if m.parse_json:
                import json
                parse_data = json.loads(m.parse_json) if isinstance(m.parse_json, str) else m.parse_json
                metric_key = parse_data.get('metric_key')
            print(f"    - {m.metric_name} ({m.raw_header}), freq={m.freq}, metric_key={metric_key}")
        
        # 3. 查找metric_key为GL_D_PRICE_NATION的指标
        print("\n3. 查找metric_key为GL_D_PRICE_NATION的指标:")
        gl_metrics = db.query(DimMetric).filter(
            func.json_extract(DimMetric.parse_json, '$.metric_key') == 'GL_D_PRICE_NATION'
        ).all()
        
        print(f"  找到 {len(gl_metrics)} 个指标")
        for m in gl_metrics:
            print(f"    - {m.metric_name} ({m.raw_header}), freq={m.freq}, sheet={m.sheet_name}")
        
        # 4. 查找所有包含"价"的指标
        print("\n4. 查找所有包含'价'的指标（前20个）:")
        price_metrics = db.query(DimMetric).filter(
            DimMetric.raw_header.like('%价%')
        ).limit(20).all()
        
        print(f"  找到 {len(price_metrics)} 个指标")
        for m in price_metrics:
            print(f"    - {m.metric_name} ({m.raw_header}), freq={m.freq}, sheet={m.sheet_name}")
    
    finally:
        db.close()

if __name__ == "__main__":
    find_price_metric()
