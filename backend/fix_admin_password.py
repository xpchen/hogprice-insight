"""
修复admin用户密码
直接更新数据库中的密码hash
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.core.security import get_password_hash, verify_password
from app.models.sys_user import SysUser

def fix_admin_password():
    """修复admin用户密码"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("Fixing admin user password...")
        print("=" * 60)
        
        # 查找admin用户
        admin_user = db.query(SysUser).filter(SysUser.username == "admin").first()
        
        if not admin_user:
            print("ERROR: admin user not found!")
            print("Please run: python init_admin_user.py")
            return False
        
        print(f"Found user: {admin_user.username}")
        print(f"Current hash: {admin_user.password_hash[:50]}...")
        
        # 生成新的密码hash
        new_password = "Admin@123"
        new_hash = get_password_hash(new_password)
        print(f"New hash: {new_hash[:50]}...")
        
        # 验证新hash
        is_valid = verify_password(new_password, new_hash)
        print(f"Verification test: {'✅ PASS' if is_valid else '❌ FAIL'}")
        
        if not is_valid:
            print("ERROR: Generated hash verification failed!")
            return False
        
        # 更新密码
        admin_user.password_hash = new_hash
        admin_user.is_active = True
        db.commit()
        
        print("\n✅ Password updated successfully!")
        print("=" * 60)
        print("Login credentials:")
        print("  Username: admin")
        print("  Password: Admin@123")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = fix_admin_password()
    sys.exit(0 if success else 1)
