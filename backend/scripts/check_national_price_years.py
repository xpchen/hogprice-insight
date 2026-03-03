"""Check which years have national price data in fact_price_daily"""
import sys
sys.path.insert(0, ".")
from app.core.database import engine
from sqlalchemy import text

def main():
    with engine.connect() as conn:
        print("=== fact_price_daily NATION - years with data ===")
        for price_type, source in [
            ("标猪均价", "YONGYI"),
            ("全国均价", "YONGYI"),
            ("hog_avg_price", "GANGLIAN"),
        ]:
            r = conn.execute(text("""
                SELECT YEAR(trade_date) as y, COUNT(*) as cnt
                FROM fact_price_daily
                WHERE price_type = :pt AND region_code = 'NATION' AND source = :src
                GROUP BY YEAR(trade_date)
                ORDER BY y
            """), {"pt": price_type, "src": source}).fetchall()
            if r:
                print(f"  {price_type} ({source}): {[x[0] for x in r]} - counts: {[x[1] for x in r]}")
            else:
                print(f"  {price_type} ({source}): (no data)")

if __name__ == "__main__":
    main()
