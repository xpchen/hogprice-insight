"""
测试供需曲线API
"""
# -*- coding: utf-8 -*-
import sys
import io
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation

def test_api():
    """测试API逻辑"""
    print("=" * 80)
    print("测试供需曲线API数据查询")
    print("=" * 80)
    
    db: Session = SessionLocal()
    try:
        # 1. 查找定点屠宰数据
        print("\n1. 查找定点屠宰数据:")
        slaughter_metrics = db.query(DimMetric).filter(
            or_(
                DimMetric.raw_header.like('%日度屠宰量%'),
                DimMetric.raw_header.like('%日屠宰量%'),
                DimMetric.raw_header.like('%屠宰量合计%')
            ),
            DimMetric.freq == "D"
        ).all()
        
        print(f"  找到 {len(slaughter_metrics)} 个屠宰指标")
        for m in slaughter_metrics:
            print(f"    - ID: {m.id}, 名称: {m.metric_name}, 表头: {m.raw_header}, sheet: {m.sheet_name}")
            count = db.query(FactObservation).filter(
                FactObservation.metric_id == m.id,
                FactObservation.period_type == 'day'
            ).count()
            print(f"      数据条数: {count}")
            
            if count > 0:
                # 测试按月聚合
                monthly = db.query(
                    func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
                    func.avg(FactObservation.value).label('monthly_avg')
                ).filter(
                    FactObservation.metric_id == m.id,
                    FactObservation.period_type == 'day'
                ).group_by('month').order_by('month').limit(5).all()
                
                print(f"      月度聚合示例（前5条）:")
                for item in monthly:
                    print(f"        {item.month}: {item.monthly_avg}")
        
        # 2. 查找钢联全国猪价数据
        print("\n\n2. 查找钢联全国猪价数据:")
        # 优先查找：分省区猪价sheet中的"中国"列
        price_metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "分省区猪价",
            or_(
                DimMetric.raw_header.like('%中国%'),
                DimMetric.raw_header.like('%全国%')
            ),
            DimMetric.freq.in_(["D", "daily"])
        ).all()
        
        print(f"  找到 {len(price_metrics)} 个钢联全国价格指标")
        for m in price_metrics:
            print(f"    - ID: {m.id}, 名称: {m.metric_name}, 表头: {m.raw_header}, sheet: {m.sheet_name}")
            count = db.query(FactObservation).filter(
                FactObservation.metric_id == m.id,
                FactObservation.period_type == 'day'
            ).count()
            print(f"      数据条数: {count}")
            
            if count > 0:
                monthly = db.query(
                    func.date_format(FactObservation.obs_date, '%Y-%m-01').label('month'),
                    func.avg(FactObservation.value).label('monthly_avg')
                ).filter(
                    FactObservation.metric_id == m.id,
                    FactObservation.period_type == 'day'
                ).group_by('month').order_by('month').limit(5).all()
                
                print(f"      月度聚合示例（前5条）:")
                for item in monthly:
                    print(f"        {item.month}: {item.monthly_avg}")
        
        # 3. 如果没有找到，尝试其他查询方式
        if len(price_metrics) == 0:
            print("\n\n3. 尝试其他方式查找钢联价格数据:")
            # 查找所有钢联相关的指标
            all_ganglian = db.query(DimMetric).filter(
                DimMetric.sheet_name.like('%钢联%')
            ).limit(10).all()
            
            print(f"  找到 {len(all_ganglian)} 个钢联相关指标:")
            for m in all_ganglian:
                print(f"    - ID: {m.id}, 名称: {m.metric_name}, 表头: {m.raw_header}, sheet: {m.sheet_name}, freq: {m.freq}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_api()
