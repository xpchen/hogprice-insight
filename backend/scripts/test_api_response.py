"""测试API返回的数据格式"""
import sys
import os
import io
import re
import json
from pathlib import Path
from datetime import date

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


def test_api_response(province_name: str):
    """测试API返回的数据格式"""
    print(f"\n测试API返回格式 - 省份: {province_name}")
    print("="*60)
    
    db = SessionLocal()
    try:
        # 查询指定省区的标肥价差指标
        metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "肥标价差",
            DimMetric.raw_header.like(f"%{province_name}%")
        ).first()
        
        if not metric:
            print(f"  ❌ 未找到指标")
            return
        
        # 构建查询
        query = db.query(FactObservation).filter(
            FactObservation.metric_id == metric.id,
            FactObservation.period_type == "day"
        )
        
        observations = query.order_by(FactObservation.obs_date).all()
        
        if not observations:
            print(f"  ⚠️  没有数据")
            return
        
        print(f"  ✓ 找到 {len(observations)} 条数据")
        
        # 按年份分组（模拟API逻辑）
        year_data = {}
        for obs in observations:
            year = obs.obs_date.year
            if year not in year_data:
                year_data[year] = []
            
            month_day = obs.obs_date.strftime("%m-%d")
            year_data[year].append({
                "month_day": month_day,
                "value": float(obs.value) if obs.value else None,
                "date": obs.obs_date
            })
        
        # 构建series（模拟API逻辑）
        series = []
        for year in sorted(year_data.keys()):
            data_points = []
            for item in sorted(year_data[year], key=lambda x: x["date"]):
                data_points.append({
                    "year": year,
                    "month_day": item["month_day"],
                    "value": item["value"]
                })
            
            series.append({
                "year": year,
                "data": data_points
            })
        
        print(f"  ✓ 构建了 {len(series)} 个年份的series")
        print(f"  年份: {[s['year'] for s in series]}")
        
        # 检查每个series的数据点数量
        for s in series:
            print(f"    {s['year']}年: {len(s['data'])} 个数据点")
            if len(s['data']) > 0:
                print(f"      第一个: {s['data'][0]}")
                print(f"      最后一个: {s['data'][-1]}")
        
        # 检查是否有空series
        empty_series = [s for s in series if len(s['data']) == 0]
        if empty_series:
            print(f"  ⚠️  发现 {len(empty_series)} 个空series: {[s['year'] for s in empty_series]}")
        else:
            print(f"  ✓ 所有series都有数据")
            
    finally:
        db.close()


def main():
    """主函数"""
    # 测试几个省份
    test_provinces = ["湖南", "河南", "湖北"]
    
    for province in test_provinces:
        test_api_response(province)


if __name__ == "__main__":
    main()
