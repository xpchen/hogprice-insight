"""批量计算所有指标的metrics"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.metrics_calculator import calculate_all_indicators_metrics


def main():
    """执行批量计算"""
    db = SessionLocal()
    
    try:
        print("开始批量计算指标metrics...")
        print("=" * 50)
        
        # 计算所有指标的metrics
        calculate_all_indicators_metrics(db, freq=None)
        
        print("\n" + "=" * 50)
        print("计算完成！")
        
    except Exception as e:
        print(f"\n计算失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
