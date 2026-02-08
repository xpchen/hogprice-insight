"""
检查价格指标的详细信息
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

def check_detail():
    """检查详细信息"""
    print("=" * 80)
    print("检查价格指标详细信息")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找ID为1的指标
        metric = db.query(DimMetric).filter(DimMetric.id == 1).first()
        
        if metric:
            print(f"\n指标ID: {metric.id}")
            print(f"  名称: {metric.metric_name}")
            print(f"  表头: {metric.raw_header}")
            print(f"  Sheet: {metric.sheet_name}")
            print(f"  Freq: {metric.freq}")
            print(f"  Unit: {metric.unit}")
            print(f"  parse_json: {metric.parse_json}")
            
            if metric.parse_json:
                if isinstance(metric.parse_json, str):
                    parse_json = json.loads(metric.parse_json)
                else:
                    parse_json = metric.parse_json
                print(f"  metric_key: {parse_json.get('metric_key')}")
        else:
            print("\n未找到ID为1的指标")
        
        # 查找所有"分省区猪价"sheet的指标
        print("\n\n所有'分省区猪价'sheet的指标:")
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价"
        ).all()
        
        for m in metrics:
            print(f"\n  ID: {m.id}")
            print(f"    名称: {m.metric_name}")
            print(f"    表头: {m.raw_header}")
            print(f"    Freq: {m.freq}")
            if "中国" in str(m.raw_header):
                print(f"    *** 这是全国价格指标 ***")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_detail()
