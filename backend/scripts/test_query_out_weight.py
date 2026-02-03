"""测试查询出栏均重数据"""
import sys
import os
import io
import json
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation
from sqlalchemy import func, text

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

db = SessionLocal()
try:
    # 模拟前端查询条件
    start_date = date.today() - timedelta(days=365*3)  # 最近3年
    end_date = date.today()
    
    print("=" * 80)
    print("测试查询出栏均重数据（模拟前端查询）")
    print("=" * 80)
    print(f"查询条件:")
    print(f"  source_code: YONGYI")
    print(f"  metric_key: YY_W_OUT_WEIGHT")
    print(f"  indicator: 均重")
    print(f"  geo_code: NATION")
    print(f"  period_type: week")
    print(f"  start_date: {start_date}")
    print(f"  end_date: {end_date}")
    print()
    
    # 查找metric
    metric = db.query(DimMetric).filter(
        func.json_unquote(
            func.json_extract(DimMetric.parse_json, '$.metric_key')
        ) == 'YY_W_OUT_WEIGHT'
    ).first()
    
    if not metric:
        print("❌ 未找到metric")
        exit(1)
    
    # 构建查询（模拟API的查询逻辑）
    query = db.query(FactObservation).filter(
        FactObservation.metric_id == metric.id,
        FactObservation.period_type == 'week',
        FactObservation.obs_date >= start_date,
        FactObservation.obs_date <= end_date,
        FactObservation.geo_id.is_(None),  # geo_code='NATION'
        func.json_unquote(
            func.json_extract(FactObservation.tags_json, '$.indicator')
        ) == '均重'
    ).order_by(FactObservation.obs_date.desc())
    
    observations = query.limit(100).all()
    
    print(f"✓ 找到 {len(observations)} 条记录（显示前10条）:")
    print()
    
    for i, obs in enumerate(observations[:10], 1):
        tags = obs.tags_json or {}
        print(f"[{i}] obs_date={obs.obs_date}, period={obs.period_start}~{obs.period_end}, value={obs.value}")
        print(f"    tags={json.dumps(tags, ensure_ascii=False)}")
        print()
    
    if len(observations) > 10:
        print(f"... 还有 {len(observations) - 10} 条记录")
    
    print("=" * 80)
    print("查询测试完成")
    print("=" * 80)
    
finally:
    db.close()
