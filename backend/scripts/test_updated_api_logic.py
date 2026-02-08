"""
测试更新后的API逻辑
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

def test_updated_logic():
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("测试更新后的API逻辑（使用数据最新日期）")
        print("=" * 80)
        
        # 模拟API的新逻辑
        start = None
        end = None
        
        # 先查询"汇总"sheet的指标，获取数据的实际日期范围
        temp_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总"
        ).all()
        
        if temp_metrics:
            temp_metric_ids = [m.id for m in temp_metrics]
            print(f"找到 {len(temp_metrics)} 个指标")
            
            # 查询数据的实际最新日期
            actual_max_date = db.query(func.max(FactObservation.obs_date)).filter(
                FactObservation.metric_id.in_(temp_metric_ids)
            ).scalar()
            
            print(f"\n数据的实际最新日期: {actual_max_date}")
            
            if actual_max_date:
                # 使用数据的实际最新日期作为结束日期
                end = end or actual_max_date
                # 从最新日期往前推4个月（120天）
                start = start or (end - timedelta(days=120))
                
                print(f"\n计算后的日期范围:")
                print(f"  开始日期: {start}")
                print(f"  结束日期: {end}")
                print(f"  天数: {(end - start).days} 天")
                
                # 检查是否包含2026-02-28
                target_date = date(2026, 2, 28)
                if start <= target_date <= end:
                    print(f"\n✓ 日期范围包含 {target_date}")
                else:
                    print(f"\n❌ 日期范围不包含 {target_date}")
                
                # 查询该日期范围内的数据
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id.in_(temp_metric_ids),
                    FactObservation.obs_date >= start,
                    FactObservation.obs_date <= end
                ).count()
                
                print(f"\n该日期范围内的数据条数: {count}")
                
                # 检查是否有2026-02-28的数据
                count_228 = db.query(FactObservation).filter(
                    FactObservation.metric_id.in_(temp_metric_ids),
                    FactObservation.obs_date == target_date
                ).count()
                
                print(f"{target_date} 的数据条数: {count_228}")
                
                if count_228 > 0:
                    print(f"✓ 成功！现在可以查询到 {target_date} 的数据")
                else:
                    print(f"❌ 仍然查询不到 {target_date} 的数据")
            else:
                print("未找到数据")
        else:
            print("未找到指标")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_updated_logic()
