#!/usr/bin/env python
"""诊断升贴水数据覆盖：检查 fact_price_daily 与 fact_futures_daily 的日期范围，找出升贴水比率为空的原因"""
import sys
from pathlib import Path

script_dir = Path(__file__).parent.parent
sys.path.insert(0, str(script_dir))

from sqlalchemy import text
from app.core.database import SessionLocal


def main():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("1. fact_price_daily 全国现货各价格类型日期范围")
        print("=" * 60)
        rows = db.execute(text("""
            SELECT price_type, source,
                   MIN(trade_date) as min_date, MAX(trade_date) as max_date, COUNT(*) as cnt
            FROM fact_price_daily
            WHERE region_code = 'NATION' AND value IS NOT NULL
            GROUP BY price_type, source
            ORDER BY min_date
        """)).fetchall()
        if not rows:
            print("  ❌ fact_price_daily 无 NATION 数据！需导入涌益日度或钢联日度。")
        else:
            for r in rows:
                print(f"  {r[0]:20} {r[1]:10} {r[2]} ~ {r[3]} ({r[4]} 条)")

        print("\n" + "=" * 60)
        print("2. fact_futures_daily 期货结算价日期范围（按合约月）")
        print("=" * 60)
        rows = db.execute(text("""
            SELECT SUBSTRING(contract_code, -2) as month_str,
                   MIN(trade_date) as min_date, MAX(trade_date) as max_date, COUNT(*) as cnt
            FROM fact_futures_daily
            WHERE settle IS NOT NULL
            GROUP BY SUBSTRING(contract_code, -2)
            ORDER BY month_str
        """)).fetchall()
        if not rows:
            print("  ❌ fact_futures_daily 无数据！需导入 4.1 盘面结算价。")
        else:
            for r in rows:
                print(f"  {r[0]}月合约: {r[1]} ~ {r[2]} ({r[3]} 条)")

        print("\n" + "=" * 60)
        print("3. _get_national_spot_map（钢联优先，涌益填补缺日）")
        print("=" * 60)
        # 模拟合并逻辑
        gl = db.execute(text("""
            SELECT trade_date FROM fact_price_daily
            WHERE price_type = 'hog_avg_price' AND region_code = 'NATION' AND source = 'GANGLIAN' AND value IS NOT NULL
        """)).fetchall()
        yy = db.execute(text("""
            SELECT trade_date FROM fact_price_daily
            WHERE price_type = '全国均价' AND region_code = 'NATION' AND source = 'YONGYI' AND value IS NOT NULL
        """)).fetchall()
        dates_set = set(r[0] for r in gl) | set(r[0] for r in yy)
        if dates_set:
            print(f"  钢联 hog_avg_price: {len(gl)} 天")
            print(f"  涌益 全国均价: {len(yy)} 天（填补钢联缺日）")
            print(f"  合并后: {min(dates_set)} ~ {max(dates_set)} ({len(dates_set)} 天)")
        else:
            print("  ❌ 无现货数据，需导入钢联分省区猪价(中国列)或涌益日度汇总")

        print("\n" + "=" * 60)
        print("4. 结论")
        print("=" * 60)
        if not dates_set:
            print("  无现货数据 → 升贴水、升贴水比率均为空")
            print("  解决：导入钢联分省区猪价(中国列)或涌益日度汇总")
        else:
            min_d = min(dates_set)
            max_d = max(dates_set)
            if min_d.year > 2022:
                print(f"  现货数据从 {min_d.year} 年开始，2022-{min_d.year-1} 年无现货 → 该时段升贴水比率为空")
                print("  解决：导入更早区间的钢联分省区猪价(中国列)，与旧版数据源一致")
            else:
                print("  现货日期覆盖正常。若仍无升贴水比率，请检查 fact_futures_daily 与现货日期是否重叠。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
