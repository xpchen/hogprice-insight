"""
生成密码hash的工具脚本
用于生成Admin@123的密码hash，以便在SQL中使用
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.core.security import get_password_hash
    
    password = "Admin@123"
    hash_value = get_password_hash(password)
    
    print("=" * 60)
    print("密码hash生成成功！")
    print("=" * 60)
    print(f"密码: {password}")
    print(f"Hash: {hash_value}")
    print("=" * 60)
    print("\nSQL插入语句：")
    print("-" * 60)
    print(f"INSERT INTO sys_user (username, password_hash, display_name, is_active, created_at, updated_at)")
    print(f"VALUES ('admin', '{hash_value}', '管理员', 1, NOW(), NOW());")
    print("-" * 60)
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
