# -*- coding: utf-8 -*-
"""测试区域价差API查询逻辑"""
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

db = next(get_db())

try:
    # 测试查询"广东-广西"
    region_pair = "广东-广西"
    regions = region_pair.split('-')
    region1, region2 = regions[0].strip(), regions[1].strip()
    
    print(f"测试查询区域对: {region_pair}")
    print(f"  区域1: {region1}")
    print(f"  区域2: {region2}")
    print()
    
    # 使用新的查询逻辑
    metric = db.query(DimMetric).filter(
        DimMetric.sheet_name == "区域价差",
        DimMetric.raw_header.like(f"%{region1}%"),
        DimMetric.raw_header.like(f"%{region2}%")
    ).first()
    
    if metric:
        print(f"✓ 找到指标:")
        print(f"  ID: {metric.id}")
        print(f"  指标名称: {metric.metric_name}")
        print(f"  原始列名: {metric.raw_header}")
        print(f"  Sheet: {metric.sheet_name}")
    else:
        print(f"✗ 未找到指标")
    
    # 测试其他几个区域对
    test_pairs = ["广东-四川", "四川-山西", "浙江-河南"]
    print("\n测试其他区域对:")
    for pair in test_pairs:
        regions = pair.split('-')
        r1, r2 = regions[0].strip(), regions[1].strip()
        m = db.query(DimMetric).filter(
            DimMetric.sheet_name == "区域价差",
            DimMetric.raw_header.like(f"%{r1}%"),
            DimMetric.raw_header.like(f"%{r2}%")
        ).first()
        if m:
            print(f"  ✓ {pair}: 找到 (ID={m.id}, raw_header={m.raw_header[:50]}...)")
        else:
            print(f"  ✗ {pair}: 未找到")
            
finally:
    db.close()
