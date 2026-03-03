# -*- coding: utf-8 -*-
"""检查 fact_monthly_indicator 中母猪效能、压栏系数及 E1 相关生产指标是否已导入"""
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# 1) 母猪效能、压栏系数（E1 页面季节性图用）
print("=" * 60)
print("1. 母猪效能 / 压栏系数（API 用 indicator_code + source=YONGYI）")
print("=" * 60)
rows = db.execute(text("""
    SELECT indicator_code, source, 
           MIN(month_date) AS min_date, MAX(month_date) AS max_date, COUNT(*) AS cnt
    FROM fact_monthly_indicator
    WHERE indicator_code IN ('prod_farrowing_count', 'prod_healthy_piglets_per_litter')
      AND source = 'YONGYI'
    GROUP BY indicator_code, source
""")).fetchall()
if not rows:
    print("  无数据。说明：母猪效能=prod_farrowing_count，压栏系数=prod_healthy_piglets_per_litter，来自涌益周度「月度-生产指标」sheet。")
else:
    for r in rows:
        print(f"  {r[0]} (source={r[1]}): {r[2]} ~ {r[3]}, 共 {r[4]} 条")

# 2) 涌益 月度-生产指标2 五指标（E1 涌益生产指标季节性）
print()
print("=" * 60)
print("2. 涌益生产指标2 五指标（月度-生产指标2 sheet）")
print("=" * 60)
codes = [
    "prod2_healthy_piglets_per_litter",  # 窝均健仔数
    "prod2_farrowing_survival_rate",      # 产房存活率
    "prod2_mating_farrowing_rate",         # 配种分娩率
    "prod2_weaning_survival_rate",        # 断奶成活率
    "prod2_fattening_survival_rate",       # 育肥出栏成活率
]
rows = db.execute(text("""
    SELECT indicator_code, MIN(month_date) AS min_date, MAX(month_date) AS max_date, COUNT(*) AS cnt
    FROM fact_monthly_indicator
    WHERE indicator_code IN :codes AND source = 'YONGYI'
    GROUP BY indicator_code
"""), {"codes": tuple(codes)}).fetchall()
if not rows:
    print("  无数据。")
else:
    for r in rows:
        print(f"  {r[0]}: {r[1]} ~ {r[2]}, 共 {r[3]} 条")

# 3) fact_monthly_indicator 中所有 source=YONGYI 的 indicator 概览
print()
print("=" * 60)
print("3. fact_monthly_indicator 中 source=YONGYI 的指标概览")
print("=" * 60)
rows = db.execute(text("""
    SELECT indicator_code, 
           MIN(month_date) AS min_date, MAX(month_date) AS max_date, COUNT(*) AS cnt
    FROM fact_monthly_indicator
    WHERE source = 'YONGYI'
    GROUP BY indicator_code
    ORDER BY indicator_code
""")).fetchall()
if not rows:
    print("  无 YONGYI 来源的月度指标。")
else:
    for r in rows:
        print(f"  {r[0]}: {r[1]} ~ {r[2]}, 共 {r[3]} 条")

# 4) A1 表格回退用的 NYB 等（能繁/新生仔猪/存栏/出栏）
print()
print("=" * 60)
print("4. A1 表格回退用：NYB 等指标（能繁/新生仔猪/存栏/出栏）")
print("=" * 60)
rows = db.execute(text("""
    SELECT indicator_code, source, sub_category,
           MIN(month_date) AS min_date, MAX(month_date) AS max_date, COUNT(*) AS cnt
    FROM fact_monthly_indicator
    WHERE indicator_code IN ('breeding_sow_inventory', 'piglet_inventory', 'hog_inventory', 'hog_turnover')
    GROUP BY indicator_code, source, sub_category
    ORDER BY indicator_code, source
""")).fetchall()
if not rows:
    print("  无数据。")
else:
    for r in rows:
        print(f"  {r[0]} (source={r[1]}, sub={r[2]}): {r[3]} ~ {r[4]}, 共 {r[5]} 条")

db.close()
print()
print("结论：若 1、2 无数据，则 E1 页母猪效能/压栏系数及涌益五指标图会空；需用 import_tool 导入涌益咨询周度数据.xlsx。")
