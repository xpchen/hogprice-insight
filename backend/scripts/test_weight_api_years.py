"""测试出栏均重 API 返回年份范围"""
import sys
from datetime import date

sys.path.insert(0, ".")
from app.core.database import SessionLocal
from app.api.observation import query_observations
from sqlalchemy.orm import Session

# 模拟 2020-2026 的请求
start = date(2020, 1, 1)
end = date(2026, 12, 31)
db = SessionLocal()
try:
    results = query_observations(
        source_code="YONGYI",
        metric_key="YY_W_OUT_WEIGHT",
        start_date=start,
        end_date=end,
        period_type="week",
        indicator="均重",
        geo_code="NATION",
        limit=500,
        offset=0,
        db=db,
        current_user=None,  # type: ignore
    )
except Exception as e:
    print("Error (need auth?):", e)
    db.close()
    sys.exit(1)

years = set()
for r in results:
    if r.obs_date:
        years.add(r.obs_date.year)
print("Years returned:", sorted(years))
print("Count:", len(results))
db.close()
