"""重新生成 dim_region 数据"""
import sys
import os
import io

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.services.region_mapping_service import rebuild_all_regions, list_all_regions


def main():
    """执行重新生成"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("重新生成 dim_region 数据")
        print("=" * 60)
        
        # 先预览
        print("\n1. 预览变更（dry_run=True）...")
        preview_result = rebuild_all_regions(db, dry_run=True)
        print(f"   总定义数: {preview_result['total']}")
        print(f"   将创建: {preview_result['created']}")
        print(f"   将更新: {preview_result['updated']}")
        print(f"   将跳过: {preview_result['skipped']}")
        
        # 确认
        if preview_result['created'] == 0 and preview_result['updated'] == 0:
            print("\n✓ 所有区域数据已是最新，无需更新")
            return
        
        print("\n2. 执行更新...")
        result = rebuild_all_regions(db, dry_run=False)
        print(f"   ✓ 创建了 {result['created']} 条记录")
        print(f"   ✓ 更新了 {result['updated']} 条记录")
        print(f"   ✓ 跳过了 {result['skipped']} 条记录")
        
        # 显示所有区域
        print("\n3. 当前所有区域数据:")
        print("-" * 60)
        print(f"{'代码':<20} {'名称':<10} {'层级':<6} {'父级':<20}")
        print("-" * 60)
        
        all_regions = list_all_regions(db)
        for region in all_regions:
            parent = region.parent_region_code or "-"
            level_name = {"0": "全国", "1": "大区", "2": "省份"}.get(region.region_level, region.region_level)
            print(f"{region.region_code:<20} {region.region_name:<10} {level_name:<6} {parent:<20}")
        
        print("-" * 60)
        print(f"总计: {len(all_regions)} 个区域")
        
        print("\n" + "=" * 60)
        print("✓ 重新生成完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 重新生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
