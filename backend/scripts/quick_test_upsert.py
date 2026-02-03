"""快速测试upsert_observations函数"""
import sys
import os
import io
import json
import hashlib
from datetime import date, timedelta
from pathlib import Path

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.import_batch import ImportBatch
from app.models.sys_user import SysUser
from app.services.ingestors.observation_upserter import upsert_observations
from app.services.ingestors.parsers.base_parser import ObservationDict


def generate_dedup_key(source_code: str, sheet_name: str, metric_key: str, geo_code: str, 
                       period_end: date, tags: dict) -> str:
    """生成dedup_key"""
    canonical_tags = "|".join([f"{k}={v}" for k, v in sorted(tags.items())])
    key_str = f"{source_code}|{sheet_name}|{metric_key}|{geo_code or 'NATION'}|{period_end}|{canonical_tags}"
    return hashlib.sha1(key_str.encode()).hexdigest()[:16]


def create_test_observations(count: int = 10) -> list[ObservationDict]:
    """创建测试observations"""
    observations = []
    sheet_name = "周度-体重"
    metric_key = "YY_W_OUT_WEIGHT"
    metric_name = "商品猪出栏体重"
    
    # 从2024-01-01开始，每周一条数据
    base_date = date(2024, 1, 1)
    
    provinces = ["河南", "湖南", "湖北", "安徽", "江西"]
    
    for i in range(count):
        period_end = base_date + timedelta(weeks=i)
        period_start = period_end - timedelta(days=6)
        province = provinces[i % len(provinces)]
        
        tags = {
            "indicator": "商品猪出栏体重",
            "province": province
        }
        
        dedup_key = generate_dedup_key(
            source_code="YONGYI",
            sheet_name=sheet_name,
            metric_key=metric_key,
            geo_code=province,
            period_end=period_end,
            tags=tags
        )
        
        obs: ObservationDict = {
            "metric_key": metric_key,
            "metric_name": metric_name,
            "obs_date": period_end,  # 周度数据使用period_end作为obs_date
            "period_type": "week",
            "period_start": period_start,
            "period_end": period_end,
            "value": 120.0 + i * 0.5,  # 模拟体重值
            "raw_value": str(120.0 + i * 0.5),
            "geo_code": province,
            "tags": tags,
            "unit": "kg",
            "dedup_key": dedup_key
        }
        
        observations.append(obs)
    
    return observations


def quick_test():
    """快速测试upsert_observations"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("快速测试 upsert_observations")
        print("=" * 80)
        
        # 1. 获取或创建测试用户
        user = db.query(SysUser).filter(SysUser.username == "admin").first()
        if not user:
            print("  ❌ 未找到admin用户，请先创建")
            return
        
        print(f"  ✓ 使用用户: {user.username} (ID: {user.id})")
        
        # 2. 创建测试batch
        batch = ImportBatch(
            filename="quick_test.xlsx",
            file_hash="test_hash",
            uploader_id=user.id,
            source_code="YONGYI",
            status="processing",
            total_rows=0,
            success_rows=0,
            failed_rows=0
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        
        print(f"  ✓ 创建测试批次: ID={batch.id}")
        
        # 3. 创建测试observations
        print(f"\n  创建测试observations...")
        observations = create_test_observations(count=10)
        print(f"  ✓ 创建了 {len(observations)} 条测试数据")
        
        # 显示前3条
        print(f"\n  前3条测试数据:")
        for i, obs in enumerate(observations[:3], 1):
            print(f"    [{i}] metric_key={obs.get('metric_key')}, geo_code={obs.get('geo_code')}, "
                  f"period_end={obs.get('period_end')}, value={obs.get('value')}")
            print(f"        dedup_key={obs.get('dedup_key')[:32]}...")
        
        # 4. 调用upsert_observations
        print(f"\n  {'='*80}")
        print(f"  开始测试 upsert_observations...")
        print(f"  {'='*80}")
        
        result = upsert_observations(
            db=db,
            observations=observations,
            batch_id=batch.id,
            sheet_name="周度-体重"
        )
        
        # 5. 显示结果
        print(f"\n  {'='*80}")
        print(f"  测试结果")
        print(f"  {'='*80}")
        print(f"    插入: {result.get('inserted', 0)} 条")
        print(f"    更新: {result.get('updated', 0)} 条")
        print(f"    错误: {result.get('errors', 0)} 条")
        
        if result.get('errors', 0) > 0:
            print(f"\n  ⚠️  有 {result.get('errors', 0)} 条错误，请查看上方的错误日志")
        else:
            print(f"\n  ✅ 所有记录都成功处理！")
        
        # 6. 验证数据库中的数据
        print(f"\n  {'='*80}")
        print(f"  验证数据库中的数据...")
        print(f"  {'='*80}")
        
        from app.models.fact_observation import FactObservation
        from app.models.dim_metric import DimMetric
        
        # 查询刚插入的数据
        obs_count = db.query(FactObservation).filter(
            FactObservation.batch_id == batch.id
        ).count()
        
        print(f"    fact_observation中batch_id={batch.id}的记录数: {obs_count}")
        
        # 查询metric
        metric = db.query(DimMetric).filter(
            DimMetric.sheet_name == "周度-体重",
            DimMetric.metric_name == "商品猪出栏体重"
        ).first()
        
        if metric:
            metric_key_in_db = None
            if metric.parse_json:
                metric_key_in_db = metric.parse_json.get("metric_key")
            print(f"    metric: {metric.metric_name}, metric_key={metric_key_in_db}")
            
            # 查询该metric的observations
            metric_obs_count = db.query(FactObservation).filter(
                FactObservation.metric_id == metric.id
            ).count()
            print(f"    该metric的observations数量: {metric_obs_count}")
        
        print(f"\n  {'='*80}")
        print(f"  测试完成")
        print(f"  {'='*80}")
        
    except Exception as e:
        db.rollback()
        print(f"\n  ❌ 测试失败: {type(e).__name__}: {str(e)}", flush=True)
        import traceback
        print(f"  详细堆栈:\n{traceback.format_exc()}", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    quick_test()
