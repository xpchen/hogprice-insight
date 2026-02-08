"""
检查parse_json的实际结构
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

def check_parse_json():
    """检查parse_json结构"""
    print("=" * 80)
    print("检查parse_json结构")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "白条市场"
        ).all()
        
        for m in metrics:
            print(f"\n指标ID: {m.id}, 名称: {m.metric_name}")
            print(f"  raw_header: {m.raw_header}")
            print(f"  parse_json类型: {type(m.parse_json)}")
            print(f"  parse_json内容: {m.parse_json}")
            
            if m.parse_json:
                if isinstance(m.parse_json, str):
                    parse_json = json.loads(m.parse_json)
                else:
                    parse_json = m.parse_json
                
                print(f"  解析后的内容:")
                print(f"    metric_key: {parse_json.get('metric_key')}")
                print(f"    tags: {parse_json.get('tags')}")
                print(f"    完整内容: {json.dumps(parse_json, ensure_ascii=False, indent=2)}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_parse_json()
