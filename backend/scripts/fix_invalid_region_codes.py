"""修复无效的 region_code - 将中文 region_code 映射到标准代码，并更新 fact_indicator_ts"""
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
from app.services.region_mapping_service import resolve_region_code, REGION_DEFINITIONS


# 无效 region_code 到标准 region_code 的映射
INVALID_TO_VALID_MAPPING = {
    # 中文名称 -> 标准代码
    "中国": "NATION",
    "全国": "NATION",
    
    # 省份中文名称 -> 标准代码
    "黑龙江": "HEILONGJIANG",
    "吉林": "JILIN",
    "辽宁": "LIAONING",
    "内蒙古": "INNER_MONGOLIA",
    "山东": "SHANDONG",
    "河北": "HEBEI",
    "河南": "HENAN",
    "山西": "SHANXI",
    "陕西": "SHAANXI",
    "重庆": "CHONGQING",
    "四川": "SICHUAN",
    "贵州": "GUIZHOU",
    "云南": "YUNNAN",
    "广西": "GUANGXI",
    "湖北": "HUBEI",
    "湖南": "HUNAN",
    "江西": "JIANGXI",
    "浙江": "ZHEJIANG",
    "广东": "GUANGDONG",
    
    # 无效的指标名称 -> 应该使用 NATION（这些数据可能是全国数据）
    "出栏价": "NATION",
    "均价": "NATION",
    "场均价": "NATION",
    "场价": "NATION",
    
    # 无效的企业类型 -> 应该使用 NATION
    "样本养殖企业": "NATION",
    "规模化养殖场": "NATION",
}


