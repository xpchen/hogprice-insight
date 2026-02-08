"""
检查"汇总"sheet的实际日期范围
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
from datetime import date, timedelta

def check_date_range():
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("检查'汇总'sheet的实际日期范围")
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
        
        # 查询日期范围
        min_date = db.query(func.min(FactObservation.obs_date)).filter(
            FactObservation.metric_id.in_(metric_ids)
        ).scalar()
        
        max_date = db.query(func.max(FactObservation.obs_date)).filter(
            FactObservation.metric_id.in_(metric_ids)
        ).scalar()
        
        print(f"\n实际日期范围:")
        print(f"  最早日期: {min_date}")
        print(f"  最晚日期: {max_date}")
        
        # 计算总天数
        if min_date and max_date:
            total_days = (max_date - min_date).days + 1
            print(f"  总天数: {total_days} 天")
        
        # 检查所有日期
        print(f"\n所有日期列表:")
        dates_query = db.query(
            FactObservation.obs_date
        ).filter(
            FactObservation.metric_id.in_(metric_ids)
        ).distinct().order_by(FactObservation.obs_date)
        
        dates = [d.obs_date for d in dates_query.all()]
        print(f"  共 {len(dates)} 个日期")
        print(f"  前10个日期: {dates[:10]}")
        print(f"  后10个日期: {dates[-10:]}")
        
        # 检查是否有2026/2/28的数据
        target_date = date(2026, 2, 28)
        print(f"\n检查是否有 {target_date} 的数据:")
        count = db.query(FactObservation).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date == target_date
        ).count()
        
        if count > 0:
            print(f"  ✓ 找到 {count} 条数据")
            # 显示示例数据
            samples = db.query(
                FactObservation.obs_date,
                FactObservation.value,
                DimMetric.metric_name,
                func.json_unquote(
                    func.json_extract(FactObservation.tags_json, '$.region')
                ).label('region'),
                func.json_unquote(
                    func.json_extract(FactObservation.tags_json, '$.period_type')
                ).label('period_type')
            ).join(
                DimMetric, FactObservation.metric_id == DimMetric.id
            ).filter(
                FactObservation.metric_id.in_(metric_ids),
                FactObservation.obs_date == target_date
            ).limit(5).all()
            
            print(f"  示例数据:")
            for sample in samples:
                print(f"    - {sample.metric_name}, {sample.region}, {sample.period_type}, 值: {sample.value}")
        else:
            print(f"  ❌ 未找到数据")
        
        # 检查API默认日期范围（最近4个月）
        print(f"\n检查API默认日期范围（最近4个月）:")
        today = date.today()
        print(f"  今天: {today}")
        
        # API默认是120天前
        api_start = today - timedelta(days=120)
        api_end = today
        print(f"  API默认范围: {api_start} 到 {api_end}")
        
        if max_date:
            if max_date > api_end:
                print(f"  ⚠️ 数据最新日期({max_date})晚于API结束日期({api_end})")
            elif max_date < api_start:
                print(f"  ⚠️ 数据最新日期({max_date})早于API开始日期({api_start})")
            else:
                print(f"  ✓ 数据最新日期在API范围内")
        
        # 建议：应该使用数据的实际日期范围，而不是固定的120天
        print(f"\n建议:")
        if max_date:
            # 从最新日期往前推4个月
            suggested_start = max_date - timedelta(days=120)
            suggested_end = max_date
            print(f"  使用数据最新日期往前推4个月:")
            print(f"    开始日期: {suggested_start}")
            print(f"    结束日期: {suggested_end}")
            print(f"    这样能包含所有数据到 {max_date}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_date_range()
