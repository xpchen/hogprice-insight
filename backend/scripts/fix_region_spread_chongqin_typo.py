#!/usr/bin/env python3
"""
说明：fact_spread_daily.spread_type 为 VARCHAR(32)，而 region_spread_GUANGDONG_CHONGQING 为 35 字符，
历史数据因此被存成 region_spread_GUANGDONG_CHONGQIN。API 已在查询时兼容该拼写，无需改库即可展示广东-重庆。
若需在库中统一为 CHONGQING，请先执行 ALTER TABLE fact_spread_daily MODIFY spread_type VARCHAR(64);
再运行本脚本（取消下方注释并执行 UPDATE）。
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
        one = conn.execute(
            text("SELECT COUNT(*) FROM fact_spread_daily WHERE spread_type = 'region_spread_GUANGDONG_CHONGQIN'")
        ).scalar()
    print(f"Rows with region_spread_GUANGDONG_CHONGQIN: {one}. API already accepts this; no DB change required.")
    # 若已把 spread_type 改为 VARCHAR(64)，可取消下面注释并执行：
    # with engine.begin() as conn:
    #     r = conn.execute(text("UPDATE fact_spread_daily SET spread_type = 'region_spread_GUANGDONG_CHONGQING' WHERE spread_type = 'region_spread_GUANGDONG_CHONGQIN'"))
    #     print("Updated", r.rowcount, "rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
