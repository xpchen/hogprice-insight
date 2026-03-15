import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir.parent))
sys.path.insert(0, str(script_dir.parent.parent))
from sqlalchemy import text
from app.core.database import engine
with engine.connect() as conn:
    r = conn.execute(text("""
        SELECT month_date, region_code, indicator, value
        FROM fact_enterprise_monthly
        WHERE company_code = 'TOTAL' AND region_code IN ('GUANGDONG','SICHUAN','GUIZHOU')
        ORDER BY month_date, region_code, indicator
    """)).fetchall()
    print("Total 汇总 records:", len(r))
    from collections import defaultdict
    keys = set()
    for row in r:
        ind = row[2]
        if "_" in ind:
            suffix = ind.rsplit("_", 1)[1]
            keys.add((row[0], suffix))
    print("Distinct (month_date, suffix):", len(keys))
    for k in sorted(keys):
        print(" ", k)
