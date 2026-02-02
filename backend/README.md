# 后端开发指南

## 环境配置

### 1. 激活虚拟环境

项目使用虚拟环境 `env`，位于 `D:\Workspace\hogprice-insight\backend\env`

**Windows PowerShell:**
```powershell
.\env\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
.\env\Scripts\activate.bat
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 数据库配置

项目使用MySQL数据库，配置信息在 `app/core/config.py` 中：

- 用户名：root
- 密码：root
- 数据库名：hogprice
- 主机：localhost
- 端口：3306

### 4. 创建数据库

**方式1：使用初始化脚本（推荐）**

```bash
python init_db.py
```

**方式2：手动创建**

连接到MySQL并执行：

```sql
CREATE DATABASE IF NOT EXISTS hogprice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. 运行数据库迁移

```bash
# 初始化Alembic（如果还没有）
alembic upgrade head
```

### 6. 启动开发服务器

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

服务器启动后：
- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 环境变量（可选）

可以创建 `.env` 文件覆盖默认配置：

```env
DATABASE_URL=mysql+pymysql://root:root@localhost:3306/hogprice?charset=utf8mb4
SECRET_KEY=your-secret-key-here
```

## 初始化数据

创建初始用户和角色：

```python
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.sys_user import SysUser
from app.models.sys_role import SysRole
from app.models.sys_user_role import SysUserRole

db = SessionLocal()

# 创建角色
roles = [
    {"code": "admin", "name": "管理员"},
    {"code": "analyst", "name": "分析师"},
    {"code": "viewer", "name": "查看者"}
]

for role_data in roles:
    role = db.query(SysRole).filter(SysRole.code == role_data["code"]).first()
    if not role:
        role = SysRole(**role_data)
        db.add(role)

db.commit()

# 创建管理员用户
admin_user = db.query(SysUser).filter(SysUser.username == "admin").first()
if not admin_user:
    admin_user = SysUser(
        username="admin",
        password_hash=get_password_hash("admin123"),  # 默认密码
        display_name="管理员",
        is_active=True
    )
    db.add(admin_user)
    db.flush()
    
    # 分配admin角色
    admin_role = db.query(SysRole).filter(SysRole.code == "admin").first()
    if admin_role:
        user_role = SysUserRole(user_id=admin_user.id, role_id=admin_role.id)
        db.add(user_role)

db.commit()
db.close()
```

## 项目结构

```
backend/
  app/
    api/              # API路由
    core/             # 核心配置
    models/           # 数据模型
    services/         # 业务逻辑
    utils/            # 工具函数
  alembic/            # 数据库迁移
  main.py            # 应用入口
  init_db.py         # 数据库初始化脚本
  requirements.txt   # Python依赖
```
