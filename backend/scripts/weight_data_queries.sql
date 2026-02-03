-- ============================================================================
-- 均重数据查询SQL - 用于前端展示
-- ============================================================================

-- 查询1: 宰前均重 (YY_W_SLAUGHTER_PRELIVE_WEIGHT, geo_code='NATION')
-- 说明: 查询全国平均值，geo_id为NULL的记录
-- ============================================================================
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) as metric_key,
    dg.province as geo_code,
    JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
    fo.tags_json
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
LEFT JOIN dim_geo dg ON fo.geo_id = dg.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_SLAUGHTER_PRELIVE_WEIGHT'
  AND fo.period_type = 'week'
  AND fo.geo_id IS NULL  -- NATION数据geo_id为NULL
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- ============================================================================
-- 查询2: 出栏均重 (YY_W_OUT_WEIGHT, indicator='全国2')
-- 说明: 查询indicator为'全国2'的记录（修复后，parser会将"全国2"列解析为indicator='全国2'）
-- ============================================================================
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) as metric_key,
    JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
    fo.tags_json
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '全国2'
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- 如果上面查询没有结果（旧数据），可以使用以下查询（geo_code='NATION'）：
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) as metric_key,
    JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
    fo.tags_json
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND fo.geo_id IS NULL  -- 全国数据
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重'  -- 临时使用实际值
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- 如果上面查询没有结果，可以查看所有indicator值：
SELECT DISTINCT
    JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
GROUP BY indicator
ORDER BY count DESC;

-- ============================================================================
-- 查询3: 规模场出栏均重 (YY_W_WEIGHT_GROUP, tag_key='crowd', tag_value='集团')
-- ============================================================================
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) as metric_key,
    fot.tag_key,
    fot.tag_value
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
JOIN fact_observation_tag fot ON fo.id = fot.observation_id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_WEIGHT_GROUP'
  AND fo.period_type = 'week'
  AND fot.tag_key = 'crowd'
  AND fot.tag_value = '集团'
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- ============================================================================
-- 查询4: 散户出栏均重 (YY_W_WEIGHT_SCATTER, tag_key='crowd', tag_value='散户')
-- ============================================================================
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) as metric_key,
    fot.tag_key,
    fot.tag_value
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
JOIN fact_observation_tag fot ON fo.id = fot.observation_id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_WEIGHT_SCATTER'
  AND fo.period_type = 'week'
  AND fot.tag_key = 'crowd'
  AND fot.tag_value = '散户'
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- ============================================================================
-- 查询5: 90Kg出栏占比 (YY_W_OUT_WEIGHT, indicator='90Kg出栏占比')
-- 说明: 查询全国数据（geo_id为NULL）且indicator='90Kg出栏占比'
-- ============================================================================
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) as metric_key,
    JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND fo.geo_id IS NULL  -- 全国数据
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '90Kg出栏占比'
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- ============================================================================
-- 查询6: 150Kg出栏占重 (YY_W_OUT_WEIGHT, indicator='150Kg出栏占重')
-- 说明: 查询全国数据（geo_id为NULL）且indicator='150Kg出栏占重'
-- ============================================================================
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) as metric_key,
    JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND fo.geo_id IS NULL  -- 全国数据
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '150Kg出栏占重'
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- ============================================================================
-- 诊断查询：检查所有indicator值
-- ============================================================================
SELECT DISTINCT
    JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
GROUP BY indicator
ORDER BY count DESC;

-- ============================================================================
-- 诊断查询：检查所有tag值（用于规模场/散户查询）
-- ============================================================================
SELECT DISTINCT
    fot.tag_key,
    fot.tag_value,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
JOIN fact_observation_tag fot ON fo.id = fot.observation_id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) IN ('YY_W_WEIGHT_GROUP', 'YY_W_WEIGHT_SCATTER')
  AND fo.period_type = 'week'
GROUP BY fot.tag_key, fot.tag_value
ORDER BY count DESC;