def fix_invalid_region_codes(db, dry_run: bool = True):
    """
    修复无效的 region_code
    
    Args:
        db: 数据库会话
        dry_run: 是否只是预览（不实际更新）
    
    Returns:
        修复统计信息
    """
    print("=" * 60)
    print("修复无效的 region_code")
    print("=" * 60)
    
    # 1. 查找所有无效的 region_code
    invalid_regions = db.query(DimRegion).filter(
        ~DimRegion.region_code.in_(list(REGION_DEFINITIONS.keys()))
    ).all()
    
    if not invalid_regions:
        print("\n✓ 没有发现无效的 region_code")
        return {"fixed": 0, "skipped": 0}
    
    print(f"\n发现 {len(invalid_regions)} 个无效的 region_code")
    print("-" * 60)
    
    fixed_count = 0
    skipped_count = 0
    updates_to_apply = []
    
    for invalid_region in invalid_regions:
        invalid_code = invalid_region.region_code
        
        # 查找映射
        valid_code = INVALID_TO_VALID_MAPPING.get(invalid_code)
        
        # 如果没有直接映射，尝试通过名称解析
        if not valid_code:
            valid_code = resolve_region_code(invalid_region.region_name)
            # 如果解析出来还是无效的，使用 NATION 作为默认值
            if valid_code not in REGION_DEFINITIONS:
                valid_code = "NATION"
        
        # 检查目标 region_code 是否存在
        target_region = db.query(DimRegion).filter(
            DimRegion.region_code == valid_code
        ).first()
        
        if not target_region:
            print(f"⚠️  {invalid_code} -> {valid_code} (目标区域不存在，将创建)")
            skipped_count += 1
            continue
        
        # 统计需要更新的 fact_indicator_ts 记录数
        affected_count = db.query(FactIndicatorTs).filter(
            FactIndicatorTs.region_code == invalid_code
        ).count()
        
        if affected_count > 0:
            print(f"  {invalid_code:<20} -> {valid_code:<20} ({affected_count} 条数据)")
            updates_to_apply.append({
                "invalid_code": invalid_code,
                "valid_code": valid_code,
                "count": affected_count
            })
        else:
            print(f"  {invalid_code:<20} -> {valid_code:<20} (无数据引用)")
    
    print("-" * 60)
    print(f"总计需要更新 {len(updates_to_apply)} 个 region_code")
    
    if dry_run:
        print("\n[预览模式] 未实际更新数据")
        return {
            "total": len(invalid_regions),
            "fixed": len(updates_to_apply),
            "skipped": skipped_count
        }
    
    # 2. 更新 fact_indicator_ts 中的 region_code（需要处理重复）
    print("\n2. 更新 fact_indicator_ts 中的 region_code...")
    for update in updates_to_apply:
        invalid_code = update["invalid_code"]
        valid_code = update["valid_code"]
        count = update["count"]
        
        # 获取所有需要更新的记录
        records_to_update = db.query(FactIndicatorTs).filter(
            FactIndicatorTs.region_code == invalid_code
        ).all()
        
        updated = 0
        merged = 0
        deleted = 0
        
        for record in records_to_update:
            try:
                # 检查目标 region_code 是否已存在相同唯一键的记录
                if record.freq == "D":
                    existing = db.query(FactIndicatorTs).filter(
                        FactIndicatorTs.indicator_code == record.indicator_code,
                        FactIndicatorTs.region_code == valid_code,
                        FactIndicatorTs.freq == "D",
                        FactIndicatorTs.trade_date == record.trade_date
                    ).first()
                else:  # W
                    existing = db.query(FactIndicatorTs).filter(
                        FactIndicatorTs.indicator_code == record.indicator_code,
                        FactIndicatorTs.region_code == valid_code,
                        FactIndicatorTs.freq == "W",
                        FactIndicatorTs.week_end == record.week_end
                    ).first()
                
                if existing:
                    # 如果已存在，删除重复的记录
                    merged += 1
                    db.delete(record)
                    db.flush()  # 立即删除
                else:
                    # 如果不存在，直接更新 region_code
                    record.region_code = valid_code
                    db.flush()  # 立即更新，避免批量更新时的唯一键冲突
                    updated += 1
            except Exception as e:
                # 如果更新失败（可能是唯一键冲突），删除这条记录
                print(f"    ⚠️  处理记录 {record.id} 时出错: {e}，将删除")
                db.rollback()
                db.delete(record)
                db.flush()
                deleted += 1
        
        print(f"  ✓ {invalid_code} -> {valid_code}: 更新了 {updated} 条，合并了 {merged} 条（删除重复）")
        fixed_count += updated
        deleted += merged
    
    db.commit()
    
    # 3. 删除无效的 region 记录（如果没有数据引用了）
    print("\n3. 删除无效的 region 记录...")
    deleted_count = 0
    for invalid_region in invalid_regions:
        # 检查是否还有数据引用
        remaining_count = db.query(FactIndicatorTs).filter(
            FactIndicatorTs.region_code == invalid_region.region_code
        ).count()
        
        if remaining_count == 0:
            db.delete(invalid_region)
            deleted_count += 1
            print(f"  ✓ 删除了 region: {invalid_region.region_code}")
    
    db.commit()
    
    print(f"\n✓ 修复完成！")
    print(f"  - 更新了 {fixed_count} 条 fact_indicator_ts 记录")
    print(f"  - 删除了 {deleted_count} 个无效的 region 记录")
    
    return {
        "total": len(invalid_regions),
        "fixed": fixed_count,
        "deleted": deleted_count,
        "skipped": skipped_count
    }


def main():
    """执行修复"""
    db = SessionLocal()
    
    try:
        # 先预览
        print("\n1. 预览需要修复的 region_code...")
        preview_result = fix_invalid_region_codes(db, dry_run=True)
        
        if preview_result["fixed"] == 0:
            print("\n✓ 没有需要修复的数据")
            return
        
        # 确认
        print(f"\n2. 执行修复...")
        result = fix_invalid_region_codes(db, dry_run=False)
        
        print("\n" + "=" * 60)
        print("✓ 修复完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 修复失败: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
