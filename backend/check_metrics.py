"""
检查数据库中的实际指标数据，用于调整 metric_code_map
"""
import sys
import io
from pathlib import Path

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.dim_metric import DimMetric
from collections import defaultdict


def check_metrics():
    """检查数据库中的指标"""
    db = SessionLocal()
    try:
        # 按指标组分组
        metrics_by_group = defaultdict(list)
        
        all_metrics = db.query(DimMetric).all()
        
        print(f"Total metrics: {len(all_metrics)}\n")
        
        for metric in all_metrics:
            metrics_by_group[metric.metric_group].append({
                "id": metric.id,
                "raw_header": metric.raw_header,
                "metric_name": metric.metric_name,
                "freq": metric.freq
            })
        
        # 打印每个组的指标
        for group, metrics in sorted(metrics_by_group.items()):
            print(f"\n{'='*60}")
            print(f"Metric Group: {group} ({len(metrics)} metrics)")
            print(f"{'='*60}")
            
            for m in metrics[:20]:  # 只显示前20个
                print(f"  ID: {m['id']:4d} | {m['freq']:6s} | {m['metric_name']:20s} | {m['raw_header']}")
            
            if len(metrics) > 20:
                print(f"  ... {len(metrics) - 20} more metrics")
        
        # 查找关键词匹配
        print(f"\n{'='*60}")
        print("Keyword Matching Test")
        print(f"{'='*60}")
        
        keywords_to_test = [
            "标肥", "肥标", "标猪", "肥猪",
            "毛白", "毛猪", "白条",
            "南北", "区域价差",
            "全国", "分省", "省",
            "集团", "企业",
            "自繁自养", "外购", "利润"
        ]
        
        for keyword in keywords_to_test:
            matches = db.query(DimMetric).filter(
                DimMetric.raw_header.like(f"%{keyword}%")
            ).limit(5).all()
            
            if matches:
                print(f"\nKeyword '{keyword}':")
                for m in matches:
                    print(f"  - [{m.metric_group}] {m.raw_header}")
    
    finally:
        db.close()


if __name__ == "__main__":
    check_metrics()
