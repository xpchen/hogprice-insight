-- 猪价智盘数据库初始化脚本
-- 使用前请确保已经运行了 alembic upgrade head 创建表结构

USE hogprice;

-- 1. 插入初始角色
INSERT INTO sys_role (code, name, created_at) VALUES
('admin', '管理员', NOW()),
('analyst', '分析师', NOW()),
('viewer', '查看者', NOW())
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 2. 插入admin用户（密码: Admin@123）
-- 注意：密码hash需要通过Python生成，请运行 init_admin_user.py 脚本
-- 或者使用以下Python代码生成hash：
-- from app.core.security import get_password_hash
-- print(get_password_hash('Admin@123'))

-- 3. 查询角色ID（用于后续关联）
-- SELECT id, code FROM sys_role;
