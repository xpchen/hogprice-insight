"""
检查"汇总"sheet的数据导入情况
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

def check_summary_sheet_data():
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("检查'汇总'sheet的数据导入情况")
        print("=" * 80)
        
        # 1. 检查"汇总"sheet的指标
        print("\n1. 检查'汇总'sheet的指标")
        print("-" * 80)
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总"
        ).all()
        
        print(f"找到 {len(metrics)} 个'汇总'sheet的指标")
        if metrics:
            for m in metrics:
                metric_key = m.parse_json.get('metric_key') if m.parse_json else None
                print(f"  - ID: {m.id}, 名称: {m.metric_name}, metric_key: {metric_key}")
        else:
            print("  ⚠️ 未找到'汇总'sheet的指标！")
        
        # 2. 检查"重点省区汇总"sheet的指标（作为对比）
        print("\n2. 检查'重点省区汇总'sheet的指标（作为对比）")
        print("-" * 80)
        province_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "重点省区汇总"
        ).all()
        
        print(f"找到 {len(province_metrics)} 个'重点省区汇总'sheet的指标")
        for m in province_metrics:
            metric_key = m.parse_json.get('metric_key') if m.parse_json else None
            print(f"  - ID: {m.id}, 名称: {m.metric_name}, metric_key: {metric_key}")
        
        # 3. 检查fact_observation中的数据
        print("\n3. 检查fact_observation中的数据")
        print("-" * 80)
        
        if not metrics:
            print("  ⚠️ 没有'汇总'sheet的指标，无法查询数据")
            print("  💡 建议：请导入包含'汇总'sheet的文件（3.2、集团企业月度数据跟踪.xlsx）")
            return
        
        metric_ids = [m.id for m in metrics]
        target_provinces = ['广东', '四川', '贵州']
        
        # 检查日期范围（最近4个月）
        end_date = date.today()
        start_date = end_date - timedelta(days=120)
        
        print(f"\n日期范围: {start_date} 到 {end_date}")
        print(f"查询的metric_ids: {metric_ids}")
        
        # 查询数据总数
        total_count = db.query(FactObservation).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start_date,
            FactObservation.obs_date <= end_date
        ).count()
        
        print(f"\n总数据条数: {total_count}")
        
        if total_count == 0:
            print("  ⚠️ 没有找到任何数据！")
            print("  💡 建议：请检查数据导入是否成功")
            return
        
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
        ).group_by(
            func.json_extract(FactObservation.tags_json, '$.region')
        ).order_by('count')
        
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
        ).group_by(
            func.json_extract(FactObservation.tags_json, '$.period_type')
        ).order_by('count')
        
        for row in period_types_query.all():
            period_type = row.period_type
            count = row.count
            print(f"  - {period_type}: {count} 条")
        
        # 检查指标分布
        print("\n指标分布（按metric_key）:")
        metric_dist_query = db.query(
            DimMetric.metric_name,
            func.json_extract(DimMetric.parse_json, '$.metric_key').label('metric_key'),
            func.count(FactObservation.id).label('count')
        ).join(
            FactObservation, FactObservation.metric_id == DimMetric.id
        ).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start_date,
            FactObservation.obs_date <= end_date
        ).group_by(
            DimMetric.id, DimMetric.metric_name, func.json_extract(DimMetric.parse_json, '$.metric_key')
        ).order_by('count')
        
        for row in metric_dist_query.all():
            metric_name = row.metric_name
            metric_key = row.metric_key
            count = row.count
            print(f"  - {metric_name} ({metric_key}): {count} 条")
        
        # 检查特定省份和指标的数据（示例）
        print("\n4. 检查特定省份和指标的数据（示例）")
        print("-" * 80)
        
        for province in target_provinces:
            print(f"\n省份: {province}")
            
            # 查找该省份的所有指标数据
            province_data_query = db.query(
                DimMetric.metric_name,
                func.json_extract(DimMetric.parse_json, '$.metric_key').label('metric_key'),
                func.count(FactObservation.id).label('count'),
                func.min(FactObservation.obs_date).label('min_date'),
                func.max(FactObservation.obs_date).label('max_date')
            ).join(
                FactObservation, FactObservation.metric_id == DimMetric.id
            ).filter(
                FactObservation.metric_id.in_(metric_ids),
                FactObservation.obs_date >= start_date,
                FactObservation.obs_date <= end_date,
                func.json_extract(FactObservation.tags_json, '$.region') == province
            ).group_by(
                DimMetric.id, DimMetric.metric_name, func.json_extract(DimMetric.parse_json, '$.metric_key')
            ).order_by('count')
            
            province_data = province_data_query.all()
            
            if not province_data:
                print(f"  ⚠️ 没有找到{province}的数据")
            else:
                print(f"  找到 {len(province_data)} 个指标的数据:")
                for row in province_data:
                    metric_name = row.metric_name
                    metric_key = row.metric_key
                    count = row.count
                    min_date = row.min_date
                    max_date = row.max_date
                    print(f"    - {metric_name} ({metric_key}): {count} 条, 日期范围: {min_date} 到 {max_date}")
                
                # 显示一些示例数据
                print(f"  示例数据（前3条）:")
                samples = db.query(
                    FactObservation.obs_date,
                    FactObservation.value,
                    DimMetric.metric_name,
                    func.json_extract(FactObservation.tags_json, '$.period_type').label('period_type')
                ).join(
                    DimMetric, FactObservation.metric_id == DimMetric.id
                ).filter(
                    FactObservation.metric_id.in_(metric_ids),
                    FactObservation.obs_date >= start_date,
                    FactObservation.obs_date <= end_date,
                    func.json_extract(FactObservation.tags_json, '$.region') == province
                ).limit(3).all()
                
                for sample in samples:
                    print(f"    - {sample.obs_date}, {sample.metric_name}, 值: {sample.value}, 旬度: {sample.period_type}")
        
        # 5. 检查是否有旬度数据
        print("\n5. 检查旬度数据")
        print("-" * 80)
        
        period_type_data = db.query(
            func.json_extract(FactObservation.tags_json, '$.period_type').label('period_type'),
            func.count(FactObservation.id).label('count')
        ).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start_date,
            FactObservation.obs_date <= end_date,
            func.json_extract(FactObservation.tags_json, '$.period_type').in_(['上旬', '中旬', '月度'])
        ).group_by(
            func.json_extract(FactObservation.tags_json, '$.period_type')
        ).all()
        
        if period_type_data:
            print("  找到旬度数据:")
            for row in period_type_data:
                print(f"    - {row.period_type}: {row.count} 条")
        else:
            print("  ⚠️ 没有找到旬度数据（上旬、中旬、月度）")
            print("  💡 这可能意味着数据导入时没有正确设置period_type标签")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_summary_sheet_data()
