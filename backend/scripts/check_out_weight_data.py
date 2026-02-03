"""检查数据库中出栏均重数据是否存在"""
import sys
import os
import io
import json

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation
from sqlalchemy import func, text

def check_out_weight_data():
    """检查出栏均重数据"""
    print("=" * 80)
    print("检查数据库中出栏均重数据")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # 1. 查找YY_W_OUT_WEIGHT的metric
        print("\n1. 查找YY_W_OUT_WEIGHT的metric...")
        metric = db.query(DimMetric).filter(
            func.json_unquote(
                func.json_extract(DimMetric.parse_json, '$.metric_key')
            ) == 'YY_W_OUT_WEIGHT'
        ).first()
        
        if not metric:
            print("  ❌ 未找到YY_W_OUT_WEIGHT的metric")
            print("  尝试查找包含'体重'或'均重'的metric...")
            metrics = db.query(DimMetric).filter(
                or_(
                    DimMetric.metric_name.like('%体重%'),
                    DimMetric.metric_name.like('%均重%'),
                    DimMetric.sheet_name == '周度-体重'
                )
            ).all()
            if metrics:
                print(f"  找到 {len(metrics)} 个相关metric:")
                for m in metrics[:5]:
                    metric_key = m.parse_json.get('metric_key') if m.parse_json else None
                    print(f"    - ID: {m.id}, Name: {m.metric_name}, Sheet: {m.sheet_name}, Metric Key: {metric_key}")
            return
        
        print(f"  ✓ 找到metric: {metric.metric_name} (ID: {metric.id})")
        print(f"    Sheet: {metric.sheet_name}")
        print(f"    Parse JSON: {json.dumps(metric.parse_json, ensure_ascii=False, indent=2) if metric.parse_json else 'None'}")
        
        # 2. 查询所有YY_W_OUT_WEIGHT的数据统计
        print("\n2. 查询所有YY_W_OUT_WEIGHT的数据统计...")
        total_count = db.query(FactObservation).filter(
            FactObservation.metric_id == metric.id
        ).count()
        print(f"  总记录数: {total_count}")
        
        if total_count == 0:
            print("  ❌ 没有找到任何YY_W_OUT_WEIGHT的数据")
            return
        
        # 3. 查询不同indicator的数据统计
        print("\n3. 查询不同indicator的数据统计...")
        sql_indicator_stats = """
        SELECT 
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
            COUNT(*) as count,
            MIN(fo.obs_date) as min_date,
            MAX(fo.obs_date) as max_date
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
        GROUP BY indicator
        ORDER BY count DESC;
        """
        result = db.execute(text(sql_indicator_stats), {"metric_id": metric.id})
        rows = result.fetchall()
        
        print(f"  找到 {len(rows)} 种不同的indicator:")
        for row in rows:
            indicator = row[0] if row[0] else "(NULL)"
            count = row[1]
            min_date = row[2]
            max_date = row[3]
            print(f"    - indicator='{indicator}': {count} 条记录, 日期范围: {min_date} ~ {max_date}")
        
        # 4. 查询indicator='均重'的数据
        print("\n4. 查询indicator='均重'的数据...")
        sql_avg_weight = """
        SELECT 
            COUNT(*) as count,
            COUNT(DISTINCT fo.geo_id) as geo_count,
            MIN(fo.obs_date) as min_date,
            MAX(fo.obs_date) as max_date
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重';
        """
        result = db.execute(text(sql_avg_weight), {"metric_id": metric.id})
        row = result.fetchone()
        
        if row and row[0] > 0:
            print(f"  ✓ 找到 {row[0]} 条indicator='均重'的记录")
            print(f"    涉及 {row[1]} 个不同的geo_id")
            print(f"    日期范围: {row[2]} ~ {row[3]}")
        else:
            print("  ❌ 没有找到indicator='均重'的记录")
        
        # 5. 查询indicator='均重'且geo_id为NULL（全国数据）的数据
        print("\n5. 查询indicator='均重'且geo_id为NULL（全国数据）的数据...")
        sql_nation_avg_weight = """
        SELECT 
            COUNT(*) as count,
            MIN(fo.obs_date) as min_date,
            MAX(fo.obs_date) as max_date,
            JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.nation_col')) as nation_col
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重'
          AND fo.geo_id IS NULL
        GROUP BY nation_col
        ORDER BY count DESC;
        """
        result = db.execute(text(sql_nation_avg_weight), {"metric_id": metric.id})
        rows = result.fetchall()
        
        if rows:
            print(f"  ✓ 找到 {len(rows)} 种不同的全国列:")
            total_nation = 0
            for row in rows:
                count = row[0]
                min_date = row[1]
                max_date = row[2]
                nation_col = row[3] if row[3] else "(NULL)"
                total_nation += count
                print(f"    - nation_col='{nation_col}': {count} 条记录, 日期范围: {min_date} ~ {max_date}")
            print(f"  总计: {total_nation} 条全国数据")
        else:
            print("  ❌ 没有找到indicator='均重'且geo_id为NULL的记录")
        
        # 6. 查询indicator='均重'且nation_col='全国2'的数据
        print("\n6. 查询indicator='均重'且nation_col='全国2'的数据...")
        sql_nation2_avg_weight = """
        SELECT 
            COUNT(*) as count,
            MIN(fo.obs_date) as min_date,
            MAX(fo.obs_date) as max_date
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重'
          AND fo.geo_id IS NULL
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.nation_col')) = '全国2';
        """
        result = db.execute(text(sql_nation2_avg_weight), {"metric_id": metric.id})
        row = result.fetchone()
        
        if row and row[0] > 0:
            print(f"  ✓ 找到 {row[0]} 条indicator='均重'且nation_col='全国2'的记录")
            print(f"    日期范围: {row[1]} ~ {row[2]}")
            
            # 显示前5条示例数据
            print("\n  前5条示例数据:")
            sql_samples = """
            SELECT 
                fo.id,
                fo.obs_date,
                fo.period_start,
                fo.period_end,
                fo.value,
                fo.tags_json
            FROM fact_observation fo
            WHERE fo.metric_id = :metric_id
              AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重'
              AND fo.geo_id IS NULL
              AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.nation_col')) = '全国2'
            ORDER BY fo.obs_date DESC
            LIMIT 5;
            """
            result = db.execute(text(sql_samples), {"metric_id": metric.id})
            samples = result.fetchall()
            for i, sample in enumerate(samples, 1):
                print(f"    [{i}] ID={sample[0]}, obs_date={sample[1]}, period={sample[2]}~{sample[3]}, value={sample[4]}")
                print(f"        tags_json={json.dumps(sample[5], ensure_ascii=False) if sample[5] else 'None'}")
        else:
            print("  ❌ 没有找到indicator='均重'且nation_col='全国2'的记录")
            
            # 检查是否有nation_col为NULL或其他值的记录
            print("\n  检查nation_col的其他值...")
            sql_other_nation_col = """
            SELECT 
                JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.nation_col')) as nation_col,
                COUNT(*) as count
            FROM fact_observation fo
            WHERE fo.metric_id = :metric_id
              AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重'
              AND fo.geo_id IS NULL
            GROUP BY nation_col;
            """
            result = db.execute(text(sql_other_nation_col), {"metric_id": metric.id})
            rows = result.fetchall()
            if rows:
                print("  找到以下nation_col值:")
                for row in rows:
                    nation_col = row[0] if row[0] else "(NULL)"
                    count = row[1]
                    print(f"    - nation_col='{nation_col}': {count} 条记录")
        
        # 7. 检查period_type
        print("\n7. 检查period_type...")
        sql_period_type = """
        SELECT 
            fo.period_type,
            COUNT(*) as count
        FROM fact_observation fo
        WHERE fo.metric_id = :metric_id
          AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重'
          AND fo.geo_id IS NULL
        GROUP BY fo.period_type;
        """
        result = db.execute(text(sql_period_type), {"metric_id": metric.id})
        rows = result.fetchall()
        if rows:
            print("  period_type统计:")
            for row in rows:
                period_type = row[0] if row[0] else "(NULL)"
                count = row[1]
                print(f"    - period_type='{period_type}': {count} 条记录")
        
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
    from sqlalchemy import or_
    check_out_weight_data()
