"""
测试修复后的省份查询
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
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from datetime import date, timedelta, datetime

def test_province_query():
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("测试修复后的省份查询")
        print("=" * 80)
        
        # 查询指标
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总"
        ).all()
        
        if not metrics:
            print("未找到指标")
            return
        
        metric_ids = [m.id for m in metrics]
        
        # 计算日期范围（使用数据最新日期）
        actual_max_date = db.query(func.max(FactObservation.obs_date)).filter(
            FactObservation.metric_id.in_(metric_ids)
        ).scalar()
        
        end = actual_max_date or date.today()
        start = end - timedelta(days=120)
        
        print(f"日期范围: {start} 到 {end}")
        
        # 测试省份查询（使用json_unquote）
        target_provinces = ['广东', '四川', '贵州']
        
        print(f"\n查询省份列表（使用json_unquote）:")
        provinces_query = db.query(
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.region')
            ).label('region')
        ).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start,
            FactObservation.obs_date <= end,
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.region')
            ).in_(target_provinces)
        ).distinct()
        
        found_provinces = [p.region for p in provinces_query.all() if p.region and p.region in target_provinces]
        provinces = [p for p in target_provinces if p in found_provinces]
        
        print(f"找到的省份: {found_provinces}")
        print(f"使用的省份: {provinces}")
        
        if provinces:
            print(f"✓ 成功找到 {len(provinces)} 个省份")
        else:
            print(f"❌ 未找到省份")
            
            # 调试：检查为什么找不到
            print(f"\n调试信息:")
            all_regions_query = db.query(
                func.json_unquote(
                    func.json_extract(FactObservation.tags_json, '$.region')
                ).label('region')
            ).filter(
                FactObservation.metric_id.in_(metric_ids),
                FactObservation.obs_date >= start,
                FactObservation.obs_date <= end,
                func.json_extract(FactObservation.tags_json, '$.region').isnot(None)
            ).distinct()
            
            all_regions = [r.region for r in all_regions_query.all()]
            print(f"该日期范围内的所有region值: {all_regions}")
            
            for region in all_regions:
                if region:
                    print(f"  '{region}' in target_provinces: {region in target_provinces}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_province_query()
