"""
调试省份查询问题
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
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from datetime import date, timedelta, datetime

def debug_region_query():
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("调试省份查询问题")
        print("=" * 80)
        
        # 查询"汇总"sheet的指标
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总"
        ).all()
        
        if not metrics:
            print("未找到'汇总'sheet的指标")
            return
        
        metric_ids = [m.id for m in metrics]
        print(f"metric_ids: {metric_ids}")
        
        # 日期范围
        start = datetime.strptime("2025-10-08", "%Y-%m-%d").date()
        end = datetime.strptime("2026-02-08", "%Y-%m-%d").date()
        print(f"日期范围: {start} 到 {end}")
        
        # 检查实际数据中的region值
        print("\n1. 检查实际数据中的region值")
        print("-" * 80)
        
        samples = db.query(
            FactObservation.obs_date,
            FactObservation.tags_json,
            DimMetric.metric_name
        ).join(
            DimMetric, FactObservation.metric_id == DimMetric.id
        ).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start,
            FactObservation.obs_date <= end
        ).limit(10).all()
        
        print(f"找到 {len(samples)} 条示例数据:")
        for sample in samples:
            tags = sample.tags_json or {}
            region = tags.get('region') if isinstance(tags, dict) else None
            print(f"  日期: {sample.obs_date}, 指标: {sample.metric_name}, region: {region}, tags: {tags}")
        
        # 检查region值的格式
        print("\n2. 检查region值的格式（使用json_extract）")
        print("-" * 80)
        
        regions_query = db.query(
            func.json_extract(FactObservation.tags_json, '$.region').label('region')
        ).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start,
            FactObservation.obs_date <= end,
            func.json_extract(FactObservation.tags_json, '$.region').isnot(None)
        ).distinct()
        
        regions = [r.region for r in regions_query.all()]
        print(f"找到的region值: {regions}")
        print(f"region值类型: {[type(r).__name__ for r in regions]}")
        
        # 检查是否有带引号的region值
        print("\n3. 检查是否有带引号的region值")
        print("-" * 80)
        
        for region in regions:
            if region:
                print(f"  region: '{region}' (长度={len(str(region))}, 类型={type(region).__name__})")
                # 检查是否包含引号
                if '"' in str(region):
                    print(f"    ⚠️ 包含引号!")
                # 检查是否等于目标省份
                target_provinces = ['广东', '四川', '贵州']
                for target in target_provinces:
                    if str(region) == target:
                        print(f"    ✓ 匹配: {target}")
                    elif str(region).strip('"') == target:
                        print(f"    ⚠️ 去除引号后匹配: {target}")
        
        # 测试查询
        print("\n4. 测试查询特定省份的数据")
        print("-" * 80)
        
        target_provinces = ['广东', '四川', '贵州']
        for province in target_provinces:
            # 直接查询
            count1 = db.query(FactObservation).filter(
                FactObservation.metric_id.in_(metric_ids),
                FactObservation.obs_date >= start,
                FactObservation.obs_date <= end,
                func.json_extract(FactObservation.tags_json, '$.region') == province
            ).count()
            
            # 使用JSON_UNQUOTE
            count2 = db.query(FactObservation).filter(
                FactObservation.metric_id.in_(metric_ids),
                FactObservation.obs_date >= start,
                FactObservation.obs_date <= end,
                func.json_unquote(
                    func.json_extract(FactObservation.tags_json, '$.region')
                ) == province
            ).count()
            
            print(f"  {province}:")
            print(f"    使用json_extract: {count1} 条")
            print(f"    使用json_unquote: {count2} 条")
        
    finally:
        db.close()

if __name__ == "__main__":
    debug_region_query()
