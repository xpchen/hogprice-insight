"""修复现有metric的parse_json，补充缺失的metric_key"""
import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from sqlalchemy import func
import json

# 从配置文件加载metric_key映射（根据sheet_name和metric_name）
METRIC_KEY_MAPPING = {
    "周度-体重": {
        "商品猪出栏体重": "YY_W_OUT_WEIGHT",
        "全国均重": "YY_W_WEIGHT_NATION_AVG",
        "集团": "YY_W_WEIGHT_GROUP",
        "散户": "YY_W_WEIGHT_SCATTER",
    },
    "周度-屠宰厂宰前活猪重": {
        "宰前活猪重": "YY_W_SLAUGHTER_PRELIVE_WEIGHT",
        "宰前活猪重较上周": "YY_W_SLAUGHTER_PRELIVE_WEIGHT_WOW",
    },
    "周度-各体重段价差": {
        "各体重段价格": "YY_W_PRICE_BY_WEIGHT",
    },
}

# 通用映射（如果sheet_name匹配但metric_name不匹配，使用这个）
SHEET_METRIC_KEY_MAPPING = {
    "周度-体重": "YY_W_OUT_WEIGHT",
    "周度-屠宰厂宰前活猪重": "YY_W_SLAUGHTER_PRELIVE_WEIGHT",
    "周度-各体重段价差": "YY_W_PRICE_BY_WEIGHT",
}

def fix_metric_keys():
    """修复现有metric的parse_json"""
    db = SessionLocal()
    try:
        # 查找所有没有metric_key的metric
        metrics = db.query(DimMetric).all()
        
        fixed_count = 0
        for metric in metrics:
            # 检查parse_json中是否有metric_key
            has_metric_key = False
            if metric.parse_json:
                has_metric_key = bool(metric.parse_json.get("metric_key"))
            
            if not has_metric_key:
                # 尝试从映射中获取metric_key
                metric_key = None
                sheet_mapping = METRIC_KEY_MAPPING.get(metric.sheet_name or "")
                if sheet_mapping:
                    metric_key = sheet_mapping.get(metric.metric_name)
                
                # 如果精确匹配失败，尝试使用sheet级别的默认值
                if not metric_key:
                    metric_key = SHEET_METRIC_KEY_MAPPING.get(metric.sheet_name or "")
                
                if metric_key:
                    if not metric.parse_json:
                        metric.parse_json = {}
                    metric.parse_json["metric_key"] = metric_key
                    fixed_count += 1
                    print(f"  ✓ 修复: {metric.sheet_name}::{metric.metric_name} -> {metric_key}")
                else:
                    print(f"  ⚠️  无法推断: {metric.sheet_name}::{metric.metric_name}")
        
        db.commit()
        print(f"\n✅ 修复完成: 共修复 {fixed_count} 个metric")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 80)
    print("修复metric的parse_json，补充缺失的metric_key")
    print("=" * 80)
    fix_metric_keys()
