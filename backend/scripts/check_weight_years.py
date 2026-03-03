"""检查 fact_weekly_indicator weight_avg 各来源的年份范围"""
import sys
sys.path.insert(0, ".")
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
r1 = db.execute(text("""
    SELECT source, MIN(YEAR(week_end)) as min_y, MAX(YEAR(week_end)) as max_y, COUNT(*) as cnt
    FROM fact_weekly_indicator
    WHERE indicator_code = :ic AND region_code = :rc
    GROUP BY source
"""), {"ic": "weight_avg", "rc": "NATION"}).fetchall()
print("weight_avg NATION by source:", r1)
r2 = db.execute(text("""
    SELECT source, MIN(YEAR(week_end)) as min_y, MAX(YEAR(week_end)) as max_y, COUNT(*) as cnt
    FROM fact_weekly_indicator
    WHERE indicator_code = :ic AND region_code != :rc
    GROUP BY source
"""), {"ic": "weight_avg", "rc": "NATION"}).fetchall()
print("weight_avg province by source:", r2)
db.close()
