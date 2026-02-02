"""
测试密码hash生成
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.core.security import get_password_hash, verify_password
    
    password = "Admin@123"
    print("Testing password hash generation...")
    print(f"Password: {password}")
    
    # 生成hash
    hash_value = get_password_hash(password)
    print(f"Hash: {hash_value}")
    
    # 验证hash
    is_valid = verify_password(password, hash_value)
    print(f"Verification: {'PASS' if is_valid else 'FAIL'}")
    
    if is_valid:
        print("\n" + "=" * 60)
        print("Password hash generation works correctly!")
        print("=" * 60)
        print(f"\nSQL INSERT statement:")
        print("-" * 60)
        print(f"INSERT INTO sys_user (username, password_hash, display_name, is_active, created_at, updated_at) VALUES")
        print(f"('admin', '{hash_value}', '管理员', 1, NOW(), NOW());")
        print("-" * 60)
    else:
        print("\nERROR: Password verification failed!")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
