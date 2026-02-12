# -*- coding: utf-8 -*-
"""直接测试波动率 API 逻辑（无需认证）"""
import sys
import io
from pathlib import Path
from datetime import date
import math

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal
from app.models.fact_futures_daily import FactFuturesDaily
from app.api.futures import calculate_volatility, is_in_seasonal_range


def main():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("波动率 API 逻辑测试")
        print("=" * 60)

        for month in [1, 3, 5]:
            month_str = f"{month:02d}"
            rows = db.query(FactFuturesDaily).filter(
                FactFuturesDaily.contract_code.like(f"%{month_str}")
            ).order_by(FactFuturesDaily.trade_date).all()

            if not rows:
                print(f"\n{month_str}合约: 无数据")
                continue

            date_dict = {}
            for r in rows:
                if r.trade_date not in date_dict:
                    date_dict[r.trade_date] = []
                date_dict[r.trade_date].append(r)

            sorted_dates = sorted(date_dict.keys())
            prices = []
            for d in sorted_dates:
                best = max(date_dict[d], key=lambda x: x.open_interest or 0)
                close = float(best.close) if best.close else None
                prices.append(close)

            data_points = []
            for i in range(len(prices)):
                if prices[i] is None:
                    continue
                trade_date = sorted_dates[i]
                if not is_in_seasonal_range(trade_date, month):
                    continue
                vol = calculate_volatility(prices, i, 10)
                if vol is not None:
                    data_points.append((trade_date, vol))

            print(f"\n{month_str}合约: 原始{len(rows)}条, 日期{len(sorted_dates)}天, 波动率输出{len(data_points)}个")
            if data_points:
                for d, v in data_points[:5]:
                    print(f"   {d}: {v:.2f}%")
                if len(data_points) > 5:
                    print(f"   ... 共{len(data_points)}个")
            else:
                print("   ⚠ 无波动率输出（可能天数不足20）")

    finally:
        db.close()


if __name__ == "__main__":
    main()
