"""
核对 fact_slaughter_daily 在 2021～2025 各农历年（正月初八～腊月二十八）区间的数据完整性。
输出：各年正月初八/腊月二十八的阳历日期、库内该区间的最早/最晚日期与条数，并判断是否完整。
"""
import sys
from pathlib import Path
from datetime import date

script_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(script_dir))

from app.core.database import engine
from app.services.lunar_alignment_service import get_lunar_year_date_range_la_ba
from sqlalchemy import text


def main():
    years = [2021, 2022, 2023, 2024, 2025]
    rows_out = []

    for ly in years:
        dr = get_lunar_year_date_range_la_ba(ly)
        if not dr:
            rows_out.append((ly, None, None, None, None, None, "无法计算农历区间"))
            continue
        start_solar, end_solar = dr
        with engine.connect() as conn:
            r = conn.execute(
                text("""
                    SELECT MIN(trade_date) AS first_d, MAX(trade_date) AS last_d, COUNT(*) AS cnt
                    FROM fact_slaughter_daily
                    WHERE region_code = 'NATION' AND source = 'YONGYI'
                      AND trade_date >= :start_date AND trade_date <= :end_date
                """),
                {"start_date": start_solar, "end_date": end_solar},
            ).fetchone()
        first_d, last_d, cnt = r[0], r[1], r[2]
        expected_days = (end_solar - start_solar).days + 1
        if first_d and last_d:
            actual_days = (last_d - first_d).days + 1
            ok = first_d <= start_solar and last_d >= end_solar and cnt >= expected_days * 0.95
            status = "完整" if ok else "不完整"
            gap_start = "缺首" if first_d > start_solar else ""
            gap_end = "缺尾" if last_d < end_solar else ""
            if gap_start or gap_end:
                status = status + "(" + gap_start + gap_end + ")"
        else:
            actual_days = 0
            status = "无数据"
        rows_out.append((ly, start_solar, end_solar, first_d, last_d, cnt, status))

    # 表头
    print("农历年 | 正月初八(阳历) | 腊月二十八(阳历) | 库内区间最早 | 库内区间最晚 | 条数 | 判定")
    print("-" * 100)
    for ly, start_solar, end_solar, first_d, last_d, cnt, status in rows_out:
        start_s = start_solar.isoformat() if start_solar else "-"
        end_s = end_solar.isoformat() if end_solar else "-"
        first_s = first_d.isoformat() if first_d else "-"
        last_s = last_d.isoformat() if last_d else "-"
        cnt_s = str(cnt) if cnt is not None else "0"
        print(f"  {ly}   | {start_s} | {end_s} | {first_s} | {last_s} | {cnt_s} | {status}")
    print()

    # 全表日期范围
    with engine.connect() as conn:
        r = conn.execute(
            text("""
                SELECT MIN(trade_date), MAX(trade_date), COUNT(*)
                FROM fact_slaughter_daily
                WHERE region_code = 'NATION' AND source = 'YONGYI'
            """)
        ).fetchone()
    print("fact_slaughter_daily (NATION, YONGYI) 全表: 最早 = %s, 最晚 = %s, 总条数 = %s" % (r[0], r[1], r[2]))


if __name__ == "__main__":
    main()
