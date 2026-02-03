"""
生成包含admin用户的完整SQL脚本
自动生成密码hash并插入到SQL中
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.core.security import get_password_hash
    
    password = "Admin@123"
    hash_value = get_password_hash(password)
    
    # 读取原始SQL文件
    sql_file = Path(__file__).parent / "init_all_tables.sql"
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 查找插入admin用户的注释位置
    admin_insert_sql = f"""
-- ========================================
-- 插入admin用户（密码: Admin@123）
-- ========================================
INSERT INTO sys_user (username, password_hash, display_name, is_active, created_at, updated_at) VALUES
('admin', '{hash_value}', '管理员', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash), is_active=VALUES(is_active);

-- ========================================
-- 关联admin用户和admin角色
-- ========================================
INSERT INTO sys_user_role (user_id, role_id)
SELECT u.id, r.id
FROM sys_user u, sys_role r
WHERE u.username = 'admin' AND r.code = 'admin'
ON DUPLICATE KEY UPDATE user_id=VALUES(user_id);

"""
    
    # 在"完成提示"之前插入admin用户SQL
    if '-- ========================================' in sql_content and '完成提示' in sql_content:
        # 找到"完成提示"的位置
        parts = sql_content.split('-- ========================================\n-- 完成提示\n-- ========================================')
        if len(parts) == 2:
            sql_content = parts[0] + admin_insert_sql + '\n-- ========================================\n-- 完成提示\n-- ========================================' + parts[1]
        else:
            # 如果找不到，在文件末尾添加
            sql_content = sql_content.rstrip() + '\n' + admin_insert_sql
    else:
        # 在文件末尾添加
        sql_content = sql_content.rstrip() + '\n' + admin_insert_sql
    
    # 写入新文件
    output_file = Path(__file__).parent / "init_all_tables_with_admin.sql"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    
    print("=" * 60)
    print("SQL script generated successfully!")
    print("=" * 60)
    print(f"Password: {password}")
    print(f"Hash: {hash_value}")
    print(f"Output file: {output_file}")
    print("=" * 60)
    print("\nYou can now run:")
    print("  mysql -u root -p < init_all_tables_with_admin.sql")
    print("or")
    print("  run_sql_with_admin.bat")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
