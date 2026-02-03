# -*- coding: utf-8 -*-
"""测试升贴水API"""
import sys
import io
from pathlib import Path
from datetime import date, datetime, timedelta

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

def test_premium_logic():
    """测试升贴水计算逻辑"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("测试升贴水API逻辑")
        print("=" * 80)
        
        # 模拟API的逻辑
        contract_months = [3, 5, 7, 9, 11, 1]
        
        # 确定年份范围
        min_year = db.query(func.min(extract('year', FactFuturesDaily.trade_date))).scalar()
        max_year = db.query(func.max(extract('year', FactFuturesDaily.trade_date))).scalar()
        if min_year and max_year:
            years = list(range(min_year, max_year + 1))
        else:
            years = [2026]
        
        print(f"\n年份范围: {years}")
        
        # 查找全国现货价格指标
        metric = db.query(DimMetric).filter(
            or_(
                DimMetric.raw_header.like("%中国%"),
                DimMetric.raw_header.like("%全国%")
            ),
            DimMetric.sheet_name == "分省区猪价",
            DimMetric.freq.in_(["D", "daily"])
        ).first()
        
        if not metric:
            print("❌ 未找到全国现货价格指标")
            return
        
        print(f"\n找到现货价格指标: {metric.metric_name} (ID: {metric.id})")
        
        for month in contract_months:
            print(f"\n{'='*80}")
            print(f"测试 {month:02d}合约:")
            print(f"{'='*80}")
            
            month_str = f"{month:02d}"
            date_dict = {}
            
            # 直接查询该月份的所有合约数据（不限制时间范围）
            futures_data = db.query(FactFuturesDaily).filter(
                FactFuturesDaily.contract_code.like(f"%{month_str}")
            ).order_by(FactFuturesDaily.trade_date).all()
            
            print(f"  找到 {len(futures_data)} 条期货数据")
            
            if futures_data:
                min_d = min(f.trade_date for f in futures_data)
                max_d = max(f.trade_date for f in futures_data)
                print(f"  日期范围: {min_d} 至 {max_d}")
            
            # 按日期分组
            for f in futures_data:
                if f.trade_date not in date_dict:
                    date_dict[f.trade_date] = []
                date_dict[f.trade_date].append(f)
            
            print(f"\n  总共收集到 {len(date_dict)} 个日期的数据")
            
            # 测试计算升贴水
            if date_dict:
                test_dates = sorted(date_dict.keys())[:3]  # 取前3个日期测试
                print(f"\n  测试前3个日期的升贴水计算:")
                for test_date in test_dates:
                    contracts = date_dict[test_date]
                    best_contract = max(contracts, key=lambda x: x.open_interest or 0)
                    
                    futures_settle_raw = float(best_contract.settle) if best_contract.settle else None
                    futures_settle = futures_settle_raw / 1000.0 if futures_settle_raw is not None else None
                    
                    spot = db.query(FactObservation).filter(
                        FactObservation.metric_id == metric.id,
                        FactObservation.obs_date == test_date,
                        FactObservation.period_type == "day"
                    ).first()
                    
                    spot_price = float(spot.value) if spot and spot.value else None
                    
                    premium = None
                    if futures_settle is not None and spot_price is not None:
                        premium = futures_settle - spot_price
                    
                    premium_str = f"{premium:.2f}" if premium is not None else "N/A"
                    print(f"    {test_date}: 期货={futures_settle:.2f}, 现货={spot_price:.2f}, 升贴水={premium_str}")
            else:
                print(f"  ❌ 没有找到数据")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_premium_logic()
