"""
创建admin用户密码hash的简单脚本
使用bcrypt直接生成，避免passlib的问题
"""
import bcrypt
import sys

password = "Admin@123"

try:
    # 生成salt
    salt = bcrypt.gensalt(rounds=12)
    # 生成hash
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    print("=" * 60)
    print("Password hash generated successfully!")
    print("=" * 60)
    print(f"Password: {password}")
    print(f"Hash: {password_hash}")
    print("=" * 60)
    print("\nSQL INSERT statement:")
    print("-" * 60)
    print(f"INSERT INTO sys_user (username, password_hash, display_name, is_active, created_at, updated_at) VALUES")
    print(f"('admin', '{password_hash}', '管理员', 1, NOW(), NOW())")
    print(f"ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash), is_active=VALUES(is_active);")
    print("-" * 60)
    
    # 更新SQL文件
    sql_file = "init_all_tables.sql"
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换hash值
        import re
        pattern = r"\('admin', '\$2b\$12\$[^']+', '管理员'"
        replacement = f"('admin', '{password_hash}', '管理员'"
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(sql_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"\nUpdated {sql_file} with new hash value!")
        else:
            print(f"\nNote: Could not find hash pattern in {sql_file}")
            print("Please manually update the hash value in the SQL file.")
            
    except Exception as e:
        print(f"\nWarning: Could not update SQL file: {e}")
        print("Please manually update the hash value in init_all_tables.sql")
    
except ImportError:
    print("ERROR: bcrypt module not found!")
    print("Please install: pip install bcrypt")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
