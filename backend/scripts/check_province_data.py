"""检查各省份在fact_observation表中的数据情况"""
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


def check_province_data():
    """检查各省份的数据"""
    print("\n" + "="*80)
    print("检查各省份在fact_observation表中的数据")
    print("="*80)
    
    db = SessionLocal()
    try:
        # 查询"肥标价差"sheet下的所有指标（排除"中国"）
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "肥标价差",
            ~DimMetric.raw_header.like("%中国%")
        ).all()
        
        print(f"\n  找到 {len(metrics)} 个指标\n")
        print(f"  {'省份':<10} {'指标ID':<10} {'数据条数':<12} {'最新日期':<12} {'最新值':<12}")
        print(f"  {'-'*10} {'-'*10} {'-'*12} {'-'*12} {'-'*12}")
        
        provinces_with_data = []
        provinces_without_data = []
        
        for metric in metrics:
            # 从raw_header中提取省区名称
            raw_header = metric.raw_header
            province_name = None
            
            match = re.search(r'：([^：（）]+)（', raw_header)
            if match:
                province_name = match.group(1).strip()
            
            if not province_name:
                continue
            
            # 查询该指标的数据条数
            count = db.query(FactObservation).filter(
                FactObservation.metric_id == metric.id
            ).count()
            
            # 查询最新数据
            latest_obs = db.query(FactObservation).filter(
                FactObservation.metric_id == metric.id
            ).order_by(FactObservation.obs_date.desc()).first()
            
            latest_date = latest_obs.obs_date if latest_obs else None
            latest_value = float(latest_obs.value) if latest_obs and latest_obs.value else None
            
            if count > 0:
                provinces_with_data.append(province_name)
                latest_date_str = latest_date.isoformat() if latest_date else "N/A"
                latest_value_str = f"{latest_value:.2f}" if latest_value is not None else "N/A"
                print(f"  {province_name:<10} {metric.id:<10} {count:<12} {latest_date_str:<12} {latest_value_str:<12}")
            else:
                provinces_without_data.append(province_name)
                print(f"  {province_name:<10} {metric.id:<10} {'0':<12} {'N/A':<12} {'N/A':<12} ⚠️")
        
        print(f"\n  总结：")
        print(f"    - 有数据的省份: {len(provinces_with_data)} 个")
        if provinces_with_data:
            print(f"      {', '.join(sorted(provinces_with_data))}")
        print(f"    - 无数据的省份: {len(provinces_without_data)} 个")
        if provinces_without_data:
            print(f"      {', '.join(sorted(provinces_without_data))}")
        
    finally:
        db.close()


if __name__ == "__main__":
    check_province_data()
