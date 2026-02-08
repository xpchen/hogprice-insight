-- 检查日度屠宰量数据的SQL查询

-- 1. 查找屠宰量指标（包括通过parse_json中的metric_key查找）
SELECT 
    id,
    metric_name,
    raw_header,
    sheet_name,
    freq,
    unit,
    parse_json,
    CASE 
        WHEN parse_json IS NOT NULL AND JSON_EXTRACT(parse_json, '$.metric_key') IS NOT NULL 
        THEN JSON_EXTRACT(parse_json, '$.metric_key')
        ELSE NULL
    END as metric_key
FROM dim_metric
WHERE (
    metric_name LIKE '%屠宰量%' 
    OR metric_name LIKE '%宰量%'
    OR raw_header LIKE '%屠宰量%'
    OR raw_header LIKE '%宰量%'
    OR (parse_json IS NOT NULL AND JSON_EXTRACT(parse_json, '$.metric_key') LIKE '%SLAUGHTER%')
)
AND (
    sheet_name = '价格+宰量' 
    OR sheet_name IS NULL
)
AND freq = 'D'
ORDER BY id;

-- 1.1 查找包含YY_D_SLAUGHTER_TOTAL_2的指标
SELECT 
    id,
    metric_name,
    raw_header,
    sheet_name,
    freq,
    unit,
    parse_json,
    JSON_EXTRACT(parse_json, '$.metric_key') as metric_key
FROM dim_metric
WHERE parse_json IS NOT NULL
AND JSON_EXTRACT(parse_json, '$.metric_key') = 'YY_D_SLAUGHTER_TOTAL_2';

-- 2. 检查观测数据（优先使用metric_key="YY_D_SLAUGHTER_TOTAL_2"）
SELECT 
    COUNT(*) as total_count,
    COUNT(value) as non_null_count,
    COUNT(*) - COUNT(value) as null_count,
    MIN(obs_date) as earliest_date,
    MAX(obs_date) as latest_date,
    MIN(value) as min_value,
    MAX(value) as max_value,
    AVG(value) as avg_value
FROM fact_observation
WHERE metric_id = (
    SELECT id FROM dim_metric 
    WHERE JSON_EXTRACT(parse_json, '$.metric_key') = 'YY_D_SLAUGHTER_TOTAL_2'
    AND freq = 'D'
    LIMIT 1
)
AND period_type = 'day';

-- 3. 查看最近的数据样本（前20条，优先使用metric_key）
SELECT 
    obs_date,
    value,
    metric_id,
    period_type,
    created_at
FROM fact_observation
WHERE metric_id = (
    SELECT id FROM dim_metric 
    WHERE JSON_EXTRACT(parse_json, '$.metric_key') = 'YY_D_SLAUGHTER_TOTAL_2'
    AND freq = 'D'
    LIMIT 1
)
AND period_type = 'day'
ORDER BY obs_date DESC
LIMIT 20;

-- 4. 按年份统计数据
SELECT 
    YEAR(obs_date) as year,
    COUNT(*) as total_count,
    COUNT(value) as non_null_count,
    COUNT(*) - COUNT(value) as null_count,
    MIN(value) as min_value,
    MAX(value) as max_value,
    AVG(value) as avg_value
FROM fact_observation
WHERE metric_id = (
    SELECT id FROM dim_metric 
    WHERE (
        metric_name LIKE '%屠宰量%' 
        OR metric_name LIKE '%宰量%'
        OR raw_header LIKE '%屠宰量%'
        OR raw_header LIKE '%宰量%'
    )
    AND sheet_name = '价格+宰量'
    AND freq = 'D'
    LIMIT 1
)
AND period_type = 'day'
GROUP BY YEAR(obs_date)
ORDER BY year DESC;

-- 5. 检查2025和2026年的数据（因为API返回的是这两个年份，优先使用metric_key）
SELECT 
    obs_date,
    value,
    metric_id
FROM fact_observation
WHERE metric_id = (
    SELECT id FROM dim_metric 
    WHERE JSON_EXTRACT(parse_json, '$.metric_key') = 'YY_D_SLAUGHTER_TOTAL_2'
    AND freq = 'D'
    LIMIT 1
)
AND period_type = 'day'
AND YEAR(obs_date) IN (2025, 2026)
ORDER BY obs_date
LIMIT 50;
