"""修复现有数据：将geo_code='NATION'且indicator='均重'的记录，添加indicator='全国2'"""
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

def fix_nation2_indicator():
    """修复现有数据：为geo_code='NATION'的记录添加indicator='全国2'"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("修复现有数据：为全国数据添加indicator='全国2'")
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
        
        # 查找需要修复的记录：geo_id为NULL且indicator='均重'
        obs_list = db.query(FactObservation).filter(
            FactObservation.metric_id == metric.id,
            FactObservation.period_type == 'week',
            FactObservation.geo_id.is_(None)
        ).all()
        
        print(f"\n找到 {len(obs_list)} 条geo_id为NULL的记录")
        
        fixed_count = 0
        for obs in obs_list:
            tags = obs.tags_json or {}
            indicator = tags.get("indicator")
            
            # 如果indicator是'均重'，且没有nation_col标记，说明可能是"全国2"列的数据
            if indicator == "均重" and "nation_col" not in tags:
                # 检查tags中是否有其他信息可以帮助判断
                # 如果没有province或province是'None'，很可能是全国数据
                province = tags.get("province")
                if not province or province == "None":
                    # 更新tags，添加indicator='全国2'（保留原有的indicator）
                    tags["indicator"] = "全国2"
                    tags["nation_col"] = "全国2"  # 标记来源列
                    obs.tags_json = tags
                    fixed_count += 1
        
        if fixed_count > 0:
            db.commit()
            print(f"\n✓ 修复了 {fixed_count} 条记录")
            print(f"  将indicator从'均重'更新为'全国2'")
        else:
            print(f"\n⚠️  没有需要修复的记录")
            print(f"  可能原因：")
            print(f"    1. 数据已经正确设置了indicator")
            print(f"    2. 数据还没有导入")
            print(f"    3. 数据格式不符合预期")
        
        # 验证修复结果
        print(f"\n验证修复结果...")
        obs_with_nation2 = db.query(FactObservation).filter(
            FactObservation.metric_id == metric.id,
            FactObservation.period_type == 'week',
            FactObservation.geo_id.is_(None),
            func.json_unquote(
                func.json_extract(FactObservation.tags_json, '$.indicator')
            ) == '全国2'
        ).count()
        
        print(f"  indicator='全国2'的记录数: {obs_with_nation2}")
        
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
    fix_nation2_indicator()
