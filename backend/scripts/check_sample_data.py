"""查看示例数据"""
import sys
import os
import io
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from sqlalchemy import func, text

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

db = SessionLocal()
try:
    metric = db.query(DimMetric).filter(
        func.json_unquote(
            func.json_extract(DimMetric.parse_json, '$.metric_key')
        ) == 'YY_W_OUT_WEIGHT'
    ).first()
    
    sql = """
    SELECT 
        fo.id,
        fo.obs_date,
        fo.period_start,
        fo.period_end,
        fo.value,
        fo.tags_json,
        fo.geo_id
    FROM fact_observation fo
    WHERE fo.metric_id = :metric_id
      AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重'
      AND fo.geo_id IS NULL
      AND fo.period_type = 'week'
    ORDER BY fo.obs_date DESC
    LIMIT 3;
    """
    result = db.execute(text(sql), {"metric_id": metric.id})
    rows = result.fetchall()
    
    print("前3条indicator='均重'且geo_id=NULL的记录:")
    for i, row in enumerate(rows, 1):
        print(f"\n[{i}]")
        print(f"  ID: {row[0]}")
        print(f"  obs_date: {row[1]}")
        print(f"  period: {row[2]} ~ {row[3]}")
        print(f"  value: {row[4]}")
        print(f"  geo_id: {row[6]}")
        print(f"  tags_json: {json.dumps(row[5], ensure_ascii=False, indent=2) if row[5] else 'None'}")
finally:
    db.close()
