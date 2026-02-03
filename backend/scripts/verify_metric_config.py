"""验证metric配置是否正确"""
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
from app.models.ingest_profile import IngestProfile, IngestProfileSheet
from sqlalchemy import func
import json

def verify_config():
    """验证配置和metric"""
    db = SessionLocal()
    try:
        print("=" * 80)
        print("验证配置和metric")
        print("=" * 80)
        
        # 1. 检查"周度-体重"的配置
        print("\n1. 检查IngestProfile配置...")
        profile = db.query(IngestProfile).filter(
            IngestProfile.profile_code == "YONGYI_WEEKLY_V1"
        ).first()
        
        if not profile:
            print("  ❌ 未找到YONGYI_WEEKLY_V1配置")
            return
        
        print(f"  ✓ Profile存在: {profile.profile_code}")
        
        # 查找"周度-体重"的sheet配置
        sheet_config = None
        for sheet in profile.sheets:
            if sheet.sheet_name == "周度-体重":
                sheet_config = sheet.config_json
                break
        
        if not sheet_config:
            print("  ❌ 未找到'周度-体重'的sheet配置")
            return
        
        print(f"  ✓ 找到'周度-体重'的sheet配置")
        
        # 检查metric_template
        metric_template = sheet_config.get("metric_template")
        if metric_template:
            print(f"  ✓ metric_template存在:")
            print(f"    - metric_key: {metric_template.get('metric_key')}")
            print(f"    - metric_name: {metric_template.get('metric_name')}")
            print(f"    - unit: {metric_template.get('unit')}")
        else:
            print(f"  ❌ metric_template不存在！")
            print(f"  sheet_config.keys(): {list(sheet_config.keys())[:20]}")
        
        # 2. 检查数据库中的metric
        print("\n2. 检查数据库中的metric...")
        metrics = db.query(DimMetric).filter(
            DimMetric.sheet_name == "周度-体重"
        ).all()
        
        if not metrics:
            print("  ⚠️  未找到'周度-体重'相关的metric")
        else:
            print(f"  ✓ 找到 {len(metrics)} 个metric:")
            for metric in metrics:
                metric_key = None
                if metric.parse_json:
                    metric_key = metric.parse_json.get("metric_key")
                
                status = "✓" if metric_key else "❌"
                print(f"    {status} {metric.metric_name}: metric_key={metric_key}")
                if metric_key:
                    print(f"      parse_json: {json.dumps(metric.parse_json, ensure_ascii=False, indent=6)}")
        
        # 3. 检查fact_observation中的数据
        print("\n3. 检查fact_observation中的数据...")
        from app.models.fact_observation import FactObservation
        
        # 查找有metric_key的metric
        metrics_with_key = db.query(DimMetric).filter(
            DimMetric.sheet_name == "周度-体重",
            func.json_unquote(
                func.json_extract(DimMetric.parse_json, '$.metric_key')
            ).isnot(None)
        ).all()
        
        if metrics_with_key:
            metric_ids = [m.id for m in metrics_with_key]
            obs_count = db.query(FactObservation).filter(
                FactObservation.metric_id.in_(metric_ids)
            ).count()
            print(f"  ✓ 找到 {obs_count} 条fact_observation记录（metric_key已设置）")
        else:
            print(f"  ⚠️  没有找到设置了metric_key的metric")
        
        print("\n" + "=" * 80)
        print("验证完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_config()
