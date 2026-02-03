"""诊断均重数据查询问题"""
import sys
import os
import io
from datetime import date, timedelta

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from app.models.fact_observation import FactObservation
from app.models.fact_observation_tag import FactObservationTag
from app.models.dim_geo import DimGeo
from sqlalchemy import func, and_, or_, text
from sqlalchemy.orm import aliased

def print_sql(title: str, sql: str):
    """打印SQL"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")
    print(sql)
    print(f"{'='*80}\n")

def diagnose():
    """诊断均重数据查询问题"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("均重数据查询诊断")
        print("=" * 80)
        
        # 1. 检查metric_key是否正确设置
        print("\n1. 检查metric_key设置情况...")
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name.in_(["周度-体重", "周度-屠宰厂宰前活猪重", "周度-体重拆分"])
        ).all()
        
        print(f"  找到 {len(metrics)} 个相关metric:")
        for metric in metrics:
            metric_key = None
            if metric.parse_json:
                metric_key = metric.parse_json.get("metric_key")
            print(f"    - {metric.metric_name} (sheet: {metric.sheet_name})")
            print(f"      metric_key: {metric_key}")
            print(f"      parse_json: {metric.parse_json}")
        
        # 2. 检查fact_observation中的数据
        print("\n2. 检查fact_observation中的数据...")
        
        # 查询各个metric_key的数据
        metric_keys_to_check = [
            "YY_W_SLAUGHTER_PRELIVE_WEIGHT",
            "YY_W_OUT_WEIGHT",
            "YY_W_WEIGHT_GROUP",
            "YY_W_WEIGHT_SCATTER"
        ]
        
        for metric_key in metric_keys_to_check:
            print(f"\n  检查 metric_key={metric_key}:")
            
            # 查找对应的metric
            metric = db.query(DimMetric).filter(
                func.json_unquote(
                    func.json_extract(DimMetric.parse_json, '$.metric_key')
                ) == metric_key
            ).first()
            
            if not metric:
                print(f"    ❌ 未找到metric_key={metric_key}的metric")
                continue
            
            print(f"    ✓ 找到metric: {metric.metric_name} (ID: {metric.id})")
            
            # 查询observations
            obs_count = db.query(FactObservation).filter(
                FactObservation.metric_id == metric.id
            ).count()
            
            print(f"    ✓ fact_observation中有 {obs_count} 条记录")
            
            if obs_count > 0:
                # 显示前3条
                obs_list = db.query(FactObservation).filter(
                    FactObservation.metric_id == metric.id
                ).order_by(FactObservation.obs_date.desc()).limit(3).all()
                
                print(f"    前3条记录:")
                for obs in obs_list:
                    geo_name = obs.geo.province if obs.geo else None
                    tags = obs.tags_json or {}
                    indicator = tags.get("indicator")
                    print(f"      - obs_date={obs.obs_date}, period_end={obs.period_end}, value={obs.value}")
                    print(f"        geo={geo_name}, indicator={indicator}, tags={tags}")
        
        # 3. 生成前端查询对应的SQL
        print("\n3. 生成前端查询对应的SQL...")
        
        # 查询1: 宰前均重 (YY_W_SLAUGHTER_PRELIVE_WEIGHT, geo_code='NATION')
        print("\n  查询1: 宰前均重")
        sql1 = """
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    dm.parse_json->>'$.metric_key' as metric_key,
    dg.province as geo_code,
    fo.tags_json
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
LEFT JOIN dim_geo dg ON fo.geo_id = dg.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_SLAUGHTER_PRELIVE_WEIGHT'
  AND fo.period_type = 'week'
  AND (fo.geo_id IS NULL OR dg.province = 'NATION')
ORDER BY fo.obs_date DESC
LIMIT 10;
"""
        print_sql("查询1: 宰前均重 (YY_W_SLAUGHTER_PRELIVE_WEIGHT, geo_code='NATION')", sql1)
        
        # 执行查询1
        result1 = db.execute(text(sql1))
        rows1 = result1.fetchall()
        print(f"  结果: {len(rows1)} 条")
        if len(rows1) > 0:
            for row in rows1[:3]:
                print(f"    - obs_date={row[1]}, period_end={row[2]}, value={row[3]}, geo_code={row[6]}")
        
        # 查询2: 出栏均重 (YY_W_OUT_WEIGHT, indicator='全国2')
        print("\n  查询2: 出栏均重")
        sql2 = """
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    dm.parse_json->>'$.metric_key' as metric_key,
    JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
    fo.tags_json
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '全国2'
ORDER BY fo.obs_date DESC
LIMIT 10;
"""
        print_sql("查询2: 出栏均重 (YY_W_OUT_WEIGHT, indicator='全国2')", sql2)
        
        # 执行查询2
        result2 = db.execute(text(sql2))
        rows2 = result2.fetchall()
        print(f"  结果: {len(rows2)} 条")
        if len(rows2) > 0:
            for row in rows2[:3]:
                print(f"    - obs_date={row[1]}, period_end={row[2]}, value={row[3]}, indicator={row[6]}")
        
        # 查询3: 规模场出栏均重 (YY_W_WEIGHT_GROUP, tag_key='crowd', tag_value='集团')
        print("\n  查询3: 规模场出栏均重")
        sql3 = """
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    dm.parse_json->>'$.metric_key' as metric_key,
    fot.tag_key,
    fot.tag_value
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
JOIN fact_observation_tag fot ON fo.id = fot.observation_id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_WEIGHT_GROUP'
  AND fo.period_type = 'week'
  AND fot.tag_key = 'crowd'
  AND fot.tag_value = '集团'
ORDER BY fo.obs_date DESC
LIMIT 10;
"""
        print_sql("查询3: 规模场出栏均重 (YY_W_WEIGHT_GROUP, tag_key='crowd', tag_value='集团')", sql3)
        
        # 执行查询3
        result3 = db.execute(text(sql3))
        rows3 = result3.fetchall()
        print(f"  结果: {len(rows3)} 条")
        if len(rows3) > 0:
            for row in rows3[:3]:
                print(f"    - obs_date={row[1]}, period_end={row[2]}, value={row[3]}, tag_value={row[7]}")
        
        # 查询4: 散户出栏均重 (YY_W_WEIGHT_SCATTER, tag_key='crowd', tag_value='散户')
        print("\n  查询4: 散户出栏均重")
        sql4 = """
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    dm.parse_json->>'$.metric_key' as metric_key,
    fot.tag_key,
    fot.tag_value
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
JOIN fact_observation_tag fot ON fo.id = fot.observation_id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_WEIGHT_SCATTER'
  AND fo.period_type = 'week'
  AND fot.tag_key = 'crowd'
  AND fot.tag_value = '散户'
ORDER BY fo.obs_date DESC
LIMIT 10;
"""
        print_sql("查询4: 散户出栏均重 (YY_W_WEIGHT_SCATTER, tag_key='crowd', tag_value='散户')", sql4)
        
        # 执行查询4
        result4 = db.execute(text(sql4))
        rows4 = result4.fetchall()
        print(f"  结果: {len(rows4)} 条")
        if len(rows4) > 0:
            for row in rows4[:3]:
                print(f"    - obs_date={row[1]}, period_end={row[2]}, value={row[3]}, tag_value={row[7]}")
        
        # 4. 检查后端API查询逻辑的问题
        print("\n4. 检查后端API查询逻辑...")
        
        # 检查geo_code='NATION'的查询问题
        print("\n  检查geo_code='NATION'的查询:")
        # 后端API使用: query.join(FactObservation.geo).filter(FactObservation.geo.has(province=geo_code))
        # 但geo_code='NATION'时，geo_id应该是NULL，所以join会失败
        
        # 检查是否有geo_id为NULL的记录
        metric_prelive = db.query(DimMetric).filter(
            func.json_unquote(
                func.json_extract(DimMetric.parse_json, '$.metric_key')
            ) == 'YY_W_SLAUGHTER_PRELIVE_WEIGHT'
        ).first()
        
        if metric_prelive:
            obs_with_null_geo = db.query(FactObservation).filter(
                and_(
                    FactObservation.metric_id == metric_prelive.id,
                    FactObservation.geo_id.is_(None)
                )
            ).count()
            
            obs_with_geo = db.query(FactObservation).filter(
                and_(
                    FactObservation.metric_id == metric_prelive.id,
                    FactObservation.geo_id.isnot(None)
                )
            ).count()
            
            print(f"    metric_id={metric_prelive.id}的记录:")
            print(f"      geo_id为NULL的记录数: {obs_with_null_geo}")
            print(f"      geo_id不为NULL的记录数: {obs_with_geo}")
            
            if obs_with_null_geo > 0:
                print(f"    ⚠️  后端API的geo_code='NATION'查询有问题！")
                print(f"    问题: 后端使用inner join，但geo_id为NULL时join会失败")
                print(f"    建议: 使用LEFT JOIN或单独处理geo_id为NULL的情况")
        
        # 5. 检查indicator筛选
        print("\n5. 检查indicator筛选...")
        metric_out = db.query(DimMetric).filter(
            func.json_unquote(
                func.json_extract(DimMetric.parse_json, '$.metric_key')
            ) == 'YY_W_OUT_WEIGHT'
        ).first()
        
        if metric_out:
            # 检查tags_json中的indicator值
            obs_list = db.query(FactObservation).filter(
                FactObservation.metric_id == metric_out.id
            ).limit(10).all()
            
            indicators = set()
            for obs in obs_list:
                if obs.tags_json:
                    indicator = obs.tags_json.get("indicator")
                    if indicator:
                        indicators.add(indicator)
            
            print(f"    找到的indicator值: {list(indicators)}")
            if "全国2" not in indicators:
                print(f"    ⚠️  未找到indicator='全国2'的记录")
        
        print("\n" + "=" * 80)
        print("诊断完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 诊断失败: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()
