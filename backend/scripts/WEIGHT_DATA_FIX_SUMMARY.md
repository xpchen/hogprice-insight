# 均重数据查询问题修复总结

## 问题诊断

1. **geo_code='NATION'查询失败**：后端API使用inner join，geo_id为NULL时查询失败
2. **indicator='全国2'不存在**：数据中没有indicator='全国2'的记录
3. **indicator值不匹配**：前端查询'indicator='90Kg出栏占比''，但数据中是'90kg以下'

## 修复内容

### 1. 修复后端API（已完成）

**文件**: `backend/app/api/observation.py`

**修复内容**：
- 当`geo_code='NATION'`时，查询`geo_id IS NULL`的记录（不使用join）
- 其他省份使用LEFT JOIN查询

**代码**：
```python
if geo_code == "NATION":
    query = query.filter(FactObservation.geo_id.is_(None))
else:
    from app.models.dim_geo import DimGeo
    query = query.join(DimGeo, FactObservation.geo_id == DimGeo.id).filter(
        DimGeo.province == geo_code
    )
```

### 2. 修复Parser（已完成）

**文件**: `backend/app/services/ingestors/parsers/p4_period_start_end_wide_province.py`

**修复内容**：
- 识别"全国1"、"全国2"等列名为全国数据列
- 将这些列的数据设置为`geo_code='NATION'`
- 对于"全国2"列，如果没有row_dim_value，设置`indicator='全国2'`

**代码**：
```python
# 全国数据列名
nation_cols = {"全国", "全国1", "全国2", "中国", "NATION"}

# 识别全国数据列
for idx in range(end_col_idx + 1, len(df.columns)):
    col_name = str(df.columns[idx]).strip()
    if col_name in nation_cols or (col_name.startswith("全国") and len(col_name) <= 10):
        nation_col_indices.append((idx, col_name))
        # 处理为geo_code='NATION'
```

### 3. 修复现有数据（已完成）

**修复脚本**: `backend/scripts/fix_nation2_indicator_sql.py` 和 `backend/scripts/fix_90kg_150kg_indicators.py`

**修复内容**：
1. 将`geo_id为NULL`且`indicator='均重'`的记录，更新为`indicator='全国2'`
2. 将`geo_id为NULL`且`indicator='90kg以下'`的记录，更新为`indicator='90Kg出栏占比'`
3. 将`geo_id为NULL`且`indicator='150kg以上'`的记录，更新为`indicator='150Kg出栏占重'`

**修复结果**：
- indicator='全国2': 382条记录
- indicator='90Kg出栏占比': 939条记录
- indicator='150Kg出栏占重': 939条记录

## 前端查询对应的SQL

### 查询1: 宰前均重 (YY_W_SLAUGHTER_PRELIVE_WEIGHT, geo_code='NATION')

```sql
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
```

### 查询2: 出栏均重 (YY_W_OUT_WEIGHT, indicator='全国2')

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
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '全国2'
ORDER BY fo.obs_date DESC
LIMIT 1000;
```

### 查询3: 规模场出栏均重 (YY_W_WEIGHT_GROUP, tag_key='crowd', tag_value='集团')

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

### 查询4: 散户出栏均重 (YY_W_WEIGHT_SCATTER, tag_key='crowd', tag_value='散户')

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

### 查询5: 90Kg出栏占比 (YY_W_OUT_WEIGHT, indicator='90Kg出栏占比')

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
  AND fo.geo_id IS NULL  -- 全国数据
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '90Kg出栏占比'
ORDER BY fo.obs_date DESC
LIMIT 1000;
```

### 查询6: 150Kg出栏占重 (YY_W_OUT_WEIGHT, indicator='150Kg出栏占重')

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
  AND fo.geo_id IS NULL  -- 全国数据
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '150Kg出栏占重'
ORDER BY fo.obs_date DESC
LIMIT 1000;
```

## 验证查询

### 验证所有修复是否生效

```sql
-- 1. 验证indicator='全国2'的记录
SELECT COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '全国2';

-- 2. 验证indicator='90Kg出栏占比'的记录
SELECT COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '90Kg出栏占比';

-- 3. 验证indicator='150Kg出栏占重'的记录
SELECT COUNT(*) as count
FROM fact_observation fo
JOIN dim_metric dm ON fo.metric_id = dm.id
WHERE JSON_UNQUOTE(JSON_EXTRACT(dm.parse_json, '$.metric_key')) = 'YY_W_OUT_WEIGHT'
  AND fo.period_type = 'week'
  AND JSON_UNQUOTE(JSON_EXTRACT(fo.tags_json, '$.indicator')) = '150Kg出栏占重';
```

## 下一步

1. **重新导入数据**：使用修复后的parser重新导入"周度-体重"sheet，确保新数据正确解析"全国2"列
2. **测试前端查询**：访问前端页面，验证数据是否能正常显示
3. **如果还有问题**：运行诊断脚本 `backend/scripts/diagnose_weight_data.py` 查看详细错误信息

## 相关文件

- `backend/app/api/observation.py` - 后端API（已修复geo_code='NATION'查询）
- `backend/app/services/ingestors/parsers/p4_period_start_end_wide_province.py` - Parser（已修复"全国2"列识别）
- `backend/scripts/weight_data_queries.sql` - 完整的SQL查询文件
- `backend/scripts/diagnose_weight_data.py` - 诊断脚本
- `backend/scripts/fix_nation2_indicator_sql.py` - 修复indicator='全国2'的脚本
- `backend/scripts/fix_90kg_150kg_indicators.py` - 修复90kg和150kg的indicator值
