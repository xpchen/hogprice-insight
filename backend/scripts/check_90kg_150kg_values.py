"""检查90kg和150kg的实际数据值"""
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

def check_values():
    """检查90kg和150kg的实际数据值"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("检查90kg和150kg的实际数据值")
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
        
        print(f"✓ 找到metric: {metric.metric_name} (ID: {metric.id})")
        
        # 检查90Kg出栏占比的数据值
        print(f"\n检查90Kg出栏占比的数据值:")
        sql_90kg = """
        SELECT 
            fo.obs_date,
            fo.period_end,
            fo.value,
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
            fo.tags_json,
            fo.raw_value
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND fo.geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '90Kg出栏占比'
        ORDER BY fo.obs_date DESC
        LIMIT 20;
        """
        
        result = db.execute(text(sql_90kg), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"  找到 {len(rows)} 条记录（前20条）:")
        values_90kg = []
        for row in rows:
            value = row[2]
            values_90kg.append(value)
            print(f"    - obs_date={row[0]}, period_end={row[1]}, value={value}, indicator={row[3]}")
            print(f"      tags_json={row[4]}, raw_value={row[5]}")
        
        if values_90kg:
            avg_90kg = sum(v for v in values_90kg if v is not None) / len([v for v in values_90kg if v is not None])
            print(f"\n  90Kg出栏占比统计:")
            print(f"    平均值: {avg_90kg:.2f}")
            print(f"    最小值: {min(v for v in values_90kg if v is not None):.2f}")
            print(f"    最大值: {max(v for v in values_90kg if v is not None):.2f}")
        
        # 检查150Kg出栏占重的数据值
        print(f"\n检查150Kg出栏占重的数据值:")
        sql_150kg = """
        SELECT 
            fo.obs_date,
            fo.period_end,
            fo.value,
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
            fo.tags_json,
            fo.raw_value
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND fo.geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '150Kg出栏占重'
        ORDER BY fo.obs_date DESC
        LIMIT 20;
        """
        
        result = db.execute(text(sql_150kg), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"  找到 {len(rows)} 条记录（前20条）:")
        values_150kg = []
        for row in rows:
            value = row[2]
            values_150kg.append(value)
            print(f"    - obs_date={row[0]}, period_end={row[1]}, value={value}, indicator={row[3]}")
            print(f"      tags_json={row[4]}, raw_value={row[5]}")
        
        if values_150kg:
            avg_150kg = sum(v for v in values_150kg if v is not None) / len([v for v in values_150kg if v is not None])
            print(f"\n  150Kg出栏占重统计:")
            print(f"    平均值: {avg_150kg:.2f}")
            print(f"    最小值: {min(v for v in values_150kg if v is not None):.2f}")
            print(f"    最大值: {max(v for v in values_150kg if v is not None):.2f}")
        
        # 检查原始indicator值（90kg以下、150kg以上）的数据值
        print(f"\n检查原始indicator值（90kg以下、150kg以上）的数据值:")
        sql_original = """
        SELECT 
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
            COUNT(*) as count,
            AVG(fo.value) as avg_value,
            MIN(fo.value) as min_value,
            MAX(fo.value) as max_value
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND fo.geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) IN ('90kg以下', '150kg以上', '均重')
        GROUP BY indicator
        ORDER BY indicator;
        """
        
        result = db.execute(text(sql_original), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"  原始indicator值统计:")
        for row in rows:
            print(f"    - indicator={row[0]}, count={row[1]}, avg={row[2]:.2f}, min={row[3]:.2f}, max={row[4]:.2f}")
        
        # 检查"均重"的数据值（作为对比）
        print(f"\n检查'均重'的数据值（作为对比）:")
        sql_avg = """
        SELECT 
            fo.obs_date,
            fo.period_end,
            fo.value,
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND fo.geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重'
        ORDER BY fo.obs_date DESC
        LIMIT 10;
        """
        
        result = db.execute(text(sql_avg), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"  找到 {len(rows)} 条记录（前10条）:")
        for row in rows:
            print(f"    - obs_date={row[0]}, period_end={row[1]}, value={row[2]}, indicator={row[3]}")
        
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
    check_values()
