"""测试省份API查询"""
import sys
import os
import io
import re
from pathlib import Path

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.fact_observation import FactObservation
from app.models.dim_metric import DimMetric
from sqlalchemy import extract


def test_province_query(province_name: str):
    """测试查询指定省份的数据"""
    print(f"\n测试查询省份: {province_name}")
    print("="*60)
    
    db = SessionLocal()
    try:
        # 模拟API查询逻辑
        metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "肥标价差",
            DimMetric.raw_header.like(f"%{province_name}%")
        ).first()
        
        if not metric:
            print(f"  ❌ 未找到指标")
            print(f"  尝试查找所有指标...")
            all_metrics = db.query(DimMetric).filter(
                DimMetric.sheet_name == "肥标价差"
            ).all()
            print(f"  找到 {len(all_metrics)} 个指标:")
            for m in all_metrics:
                print(f"    - ID={m.id}, raw_header={m.raw_header}")
            return
        
        print(f"  ✓ 找到指标: ID={metric.id}, raw_header={metric.raw_header}")
        
        # 查询数据
        query = db.query(FactObservation).filter(
            FactObservation.metric_id == metric.id,
            FactObservation.period_type == "day"
        )
        
        observations = query.order_by(FactObservation.obs_date).all()
        
        print(f"  ✓ 找到 {len(observations)} 条数据")
        
        if len(observations) > 0:
            latest = observations[-1]
            print(f"  ✓ 最新数据: 日期={latest.obs_date}, 值={latest.value}")
            
            # 检查年份分布
            years = {}
            for obs in observations:
                year = obs.obs_date.year
                years[year] = years.get(year, 0) + 1
            
            print(f"  ✓ 年份分布:")
            for year in sorted(years.keys()):
                print(f"    {year}年: {years[year]} 条")
        else:
            print(f"  ⚠️  没有数据")
            
    finally:
        db.close()


def main():
    """主函数"""
    # 测试几个省份
    test_provinces = ["湖南", "河南", "湖北", "河北", "江西", "山西", "山东", "四川", "吉林"]
    
    for province in test_provinces:
        test_province_query(province)


if __name__ == "__main__":
    main()
