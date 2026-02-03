"""修复ganglian_daily_fat_std_spread表中region_code字段，将完整列名替换为提取后的省区名称"""
import sys
import os
import io
import re
from pathlib import Path

# 设置UTF-8编码输出（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from sqlalchemy import text


def fix_region_codes(db, auto_confirm=False):
    """修复region_code字段"""
    print("\n" + "="*80)
    print("修复 ganglian_daily_fat_std_spread 表的 region_code 字段")
    print("="*80)
    
    # 提取模式
    pattern = r'生猪标肥：价差：(.*?)（日）'
    
    # 查询所有需要修复的记录
    results = db.execute(text("""
        SELECT DISTINCT region_code
        FROM ganglian_daily_fat_std_spread
        WHERE region_code LIKE '%生猪标肥：价差：%'
    """))
    
    updates = []
    for row in results:
        old_region_code = row[0]
        match = re.search(pattern, old_region_code)
        if match:
            new_region_code = match.group(1).strip()
            updates.append((old_region_code, new_region_code))
    
    if not updates:
        print("\n  没有需要修复的记录")
        return
    
    print(f"\n  找到 {len(updates)} 个需要修复的region_code：\n")
    print(f"  {'原值':<40} {'新值':<10}")
    print(f"  {'-'*40} {'-'*10}")
    
    for old_val, new_val in updates:
        print(f"  {old_val:<40} {new_val:<10}")
    
    # 确认是否执行更新
    if not auto_confirm:
        print(f"\n  是否执行更新？(y/n): ", end="", flush=True)
        try:
            confirm = input().strip().lower()
        except EOFError:
            print("\n  非交互式环境，使用自动模式")
            confirm = 'y'
    else:
        confirm = 'y'
    
    if confirm != 'y' and confirm != '是':
        print("  已取消更新")
        return
    
    # 执行更新
    print(f"\n  开始更新...")
    updated_count = 0
    
    for old_val, new_val in updates:
        result = db.execute(text("""
            UPDATE ganglian_daily_fat_std_spread
            SET region_code = :new_val
            WHERE region_code = :old_val
        """), {"new_val": new_val, "old_val": old_val})
        
        updated_count += result.rowcount
        print(f"  ✓ {old_val} -> {new_val}: 更新 {result.rowcount} 条记录")
    
    db.commit()
    
    print(f"\n  ✅ 更新完成！共更新 {updated_count} 条记录")
    
    # 验证更新结果
    print(f"\n  验证更新结果：")
    verify_results = db.execute(text("""
        SELECT 
            region_code,
            COUNT(*) as count
        FROM ganglian_daily_fat_std_spread
        GROUP BY region_code
        ORDER BY region_code
    """))
    
    print(f"\n  {'省份':<10} {'数据条数':<12}")
    print(f"  {'-'*10} {'-'*12}")
    
    for row in verify_results:
        region_code = row[0]
        count = row[1]
        print(f"  {region_code:<10} {count:<12}")


def main():
    """主函数"""
    import sys
    auto_confirm = len(sys.argv) > 1 and sys.argv[1] in ['-y', '--yes', '--auto']
    
    db = SessionLocal()
    try:
        fix_region_codes(db, auto_confirm=auto_confirm)
    finally:
        db.close()


if __name__ == "__main__":
    main()
