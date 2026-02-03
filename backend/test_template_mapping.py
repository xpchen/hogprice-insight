"""
测试模板指标映射
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.metric_code_map import resolve_metric_id, METRIC_CODE_MAP
from app.models.dim_metric import DimMetric


def test_mapping():
    """测试指标映射"""
    db = SessionLocal()
    try:
        print("Testing metric code mapping...\n")
        
        for code, config in METRIC_CODE_MAP.items():
            metric_id = resolve_metric_id(db, code)
            if metric_id:
                metric = db.query(DimMetric).filter(DimMetric.id == metric_id).first()
                if metric:
                    print(f"✓ {code:30s} -> ID {metric_id:4d} | [{metric.metric_group:10s}] {metric.raw_header}")
                else:
                    print(f"✗ {code:30s} -> ID {metric_id:4d} (not found)")
            else:
                print(f"✗ {code:30s} -> None (mapping failed)")
        
        print("\n" + "="*80)
        print("Template mapping test completed!")
    
    finally:
        db.close()


if __name__ == "__main__":
    test_mapping()
