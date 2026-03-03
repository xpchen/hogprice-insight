"""验证出栏均重合并逻辑：NATION + 省均"""
import sys
from datetime import date

sys.path.insert(0, ".")
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
start = date(2020, 1, 1)
end = date(2026, 12, 31)

# 1. NATION 直接数据
nation = db.execute(text("""
    SELECT week_end, value, unit, region_code
    FROM fact_weekly_indicator
    WHERE indicator_code = 'weight_avg' AND region_code = 'NATION' AND source = 'YONGYI'
      AND week_end >= :start AND week_end <= :end
    ORDER BY week_end DESC
"""), {"start": start, "end": end}).fetchall()
have_weeks = {r[0] for r in nation}
print("NATION rows:", len(nation), "years:", sorted({r[0].year for r in nation}))

# 2. 省均补充
fill = db.execute(text("""
    SELECT week_end, ROUND(AVG(value), 2) as value, MIN(unit) as unit, 'NATION' as region_code
    FROM fact_weekly_indicator
    WHERE indicator_code = 'weight_avg' AND region_code != 'NATION' AND source = 'YONGYI'
      AND week_end >= :start AND week_end <= :end
    GROUP BY week_end
    ORDER BY week_end DESC
"""), {"start": start, "end": end}).fetchall()
fill_added = [r for r in fill if r[0] not in have_weeks]
print("Fill rows (new weeks):", len(fill_added), "years:", sorted({r[0].year for r in fill_added}))

merged = list(nation) + fill_added
merged.sort(key=lambda x: x[0], reverse=True)
all_years = sorted({r[0].year for r in merged})
print("Merged total:", len(merged), "years:", all_years)
db.close()
