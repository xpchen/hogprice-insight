#!/usr/bin/env python3
"""
检查 fact_spread_daily 中区域价差数据，重点核查广东-重庆等。
若 Excel（docs/0306_生猪/生猪/1、价格：钢联自动更新模板.xlsx）有对应列但库中无数据，
说明需使用该 Excel 所在目录重新执行导入。
"""
import os
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)

def main():
    from sqlalchemy import text
    from import_tool.db import get_engine

    engine = get_engine()
    with engine.connect() as conn:
        # 所有区域价差类型
        rows = conn.execute(text("""
            SELECT spread_type, COUNT(*) AS cnt, MIN(trade_date) AS min_d, MAX(trade_date) AS max_d
            FROM fact_spread_daily
            WHERE spread_type LIKE 'region_spread_%'
            GROUP BY spread_type
            ORDER BY spread_type
        """)).fetchall()

        print("fact_spread_daily region_spread_* summary:")
        if not rows:
            print("  (no region_spread data)")
        else:
            for r in rows:
                print(f"  {r[0]}: {r[1]} rows, {r[2]} ~ {r[3]}")

        target = "region_spread_GUANGDONG_CHONGQING"
        one = conn.execute(
            text("SELECT COUNT(*), MIN(trade_date), MAX(trade_date) FROM fact_spread_daily WHERE spread_type = :st"),
            {"st": target},
        ).fetchone()
        print(f"\nGuangdong-Chongqing ({target}):")
        if one and one[0] and one[0] > 0:
            print(f"  OK: {one[0]} rows, {one[1]} ~ {one[2]}")
        else:
            print("  MISSING. Re-import from: docs/0306_生猪/生猪/  using file 1、价格：钢联自动更新模板.xlsx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
