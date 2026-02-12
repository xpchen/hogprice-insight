# -*- coding: utf-8 -*-
"""检查波动率数据及API逻辑"""
import sys
import io
from pathlib import Path
from datetime import date

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.fact_futures_daily import FactFuturesDaily


def is_in_seasonal_range(date_obj: date, contract_month: int) -> bool:
    month = date_obj.month
    start_month = (contract_month + 1) % 12
    if start_month == 0:
        start_month = 12
    end_month = contract_month - 1
    if end_month == 0:
        end_month = 12
    if start_month > end_month:
        return month >= start_month or month <= end_month
    return start_month <= month <= end_month


def main():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("波动率数据检查")
        print("=" * 60)
        
        total = db.query(func.count(FactFuturesDaily.id)).scalar()
        print(f"\n1. fact_futures_daily 总记录数: {total}")
        if total == 0:
            print("   ❌ 无数据！请先导入期货数据（lh_ftr.xlsx）")
            return
        
        min_d = db.query(func.min(FactFuturesDaily.trade_date)).scalar()
        max_d = db.query(func.max(FactFuturesDaily.trade_date)).scalar()
        print(f"   日期范围: {min_d} 至 {max_d}")
        
        print("\n2. 按合约月份统计:")
        for month in [1, 3, 5, 7, 9, 11]:
            month_str = f"{month:02d}"
            rows = db.query(FactFuturesDaily).filter(
                FactFuturesDaily.contract_code.like(f"%{month_str}")
            ).order_by(FactFuturesDaily.trade_date).all()
            cnt = len(rows)
            print(f"   {month_str}合约: {cnt} 条")
            if cnt > 0:
                dates = [r.trade_date for r in rows]
                in_range = sum(1 for d in dates if is_in_seasonal_range(d, month))
                print(f"      季节性范围内(4月1日~2月28日等): {in_range} 条")
                # 10日波动率需要至少20个交易日
                need_for_10d = 20
                if cnt >= need_for_10d:
                    print(f"      ✓ 足够计算10日波动率(需≥{need_for_10d}天)")
                else:
                    print(f"      ⚠ 不足20天，无法计算10日波动率")
        
        print("\n3. 模拟波动率API查询（03合约）:")
        month_str = "03"
        rows = db.query(FactFuturesDaily).filter(
            FactFuturesDaily.contract_code.like(f"%{month_str}")
        ).order_by(FactFuturesDaily.trade_date).all()
        
        if not rows:
            print("   无03合约数据")
            return
        
        date_dict = {}
        for r in rows:
            if r.trade_date not in date_dict:
                date_dict[r.trade_date] = []
            date_dict[r.trade_date].append(r)
        
        sorted_dates = sorted(date_dict.keys())
        print(f"   去重后交易日数: {len(sorted_dates)}")
        
        in_seasonal = [d for d in sorted_dates if is_in_seasonal_range(d, 3)]
        print(f"   季节性范围内: {len(in_seasonal)} 天")
        
        # 10日波动率：从第20天起
        window = 10
        first_vol_idx = 2 * window - 1  # 19
        if len(sorted_dates) > first_vol_idx:
            first_vol_date = sorted_dates[first_vol_idx]
            print(f"   首个可计算10日波动率的日期: {first_vol_date} (第{first_vol_idx+1}天)")
            if is_in_seasonal_range(first_vol_date, 3):
                print(f"   ✓ 该日在季节性范围内，应有输出")
            else:
                print(f"   ✗ 该日不在季节性范围内，会被过滤")
        else:
            print(f"   ⚠ 仅有{len(sorted_dates)}天，不足{first_vol_idx+1}天，无法计算10日波动率")
        
        print("\n4. 检查 contract_code 格式:")
        sample = rows[0]
        print(f"   示例: {sample.contract_code} (trade_date={sample.trade_date})")
        print(f"   LIKE '%03' 会匹配以03结尾的合约，如 lh2603")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
