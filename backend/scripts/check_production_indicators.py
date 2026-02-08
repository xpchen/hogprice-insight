"""
检查月度-生产指标数据
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
from app.models.raw_sheet import RawSheet
from app.models.raw_table import RawTable
from app.models.raw_file import RawFile

def check_production_indicators():
    """检查月度-生产指标数据"""
    print("=" * 80)
    print("检查月度-生产指标数据")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 查找raw_sheet
        sheet = db.query(RawSheet).join(RawFile).filter(
            RawSheet.sheet_name == "月度-生产指标"
        ).first()
        
        if sheet:
            print(f"\n找到sheet: {sheet.sheet_name}")
            print(f"Sheet ID: {sheet.id}")
            print(f"文件: {sheet.raw_file.filename if sheet.raw_file else 'N/A'}")
            
            # 查找raw_table数据
            raw_tables = db.query(RawTable).filter(
                RawTable.raw_sheet_id == sheet.id
            ).limit(20).all()
            
            print(f"\n找到 {len(raw_tables)} 条raw_table数据（显示前20条）")
            for rt in raw_tables[:5]:
                print(f"  Row {rt.row_idx}: {rt.row_data}")
        else:
            print("\n未找到'月度-生产指标'sheet")
        
        # 查找DimMetric
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "月度-生产指标"
        ).all()
        
        print(f"\n找到 {len(metrics)} 个指标")
        for m in metrics:
            print(f"  - ID: {m.id}, 名称: {m.metric_name}, 原始表头: {m.raw_header}")
            if m.parse_json:
                if isinstance(m.parse_json, str):
                    parse_json = json.loads(m.parse_json)
                else:
                    parse_json = m.parse_json
                print(f"    metric_key: {parse_json.get('metric_key')}")
                
                # 检查数据条数
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == m.id
                ).count()
                print(f"    数据条数: {count}")
                
                if count > 0:
                    recent_obs = db.query(
                        FactObservation.obs_date,
                        FactObservation.value
                    ).filter(
                        FactObservation.metric_id == m.id
                    ).order_by(FactObservation.obs_date.desc()).limit(3).all()
                    print(f"    最近3条数据:")
                    for obs in recent_obs:
                        print(f"      {obs.obs_date}: {obs.value}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_production_indicators()
