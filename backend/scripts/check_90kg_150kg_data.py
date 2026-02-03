"""检查90kg和150kg的数据"""
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
    """检查90kg和150kg的数据"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("检查90kg和150kg的数据")
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
        
        # 检查所有indicator值
        sql = """
        SELECT DISTINCT
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
            COUNT(*) as count
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
        GROUP BY indicator
        ORDER BY count DESC;
        """
        
        result = db.execute(text(sql), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"\n所有indicator值:")
        for row in rows:
            indicator = row[0] if row[0] else "NULL"
            count = row[1]
            print(f"  - {indicator}: {count} 条")
        
        # 检查90kg相关的数据
        print(f"\n检查90kg相关的数据:")
        sql_90kg = """
        SELECT 
            fo.id,
            fo.obs_date,
            fo.period_end,
            fo.value,
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
            fo.geo_id,
            fo.tags_json
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND (JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) LIKE '%90%'
               OR JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) LIKE '%90kg%')
        ORDER BY fo.obs_date DESC
        LIMIT 10;
        """
        
        result = db.execute(text(sql_90kg), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"  找到 {len(rows)} 条90kg相关的记录（前10条）:")
        for row in rows:
            print(f"    - obs_date={row[1]}, period_end={row[2]}, value={row[3]}, indicator={row[4]}, geo_id={row[5]}")
        
        # 检查150kg相关的数据
        print(f"\n检查150kg相关的数据:")
        sql_150kg = """
        SELECT 
            fo.id,
            fo.obs_date,
            fo.period_end,
            fo.value,
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
            fo.geo_id,
            fo.tags_json
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND (JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) LIKE '%150%'
               OR JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) LIKE '%150kg%')
        ORDER BY fo.obs_date DESC
        LIMIT 10;
        """
        
        result = db.execute(text(sql_150kg), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"  找到 {len(rows)} 条150kg相关的记录（前10条）:")
        for row in rows:
            print(f"    - obs_date={row[1]}, period_end={row[2]}, value={row[3]}, indicator={row[4]}, geo_id={row[5]}")
        
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
