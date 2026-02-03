"""
检查数据库中的用户信息
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.sys_user import SysUser
from app.models.sys_role import SysRole
from app.models.sys_user_role import SysUserRole
from app.core.security import verify_password

def check_users():
    """检查用户信息"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("Checking users in database...")
        print("=" * 60)
        
        # 查询所有用户
        users = db.query(SysUser).all()
        
        if not users:
            print("No users found in database!")
            print("Please run: python init_admin_user.py")
            return False
        
        print(f"\nFound {len(users)} user(s):\n")
        
        for user in users:
            print(f"ID: {user.id}")
            print(f"Username: {user.username}")
            print(f"Display Name: {user.display_name}")
            print(f"Is Active: {user.is_active}")
            print(f"Password Hash: {user.password_hash[:50]}...")
            
            # 测试密码验证
            test_password = "Admin@123"
            is_valid = verify_password(test_password, user.password_hash)
            print(f"Password 'Admin@123' verification: {'✅ VALID' if is_valid else '❌ INVALID'}")
            
            # 查询角色
            roles = db.query(SysRole.code).join(
                SysUserRole, SysUserRole.role_id == SysRole.id
            ).filter(SysUserRole.user_id == user.id).all()
            
            role_codes = [role[0] for role in roles]
            print(f"Roles: {', '.join(role_codes) if role_codes else 'None'}")
            print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = check_users()
    sys.exit(0 if success else 1)
