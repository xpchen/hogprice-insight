"""检查'全国2'列的数据"""
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

def check_nation2():
    """检查'全国2'列的数据"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("检查'全国2'列的数据")
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
        
        # 查询所有geo_code值
        sql = """
        SELECT DISTINCT
            dg.province as geo_code,
            COUNT(*) as count
        FROM fact_observation fo
        LEFT JOIN dim_geo dg ON fo.geo_id = dg.id
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
        GROUP BY dg.province
        ORDER BY count DESC
        LIMIT 50;
        """
        
        result = db.execute(text(sql), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"\n所有geo_code值（前50个）:")
        for row in rows:
            geo_code = row[0] if row[0] else "NULL"
            count = row[1]
            print(f"  - {geo_code}: {count} 条")
        
        # 检查是否有"全国2"这个geo_code
        has_nation2 = any(row[0] == "全国2" for row in rows)
        
        if has_nation2:
            print(f"\n✓ 找到geo_code='全国2'的数据")
            
            # 查询具体数据
            sql2 = """
            SELECT 
                fo.id,
                fo.obs_date,
                fo.period_end,
                fo.value,
                dg.province as geo_code,
                JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator
            FROM fact_observation fo
            LEFT JOIN dim_geo dg ON fo.geo_id = dg.id
            WHERE fo.metric_id = :metric_id
              AND fo.period_type = 'week'
              AND dg.province = '全国2'
            ORDER BY fo.obs_date DESC
            LIMIT 10;
            """
            
            result2 = db.execute(text(sql2), {"metric_id": metric.id})
            rows2 = result2.fetchall()
            
            print(f"\n'全国2'的数据（前10条）:")
            for row in rows2:
                print(f"  - obs_date={row[1]}, period_end={row[2]}, value={row[3]}, indicator={row[5]}")
        else:
            print(f"\n❌ 未找到geo_code='全国2'的数据")
            print(f"  可能原因:")
            print(f"    1. '全国2'列的数据没有被正确解析")
            print(f"    2. '全国2'被解析为其他geo_code值")
            print(f"    3. 数据还没有导入")
        
        # 检查indicator值
        print(f"\n检查indicator值:")
        sql3 = """
        SELECT DISTINCT
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
            COUNT(*) as count
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
        GROUP BY indicator
        ORDER BY count DESC
        LIMIT 20;
        """
        
        result3 = db.execute(text(sql3), {"metric_id": metric.id})
        rows3 = result3.fetchall()
        
        print(f"所有indicator值（前20个）:")
        for row in rows3:
            indicator = row[0] if row[0] else "NULL"
            count = row[1]
            print(f"  - {indicator}: {count} 条")
        
        # 检查geo_code为NULL但可能有特殊标记的数据
        print(f"\n检查geo_id为NULL的数据:")
        sql4 = """
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
        ORDER BY fo.obs_date DESC
        LIMIT 10;
        """
        
        result4 = db.execute(text(sql4), {"metric_id": metric.id})
        rows4 = result4.fetchall()
        
        print(f"geo_id为NULL的数据（前10条）:")
        for row in rows4:
            tags = row[4] or {}
            print(f"  - obs_date={row[1]}, period_end={row[2]}, value={row[3]}, tags={tags}")
        
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
    check_nation2()
