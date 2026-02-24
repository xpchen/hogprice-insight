-- ========================================
-- 清除所有业务数据（保留用户与角色）
-- 用于测试导入模块前清空数据
-- ========================================
-- 使用：mysql -u root -p hogprice < backend/scripts/clear_all_data.sql
-- 或：mysql -u root -p
--     USE hogprice;
--     SOURCE D:/Workspace/hogprice-insight/backend/scripts/clear_all_data.sql;
-- ========================================

USE hogprice;

SET FOREIGN_KEY_CHECKS = 0;

-- 事实表
TRUNCATE TABLE fact_observation_tag;
TRUNCATE TABLE fact_observation;
TRUNCATE TABLE fact_futures_daily;
TRUNCATE TABLE fact_options_daily;
TRUNCATE TABLE fact_indicator_ts;
TRUNCATE TABLE fact_indicator_metrics;

-- Raw 层
TRUNCATE TABLE raw_table;
TRUNCATE TABLE raw_sheet;
TRUNCATE TABLE raw_file;

-- 导入相关
TRUNCATE TABLE ingest_error;
TRUNCATE TABLE ingest_mapping;
TRUNCATE TABLE import_batch;

-- 配置与映射
TRUNCATE TABLE ingest_profile_sheet;
TRUNCATE TABLE ingest_profile;
TRUNCATE TABLE metric_alias;
TRUNCATE TABLE metric_code_map;

-- 维度表（业务数据）
TRUNCATE TABLE dim_location_alias;
TRUNCATE TABLE dim_location;
TRUNCATE TABLE dim_metric;
TRUNCATE TABLE dim_geo;
TRUNCATE TABLE dim_company;
TRUNCATE TABLE dim_warehouse;
TRUNCATE TABLE dim_region;
TRUNCATE TABLE dim_indicator;
TRUNCATE TABLE dim_source;
TRUNCATE TABLE dim_contract;
TRUNCATE TABLE dim_option;

-- 报表与图表
TRUNCATE TABLE report_run;
TRUNCATE TABLE report_template;
TRUNCATE TABLE chart_template;

SET FOREIGN_KEY_CHECKS = 1;

-- 重新插入基础数据源（导入需要）
INSERT INTO dim_source (source_code, source_name, update_freq, source_type, license_note, created_at, updated_at) VALUES
('YONGYI', '涌益咨询', 'daily,weekly', 'vendor', '涌益咨询数据，需授权使用', NOW(), NOW()),
('GANGLIAN', '钢联数据', 'daily', 'vendor', '钢联数据，需授权使用', NOW(), NOW()),
('MYSTEEL', '钢联数据', 'daily', 'vendor', '钢联数据，需授权使用', NOW(), NOW()),
('DCE', '大连商品交易所', 'daily', 'exchange', '公开数据', NOW(), NOW()),
('ENTERPRISE', '集团企业出栏跟踪', 'daily,monthly', 'vendor', '集团企业出栏数据', NOW(), NOW()),
('ENTERPRISE_MONTHLY', '集团企业月度出栏', 'monthly', 'vendor', '集团企业月度出栏数据', NOW(), NOW()),
('WHITE_STRIP_MARKET', '白条市场跟踪', 'daily', 'vendor', '白条到货量及价格', NOW(), NOW()),
('INDUSTRY_DATA', '生猪产业数据', 'monthly', 'vendor', '协会/NYB/统计局/供需曲线', NOW(), NOW()),
('PREMIUM_DATA', '升贴水数据', 'daily', 'vendor', '期货盘面结算价', NOW(), NOW())
ON DUPLICATE KEY UPDATE source_name=VALUES(source_name), updated_at=NOW();

SELECT '清除完成。已保留 sys_user/sys_role，已重新插入 dim_source。' AS message;
