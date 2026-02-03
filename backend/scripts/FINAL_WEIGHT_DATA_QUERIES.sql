-- ============================================================================
-- 均重数据查询SQL - 最终版本（所有查询已验证可用）
-- ============================================================================
-- 生成时间: 2026-02-03
-- 说明: 这些SQL查询对应前端/national-data/weight页面的6个图表
-- ============================================================================

-- ============================================================================
-- 查询1: 宰前均重
-- 前端需求: YY_W_SLAUGHTER_PRELIVE_WEIGHT, geo_code='NATION', period_type='week'
-- 数据来源: 周度-屠宰厂宰前活猪重 sheet，全国平均值列
-- ============================================================================
SELECT 
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) as metric_key,
    dg.province as geo_code,
    JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
LEFT JOIN dim_geo dg ON fo.geo_id = dg.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_SLAUGHTER_PRELIVE_WEIGHT'
  AND fo.period_type = 'week'
  AND fo.geo_id IS NULL  -- NATION数据geo_id为NULL
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- 验证: SELECT COUNT(*) FROM fact_observation fo JOIN dim_metric dm ON fo.metric_id = dm.id WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_SLAUGHTER_PRELIVE_WEIGHT' AND fo.period_type = 'week' AND fo.geo_id IS NULL;
-- 结果: 146条记录


-- ============================================================================
-- 查询2: 出栏均重
-- 前端需求: YY_W_OUT_WEIGHT, indicator='全国2', period_type='week'
-- 数据来源: 周度-体重 sheet，"全国2"列，"均重"行
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
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '全国2'
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- 验证: SELECT COUNT(*) FROM fact_observation fo JOIN dim_metric dm ON fo.metric_id = dm.id WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT' AND fo.period_type = 'week' AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '全国2';
-- 结果: 382条记录


-- ============================================================================
-- 查询3: 规模场出栏均重
-- 前端需求: YY_W_WEIGHT_GROUP, tag_key='crowd', tag_value='集团', period_type='week'
-- 数据来源: 周度-体重拆分 sheet，"集团"列
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

-- 验证: SELECT COUNT(*) FROM fact_observation fo JOIN dim_metric dm ON fo.metric_id = dm.id JOIN fact_observation_tag fot ON fo.id = fot.observation_id WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_WEIGHT_GROUP' AND fo.period_type = 'week' AND fot.tag_key = 'crowd' AND fot.tag_value = '集团';
-- 结果: 69条记录


-- ============================================================================
-- 查询4: 散户出栏均重
-- 前端需求: YY_W_WEIGHT_SCATTER, tag_key='crowd', tag_value='散户', period_type='week'
-- 数据来源: 周度-体重拆分 sheet，"散户"列
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

-- 验证: SELECT COUNT(*) FROM fact_observation fo JOIN dim_metric dm ON fo.metric_id = dm.id JOIN fact_observation_tag fot ON fo.id = fot.observation_id WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_WEIGHT_SCATTER' AND fo.period_type = 'week' AND fot.tag_key = 'crowd' AND fot.tag_value = '散户';
-- 结果: 69条记录


-- ============================================================================
-- 查询5: 90Kg出栏占比
-- 前端需求: YY_W_OUT_WEIGHT, indicator='90Kg出栏占比', period_type='week'
-- 数据来源: 周度-体重 sheet，"全国2"列，"90kg以下"行
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

-- 验证: SELECT COUNT(*) FROM fact_observation fo JOIN dim_metric dm ON fo.metric_id = dm.id WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT' AND fo.period_type = 'week' AND fo.geo_id IS NULL AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '90Kg出栏占比';
-- 结果: 939条记录


-- ============================================================================
-- 查询6: 150Kg出栏占重
-- 前端需求: YY_W_OUT_WEIGHT, indicator='150Kg出栏占重', period_type='week'
-- 数据来源: 周度-体重 sheet，"全国2"列，"150kg以上"行
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

-- 验证: SELECT COUNT(*) FROM fact_observation fo JOIN dim_metric dm ON fo.metric_id = dm.id WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT' AND fo.period_type = 'week' AND fo.geo_id IS NULL AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '150Kg出栏占重';
-- 结果: 939条记录


-- ============================================================================
-- 综合验证：检查所有6个查询的数据量
-- ============================================================================
SELECT 
    '查询1: 宰前均重' as query_name,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_SLAUGHTER_PRELIVE_WEIGHT'
  AND fo.period_type = 'week'
  AND fo.geo_id IS NULL

UNION ALL

SELECT 
    '查询2: 出栏均重(全国2)' as query_name,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '全国2'

UNION ALL

SELECT 
    '查询3: 规模场出栏均重' as query_name,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
JOIN fact_observation_tag fot ON fo.id = fot.observation_id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_WEIGHT_GROUP'
  AND fo.period_type = 'week'
  AND fot.tag_key = 'crowd'
  AND fot.tag_value = '集团'

UNION ALL

SELECT 
    '查询4: 散户出栏均重' as query_name,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
JOIN fact_observation_tag fot ON fo.id = fot.observation_id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_WEIGHT_SCATTER'
  AND fo.period_type = 'week'
  AND fot.tag_key = 'crowd'
  AND fot.tag_value = '散户'

UNION ALL

SELECT 
    '查询5: 90Kg出栏占比' as query_name,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND fo.geo_id IS NULL
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '90Kg出栏占比'

UNION ALL

SELECT 
    '查询6: 150Kg出栏占重' as query_name,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND fo.geo_id IS NULL
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '150Kg出栏占重';

-- 预期结果:
-- 查询1: 宰前均重 - 146条
-- 查询2: 出栏均重(全国2) - 382条
-- 查询3: 规模场出栏均重 - 69条
-- 查询4: 散户出栏均重 - 69条
-- 查询5: 90Kg出栏占比 - 939条
-- 查询6: 150Kg出栏占重 - 939条
