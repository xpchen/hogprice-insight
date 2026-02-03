# -*- coding: utf-8 -*-
"""检查升贴水数据"""
import sys
import io
from pathlib import Path
from datetime import date, datetime

# 设置UTF-8编码输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func, extract, or_
from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation
from app.models.fact_futures_daily import FactFuturesDaily

def check_premium_data():
    """检查升贴水数据"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("检查升贴水数据")
        print("=" * 80)
        
        # 1. 检查期货数据
        print("\n1. 检查期货数据:")
        print("-" * 80)
        futures_count = db.query(func.count(FactFuturesDaily.id)).scalar()
        print(f"期货数据总数: {futures_count}")
        
        if futures_count > 0:
            min_date = db.query(func.min(FactFuturesDaily.trade_date)).scalar()
            max_date = db.query(func.max(FactFuturesDaily.trade_date)).scalar()
            print(f"日期范围: {min_date} 至 {max_date}")
            
            # 检查各月份合约
            print("\n各月份合约数据量:")
            for month in [3, 5, 7, 9, 11, 1]:
                month_str = f"{month:02d}"
                count = db.query(func.count(FactFuturesDaily.id)).filter(
                    FactFuturesDaily.contract_code.like(f"%{month_str}")
                ).scalar()
                print(f"  {month_str}合约: {count} 条")
                
                # 检查该月份合约的日期范围
                if count > 0:
                    min_d = db.query(func.min(FactFuturesDaily.trade_date)).filter(
                        FactFuturesDaily.contract_code.like(f"%{month_str}")
                    ).scalar()
                    max_d = db.query(func.max(FactFuturesDaily.trade_date)).filter(
                        FactFuturesDaily.contract_code.like(f"%{month_str}")
                    ).scalar()
                    print(f"    日期范围: {min_d} 至 {max_d}")
                    
                    # 检查几个样本数据
                    samples = db.query(FactFuturesDaily).filter(
                        FactFuturesDaily.contract_code.like(f"%{month_str}")
                    ).order_by(FactFuturesDaily.trade_date).limit(3).all()
                    print(f"    样本数据（前3条）:")
                    for s in samples:
                        print(f"      {s.trade_date}: {s.contract_code}, 结算价={s.settle}")
        else:
            print("❌ 数据库中没有期货数据！")
        
        # 2. 检查全国现货价格数据
        print("\n2. 检查全国现货价格数据:")
        print("-" * 80)
        
        # 尝试多种方式查找指标
        metrics = []
        
        # 方式1: 通过raw_header和sheet_name查找
        metric1 = db.query(DimMetric).filter(
            or_(
                DimMetric.raw_header.like("%中国%"),
                DimMetric.raw_header.like("%全国%")
            ),
            DimMetric.sheet_name == "分省区猪价",
            DimMetric.freq.in_(["D", "daily"])
        ).first()
        if metric1:
            metrics.append(("方式1: raw_header+sheet_name+freq", metric1))
        
        # 方式2: 通过metric_key查找（从parse_json中）
        metric2 = db.query(DimMetric).filter(
            func.json_unquote(
                func.json_extract(DimMetric.parse_json, '$.metric_key')
            ) == "GL_D_PRICE_NATION"
        ).first()
        if metric2 and metric2 not in [m[1] for m in metrics]:
            metrics.append(("方式2: metric_key", metric2))
        
        # 方式3: 通过metric_name查找
        metric3 = db.query(DimMetric).filter(
            DimMetric.metric_name.like("%全国%"),
            DimMetric.metric_name.like("%价格%"),
            DimMetric.freq.in_(["D", "daily"])
        ).first()
        if metric3 and metric3 not in [m[1] for m in metrics]:
            metrics.append(("方式3: metric_name+freq", metric3))
        
        # 方式4: 只通过sheet_name和raw_header查找（不限制freq）
        metric4 = db.query(DimMetric).filter(
            DimMetric.raw_header.like("%中国%"),
            DimMetric.sheet_name == "分省区猪价"
        ).first()
        if metric4 and metric4 not in [m[1] for m in metrics]:
            metrics.append(("方式4: raw_header+sheet_name", metric4))
        
        if metrics:
            print(f"找到 {len(metrics)} 个可能的指标:")
            for method, metric in metrics:
                print(f"\n{method}:")
                print(f"  ID: {metric.id}")
                print(f"  指标名称: {metric.metric_name}")
                print(f"  原始列名: {metric.raw_header}")
                print(f"  Sheet: {metric.sheet_name}")
                print(f"  Freq: {metric.freq}")
                metric_key = None
                if metric.parse_json:
                    metric_key = metric.parse_json.get("metric_key")
                print(f"  Metric Key: {metric_key}")
                
                # 查询该指标的数据数量
                obs_count = db.query(func.count(FactObservation.id)).filter(
                    FactObservation.metric_id == metric.id,
                    FactObservation.period_type == "day"
                ).scalar()
                print(f"  数据条数: {obs_count}")
                
                if obs_count > 0:
                    min_d = db.query(func.min(FactObservation.obs_date)).filter(
                        FactObservation.metric_id == metric.id,
                        FactObservation.period_type == "day"
                    ).scalar()
                    max_d = db.query(func.max(FactObservation.obs_date)).filter(
                        FactObservation.metric_id == metric.id,
                        FactObservation.period_type == "day"
                    ).scalar()
                    print(f"  日期范围: {min_d} 至 {max_d}")
                    
                    # 检查几个样本数据
                    samples = db.query(FactObservation).filter(
                        FactObservation.metric_id == metric.id,
                        FactObservation.period_type == "day"
                    ).order_by(FactObservation.obs_date).limit(3).all()
                    print(f"  样本数据（前3条）:")
                    for s in samples:
                        print(f"    {s.obs_date}: {s.value}")
        else:
            print("❌ 未找到全国现货价格指标！")
            print("\n尝试查找所有'分省区猪价'相关的指标:")
            all_metrics = db.query(DimMetric).filter(
                DimMetric.sheet_name == "分省区猪价"
            ).all()
            print(f"找到 {len(all_metrics)} 个指标:")
            for m in all_metrics[:10]:  # 只显示前10个
                print(f"  - {m.metric_name} (raw_header: {m.raw_header}, freq: {m.freq})")
        
        # 3. 检查时间重叠
        print("\n3. 检查时间重叠:")
        print("-" * 80)
        if futures_count > 0 and metrics:
            futures_min = db.query(func.min(FactFuturesDaily.trade_date)).scalar()
            futures_max = db.query(func.max(FactFuturesDaily.trade_date)).scalar()
            
            for method, metric in metrics:
                obs_count = db.query(func.count(FactObservation.id)).filter(
                    FactObservation.metric_id == metric.id,
                    FactObservation.period_type == "day"
                ).scalar()
                
                if obs_count > 0:
                    spot_min = db.query(func.min(FactObservation.obs_date)).filter(
                        FactObservation.metric_id == metric.id,
                        FactObservation.period_type == "day"
                    ).scalar()
                    spot_max = db.query(func.max(FactObservation.obs_date)).filter(
                        FactObservation.metric_id == metric.id,
                        FactObservation.period_type == "day"
                    ).scalar()
                    
                    print(f"\n{method}:")
                    print(f"  期货日期范围: {futures_min} 至 {futures_max}")
                    print(f"  现货日期范围: {spot_min} 至 {spot_max}")
                    
                    # 计算重叠日期范围
                    overlap_start = max(futures_min, spot_min) if futures_min and spot_min else None
                    overlap_end = min(futures_max, spot_max) if futures_max and spot_max else None
                    
                    if overlap_start and overlap_end and overlap_start <= overlap_end:
                        print(f"  ✓ 重叠日期范围: {overlap_start} 至 {overlap_end}")
                        
                        # 检查重叠范围内的数据量
                        overlap_days = (overlap_end - overlap_start).days + 1
                        print(f"  重叠天数: {overlap_days} 天")
                    else:
                        print(f"  ❌ 没有时间重叠！")
        
        # 4. 测试计算升贴水
        print("\n4. 测试计算升贴水（03合约，2026年）:")
        print("-" * 80)
        if futures_count > 0 and metrics:
            # 找一个有数据的日期
            test_date_result = db.query(FactFuturesDaily.trade_date).filter(
                FactFuturesDaily.contract_code.like("%03")
            ).order_by(FactFuturesDaily.trade_date).first()
            
            if test_date_result:
                # 处理查询结果
                if hasattr(test_date_result, 'trade_date'):
                    test_date = test_date_result.trade_date
                elif isinstance(test_date_result, tuple):
                    test_date = test_date_result[0]
                else:
                    test_date = test_date_result
                print(f"测试日期: {test_date}")
                
                # 查找该日期的期货数据
                futures = db.query(FactFuturesDaily).filter(
                    FactFuturesDaily.contract_code.like("%03"),
                    FactFuturesDaily.trade_date == test_date
                ).all()
                
                if futures:
                    best_futures = max(futures, key=lambda x: x.open_interest or 0)
                    print(f"期货合约: {best_futures.contract_code}")
                    print(f"期货结算价: {best_futures.settle}")
                    
                    # 查找该日期的现货价格
                    for method, metric in metrics:
                        spot = db.query(FactObservation).filter(
                            FactObservation.metric_id == metric.id,
                            FactObservation.obs_date == test_date,
                            FactObservation.period_type == "day"
                        ).first()
                        
                        if spot:
                            print(f"\n{method}:")
                            print(f"  现货价格: {spot.value}")
                            if best_futures.settle and spot.value:
                                # 注意：期货价格单位可能是元/吨，现货价格单位是元/公斤
                                # 需要转换：1吨 = 1000公斤
                                futures_price_per_kg = float(best_futures.settle) / 1000.0
                                spot_price = float(spot.value)
                                premium = futures_price_per_kg - spot_price
                                print(f"  期货结算价（元/公斤）: {futures_price_per_kg:.2f}")
                                print(f"  现货价格（元/公斤）: {spot_price:.2f}")
                                print(f"  升贴水（元/公斤）: {premium:.2f}")
                            break
                    else:
                        print(f"  ❌ 该日期没有现货价格数据")
                else:
                    print(f"  ❌ 该日期没有期货数据")
            else:
                print("  ❌ 没有找到03合约的数据")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_premium_data()
