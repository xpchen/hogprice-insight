# 均重数据查询诊断和SQL

## 问题总结

1. **geo_code='NATION'查询问题**：已修复后端API，现在使用LEFT JOIN或单独处理geo_id为NULL的情况
2. **indicator='全国2'不存在**：数据中没有indicator='全国2'的记录，只有indicator='均重'等
3. **"全国2"列数据问题**：数据中geo_code='全国2'的记录不存在，只有geo_id为NULL且province='None'的记录

## 诊断SQL

### 1. 检查metric_key设置

```sql
-- 检查所有相关metric的metric_key设置
SELECT 
    id,
    metric_name,
    sheet_name,
    JSON_UNQUOTE(JSON_EXTRACT(parse_json, '$.metric_key')) as metric_key,
    parse_json
FROM dim_metric
WHERE sheet_name IN ('周度-体重', '周度-屠宰厂宰前活猪重', '周度-体重拆分')
ORDER BY sheet_name, metric_name;
```

### 2. 检查fact_observation中的数据量

```sql
-- 统计各metric_key的数据量
SELECT 
    JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) as metric_key,
    dm.metric_name,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) IN (
    'YY_W_SLAUGHTER_PRELIVE_WEIGHT',
    'YY_W_OUT_WEIGHT',
    'YY_W_WEIGHT_GROUP',
    'YY_W_WEIGHT_SCATTER'
)
AND fo.period_type = 'week'
GROUP BY metric_key, dm.metric_name
ORDER BY count DESC;
```

### 3. 检查geo_code值分布

```sql
-- 检查YY_W_OUT_WEIGHT的所有geo_code值
SELECT 
    dg.province as geo_code,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
LEFT JOIN dim_geo dg ON fo.geo_id = dg.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
GROUP BY dg.province
ORDER BY count DESC
LIMIT 50;
```

### 4. 检查indicator值分布

```sql
-- 检查YY_W_OUT_WEIGHT的所有indicator值
SELECT 
    JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) as indicator,
    COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
GROUP BY indicator
ORDER BY count DESC;
```

## 前端查询对应的SQL（修复后）

### 查询1: 宰前均重 (YY_W_SLAUGHTER_PRELIVE_WEIGHT, geo_code='NATION')

**前端需求**：查询全国平均值，geo_code='NATION'

**修复后的SQL**：
```sql
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
```

**说明**：后端API已修复，现在会正确处理geo_code='NATION'的情况（查询geo_id为NULL的记录）

### 查询2: 出栏均重 (YY_W_OUT_WEIGHT, indicator='全国2')

**前端需求**：查询indicator='全国2'的记录

**问题**：数据中没有indicator='全国2'的记录，只有indicator='均重'等

**临时解决方案SQL**（使用indicator='均重'且geo_id为NULL）：
```sql
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
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '均重'
  AND fo.geo_id IS NULL  -- 全国数据
ORDER BY fo.obs_date DESC
LIMIT 1000;
```

**建议修复**：
1. 检查Excel文件中"全国2"列的实际位置和含义
2. 修复parser，确保"全国2"列被正确解析为indicator='全国2'或geo_code='全国2'
3. 或者调整前端查询逻辑，使用indicator='均重'且geo_id为NULL

### 查询3: 规模场出栏均重 (YY_W_WEIGHT_GROUP, tag_key='crowd', tag_value='集团')

**SQL**：
```sql
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
```

**状态**：✅ 正常，有69条数据

### 查询4: 散户出栏均重 (YY_W_WEIGHT_SCATTER, tag_key='crowd', tag_value='散户')

**SQL**：
```sql
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
```

**状态**：✅ 正常，有69条数据

### 查询5: 90Kg出栏占比 (YY_W_OUT_WEIGHT, indicator='90Kg出栏占比')

**SQL**：
```sql
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
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '90Kg出栏占比'
ORDER BY fo.obs_date DESC
LIMIT 1000;
```

**问题**：数据中indicator='90kg以下'，不是'90Kg出栏占比'

**临时解决方案SQL**：
```sql
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
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '90kg以下'
  AND fo.geo_id IS NULL  -- 全国数据
ORDER BY fo.obs_date DESC
LIMIT 1000;
```

### 查询6: 150Kg出栏占重 (YY_W_OUT_WEIGHT, indicator='150Kg出栏占重')

**SQL**：
```sql
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
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '150Kg出栏占重'
ORDER BY fo.obs_date DESC
LIMIT 1000;
```

**问题**：数据中indicator='150kg以上'，不是'150Kg出栏占重'

**临时解决方案SQL**：
```sql
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
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '150kg以上'
  AND fo.geo_id IS NULL  -- 全国数据
ORDER BY fo.obs_date DESC
LIMIT 1000;
```

## 修复建议

### 1. 修复后端API（已完成）

已修复`backend/app/api/observation.py`中的geo_code='NATION'查询逻辑。

### 2. 修复数据解析问题

需要检查parser是否正确处理了"全国2"列。可能的问题：
- "全国2"列没有被识别为省份列
- "全国2"被错误地解析为province='None'而不是geo_code='全国2'

### 3. 调整前端查询逻辑（临时方案）

如果数据已经导入但indicator值不匹配，可以：
1. 修改前端查询，使用实际的indicator值（如'均重'、'90kg以下'、'150kg以上'）
2. 或者修复数据，重新导入并确保indicator值正确

## 完整的查询SQL文件

所有SQL查询已保存在 `backend/scripts/weight_data_queries.sql`
