"""修复90kg和150kg的错误数值（删除province='指标'的记录）"""
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

def fix():
    """删除province='指标'的错误记录"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("删除province='指标'的错误记录")
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
        
        # 先统计需要删除的记录数
        count_sql = """
        SELECT COUNT(*) as cnt
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.province')) = '指标'
        """
        
        result = db.execute(text(count_sql), {"metric_id": metric.id})
        count = result.fetchone()[0]
        
        print(f"\n找到 {count} 条需要删除的记录")
        
        if count == 0:
            print("⚠️  没有需要删除的记录")
            return
        
        # 删除这些记录
        delete_sql = """
        DELETE FROM fact_observation
        WHERE metric_id = :metric_id
          AND period_type = 'week'
          AND JSON_UNQUOTE(JSON_EXTRACT(tags_json, '$.province')) = '指标'
        """
        
        result = db.execute(text(delete_sql), {"metric_id": metric.id})
        db.commit()
        
        deleted_count = result.rowcount
        print(f"\n✓ 删除了 {deleted_count} 条错误记录")
        
        print("\n" + "=" * 80)
        print("修复完成")
        print("=" * 80)
        print("\n💡 建议：重新导入数据，使用修复后的parser")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ 修复失败: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix()
