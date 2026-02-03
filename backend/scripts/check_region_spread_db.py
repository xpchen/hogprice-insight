# -*- coding: utf-8 -*-
"""检查数据库中区域价差数据"""
import sys
import io
from pathlib import Path

# 设置UTF-8编码输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

db = next(get_db())

try:
    # 查询所有区域价差指标
    metrics = db.query(DimMetric).filter(
        DimMetric.sheet_name == "区域价差"
    ).all()
    
    print(f"找到 {len(metrics)} 个区域价差指标：")
    for metric in metrics:
        print(f"  - ID: {metric.id}")
        print(f"    指标名称: {metric.metric_name}")
        print(f"    原始列名: {metric.raw_header}")
        print(f"    Sheet: {metric.sheet_name}")
        
        # 查询该指标的数据数量
        obs_count = db.query(FactObservation).filter(
            FactObservation.metric_id == metric.id
        ).count()
        print(f"    数据条数: {obs_count}")
        
        # 查询最新数据
        latest_obs = db.query(FactObservation).filter(
            FactObservation.metric_id == metric.id
        ).order_by(FactObservation.obs_date.desc()).first()
        if latest_obs:
            print(f"    最新日期: {latest_obs.obs_date}, 最新值: {latest_obs.value}")
        print()
    
    # 测试查询"区域价差：广东-广西"
    test_pair = "广东-广西"
    test_metric_name = f"区域价差：{test_pair}"
    print(f"\n测试查询指标名称: '{test_metric_name}'")
    test_metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "区域价差",
        DimMetric.metric_name == test_metric_name
    ).first()
    
    if test_metric:
        print(f"✓ 找到指标: {test_metric.metric_name}")
        obs_count = db.query(FactObservation).filter(
            FactObservation.metric_id == test_metric.id
        ).count()
        print(f"  数据条数: {obs_count}")
    else:
        print(f"✗ 未找到指标")
        # 尝试模糊查询
        print("\n尝试模糊查询:")
        similar_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "区域价差",
            DimMetric.metric_name.like(f"%{test_pair}%")
        ).all()
        for m in similar_metrics:
            print(f"  - {m.metric_name}")
            
finally:
    db.close()
