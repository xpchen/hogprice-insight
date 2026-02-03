"""验证indicator='全国2'的修复"""
import sys
import os
import io

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation
from sqlalchemy import func, text
import json

def verify():
    """验证修复结果"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("验证indicator='全国2'的修复")
        print("=" * 80)
        
        # 查找YY_W_OUT_WEIGHT的metric
        metric = db.query(DimMetric).filter(
            func.json_unquote(
                func.json_extract(DimMetric.parse_json, '$.metric_key')
            ) == 'YY_W_OUT_WEIGHT'
        ).first()
        
        if not metric:
            print("❌ 未找到YY_W_OUT_WEIGHT的metric")
            return
        
        # 查询geo_id为NULL的记录，检查tags_json
        obs_list = db.query(FactObservation).filter(
            FactObservation.metric_id == metric.id,
            FactObservation.period_type == 'week',
            FactObservation.geo_id.is_(None)
        ).limit(10).all()
        
        print(f"\n检查前10条geo_id为NULL的记录:")
        for obs in obs_list:
            tags = obs.tags_json or {}
            indicator = tags.get("indicator")
            nation_col = tags.get("nation_col")
            print(f"  - obs_date={obs.obs_date}, period_end={obs.period_end}, value={obs.value}")
            print(f"    indicator={indicator}, nation_col={nation_col}, tags={tags}")
        
        # 使用SQL查询indicator='全国2'的记录
        sql = """
        SELECT 
            fo.id,
            fo.obs_date,
            fo.period_end,
            fo.value,
            fo.tags_json
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND fo.geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '全国2'
        ORDER BY fo.obs_date DESC
        LIMIT 10;
        """
        
        result = db.execute(text(sql), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"\n使用SQL查询indicator='全国2'的记录: {len(rows)} 条")
        for row in rows:
            print(f"  - obs_date={row[1]}, period_end={row[2]}, value={row[3]}")
            print(f"    tags_json={row[4]}")
        
        print("\n" + "=" * 80)
        print("验证完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 验证失败: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify()
