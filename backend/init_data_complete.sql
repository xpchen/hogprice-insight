-- ========================================
-- 猪价智盘数据库完整初始化SQL脚本
-- ========================================
-- 使用说明：
-- 1. 先运行 alembic upgrade head 创建表结构
-- 2. 然后运行此SQL脚本插入初始数据
-- 3. 或者直接运行 init_admin_user.py 脚本（推荐）
-- ========================================

USE hogprice;

-- 1. 插入初始角色
INSERT INTO sys_role (code, name, created_at) VALUES
('admin', '管理员', NOW()),
('analyst', '分析师', NOW()),
('viewer', '查看者', NOW())
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 2. 插入admin用户
-- 注意：密码hash需要通过Python生成
-- 请运行: python init_admin_user.py
-- 或者使用以下命令生成hash后替换下面的hash值：
-- python -c "from app.core.security import get_password_hash; print(get_password_hash('Admin@123'))"

-- 以下是一个示例hash（请替换为实际生成的hash）
-- INSERT INTO sys_user (username, password_hash, display_name, is_active, created_at, updated_at) VALUES
-- ('admin', '$2b$12$YOUR_HASH_HERE', '管理员', 1, NOW(), NOW())
-- ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash);

-- 3. 关联admin用户和admin角色
-- 注意：需要先获取user_id和role_id
-- INSERT INTO sys_user_role (user_id, role_id)
-- SELECT u.id, r.id
-- FROM sys_user u, sys_role r
-- WHERE u.username = 'admin' AND r.code = 'admin'
-- ON DUPLICATE KEY UPDATE user_id=VALUES(user_id);

-- ========================================
-- 推荐方式：直接运行Python脚本
-- python init_admin_user.py
-- ========================================
