-- 清理导入数据脚本
-- 注意：此脚本会删除所有导入的数据，但保留基础维度表数据（dim_indicator, dim_region等）
-- 注意：如果表不存在，会跳过该表的清理

-- 禁用安全更新模式（仅在当前会话中）
SET SQL_SAFE_UPDATES = 0;

-- 1. 清理事实表数据（导入的数据）
-- 使用WHERE 1=1来绕过MySQL安全更新模式
DELETE FROM fact_futures_daily WHERE 1=1;
DELETE FROM fact_options_daily WHERE 1=1;
DELETE FROM fact_indicator_ts WHERE 1=1;
DELETE FROM fact_indicator_metrics WHERE 1=1;  -- 预计算的指标metrics

-- 2. 清理导入相关的元数据表
DELETE FROM ingest_error WHERE 1=1;
DELETE FROM ingest_mapping WHERE 1=1;
DELETE FROM import_batch WHERE 1=1;

-- 3. 清理合约维度表（可选：如果不想保留合约信息，取消下面的注释）
-- DELETE FROM dim_option WHERE 1=1;
-- DELETE FROM dim_contract WHERE 1=1;

-- 恢复安全更新模式
SET SQL_SAFE_UPDATES = 1;

-- 4. 重置自增ID（可选：如果需要从1开始重新计数）
-- ALTER TABLE fact_futures_daily AUTO_INCREMENT = 1;
-- ALTER TABLE fact_options_daily AUTO_INCREMENT = 1;
-- ALTER TABLE fact_indicator_ts AUTO_INCREMENT = 1;
-- ALTER TABLE fact_indicator_metrics AUTO_INCREMENT = 1;
-- ALTER TABLE import_batch AUTO_INCREMENT = 1;
-- ALTER TABLE ingest_error AUTO_INCREMENT = 1;
-- ALTER TABLE ingest_mapping AUTO_INCREMENT = 1;

-- 查看清理后的记录数（验证）
-- 注意：如果表不存在，查询会报错，这是正常的
SELECT 'fact_futures_daily' AS table_name, COUNT(*) AS record_count FROM fact_futures_daily
UNION ALL
SELECT 'fact_options_daily', COUNT(*) FROM fact_options_daily
UNION ALL
SELECT 'fact_indicator_ts', COUNT(*) FROM fact_indicator_ts
UNION ALL
SELECT 'fact_indicator_metrics', COUNT(*) FROM fact_indicator_metrics
UNION ALL
SELECT 'import_batch', COUNT(*) FROM import_batch
UNION ALL
SELECT 'ingest_error', COUNT(*) FROM ingest_error
UNION ALL
SELECT 'ingest_mapping', COUNT(*) FROM ingest_mapping
UNION ALL
SELECT 'dim_contract', COUNT(*) FROM dim_contract
UNION ALL
SELECT 'dim_option', COUNT(*) FROM dim_option;
