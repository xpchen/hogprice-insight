"""修复90kg和150kg的indicator值"""
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
    """修复90kg和150kg的indicator值"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("修复90kg和150kg的indicator值")
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
        
        # 修复90kg以下 -> 90Kg出栏占比（仅限geo_id为NULL的全国数据）
        print(f"\n修复90kg以下 -> 90Kg出栏占比...")
        sql_90kg = """
        UPDATE fact_observation
        SET tags_json = JSON_SET(
            JSON_SET(tags_json, '$.indicator', '90Kg出栏占比'),
            '$.nation_col', '全国2'
        )
        WHERE metric_id = :metric_id
          AND period_type = 'week'
          AND geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(tags_json, '$.indicator')) = '90kg以下'
        """
        
        result = db.execute(text(sql_90kg), {"metric_id": metric.id})
        updated_90kg = result.rowcount
        print(f"  ✓ 更新了 {updated_90kg} 条记录")
        
        # 修复150kg以上 -> 150Kg出栏占重（仅限geo_id为NULL的全国数据）
        print(f"\n修复150kg以上 -> 150Kg出栏占重...")
        sql_150kg = """
        UPDATE fact_observation
        SET tags_json = JSON_SET(
            JSON_SET(tags_json, '$.indicator', '150Kg出栏占重'),
            '$.nation_col', '全国2'
        )
        WHERE metric_id = :metric_id
          AND period_type = 'week'
          AND geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(tags_json, '$.indicator')) = '150kg以上'
        """
        
        result = db.execute(text(sql_150kg), {"metric_id": metric.id})
        updated_150kg = result.rowcount
        print(f"  ✓ 更新了 {updated_150kg} 条记录")
        
        db.commit()
        
        # 验证修复结果
        print(f"\n验证修复结果...")
        
        sql_verify_90kg = """
        SELECT COUNT(*) as cnt
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND fo.geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '90Kg出栏占比'
        """
        
        result = db.execute(text(sql_verify_90kg), {"metric_id": metric.id})
        count_90kg = result.fetchone()[0]
        print(f"  indicator='90Kg出栏占比'的记录数: {count_90kg}")
        
        sql_verify_150kg = """
        SELECT COUNT(*) as cnt
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND fo.period_type = 'week'
          AND fo.geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '150Kg出栏占重'
        """
        
        result = db.execute(text(sql_verify_150kg), {"metric_id": metric.id})
        count_150kg = result.fetchone()[0]
        print(f"  indicator='150Kg出栏占重'的记录数: {count_150kg}")
        
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
    fix()
