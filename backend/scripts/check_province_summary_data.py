"""
检查重点省份旬度汇总表格数据
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

# 添加项目根目录到路径
script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.core.database import SessionLocal
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from datetime import date, timedelta

def check_data():
    db: Session = SessionLocal()
    try:
        # 1. 检查"汇总"sheet的指标
        print("=" * 60)
        print("1. 检查'汇总'sheet的指标")
        print("=" * 60)
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总"
        ).all()
        
        print(f"找到 {len(metrics)} 个指标")
        for m in metrics[:10]:  # 只显示前10个
            metric_key = m.parse_json.get('metric_key') if m.parse_json else None
            print(f"  - ID: {m.id}, 名称: {m.metric_name}, metric_key: {metric_key}, sheet: {m.sheet_name}")
        
        if not metrics:
            print("\n⚠️ 未找到'汇总'sheet的指标，尝试查找'重点省区汇总'")
            metrics = db.query(DimMetric).filter(
                DimMetric.sheet_name == "重点省区汇总"
            ).all()
            print(f"找到 {len(metrics)} 个'重点省区汇总'指标")
            for m in metrics[:10]:
                metric_key = m.parse_json.get('metric_key') if m.parse_json else None
                print(f"  - ID: {m.id}, 名称: {m.metric_name}, metric_key: {metric_key}")
        
        if not metrics:
            print("\n❌ 未找到任何相关指标！")
            return
        
        # 2. 检查fact_observation中的数据
        print("\n" + "=" * 60)
        print("2. 检查fact_observation中的数据")
        print("=" * 60)
        
        metric_ids = [m.id for m in metrics]
        target_provinces = ['广东', '四川', '贵州']
        
        # 检查日期范围（最近4个月）
        end_date = date.today()
        start_date = end_date - timedelta(days=120)
        
        print(f"日期范围: {start_date} 到 {end_date}")
        print(f"查询的metric_ids: {metric_ids[:5]}... (共{len(metric_ids)}个)")
        
        # 查询数据总数
        total_count = db.query(FactObservation).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start_date,
            FactObservation.obs_date <= end_date
        ).count()
        
        print(f"\n总数据条数: {total_count}")
        
        # 检查省份分布
        print("\n省份分布:")
        provinces_query = db.query(
            func.json_extract(FactObservation.tags_json, '$.region').label('region'),
            func.count(FactObservation.id).label('count')
        ).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start_date,
            FactObservation.obs_date <= end_date,
            func.json_extract(FactObservation.tags_json, '$.region').isnot(None)
        ).group_by('region').order_by('count')
        
        for row in provinces_query.all():
            region = row.region
            count = row.count
            print(f"  - {region}: {count} 条")
        
        # 检查旬度类型分布
        print("\n旬度类型分布:")
        period_types_query = db.query(
            func.json_extract(FactObservation.tags_json, '$.period_type').label('period_type'),
            func.count(FactObservation.id).label('count')
        ).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start_date,
            FactObservation.obs_date <= end_date,
            func.json_extract(FactObservation.tags_json, '$.period_type').isnot(None)
        ).group_by('period_type').order_by('count')
        
        for row in period_types_query.all():
            period_type = row.period_type
            count = row.count
            print(f"  - {period_type}: {count} 条")
        
        # 检查特定省份和指标的数据
        print("\n" + "=" * 60)
        print("3. 检查特定省份和指标的数据（示例）")
        print("=" * 60)
        
        for province in target_provinces:
            print(f"\n省份: {province}")
            # 查找该省份的metric
            province_metrics = []
            for m in metrics:
                metric_key = m.parse_json.get('metric_key') if m.parse_json else None
                if metric_key in ['PROVINCE_PLAN', 'PROVINCE_ACTUAL', 'PROVINCE_COMPLETION_RATE', 'PROVINCE_AVG_WEIGHT', 'PROVINCE_PRICE']:
                    province_metrics.append((m.id, m.metric_name, metric_key))
            
            print(f"  找到 {len(province_metrics)} 个相关指标")
            
            for metric_id, metric_name, metric_key in province_metrics[:3]:  # 只显示前3个
                count = db.query(FactObservation).filter(
                    FactObservation.metric_id == metric_id,
                    FactObservation.obs_date >= start_date,
                    FactObservation.obs_date <= end_date,
                    func.json_extract(FactObservation.tags_json, '$.region') == province
                ).count()
                
                print(f"    - {metric_name} ({metric_key}): {count} 条")
                
                # 显示一些示例数据
                if count > 0:
                    samples = db.query(
                        FactObservation.obs_date,
                        FactObservation.value,
                        func.json_extract(FactObservation.tags_json, '$.period_type').label('period_type')
                    ).filter(
                        FactObservation.metric_id == metric_id,
                        FactObservation.obs_date >= start_date,
                        FactObservation.obs_date <= end_date,
                        func.json_extract(FactObservation.tags_json, '$.region') == province
                    ).limit(3).all()
                    
                    for sample in samples:
                        print(f"      示例: {sample.obs_date}, 值: {sample.value}, 旬度: {sample.period_type}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
