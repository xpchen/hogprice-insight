"""使用SQL直接修复indicator='全国2'"""
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
from sqlalchemy import func, text

def fix_with_sql():
    """使用SQL直接修复"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("使用SQL修复indicator='全国2'")
        print("=" * 80)
        
        # 查找YY_W_OUT_WEIGHT的metric_id
        metric = db.query(DimMetric).filter(
            func.json_unquote(
                func.json_extract(DimMetric.parse_json, '$.metric_key')
            ) == 'YY_W_OUT_WEIGHT'
        ).first()
        
        if not metric:
            print("❌ 未找到YY_W_OUT_WEIGHT的metric")
            return
        
        print(f"✓ 找到metric: {metric.metric_name} (ID: {metric.id})")
        
        # 先统计需要修复的记录数
        count_sql = """
        SELECT COUNT(*) as cnt
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND fo.geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重'
          AND (JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.province')) = 'None' 
               OR JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.province')) IS NULL
               OR JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.province')) = '')
        """
        
        result = db.execute(text(count_sql), {"metric_id": metric.id})
        count = result.fetchone()[0]
        
        print(f"\n找到 {count} 条需要修复的记录")
        
        if count == 0:
            print("⚠️  没有需要修复的记录")
            return
        
        # 更新tags_json，将indicator从'均重'改为'全国2'，并添加nation_col='全国2'
        update_sql = """
        UPDATE fact_observation
        SET tags_json = JSON_SET(
            JSON_SET(tags_json, '$.indicator', '全国2'),
            '$.nation_col', '全国2'
        )
        WHERE metric_id = :metric_id
          AND period_type = 'week'
          AND geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(tags_json, '$.indicator')) = '均重'
          AND (JSON_UNQUOTE(JSON_EXTRACT(tags_json, '$.province')) = 'None' 
               OR JSON_UNQUOTE(JSON_EXTRACT(tags_json, '$.province')) IS NULL
               OR JSON_UNQUOTE(JSON_EXTRACT(tags_json, '$.province')) = '')
        """
        
        result = db.execute(text(update_sql), {"metric_id": metric.id})
        db.commit()
        
        updated_count = result.rowcount
        print(f"\n✓ 更新了 {updated_count} 条记录")
        
        # 验证更新结果
        verify_sql = """
        SELECT COUNT(*) as cnt
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND fo.geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '全国2'
        """
        
        result = db.execute(text(verify_sql), {"metric_id": metric.id})
        count_after = result.fetchone()[0]
        
        print(f"\n验证结果:")
        print(f"  indicator='全国2'的记录数: {count_after}")
        
        # 显示前5条更新后的记录
        sample_sql = """
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
        LIMIT 5;
        """
        
        result = db.execute(text(sample_sql), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"\n更新后的记录示例（前5条）:")
        for row in rows:
            print(f"  - obs_date={row[1]}, period_end={row[2]}, value={row[3]}")
            print(f"    tags_json={row[4]}")
        
        print("\n" + "=" * 80)
        print("修复完成")
        print("=" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ 修复失败: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_with_sql()
