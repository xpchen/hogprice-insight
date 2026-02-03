"""数据迁移脚本：从fact_observation迁移到fact_indicator_ts"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.data_migration_service import migrate_observations_to_indicators


def main():
    """执行迁移"""
    db = SessionLocal()
    
    try:
        print("开始数据迁移...")
        print("=" * 50)
        
        # 先预览（dry_run=True）
        print("\n1. 预览迁移结果（dry run）...")
        preview_result = migrate_observations_to_indicators(db, dry_run=True)
        print(f"   总记录数: {preview_result['total_observations']}")
        print(f"   预计迁移: {preview_result['migrated']}")
        print(f"   预计失败: {preview_result['failed']}")
        
        if preview_result['errors']:
            print(f"\n   错误示例（前10个）:")
            for error in preview_result['errors'][:10]:
                print(f"     - {error}")
        
        # 确认是否继续
        print("\n" + "=" * 50)
        confirm = input("\n是否继续执行实际迁移？(yes/no): ")
        
        if confirm.lower() != 'yes':
            print("迁移已取消")
            return
        
        # 执行实际迁移
        print("\n2. 执行实际迁移...")
        result = migrate_observations_to_indicators(db, dry_run=False)
        
        print(f"\n迁移完成！")
        print(f"   总记录数: {result['total_observations']}")
        print(f"   成功迁移: {result['migrated']}")
        print(f"   失败: {result['failed']}")
        
        if result['errors']:
            print(f"\n错误列表（前20个）:")
            for error in result['errors'][:20]:
                print(f"  - {error}")
        
    except Exception as e:
        print(f"\n迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
