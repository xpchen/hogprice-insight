"""检查为什么会有province='指标'的记录"""
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

def check():
    """检查为什么会有province='指标'的记录"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("检查province='指标'的记录")
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
        
        # 查找province='指标'的记录
        sql = """
        SELECT 
            fo.id,
            fo.obs_date,
            fo.period_end,
            fo.value,
            fo.raw_value,
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.province')) as province,
            fo.tags_json
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.province')) = '指标'
        ORDER BY fo.obs_date DESC
        LIMIT 10;
        """
        
        result = db.execute(text(sql), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"\n找到 {len(rows)} 条province='指标'的记录（前10条）:")
        for row in rows:
            print(f"  - obs_date={row[1]}, period_end={row[2]}, value={row[3]}, raw_value={row[4]}")
            print(f"    indicator={row[5]}, province={row[6]}")
            print(f"    tags_json={row[7]}")
        
        # 检查这些记录的geo_code
        sql_geo = """
        SELECT 
            fo.geo_code,
            COUNT(*) as count
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.province')) = '指标'
        GROUP BY fo.geo_code
        ORDER BY count DESC;
        """
        
        result = db.execute(text(sql_geo), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"\nprovince='指标'的记录的geo_code分布:")
        for row in rows:
            print(f"  - geo_code={row[0]}, count={row[1]}")
        
        print("\n" + "=" * 80)
        print("检查完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 检查失败: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check()
