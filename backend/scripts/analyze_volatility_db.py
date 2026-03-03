# -*- coding: utf-8 -*-
"""分析波动率相关数据库数据，诊断为何波动率不显示"""
import sys
import io
from pathlib import Path
from datetime import date

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import func, text
from app.core.database import SessionLocal
from app.api.futures import calculate_volatility, is_in_seasonal_range


def main():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("波动率数据库数据分析（模拟 API 取数与计算）")
        print("=" * 70)

        # 使用 raw SQL 避免表缺 instrument 列时 ORM 报错
        total = db.execute(text("SELECT COUNT(*) FROM fact_futures_daily")).scalar() or 0
        print(f"\n【1. fact_futures_daily 总览】")
        print(f"    总记录数: {total}")
        if total == 0:
            print("    ❌ 表无数据！请先导入 4.1 盘面结算价 或 lh_ftr.xlsx")
            return

        min_max = db.execute(text("SELECT MIN(trade_date), MAX(trade_date) FROM fact_futures_daily")).first()
        min_d, max_d = min_max[0], min_max[1]
        print(f"    日期范围: {min_d} ~ {max_d}")

        has_close = db.execute(text(
            "SELECT COUNT(*) FROM fact_futures_daily WHERE `close` IS NOT NULL AND `close` > 0"
        )).scalar() or 0
        has_settle = db.execute(text(
            "SELECT COUNT(*) FROM fact_futures_daily WHERE settle IS NOT NULL AND settle > 0"
        )).scalar() or 0
        print(f"    有 close>0 的记录: {has_close}")
        print(f"    有 settle>0 的记录: {has_settle}")
        if has_close == 0 and has_settle == 0:
            print("    ❌ 没有有效价格(close/settle)，波动率无法计算")

        samples = db.execute(text("SELECT DISTINCT contract_code FROM fact_futures_daily LIMIT 15")).fetchall()
        codes = [s[0] for s in samples]
        print(f"    contract_code 样本: {codes[:10]}...")

        print("\n【2. 按合约月份（API 用 LIKE '%01'/'%03' 等）】")
        for month in [1, 3, 5, 7, 9, 11]:
            month_str = f"{month:02d}"
            rows = db.execute(text(
                "SELECT trade_date, contract_code, `close`, settle, open_interest FROM fact_futures_daily "
                "WHERE contract_code LIKE :pat ORDER BY trade_date"
            ), {"pat": f"%{month_str}"}).fetchall()

            cnt = len(rows)
            if cnt == 0:
                print(f"    {month_str}合约: 0 条 (LIKE '%{month_str}' 无匹配)")
                continue

            # 与 API 一致：按交易日分组，取当日 open_interest 最大；价格用 settle（4.1 盘面 close 为空）
            date_dict = {}
            for r in rows:
                td = r[0]
                if td not in date_dict:
                    date_dict[td] = []
                date_dict[td].append(r)

            sorted_dates = sorted(date_dict.keys())
            num_dates = len(sorted_dates)
            prices = []
            date_list = []
            for d in sorted_dates:
                best = max(date_dict[d], key=lambda x: x[4] or 0)
                raw = best[2] if (best[2] is not None and float(best[2] or 0) > 0) else best[3]
                p = float(raw) if raw is not None else None
                prices.append(p)
                date_list.append(d)

            valid_prices = sum(1 for p in prices if p is not None and p > 0)
            in_seasonal = sum(1 for i in range(len(prices)) if prices[i] and prices[i] > 0 and is_in_seasonal_range(date_list[i], month))
            # 能产出波动率的点数（需要 i>=2*window_days 且 in_seasonal）
            window = 10
            vol_outputs = 0
            for i in range(len(prices)):
                if prices[i] is None or prices[i] <= 0:
                    continue
                if not is_in_seasonal_range(date_list[i], month):
                    continue
                vol = calculate_volatility(prices, i, window)
                if vol is not None:
                    vol_outputs += 1

            print(f"    {month_str}合约: 原始{cnt}条 -> 去重后{num_dates}个交易日")
            print(f"        有效价格(close或settle): {valid_prices} 天, 季节性范围内: {in_seasonal} 天")
            print(f"        10日波动率可输出点数: {vol_outputs}")
            if num_dates < 20:
                print(f"        ⚠ 交易日<20，无法产出10日波动率")
            elif valid_prices == 0:
                print(f"        ⚠ 无有效价格(close/settle 均为空?)")
            elif vol_outputs == 0 and in_seasonal > 0:
                print(f"        ⚠ 有季节性数据但波动率输出为0，可能前20天都不在季节性范围内")

        # 3. 模拟 03 合约完整链路
        print("\n【3. 03 合约模拟 API 全链路】")
        month_str = "03"
        month = 3
        rows03 = db.execute(text(
            "SELECT trade_date, contract_code, `close`, settle, open_interest FROM fact_futures_daily "
            "WHERE contract_code LIKE :pat ORDER BY trade_date"
        ), {"pat": f"%{month_str}"}).fetchall()
        if not rows03:
            print("    无 03 合约数据")
        else:
            date_dict = {}
            for r in rows03:
                td = r[0]
                if td not in date_dict:
                    date_dict[td] = []
                date_dict[td].append(r)
            sorted_dates = sorted(date_dict.keys())
            prices = []
            date_list = []
            for d in sorted_dates:
                best = max(date_dict[d], key=lambda x: x[4] or 0)
                raw = best[2] if (best[2] is not None and float(best[2] or 0) > 0) else best[3]
                p = float(raw) if raw is not None else None
                prices.append(p)
                date_list.append(d)
            print(f"    交易日数: {len(prices)}, 有效价格数: {sum(1 for p in prices if p)}")
            if len(prices) >= 20:
                d19 = date_list[19]
                print(f"    第20天日期: {d19}, 在季节性范围: {is_in_seasonal_range(d19, 3)}")
                vol19 = calculate_volatility(prices, 19, 10)
                print(f"    第20天 10日波动率: {vol19}")
            print("    前5天样本: 日期, close, settle, open_interest")
            for i in range(min(5, len(date_list))):
                best = max(date_dict[date_list[i]], key=lambda x: x[4] or 0)
                print(f"      {date_list[i]}: close={best[2]}, settle={best[3]}, oi={best[4]}")

        print("\n" + "=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
