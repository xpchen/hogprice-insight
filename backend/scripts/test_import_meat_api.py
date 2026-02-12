"""
测试猪肉进口API（实际是猪价系数）
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation
from sqlalchemy import func, or_

def test_import_meat_api():
    """测试猪肉进口API（实际是猪价系数）"""
    db: Session = SessionLocal()
    try:
        print("=" * 80)
        print("测试猪肉进口API（猪价系数）")
        print("=" * 80)
        
        # 1. 获取钢联全国猪价数据
        print("\n1. 查找钢联全国猪价指标:")
        price_metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价",
            or_(
                DimMetric.raw_header.like('%中国%'),
                DimMetric.raw_header.like('%全国%')
            ),
            DimMetric.freq.in_(["D", "daily"])
        ).first()
        
        if not price_metric:
            price_metric = db.query(DimMetric).filter(
                DimMetric.sheet_name.like('%钢联%'),
                or_(
                    DimMetric.raw_header.like('%全国%价%'),
                    DimMetric.raw_header.like('%中国%价%')
                ),
                DimMetric.freq.in_(["D", "daily"])
            ).first()
        
        if not price_metric:
            print("  ✗ 未找到钢联全国猪价指标")
            return
        
        print(f"  ✓ 找到指标: {price_metric.metric_name}")
        print(f"    Sheet: {price_metric.sheet_name}")
        print(f"    Header: {price_metric.raw_header}")
        
        # 2. 查询价格数据并按月聚合
        print("\n2. 查询月度价格数据:")
        price_monthly = db.query(
            func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
            func.avg(FactObservation.value).label('monthly_avg')
        ).filter(
            FactObservation.metric_id == price_metric.id,
            FactObservation.period_type == 'day'
        ).group_by('month').order_by('month').all()
        
        if not price_monthly:
            print("  ✗ 没有月度价格数据")
            return
        
        print(f"  ✓ 找到 {len(price_monthly)} 个月的数据")
        
        # 3. 计算历年平均值
        print("\n3. 计算历年平均值:")
        price_values = [float(item.monthly_avg) for item in price_monthly if item.monthly_avg]
        price_avg = sum(price_values) / len(price_values) if price_values else None
        
        if not price_avg or price_avg <= 0:
            print("  ✗ 无法计算平均值")
            return
        
        print(f"  ✓ 历年平均值: {price_avg:.2f}")
        
        # 4. 计算系数
        print("\n4. 计算猪价系数:")
        data_points = []
        for item in price_monthly:
            if not item.monthly_avg:
                continue
            
            month_str = item.month
            monthly_avg = float(item.monthly_avg)
            price_coef = monthly_avg / price_avg
            
            data_points.append({
                'month': month_str,
                'price_coefficient': round(price_coef, 4)
            })
        
        print(f"  ✓ 计算了 {len(data_points)} 个数据点")
        
        # 5. 显示结果
        print("\n5. 数据样本:")
        print(f"\n  前10个数据点:")
        for item in data_points[:10]:
            print(f"    {item['month']}: 系数={item['price_coefficient']}")
        
        print(f"\n  后10个数据点:")
        for item in data_points[-10:]:
            print(f"    {item['month']}: 系数={item['price_coefficient']}")
        
        latest_month = data_points[-1]['month'] if data_points else None
        print(f"\n  最新月份: {latest_month}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_import_meat_api()
