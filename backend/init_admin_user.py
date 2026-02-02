"""
初始化admin用户脚本
创建默认管理员账户：admin / Admin@123
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.sys_user import SysUser
from app.models.sys_role import SysRole
from app.models.sys_user_role import SysUserRole


def init_admin_user():
    """初始化admin用户"""
    db = SessionLocal()
    
    try:
        # 1. 确保角色存在
        roles_data = [
            {"code": "admin", "name": "管理员"},
            {"code": "analyst", "name": "分析师"},
            {"code": "viewer", "name": "查看者"}
        ]
        
        for role_data in roles_data:
            role = db.query(SysRole).filter(SysRole.code == role_data["code"]).first()
            if not role:
                role = SysRole(**role_data)
                db.add(role)
                print(f"创建角色: {role_data['code']} - {role_data['name']}")
            else:
                print(f"角色已存在: {role_data['code']} - {role_data['name']}")
        
        db.commit()
        
        # 2. 创建或更新admin用户
        admin_user = db.query(SysUser).filter(SysUser.username == "admin").first()
        
        if admin_user:
            # 更新密码
            admin_user.password_hash = get_password_hash("Admin@123")
            admin_user.is_active = True
            print("更新admin用户密码")
        else:
            # 创建新用户
            admin_user = SysUser(
                username="admin",
                password_hash=get_password_hash("Admin@123"),
                display_name="管理员",
                is_active=True
            )
            db.add(admin_user)
            print("创建admin用户")
        
        db.flush()
        
        # 3. 分配admin角色
        admin_role = db.query(SysRole).filter(SysRole.code == "admin").first()
        if admin_role:
            # 检查是否已有角色关联
            existing_role = db.query(SysUserRole).filter(
                SysUserRole.user_id == admin_user.id,
                SysUserRole.role_id == admin_role.id
            ).first()
            
            if not existing_role:
                user_role = SysUserRole(user_id=admin_user.id, role_id=admin_role.id)
                db.add(user_role)
                print("分配admin角色")
            else:
                print("admin角色已分配")
        
        db.commit()
        print("\n✅ 初始化完成！")
        print("=" * 50)
        print("默认登录账户：")
        print("  用户名: admin")
        print("  密码: Admin@123")
        print("=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()
    
    return True


if __name__ == "__main__":
    print("开始初始化admin用户...")
    success = init_admin_user()
    sys.exit(0 if success else 1)
