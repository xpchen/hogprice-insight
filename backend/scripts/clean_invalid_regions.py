"""清理无效的区域数据"""
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
from app.models import DimRegion, FactIndicatorTs
from app.services.region_mapping_service import REGION_DEFINITIONS, is_valid_region_name


def clean_invalid_regions(db, dry_run: bool = True):
    """
    清理无效的区域数据
    
    Args:
        db: 数据库会话
        dry_run: 是否只是预览（不实际删除）
    
    Returns:
        清理统计信息
    """
    # 获取所有区域
    all_regions = db.query(DimRegion).all()
    
    invalid_regions = []
    valid_region_codes = set(REGION_DEFINITIONS.keys())
    
    for region in all_regions:
        # 检查1: region_code 不在定义中
        if region.region_code not in valid_region_codes:
            invalid_regions.append({
                "region": region,
                "reason": f"region_code '{region.region_code}' 不在预定义列表中"
            })
            continue
        
        # 检查2: region_name 不是有效的区域名称
        if not is_valid_region_name(region.region_name):
            invalid_regions.append({
                "region": region,
                "reason": f"region_name '{region.region_name}' 不是有效的区域名称"
            })
            continue
        
        # 检查3: 验证 region_code 和 region_name 是否匹配
        expected_info = REGION_DEFINITIONS.get(region.region_code)
        if expected_info:
            expected_name, expected_level, expected_parent = expected_info
            if region.region_name != expected_name:
                invalid_regions.append({
                    "region": region,
                    "reason": f"region_name 不匹配：期望 '{expected_name}'，实际 '{region.region_name}'"
                })
                continue
    
    # 检查是否有数据引用这些无效区域
    invalid_region_codes = [r["region"].region_code for r in invalid_regions]
    referenced_regions = set()
    
    if invalid_region_codes:
        # 检查 fact_indicator_ts 中是否有引用
        referenced = db.query(FactIndicatorTs.region_code).filter(
            FactIndicatorTs.region_code.in_(invalid_region_codes)
        ).distinct().all()
        referenced_regions = {r[0] for r in referenced}
    
    print("=" * 60)
    print("清理无效区域数据")
    print("=" * 60)
    print(f"\n发现 {len(invalid_regions)} 个无效区域：")
    print("-" * 60)
    print(f"{'代码':<25} {'名称':<20} {'原因':<30}")
    print("-" * 60)
    
    for item in invalid_regions:
        region = item["region"]
        reason = item["reason"]
        referenced = "（有数据引用）" if region.region_code in referenced_regions else ""
        print(f"{region.region_code:<25} {region.region_name:<20} {reason:<30} {referenced}")
    
    print("-" * 60)
    
    if referenced_regions:
        print(f"\n⚠️  警告：有 {len(referenced_regions)} 个无效区域被数据引用，删除前需要先处理这些数据！")
        print("被引用的区域代码：", ", ".join(referenced_regions))
    
    if dry_run:
        print("\n[预览模式] 未实际删除数据")
        return {
            "total": len(all_regions),
            "invalid": len(invalid_regions),
            "referenced": len(referenced_regions),
            "can_delete": len(invalid_regions) - len(referenced_regions)
        }
    else:
        # 只删除没有被引用的无效区域
        deleted_count = 0
        for item in invalid_regions:
            region = item["region"]
            if region.region_code not in referenced_regions:
                db.delete(region)
                deleted_count += 1
        
        db.commit()
        
        print(f"\n✓ 已删除 {deleted_count} 个无效区域")
        if len(referenced_regions) > 0:
            print(f"⚠️  保留了 {len(referenced_regions)} 个被数据引用的无效区域，需要手动处理")
        
        return {
            "total": len(all_regions),
            "invalid": len(invalid_regions),
            "referenced": len(referenced_regions),
            "deleted": deleted_count
        }


def main():
    """执行清理"""
    db = SessionLocal()
    
    try:
        # 先预览
        print("\n1. 预览无效区域...")
        preview_result = clean_invalid_regions(db, dry_run=True)
        
        if preview_result["invalid"] == 0:
            print("\n✓ 没有发现无效区域")
            return
        
        # 确认
        if preview_result["can_delete"] > 0:
            print(f"\n2. 将删除 {preview_result['can_delete']} 个无效区域...")
            result = clean_invalid_regions(db, dry_run=False)
            print(f"\n✓ 清理完成！")
        else:
            print("\n⚠️  所有无效区域都被数据引用，无法自动删除")
            print("   请先处理引用这些区域的数据，然后手动删除")
        
    except Exception as e:
        print(f"\n✗ 清理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
