-- 检查分省区猪价相关指标及观测数据
-- 用于排查：省份升贴水有数据、升贴水比率无数据的问题

-- 1. 分省区猪价 sheet 下所有指标（含全国、各省）
SELECT id, metric_name, raw_header, sheet_name, freq,
       (SELECT COUNT(*) FROM fact_observation fo WHERE fo.metric_id = dm.id AND fo.period_type = 'day') AS obs_count,
       (SELECT MIN(obs_date) FROM fact_observation fo WHERE fo.metric_id = dm.id AND fo.period_type = 'day') AS min_date,
       (SELECT MAX(obs_date) FROM fact_observation fo WHERE fo.metric_id = dm.id AND fo.period_type = 'day') AS max_date
FROM dim_metric dm
WHERE sheet_name = '分省区猪价'
ORDER BY raw_header;

-- 2. 重点区域：贵州、四川、云南、广东、广西、江苏、内蒙古 的指标及观测数
SELECT 
  dm.id,
  dm.raw_header,
  dm.freq,
  COUNT(fo.id) AS obs_count,
  MIN(fo.obs_date) AS min_date,
  MAX(fo.obs_date) AS max_date
FROM dim_metric dm
LEFT JOIN fact_observation fo ON fo.metric_id = dm.id AND fo.period_type = 'day' AND fo.value IS NOT NULL
WHERE dm.sheet_name = '分省区猪价'
  AND (dm.raw_header LIKE '%贵州%' OR dm.raw_header LIKE '%四川%' OR dm.raw_header LIKE '%云南%'
       OR dm.raw_header LIKE '%广东%' OR dm.raw_header LIKE '%广西%' OR dm.raw_header LIKE '%江苏%'
       OR dm.raw_header LIKE '%内蒙古%' OR dm.raw_header LIKE '%内蒙%' OR dm.raw_header LIKE '%中国%' OR dm.raw_header LIKE '%全国%')
GROUP BY dm.id, dm.raw_header, dm.freq;
