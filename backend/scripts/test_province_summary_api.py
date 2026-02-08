"""
测试省份汇总表格API的查询逻辑
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
from datetime import date, timedelta, datetime

def test_api_query_logic():
    """模拟API的查询逻辑"""
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("测试省份汇总表格API的查询逻辑")
        print("=" * 80)
        
        # 模拟API参数
        start_date_str = "2025-10-08"
        end_date_str = "2026-02-08"
        
        start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        print(f"\n日期范围: {start} 到 {end}")
        
        # 1. 查询指标（优先查找"汇总"sheet）
        print("\n1. 查询指标")
        print("-" * 80)
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "汇总"
        ).all()
        
        print(f"找到 {len(metrics)} 个'汇总'sheet的指标")
        if not metrics:
            print("  ⚠️ 未找到指标，尝试查找'重点省区汇总'")
            metrics = db.query(DimMetric).filter(
                and_(
                    DimMetric.sheet_name == "重点省区汇总",
                    or_(
                        func.json_extract(DimMetric.parse_json, '$.metric_key') == 'PROVINCE_PLAN',
                        DimMetric.metric_name.like('%计划%')
                    )
                )
            ).all()
            print(f"找到 {len(metrics)} 个'重点省区汇总'sheet的指标")
        
        if not metrics:
            print("  ❌ 未找到任何指标！")
            return
        
        for m in metrics:
            metric_key = m.parse_json.get('metric_key') if m.parse_json else None
            print(f"  - ID: {m.id}, 名称: {m.metric_name}, metric_key: {metric_key}")
        
        # 2. 过滤有效的DimMetric对象
        print("\n2. 过滤有效的DimMetric对象")
        print("-" * 80)
        valid_metrics = [m for m in metrics if hasattr(m, 'id') and hasattr(m, 'metric_name')]
        print(f"有效指标数量: {len(valid_metrics)}")
        
        if not valid_metrics:
            print("  ❌ 没有有效指标！")
            return
        
        metric_ids = [m.id for m in valid_metrics]
        print(f"metric_ids: {metric_ids}")
        
        # 3. 获取省份列表
        print("\n3. 获取省份列表")
        print("-" * 80)
        target_provinces = ['广东', '四川', '贵州']
        
        try:
            provinces_query = db.query(
                func.json_extract(FactObservation.tags_json, '$.region').label('region')
            ).filter(
                FactObservation.metric_id.in_(metric_ids),
                FactObservation.obs_date >= start,
                FactObservation.obs_date <= end,
                func.json_extract(FactObservation.tags_json, '$.region').in_(target_provinces)
            ).distinct()
            
            found_provinces = [p.region for p in provinces_query.all() if p.region and p.region in target_provinces]
            provinces = [p for p in target_provinces if p in found_provinces]
            print(f"找到的省份: {provinces}")
        except Exception as e:
            print(f"  ⚠️ 获取省份列表失败: {e}")
            provinces = target_provinces
        
        if not provinces:
            provinces = target_provinces
        
        print(f"使用的省份: {provinces}")
        
        # 4. 获取日期和旬度类型
        print("\n4. 获取日期和旬度类型")
        print("-" * 80)
        dates_periods_query = db.query(
            FactObservation.obs_date,
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.period_type')
            ).label('period_type')
        ).filter(
            FactObservation.metric_id.in_(metric_ids),
            FactObservation.obs_date >= start,
            FactObservation.obs_date <= end,
            func.json_extract(FactObservation.tags_json, '$.period_type').isnot(None)
        ).distinct().order_by(FactObservation.obs_date)
        
        dates_periods = [(d.obs_date, d.period_type) for d in dates_periods_query.all()]
        print(f"找到 {len(dates_periods)} 个日期-旬度组合")
        
        if dates_periods:
            print("前10个日期-旬度组合:")
            for dp in dates_periods[:10]:
                print(f"  - {dp[0]}, 旬度: {dp[1]}")
        else:
            print("  ⚠️ 没有找到日期-旬度组合，尝试从日期推断")
            dates_query = db.query(
                FactObservation.obs_date
            ).filter(
                FactObservation.metric_id.in_(metric_ids),
                FactObservation.obs_date >= start,
                FactObservation.obs_date <= end
            ).distinct().order_by(FactObservation.obs_date)
            
            dates = [d.obs_date for d in dates_query.all()]
            dates_periods = []
            for date_val in dates:
                day = date_val.day
                if day <= 10:
                    period_type = '上旬'
                elif day <= 20:
                    period_type = '中旬'
                else:
                    period_type = '月度'
                dates_periods.append((date_val, period_type))
            print(f"推断得到 {len(dates_periods)} 个日期-旬度组合")
        
        # 5. 测试查询特定省份和指标的数据
        print("\n5. 测试查询特定省份和指标的数据")
        print("-" * 80)
        
        # 定义指标映射
        metric_mapping = {
            '出栏计划': 'PROVINCE_PLAN',
            '计划出栏量': 'PROVINCE_PLAN',
            '实际出栏量': 'PROVINCE_ACTUAL',
            '计划完成率': 'PROVINCE_COMPLETION_RATE',
            '计划达成率': 'PROVINCE_COMPLETION_RATE',
            '均重': 'PROVINCE_AVG_WEIGHT',
            '实际均重': 'PROVINCE_AVG_WEIGHT',
            '计划均重': 'PROVINCE_PLAN_WEIGHT',
            '销售均价': 'PROVINCE_PRICE'
        }
        
        # 定义各省份的指标配置
        province_metrics_config = {
            '广东': ['出栏计划', '实际出栏量', '计划完成率', '均重', '销售均价'],
            '四川': ['出栏计划', '实际出栏量', '计划完成率', '均重'],
            '贵州': ['计划出栏量', '实际出栏量', '计划达成率', '实际均重']
        }
        
        # 测试查询一个日期和省份的数据
        if dates_periods:
            test_date, test_period = dates_periods[0]
            test_province = provinces[0] if provinces else '广东'
            
            print(f"\n测试查询: 日期={test_date}, 旬度={test_period}, 省份={test_province}")
            
            metrics_list = province_metrics_config.get(test_province, [])
            print(f"需要查询的指标: {metrics_list}")
            
            for metric_display in metrics_list[:2]:  # 只测试前2个指标
                target_metric_key = metric_mapping.get(metric_display)
                print(f"\n  查询指标: {metric_display} (metric_key={target_metric_key})")
                
                if not target_metric_key:
                    print(f"    ⚠️ 未找到metric_key映射")
                    continue
                
                # 查找对应的DimMetric
                target_metric = None
                for m in valid_metrics:
                    metric_key = m.parse_json.get('metric_key') if m.parse_json else None
                    metric_name = m.metric_name or ""
                    
                    if metric_key == target_metric_key:
                        target_metric = m
                        print(f"    ✓ 通过metric_key匹配: {m.metric_name} (ID={m.id})")
                        break
                    elif metric_display in metric_name:
                        if not metric_key or metric_key == target_metric_key:
                            target_metric = m
                            print(f"    ✓ 通过metric_name匹配: {m.metric_name} (ID={m.id})")
                            break
                
                if not target_metric:
                    print(f"    ❌ 未找到对应的DimMetric")
                    continue
                
                # 查询数据（使用json_unquote去除引号）
                obs_query = db.query(FactObservation).filter(
                    FactObservation.metric_id == target_metric.id,
                    FactObservation.obs_date == test_date,
                    func.json_unquote(
                        func.json_extract(FactObservation.tags_json, '$.region')
                    ) == test_province
                )
                
                if test_period and test_period.strip():
                    obs_query = obs_query.filter(
                        func.json_unquote(
                            func.json_extract(FactObservation.tags_json, '$.period_type')
                        ) == test_period
                    )
                
                obs = obs_query.first()
                
                if obs:
                    print(f"    ✓ 找到数据: 值={obs.value}, 日期={obs.obs_date}")
                    # 检查tags
                    tags = obs.tags_json or {}
                    print(f"    tags: {tags}")
                else:
                    print(f"    ❌ 未找到数据")
                    # 检查是否有该metric的数据
                    count = db.query(FactObservation).filter(
                        FactObservation.metric_id == target_metric.id,
                        func.json_extract(FactObservation.tags_json, '$.region') == test_province
                    ).count()
                    print(f"    但该指标在该省份总共有 {count} 条数据")
        
        print("\n测试完成！")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_api_query_logic()
