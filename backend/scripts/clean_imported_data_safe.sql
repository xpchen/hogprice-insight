-- 清理导入数据脚本（安全版本 - 带表存在性检查）
-- 注意：此脚本会删除所有导入的数据，但保留基础维度表数据（dim_indicator, dim_region等）

-- 禁用安全更新模式（仅在当前会话中）
SET SQL_SAFE_UPDATES = 0;

-- 1. 清理事实表数据（导入的数据）
-- 使用存储过程来检查表是否存在
DROP PROCEDURE IF EXISTS clean_imported_data;

DELIMITER $$

CREATE PROCEDURE clean_imported_data()
BEGIN
    DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END;
    
    -- 清理事实表数据
    DELETE FROM fact_futures_daily WHERE 1=1;
    DELETE FROM fact_options_daily WHERE 1=1;
    DELETE FROM fact_indicator_ts WHERE 1=1;
    DELETE FROM fact_indicator_metrics WHERE 1=1;
    
    -- 清理导入相关的元数据表
    DELETE FROM ingest_error WHERE 1=1;
    DELETE FROM ingest_mapping WHERE 1=1;
    DELETE FROM import_batch WHERE 1=1;
    
    -- 可选：清理合约维度表（取消注释以启用）
    -- DELETE FROM dim_option WHERE 1=1;
    -- DELETE FROM dim_contract WHERE 1=1;
    
END$$

DELIMITER ;

-- 执行清理
CALL clean_imported_data();

-- 删除存储过程
DROP PROCEDURE IF EXISTS clean_imported_data;

-- 恢复安全更新模式
SET SQL_SAFE_UPDATES = 1;

-- 查看清理后的记录数（验证）
SELECT 'fact_futures_daily' AS table_name, 
       IFNULL((SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'fact_futures_daily'), 0) AS table_exists,
       IFNULL((SELECT COUNT(*) FROM fact_futures_daily), 0) AS record_count
UNION ALL
SELECT 'fact_options_daily', 
       IFNULL((SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'fact_options_daily'), 0),
       IFNULL((SELECT COUNT(*) FROM fact_options_daily), 0)
UNION ALL
SELECT 'fact_indicator_ts',
       IFNULL((SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'fact_indicator_ts'), 0),
       IFNULL((SELECT COUNT(*) FROM fact_indicator_ts), 0)
UNION ALL
SELECT 'fact_indicator_metrics',
       IFNULL((SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'fact_indicator_metrics'), 0),
       IFNULL((SELECT COUNT(*) FROM fact_indicator_metrics), 0)
UNION ALL
SELECT 'import_batch',
       IFNULL((SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'import_batch'), 0),
       IFNULL((SELECT COUNT(*) FROM import_batch), 0)
UNION ALL
SELECT 'ingest_error',
       IFNULL((SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'ingest_error'), 0),
       IFNULL((SELECT COUNT(*) FROM ingest_error), 0)
UNION ALL
SELECT 'ingest_mapping',
       IFNULL((SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'ingest_mapping'), 0),
       IFNULL((SELECT COUNT(*) FROM ingest_mapping), 0)
UNION ALL
SELECT 'dim_contract',
       IFNULL((SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'dim_contract'), 0),
       IFNULL((SELECT COUNT(*) FROM dim_contract), 0)
UNION ALL
SELECT 'dim_option',
       IFNULL((SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'dim_option'), 0),
       IFNULL((SELECT COUNT(*) FROM dim_option), 0);
