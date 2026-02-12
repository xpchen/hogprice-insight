-- ============================================================================
-- A3. 日度屠宰量（全国，涌益）— 屠宰量&价格 数据查询
-- 对应前端：national-data/Slaughter.vue「屠宰量&价格」图表
-- 数据来源：涌益日度「价格+宰量」sheet
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. 日度屠宰量（日屠宰量合计1）
-- metric_key: YY_D_SLAUGHTER_TOTAL_1, period_type='day', 全国无 geo_id
-- ----------------------------------------------------------------------------
SELECT
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) AS metric_key
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_D_SLAUGHTER_TOTAL_1'
  AND fo.period_type = 'day'
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- 统计：条数、日期范围
-- SELECT COUNT(*) AS cnt, MIN(fo.obs_date) AS min_date, MAX(fo.obs_date) AS max_date
-- FROM fact_observation fo
-- JOIN dim_metric dm ON fo.metric_id = dm.id
-- WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_D_SLAUGHTER_TOTAL_1'
--   AND fo.period_type = 'day';


-- ----------------------------------------------------------------------------
-- 2. 全国均价（价格）
-- metric_key: YY_D_PRICE_NATION_AVG, period_type='day', 全国无 geo_id
-- ----------------------------------------------------------------------------
SELECT
    fo.id,
    fo.obs_date,
    fo.period_end,
    fo.value,
    dm.metric_name,
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) AS metric_key
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_D_PRICE_NATION_AVG'
  AND fo.period_type = 'day'
ORDER BY fo.obs_date DESC
LIMIT 1000;

-- 统计：条数、日期范围
-- SELECT COUNT(*) AS cnt, MIN(fo.obs_date) AS min_date, MAX(fo.obs_date) AS max_date
-- FROM fact_observation fo
-- JOIN dim_metric dm ON fo.metric_id = dm.id
-- WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_D_PRICE_NATION_AVG'
--   AND fo.period_type = 'day';


-- ----------------------------------------------------------------------------
-- 3. 指标是否存在（dim_metric）
-- ----------------------------------------------------------------------------
SELECT
    id,
    metric_name,
    raw_header,
    sheet_name,
    unit,
    JSON_UNQUOTE(JSON_EXTRACT(parse_json, '$.metric_key')) AS metric_key
FROM dim_metric
WHERE JSON_UNQUOTE(JSON_EXTRACT(parse_json, '$.metric_key')) IN ('YY_D_SLAUGHTER_TOTAL_1', 'YY_D_PRICE_NATION_AVG')
   OR (sheet_name = '价格+宰量' AND (metric_name LIKE '%屠宰量%' OR metric_name LIKE '%全国均价%'));
