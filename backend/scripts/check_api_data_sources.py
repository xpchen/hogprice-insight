"""Quick check of actual values in hogprice_v3 tables"""
import sys
sys.path.insert(0, ".")
from app.core.database import engine
from sqlalchemy import text

def main():
    with engine.connect() as conn:
        print("=== fact_price_daily NATION ===")
        r = conn.execute(text(
            "SELECT DISTINCT price_type, source FROM fact_price_daily WHERE region_code='NATION'"
        )).fetchall()
        for row in r:
            print("  ", row[0], "|", row[1])

        print("\n=== fact_spread_daily NATION ===")
        r2 = conn.execute(text(
            "SELECT DISTINCT spread_type, source FROM fact_spread_daily WHERE region_code='NATION'"
        )).fetchall()
        for row in r2:
            print("  ", row[0], "|", row[1])

        print("\n=== fact_slaughter_daily NATION? ===")
        r3a = conn.execute(text(
            "SELECT region_code, source, COUNT(*) FROM fact_slaughter_daily WHERE region_code='NATION' GROUP BY region_code, source"
        )).fetchall()
        for row in r3a:
            print("  ", row[0], "|", row[1], "|", row[2])
        if not r3a:
            print("  (no NATION - check regions)")
        r3 = conn.execute(text(
            "SELECT region_code, source, COUNT(*) FROM fact_slaughter_daily GROUP BY region_code, source LIMIT 5"
        )).fetchall()
        for row in r3:
            print("  sample:", row[0], "|", row[1], "|", row[2])

        print("\n=== fact_spread_daily std_fat / fat_std / 标肥 ===")
        r2b = conn.execute(text(
            "SELECT DISTINCT spread_type FROM fact_spread_daily"
        )).fetchall()
        print("  all spread_type:", [x[0] for x in r2b])

        print("\n=== fact_quarterly_stats indicator_codes ===")
        r4 = conn.execute(text(
            "SELECT DISTINCT indicator_code FROM fact_quarterly_stats WHERE region_code='NATION' ORDER BY indicator_code"
        )).fetchall()
        for row in r4:
            print("  ", row[0])

if __name__ == "__main__":
    main()
