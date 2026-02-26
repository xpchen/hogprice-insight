-- ============================================================================
-- 最新观察数据查询 - 查看已导入的数据
-- 用途：按指标/sheet 汇总，查看最新日期、条数
-- ============================================================================

-- 1. 按 sheet_name 汇总：每个 sheet 的最新日期、数据条数
-- ============================================================================
SELECT 
    dm.sheet_name AS '数据表/sheet',
    dm.metric_name AS '指标名称',
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) AS 'metric_key',
    COUNT(fo.id) AS '条数',
    MIN(fo.obs_date) AS '最早日期',
    MAX(fo.obs_date) AS '最新日期',
    MAX(COALESCE(fo.period_end, fo.obs_date)) AS '最新周期结束'
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
GROUP BY dm.sheet_name, dm.id, dm.metric_name, JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key'))
ORDER BY dm.sheet_name, dm.metric_name;


-- 2. 简化版：按 sheet 汇总（同一 sheet 下多个指标合并）
-- ============================================================================
SELECT 
    dm.sheet_name AS 'sheet',
    COUNT(DISTINCT dm.id) AS '指标数',
    COUNT(fo.id) AS '总条数',
    MIN(fo.obs_date) AS '最早日期',
    MAX(fo.obs_date) AS '最新日期'
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
GROUP BY dm.sheet_name
ORDER BY MAX(fo.obs_date) DESC;


-- 3. 最新 30 天有数据的 sheet（近期活跃数据）
-- ============================================================================
SELECT 
    dm.sheet_name AS 'sheet',
    COUNT(DISTINCT dm.id) AS '指标数',
    COUNT(fo.id) AS '近期条数',
    MAX(fo.obs_date) AS '最新日期'
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE fo.obs_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY dm.sheet_name
ORDER BY MAX(fo.obs_date) DESC;


-- 4. 查看各 sheet 最新一条数据样例（含周期）
-- ============================================================================
SELECT 
    dm.sheet_name AS 'sheet',
    dm.metric_name AS 'metric_name',
    fo.obs_date,
    fo.period_type,
    fo.period_start,
    fo.period_end,
    fo.value,
    fo.tags_json
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE (dm.sheet_name, fo.id) IN (
    SELECT dm2.sheet_name, MAX(fo2.id)
    FROM fact_observation fo2
    JOIN dim_metric dm2 ON fo2.metric_id = dm2.id
    GROUP BY dm2.sheet_name
)
ORDER BY dm.sheet_name;


-- 5. 全局最新观察数据（最近导入的 50 条）
-- ============================================================================
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_type,
    fo.period_end,
    fo.value,
    dm.sheet_name,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) AS metric_key
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
ORDER BY fo.obs_date DESC, fo.period_end DESC
LIMIT 50;


-- 6. 关键业务指标最新数据（常用展示页用到的指标）
-- ============================================================================
SELECT 
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) AS metric_key,
    dm.sheet_name,
    dm.metric_name,
    MAX(fo.obs_date) AS latest_obs_date,
    MAX(COALESCE(fo.period_end, fo.obs_date)) AS latest_period,
    COUNT(*) AS cnt
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) IN (
    'GL_D_PRICE_NATION',           -- A1 全国猪价
    'YY_D_SLAUGHTER_TOTAL',        -- A1 日度屠宰量
    'YY_W_SLAUGHTER_PRELIVE_WEIGHT', -- A2 宰前均重
    'YY_W_OUT_WEIGHT',             -- A2 出栏均重
    'CR5_DAILY_OUTPUT',            -- D1 CR5日度出栏
    'PROVINCE_ACTUAL',             -- D2 实际出栏量
    'CR5_MONTHLY_PLAN'             -- D3 销售计划
)
   OR dm.sheet_name IN ('集团企业出栏价', '汇总', '重点省区汇总', '华宝和牧原白条')
GROUP BY dm.id, dm.sheet_name, dm.metric_name, JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key'))
ORDER BY latest_period DESC;
