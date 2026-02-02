-- ========================================
-- 猪价智盘 - 完整数据库初始化SQL脚本
-- ========================================
-- 此脚本包含：
-- 1. 创建数据库
-- 2. 创建所有表结构
-- 3. 插入初始角色
-- 4. 插入admin用户（需要先运行 get_password_hash.py 获取密码hash）
-- ========================================
-- 使用方法：
-- mysql -u root -p < init_all_tables.sql
-- 或者：
-- mysql -u root -p
-- source D:/Workspace/hogprice-insight/backend/init_all_tables.sql
-- ========================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS hogprice CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE hogprice;

-- ========================================
-- 表结构创建
-- ========================================

-- 1. 用户表
DROP TABLE IF EXISTS sys_user;
CREATE TABLE sys_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(64),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX ix_sys_user_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 角色表
DROP TABLE IF EXISTS sys_role;
CREATE TABLE sys_role (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(64) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX ix_sys_role_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 用户角色关联表
DROP TABLE IF EXISTS sys_user_role;
CREATE TABLE sys_user_role (
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES sys_role(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 导入批次表
DROP TABLE IF EXISTS import_batch;
CREATE TABLE import_batch (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64),
    uploader_id BIGINT,
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    total_rows BIGINT DEFAULT 0,
    success_rows BIGINT DEFAULT 0,
    failed_rows BIGINT DEFAULT 0,
    error_json JSON,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_import_batch_created_at (created_at),
    FOREIGN KEY (uploader_id) REFERENCES sys_user(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 指标维度表
DROP TABLE IF EXISTS dim_metric;
CREATE TABLE dim_metric (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    metric_group VARCHAR(32) NOT NULL,
    metric_name VARCHAR(64) NOT NULL,
    unit VARCHAR(32),
    freq VARCHAR(16) NOT NULL,
    raw_header VARCHAR(500) NOT NULL,
    sheet_name VARCHAR(64),
    source_updated_at VARCHAR(64),
    parse_json JSON,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_dim_metric_raw_sheet (raw_header, sheet_name),
    INDEX idx_dim_metric_group_freq (metric_group, freq),
    INDEX ix_dim_metric_metric_group (metric_group),
    INDEX ix_dim_metric_metric_name (metric_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. 地区维度表
DROP TABLE IF EXISTS dim_geo;
CREATE TABLE dim_geo (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    province VARCHAR(32) NOT NULL UNIQUE,
    region VARCHAR(32),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX ix_dim_geo_province (province)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. 企业维度表
DROP TABLE IF EXISTS dim_company;
CREATE TABLE dim_company (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(128) NOT NULL UNIQUE,
    province VARCHAR(32),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX ix_dim_company_company_name (company_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. 交割库维度表
DROP TABLE IF EXISTS dim_warehouse;
CREATE TABLE dim_warehouse (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    warehouse_name VARCHAR(128) NOT NULL UNIQUE,
    province VARCHAR(32),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX ix_dim_warehouse_warehouse_name (warehouse_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. 事实表：观测数据
DROP TABLE IF EXISTS fact_observation;
CREATE TABLE fact_observation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    metric_id BIGINT NOT NULL,
    obs_date DATE NOT NULL,
    value DECIMAL(18, 6),
    geo_id BIGINT,
    company_id BIGINT,
    warehouse_id BIGINT,
    tags_json JSON,
    raw_value VARCHAR(64),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_fact_metric_date (metric_id, obs_date),
    INDEX idx_fact_geo_date (geo_id, obs_date),
    INDEX idx_fact_company_date (company_id, obs_date),
    INDEX idx_fact_warehouse_date (warehouse_id, obs_date),
    INDEX ix_fact_observation_metric_id (metric_id),
    INDEX ix_fact_observation_obs_date (obs_date),
    INDEX ix_fact_observation_geo_id (geo_id),
    INDEX ix_fact_observation_company_id (company_id),
    INDEX ix_fact_observation_warehouse_id (warehouse_id),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    FOREIGN KEY (metric_id) REFERENCES dim_metric(id) ON DELETE CASCADE,
    FOREIGN KEY (geo_id) REFERENCES dim_geo(id),
    FOREIGN KEY (company_id) REFERENCES dim_company(id),
    FOREIGN KEY (warehouse_id) REFERENCES dim_warehouse(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 初始数据插入
-- ========================================

-- 插入角色
INSERT INTO sys_role (code, name, created_at) VALUES
('admin', '管理员', NOW()),
('analyst', '分析师', NOW()),
('viewer', '查看者', NOW())
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- ========================================
-- 插入admin用户（密码: Admin@123）
-- Hash值已通过bcrypt生成，密码为 Admin@123
-- 如果此hash无法使用，请运行: python init_admin_user.py 重新创建用户
-- ========================================
INSERT INTO sys_user (username, password_hash, display_name, is_active, created_at, updated_at) VALUES
('admin', '$2b$12$wTE.0V/PiP01RGU.Sc2pOe94b1xVB4hCLMCCwJUNSfVlmvL8XzuV6', '管理员', 1, NOW(), NOW())
ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash), is_active=VALUES(is_active);

-- ========================================
-- 关联admin用户和admin角色
-- ========================================
INSERT INTO sys_user_role (user_id, role_id)
SELECT u.id, r.id
FROM sys_user u, sys_role r
WHERE u.username = 'admin' AND r.code = 'admin'
ON DUPLICATE KEY UPDATE user_id=VALUES(user_id);

-- ========================================
-- 完成提示
-- ========================================
SELECT '========================================' AS '';
SELECT 'Database schema created successfully!' AS '';
SELECT '========================================' AS '';
SELECT '' AS '';
SELECT 'Initialization completed!' AS '';
SELECT '' AS '';
SELECT 'Default login credentials:' AS '';
SELECT '  Username: admin' AS '';
SELECT '  Password: Admin@123' AS '';
SELECT '' AS '';
SELECT 'You can now start the server with: run.bat' AS '';
SELECT '========================================' AS '';
