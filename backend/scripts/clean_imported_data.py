"""清理导入数据的Python脚本"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models import (
    FactFuturesDaily, FactOptionsDaily, FactIndicatorTs, FactIndicatorMetrics,
    ImportBatch, IngestError, IngestMapping,
    DimContract, DimOption
)

def clean_imported_data(keep_contracts=True):
    """
    清理导入的数据
    
    Args:
        keep_contracts: 是否保留合约维度表数据（默认True）
    """
    db = SessionLocal()
    try:
        print("=" * 80)
        print("开始清理导入数据...")
        print("=" * 80)
        
        # 显示清理前的记录数
        print("\n清理前的记录数:")
        print(f"  期货数据: {db.query(FactFuturesDaily).count()}")
        print(f"  期权数据: {db.query(FactOptionsDaily).count()}")
        print(f"  指标时序数据: {db.query(FactIndicatorTs).count()}")
        print(f"  指标metrics: {db.query(FactIndicatorMetrics).count()}")
        print(f"  导入批次: {db.query(ImportBatch).count()}")
        print(f"  导入错误: {db.query(IngestError).count()}")
        print(f"  导入映射: {db.query(IngestMapping).count()}")
        if keep_contracts:
            print(f"  期货合约维度: {db.query(DimContract).count()} (保留)")
            print(f"  期权合约维度: {db.query(DimOption).count()} (保留)")
        else:
            print(f"  期货合约维度: {db.query(DimContract).count()}")
            print(f"  期权合约维度: {db.query(DimOption).count()}")
        
        # 确认
        response = input("\n确认要清理所有导入数据吗？(yes/no): ")
        if response.lower() != 'yes':
            print("取消清理操作")
            return
        
        # 1. 清理事实表数据（使用synchronize_session=False避免加载所有对象到内存）
        print("\n清理事实表数据...")
        try:
            db.query(FactFuturesDaily).delete(synchronize_session=False)
            print("  ✓ fact_futures_daily 已清理")
        except Exception as e:
            print(f"  ⚠ fact_futures_daily 清理失败（表可能不存在）: {e}")
        
        try:
            db.query(FactOptionsDaily).delete(synchronize_session=False)
            print("  ✓ fact_options_daily 已清理")
        except Exception as e:
            print(f"  ⚠ fact_options_daily 清理失败（表可能不存在）: {e}")
        
        try:
            db.query(FactIndicatorTs).delete(synchronize_session=False)
            print("  ✓ fact_indicator_ts 已清理")
        except Exception as e:
            print(f"  ⚠ fact_indicator_ts 清理失败（表可能不存在）: {e}")
        
        try:
            db.query(FactIndicatorMetrics).delete(synchronize_session=False)
            print("  ✓ fact_indicator_metrics 已清理")
        except Exception as e:
            print(f"  ⚠ fact_indicator_metrics 清理失败（表可能不存在）: {e}")
        
        # 2. 清理导入相关的元数据表
        print("\n清理导入元数据表...")
        try:
            db.query(IngestError).delete(synchronize_session=False)
            print("  ✓ ingest_error 已清理")
        except Exception as e:
            print(f"  ⚠ ingest_error 清理失败（表可能不存在）: {e}")
        
        try:
            db.query(IngestMapping).delete(synchronize_session=False)
            print("  ✓ ingest_mapping 已清理")
        except Exception as e:
            print(f"  ⚠ ingest_mapping 清理失败（表可能不存在）: {e}")
        
        try:
            db.query(ImportBatch).delete(synchronize_session=False)
            print("  ✓ import_batch 已清理")
        except Exception as e:
            print(f"  ⚠ import_batch 清理失败（表可能不存在）: {e}")
        
        # 3. 清理合约维度表（可选）
        if not keep_contracts:
            print("\n清理合约维度表...")
            try:
                db.query(DimOption).delete(synchronize_session=False)
                print("  ✓ dim_option 已清理")
            except Exception as e:
                print(f"  ⚠ dim_option 清理失败（表可能不存在）: {e}")
            
            try:
                db.query(DimContract).delete(synchronize_session=False)
                print("  ✓ dim_contract 已清理")
            except Exception as e:
                print(f"  ⚠ dim_contract 清理失败（表可能不存在）: {e}")
        
        # 提交事务
        db.commit()
        
        # 显示清理后的记录数
        print("\n" + "=" * 80)
        print("清理完成！")
        print("=" * 80)
        print("\n清理后的记录数:")
        print(f"  期货数据: {db.query(FactFuturesDaily).count()}")
        print(f"  期权数据: {db.query(FactOptionsDaily).count()}")
        print(f"  指标时序数据: {db.query(FactIndicatorTs).count()}")
        print(f"  指标metrics: {db.query(FactIndicatorMetrics).count()}")
        print(f"  导入批次: {db.query(ImportBatch).count()}")
        print(f"  导入错误: {db.query(IngestError).count()}")
        print(f"  导入映射: {db.query(IngestMapping).count()}")
        print(f"  期货合约维度: {db.query(DimContract).count()}")
        print(f"  期权合约维度: {db.query(DimOption).count()}")
        
    except Exception as e:
        db.rollback()
        print(f"\n清理失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="清理导入的数据")
    parser.add_argument(
        "--remove-contracts",
        action="store_true",
        help="同时清理合约维度表数据（默认保留）"
    )
    args = parser.parse_args()
    
    clean_imported_data(keep_contracts=not args.remove_contracts)
