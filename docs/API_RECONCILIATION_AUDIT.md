# 新旧后端 API 全量对账与溯源审计报告

> 审计日期：2026-03-02  
> 目标：找出迁移后（hogprice_v3）与迁移前（hogprice_old）数据不一致的根本原因

---

## 修复记录（2026-03-02）

已完成以下修复（**不涉及表结构变更**）：

1. **price_display**  
   - 屠宰量：所有 `fact_slaughter_daily` 全国查询增加 `source='YONGYI'`，与旧版「价格+宰量」口径一致  
   - 全国猪价：增加 `全国均价` 作为备选，优先级为 标猪均价 → 全国均价 → hog_avg_price(GANGLIAN)  
   - 标肥价差：全国增加 `source='GANGLIAN'`（仅钢联有 fat_std_spread 全国数据）  
   - `std_fat_spread` 统一改为 `fat_std_spread`（与实际表字段一致）

2. **dashboard**  
   - 卡片 1 标肥价差：`std_fat_spread` → `fat_std_spread`，`source='YONGYI'` → `source='GANGLIAN'`

3. **observation**  
   - `YY_D_STD_FAT_SPREAD` 映射：`std_fat_spread` → `fat_std_spread`  
   - 屠宰量全国：默认 `source='YONGYI'`  
   - 标肥价差全国：默认 `source='GANGLIAN'`  
   - **出栏均重（YY_W_OUT_WEIGHT, indicator=均重, geo_code=NATION）**：NATION 行仅 2024–2026（来自周度-体重拆分），缺少年份用各省 weight_avg 的 AVG 补充（省均有 2018–2026），使 `/national-data/weight` 页可展示 2020–2026

4. **ts**  
   - `spread_std_fat`：`std_fat_spread` → `fat_std_spread`，默认来源改为 `GANGLIAN`

5. **supply_demand**  
   - `_get_national_monthly_price`：增加第三备选「全国均价」

---

## 第一部分：缓存禁用说明

### 1.1 已识别的缓存点

| 缓存类型 | 位置 | 说明 |
|---------|------|------|
| **图表数据库缓存** | `ChartTimingAndCacheMiddleware` | 对 `CHART_API_PATH_PREFIXES` 下的 GET 请求进行读写缓存，存于 `quick_chart_cache` 表 |
| **merged_cell 内存缓存** | `merged_cell_handler.py` | Excel 解析时的合并单元格缓存，**不影响 API 返回** |
| **observation_upserter 内存缓存** | `observation_upserter.py` | 导入时的 metric/geo 查询缓存，**不影响 API 返回** |

### 1.2 已执行的禁用操作

**修改文件：**

1. **`backend/app/core/config.py`**
   - 新增配置项：`DISABLE_CHART_CACHE: bool = False`
   - 在 `.env` 中设置 `DISABLE_CHART_CACHE=true` 可禁用图表缓存

2. **`backend/app/middleware/chart_timing_and_cache.py`**
   - 在 `dispatch` 开头：若 `DISABLE_CHART_CACHE=True`，**直接透传请求**，不读缓存
   - 在写入逻辑：若 `DISABLE_CHART_CACHE=True`，**不写入** `quick_chart_cache`

3. **`backend/.env.example`**
   - 添加了 `DISABLE_CHART_CACHE` 的说明注释

### 1.3 审计时操作步骤

在 `.env` 中增加或修改：

```
DISABLE_CHART_CACHE=true
```

然后重启后端。**对账期间务必保持该配置**，否则可能拿到的是历史缓存结果。

### 1.4 风险点

- **其他缓存**：未发现 Redis、HTTP 缓存等；若有反向代理或 CDN 缓存，需在部署侧单独关闭
- **quick_chart_cache 表**：禁用后仍存在，历史数据不影响；如需清空可执行：`DELETE FROM quick_chart_cache;`

---

## 第二部分：API 总览表

| 序号 | 模块 | API | 方法 | 新版处理函数 | 旧版处理函数 | 新版数据源(hogprice_v3) | 旧版数据源(hogprice_old) | 数据源一致性 | 逻辑一致性 | 问题归类 | 优先级 | 备注 |
|-----|------|-----|------|-------------|-------------|------------------------|-------------------------|-------------|-----------|---------|-------|------|
| 1 | auth | /api/auth/login | POST | login | login | - | - | - | - | 非数据API | 低 | |
| 2 | auth | /api/auth/me | GET | get_me | get_me | - | - | - | - | 非数据API | 低 | |
| 3 | metadata | /api/dim/metrics | GET | get_metrics | get_metrics | dim_metric | dim_metric | 一致 | 存疑 | 建议复核 | 中 | 新版查 dim_metric，schema 可能不同 |
| 4 | metadata | /api/dim/geo | GET | get_geo | get_geo | dim_region | dim_geo | **不一致** | 存疑 | 数据来源问题 | 高 | 表名 dim_geo→dim_region |
| 5 | metadata | /api/dim/company | GET | get_company | get_company | dim_company | dim_company | 一致 | 存疑 | 建议复核 | 中 | |
| 6 | metadata | /api/dim/warehouse | GET | get_warehouse | get_warehouse | fact_futures_basis | fact_futures_basis | 一致 | 存疑 | 建议复核 | 中 | |
| 7 | metadata | /api/dim/metrics/completeness | GET | get_metrics_completeness_api | - | fact_* 多表 | - | - | - | 新版新增 | 低 | |
| 8 | ts | /api/ts | GET | get_timeseries | get_timeseries | fact_* 多表 | fact_observation | **不一致** | **不一致** | 两者都有 | 高 | 旧版 fact_observation，新版 fact_* |
| 9 | futures | /api/futures/daily | GET | get_futures_daily | get_futures_daily | fact_futures_daily | fact_futures_daily | 部分一致 | 存疑 | 建议复核 | 中 | 列名 open_price→open 等 |
| 10 | futures | /api/futures/premium/v2 | GET | get_premium_v2 | get_premium_v2 | fact_futures_basis | fact_futures_basis | 部分一致 | 存疑 | 建议复核 | 中 | 仓单企业 LIKE 匹配 |
| 11 | price-display | /api/v1/price-display/national-price/seasonality | GET | get_national_price_seasonality | - | fact_price_daily | fact_observation+DimMetric | **不一致** | **不一致** | 两者都有 | 高 | 核心价差接口 |
| 12 | price-display | /api/v1/price-display/fat-std-spread/seasonality | GET | get_fat_std_spread_seasonality | - | fact_spread_daily | fact_observation+DimMetric | **不一致** | **不一致** | 两者都有 | 高 | 标肥价差 |
| 13 | price-display | /api/v1/price-display/price-and-spread | GET | get_price_and_spread | - | fact_price_daily, fact_spread_daily | fact_observation | **不一致** | **不一致** | 两者都有 | 高 | |
| 14 | price-display | /api/v1/price-display/slaughter/lunar | GET | get_slaughter_lunar | - | fact_slaughter_daily | fact_observation | **不一致** | **不一致** | 两者都有 | 高 | 屠宰量 |
| 15 | price-display | /api/v1/price-display/slaughter-price-trend/solar | GET | get_slaughter_price_trend_solar | - | fact_slaughter_daily, fact_price_daily | fact_observation | **不一致** | **不一致** | 两者都有 | 高 | |
| 16 | price-display | /api/v1/price-display/price-changes | GET | get_price_changes | - | fact_price_daily, fact_spread_daily | fact_observation | **不一致** | **不一致** | 两者都有 | 高 | |
| 17 | price-display | /api/v1/price-display/region-spread/* | GET | get_region_spread_* | - | fact_spread_daily | fact_observation(raw_header 区域价差) | **不一致** | **不一致** | 两者都有 | 高 | |
| 18 | price-display | /api/v1/price-display/frozen-inventory/* | GET | get_frozen_* | - | fact_weekly_indicator | fact_observation(库容率) | **不一致** | **不一致** | 两者都有 | 高 | |
| 19 | price-display | /api/v1/price-display/industry-chain/* | GET | get_industry_chain_* | - | fact_weekly_indicator | fact_observation | **不一致** | **不一致** | 两者都有 | 高 | |
| 20 | price-display | /api/v1/price-display/province-indicators/* | GET | get_province_indicators_seasonality | - | fact_price_daily, fact_spread_daily, fact_weekly_indicator | fact_observation | **不一致** | **不一致** | 两者都有 | 高 | |
| 21 | statistics-bureau | /api/v1/statistics-bureau/quarterly-data | GET | get_quarterly_data | - | fact_quarterly_stats | raw_table(Excel JSON) | **不一致** | **不一致** | 两者都有 | 高 | 旧版读 Excel 原始表 |
| 22 | statistics-bureau | /api/v1/statistics-bureau/output-slaughter | GET | get_output_slaughter | - | fact_quarterly_stats | raw_table | **不一致** | **不一致** | 两者都有 | 高 | |
| 23 | statistics-bureau | /api/v1/statistics-bureau/import-meat | GET | get_import_meat | - | fact_monthly_indicator, fact_quarterly_stats | raw_table | **不一致** | **不一致** | 两者都有 | 高 | 猪肉进口 |
| 24 | supply-demand | /api/v1/supply-demand/curve | GET | get_supply_demand_curve | - | fact_price_daily, fact_monthly_indicator | raw_table | **不一致** | **不一致** | 两者都有 | 高 | 旧版解析 Excel |
| 25 | supply-demand | /api/v1/supply-demand/breeding-inventory-price | GET | get_breeding_inventory_price | - | fact_monthly_indicator, fact_price_daily | raw_table | **不一致** | **不一致** | 两者都有 | 高 | |
| 26 | supply-demand | /api/v1/supply-demand/piglet-price | GET | get_piglet_price | - | fact_monthly_indicator, fact_price_daily | raw_table | **不一致** | **不一致** | 两者都有 | 高 | |
| 27 | multi-source | /api/v1/multi-source/data | GET | get_multi_source_data | - | fact_monthly_indicator | raw_table | **不一致** | **不一致** | 两者都有 | 高 | E2 多渠道汇总 |
| 28 | enterprise-statistics | /api/v1/enterprise-statistics/* | GET | get_*_daily, get_province_summary_table | - | fact_enterprise_daily | fact_observation+DimMetric | **不一致** | **不一致** | 两者都有 | 高 | CR5/四川/广西/西南 |
| 29 | structure-analysis | /api/v1/structure-analysis/data | GET | get_structure_analysis_data | - | fact_enterprise_monthly, fact_monthly_indicator | raw_table/fact_observation | **不一致** | **不一致** | 两者都有 | 高 | |
| 30 | structure-analysis | /api/v1/structure-analysis/table | GET | get_structure_analysis_table | - | fact_enterprise_monthly, fact_monthly_indicator | raw_table | **不一致** | **不一致** | 两者都有 | 高 | |
| 31 | group-price | /api/v1/group-price/group-enterprise-price | GET | get_group_enterprise_price | - | fact_enterprise_daily | fact_observation | **不一致** | **不一致** | 两者都有 | 高 | |
| 32 | group-price | /api/v1/group-price/white-strip-market | GET | get_white_strip_market | - | fact_carcass_market | fact_observation/raw_table | **不一致** | **不一致** | 两者都有 | 高 | 白条市场 |
| 33 | sales-plan | /api/v1/sales-plan/data | GET | get_sales_plan_data | - | fact_enterprise_monthly | raw_table/fact_observation | **不一致** | **不一致** | 两者都有 | 高 | |
| 34 | production-indicators | /api/v1/production-indicators/* | GET | get_* | - | fact_monthly_indicator, fact_weekly_indicator | raw_table/fact_observation | **不一致** | **不一致** | 两者都有 | 高 | |
| 35 | observation | /api/v1/observation/query | GET | query_observations | - | fact_* (兼容层映射) | fact_observation | **不一致** | 部分一致 | 两者都有 | 高 | 兼容层，映射可能不全 |
| 36 | dashboard | /api/dashboard/default | GET | get_default_dashboard | - | fact_price_daily, fact_weekly_indicator | fact_observation | **不一致** | **不一致** | 两者都有 | 高 | |
| 37 | reconciliation | /api/reconciliation/* | GET | get_* | - | fact_* | fact_* | 一致 | 存疑 | 建议复核 | 中 | 对账API |
| 38 | data-freshness | /api/data-freshness | GET | get_data_freshness | 旧版无 | fact_* 多表 | - | - | - | 新版新增 | 低 | |
| 39 | ingest/query/export | 多种 | - | - | - | - | - | - | - | 非对账重点 | 低 | 导入/查询/导出 |

---

## 第三部分：逐接口详细分析（高优先级样本）

### [price-display] /api/v1/price-display/national-price/seasonality

#### 1. 基础信息
- 请求方式：GET
- 新版入口：`get_national_price_seasonality` (price_display.py)
- 旧版入口：原 price_display 或 price_national，基于 fact_observation
- 新版文件：`backend/app/api/price_display.py`
- 旧版文件：同一文件，迁移前版本（commit 9352d3e 之前）

#### 2. 新版数据来源
- 数据库：hogprice_v3
- 表/视图：`fact_price_daily`
- 查询链路：Controller → `db.execute(text(...))` 直接 SQL
- SQL/ORM 摘要：
  ```sql
  SELECT trade_date, value FROM fact_price_daily
  WHERE price_type = '标猪均价' AND region_code = 'NATION'  -- 或类似
  ```
- 缓存：经 ChartTimingAndCacheMiddleware（可禁用）
- 业务加工：按农历/年度分组、 seasonal 序列组装

#### 3. 旧版数据来源
- 数据库：hogprice_old
- 表/视图：`fact_observation` + `dim_metric` + `dim_geo`
- 查询链路：FactObservation.query().join(DimMetric).filter(DimMetric.raw_header.like("%出栏均价%"), ...)
- 缓存：同 ChartTimingAndCacheMiddleware
- 业务加工：通过 raw_header 模糊匹配（如 "商品猪：出栏均价：中国（日）"）

#### 4. 对比结论
- 数据源是否一致：**不一致** — 旧版 fact_observation，新版 fact_price_daily
- 业务逻辑是否一致：**不一致** — 旧版 raw_header LIKE，新版 price_type/region_code 精确匹配
- 主要差异点：
  1. 指标名：旧版 "标猪均价"/"出栏均价" 通过 raw_header 匹配；新版需确保 price_type 与 v3 配置一致
  2. 区域：旧版 geo/region；新版 region_code='NATION'
  3. 来源：旧版无 source 筛选；新版可能需 source 优先级（如 YONGYI/GANGLIAN）

#### 5. 问题归类
- 结论：**两者都有** — 数据源与匹配逻辑均变化

#### 6. 修复建议
- 建议修改位置：`price_display.py` 中 `get_national_price_seasonality` 的 SQL
- 建议修改内容：
  1. 确认 hogprice_v3 中全国猪价对应的 `price_type` 实际值（标猪均价、hog_avg_price 等）
  2. 如有多个 source，明确优先级（如 GANGLIAN > YONGYI）并加 WHERE source = ...
  3. 与业务确认口径：是否需与旧版 raw_header 语义完全一致
- 风险点：v3 的 price_type 枚举可能与旧 metric 命名不完全对应

---

### [statistics-bureau] /api/v1/statistics-bureau/quarterly-data

#### 1. 基础信息
- 请求方式：GET
- 新版入口：`get_quarterly_data` (statistics_bureau.py)
- 旧版入口：同模块，原从 raw_table 读取
- 新版文件：`backend/app/api/statistics_bureau.py`
- 旧版文件：同一文件

#### 2. 新版数据来源
- 数据库：hogprice_v3
- 表/视图：`fact_quarterly_stats` (region_code='NATION')
- 查询链路：直接 `text(""" SELECT ... FROM fact_quarterly_stats ... """)`
- 缓存：经 ChartTimingAndCacheMiddleware
- 业务加工：按 indicator_code 映射到 Excel 列序（B-Y）

#### 3. 旧版数据来源
- 数据库：hogprice_old
- 表/视图：`raw_table`（Excel 的 table_json）
- 查询链路：RawSheet → RawTable → table_json，sheet 名 "03.统计局季度数据"
- 缓存：同
- 业务加工：解析二维数组，按行列索引取数

#### 4. 对比结论
- 数据源是否一致：**不一致** — 旧版 Excel 原始 JSON，新版结构化 fact_quarterly_stats
- 业务逻辑是否一致：**不一致** — 列序、指标含义需与导入逻辑严格对齐
- 主要差异点：
  1. 旧版：Excel 列顺序即数据顺序；新版：indicator_code 映射到固定列
  2. 需核对 fact_quarterly_stats 的 indicator_code 与 Excel 表头/列序一一对应
  3. 缺失值、空行处理可能不同

#### 5. 问题归类
- 结论：**两者都有**

#### 6. 修复建议
- 建议修改位置：`statistics_bureau.py` + 导入 pipeline 的 indicator 配置
- 建议修改内容：
  1. 对照 Excel "03.统计局季度数据" 的列顺序，逐一核对 fact_quarterly_stats 的 indicator_code
  2. 确认导入脚本是否正确写入 fact_quarterly_stats
  3. 对空值、NULL 的处理与旧版保持一致
- 风险点：列序错位会导致整列数据错位

---

### [supply-demand] /api/v1/supply-demand/curve

#### 1. 基础信息
- 请求方式：GET
- 新版入口：`get_supply_demand_curve` (supply_demand.py)
- 旧版入口：同
- 新版文件：`backend/app/api/supply_demand.py`
- 旧版文件：同一文件

#### 2. 新版数据来源
- 数据库：hogprice_v3
- 表/视图：`fact_price_daily`（全国猪价）、`fact_monthly_indicator`（定点屠宰、NYB 环比）
- 查询链路：`_get_national_monthly_price()` → fact_price_daily；定点屠宰 → fact_monthly_indicator
- 缓存：经 ChartTimingAndCacheMiddleware
- 业务加工：按月聚合、计算系数、滞后对齐

#### 3. 旧版数据来源
- 数据库：hogprice_old
- 表/视图：`raw_table`（Excel JSON）
- 查询链路：`_get_raw_table_data(db, sheet_name)` → RawSheet/RawTable
- 缓存：同
- 业务加工：解析 Excel 行列，`_parse_excel_date` 解析日期

#### 4. 对比结论
- 数据源是否一致：**不一致** — 旧版 raw_table，新版 fact_*
- 业务逻辑是否一致：**不一致** — 计算逻辑（定点屠宰系数、猪价系数）需逐项核对
- 主要差异点：
  1. 猪价来源：旧版来自 Excel 某 sheet；新版来自 fact_price_daily，需确认 source/price_type
  2. 定点屠宰：旧版 Excel；新版 fact_monthly_indicator，indicator_code 需正确
  3. 日期解析：旧版 Excel 序列号；新版 SQL date 类型

#### 5. 问题归类
- 结论：**两者都有**

#### 6. 修复建议
- 建议修改位置：`supply_demand.py` 中 `_get_national_monthly_price` 及定点屠宰查询
- 建议修改内容：核对 indicator_code、source、价格类型与旧 Excel 对应关系
- 风险点：滞后月份、聚合口径可能与旧版不同

---

### [multi-source] /api/v1/multi-source/data

#### 1. 基础信息
- 请求方式：GET
- 新版入口：`get_multi_source_data` (multi_source.py)
- 旧版入口：同
- 新版文件：`backend/app/api/multi_source.py`
- 旧版文件：同一文件

#### 2. 新版数据来源
- 数据库：hogprice_v3
- 表/视图：`fact_monthly_indicator` (value_type='mom_pct' 或 'abs')
- 查询链路：INDICATOR_FIELD_MAP 映射 (indicator_code, source, sub_category, region_code) → 响应字段
- 缓存：经 ChartTimingAndCacheMiddleware
- 业务加工：ABS_COMPUTED_FIELDS 对无 mom_pct 的指标用 abs 计算环比

#### 3. 旧版数据来源
- 数据库：hogprice_old
- 表/视图：raw_table（Excel）
- 查询链路：按 sheet 名取 raw_table，解析行列
- 缓存：同
- 业务加工：行列索引映射到各渠道指标

#### 4. 对比结论
- 数据源是否一致：**不一致**
- 业务逻辑是否一致：**不一致** — 字段映射、环比计算需核对
- 主要差异点：
  1. 淘汰母猪屠宰：cull_slaughter vs cull_sow_slaughter（GANGLIAN）
  2. 钢联规模场：breeding_sow_inventory_large
  3. 生猪存栏钢联：hog_inventory_total / hog_inventory_large

#### 5. 问题归类
- 结论：**两者都有**

#### 6. 修复建议
- 建议修改位置：`multi_source.py` 中 INDICATOR_FIELD_MAP、ABS_COMPUTED_FIELDS
- 建议修改内容：逐项对照旧 Excel 列与 fact_monthly_indicator 的 indicator_code/sub_category/source
- 风险点：sub_category 取值（nation/scale/small/small_nation）易混

---

### [enterprise-statistics] /api/v1/enterprise-statistics/cr5-daily

#### 1. 基础信息
- 请求方式：GET
- 新版入口：`get_cr5_daily` (enterprise_statistics.py)
- 旧版入口：同
- 新版文件：`backend/app/api/enterprise_statistics.py`
- 旧版文件：同一文件

#### 2. 新版数据来源
- 数据库：hogprice_v3
- 表/视图：`fact_enterprise_daily` (metric_type='output_cumulative' 等)
- 查询链路：`_query_aggregate` / `_query_region_sum` 按 company_code、metric_type、region_code
- 缓存：经 ChartTimingAndCacheMiddleware
- 业务加工：按企业聚合、格式化日期

#### 3. 旧版数据来源
- 数据库：hogprice_old
- 表/视图：`fact_observation` + `dim_metric` + `dim_company`
- 查询链路：FactObservation.join(DimMetric).filter(metric.sheet_name 含 "CR5")
- 缓存：同
- 业务加工：通过 metric 的 raw_header/sheet_name 识别企业、指标

#### 4. 对比结论
- 数据源是否一致：**不一致**
- 业务逻辑是否一致：**不一致** — metric_type 枚举需与旧 metric 语义对应
- 主要差异点：commit 提及 "对齐 metric_type 为 output_cumulative"，需确认 CR5 各企业、各省是否一致

#### 5. 问题归类
- 结论：**两者都有**

#### 6. 修复建议
- 建议修改位置：`enterprise_statistics.py` 中 metric_type 及 company_code 过滤
- 建议修改内容：核对 fact_enterprise_daily 中 CR5 企业的 company_code、metric_type 与旧 observation 对应关系
- 风险点：区域汇总（region_code）与旧版省份维度可能不同

---

### [observation] /api/v1/observation/query

#### 1. 基础信息
- 请求方式：GET
- 新版入口：`query_observations` (observation.py)
- 旧版入口：同
- 新版文件：`backend/app/api/observation.py`
- 旧版文件：同一文件

#### 2. 新版数据来源
- 数据库：hogprice_v3
- 表/视图：fact_price_daily, fact_spread_daily, fact_slaughter_daily, fact_weekly_indicator（通过 OBS_TABLE_MAP 映射）
- 查询链路：根据 metric_key 查 OBS_TABLE_MAP → 对应 fact 表 + filter 列
- 缓存：部分路径经 ChartTimingAndCacheMiddleware
- 业务加工：将 fact 行转为 ObservationResponse 结构

#### 3. 旧版数据来源
- 数据库：hogprice_old
- 表/视图：fact_observation
- 查询链路：直接查 fact_observation
- 缓存：同
- 业务加工：无

#### 4. 对比结论
- 数据源是否一致：**不一致**
- 业务逻辑是否一致：**部分一致** — 兼容层若映射不全会导致部分 metric_key 无数据
- 主要差异点：OBS_TABLE_MAP 需覆盖所有前端使用的 metric_key，且 filter 列（price_type、indicator_code 等）需正确

#### 5. 问题归类
- 结论：**两者都有**

#### 6. 修复建议
- 建议修改位置：`observation.py` 中 OBS_TABLE_MAP
- 建议修改内容：对照前端调用的 metric_key 列表，补全映射；对未映射的尝试 fact_weekly_indicator 按 indicator_code 搜索
- 风险点：新增指标未加入映射会返回空

---

### [futures] /api/futures/volatility 与 /volatility-analysis（波动率）

#### 1. 基础信息
- 请求方式：GET
- 新版入口：`get_volatility` / `get_volatility_analysis` (futures.py)
- 参考逻辑：`old_backend/scripts/test_volatility_api.py`、`check_volatility_data.py`
- 前端页面：`/futures-market/volatility`

#### 2. 数据源对比
| 项目 | 当前实现 | 旧版/参考 |
|------|----------|-----------|
| 表 | fact_futures_daily | fact_futures_daily |
| 主力合约 | 每日 open_interest 最大 | 同左 |
| 波动率公式 | stdev(ln(P[i]/P[i-n])) × √252 × 100 | 同左（calculate_volatility） |
| 窗口 | window_days 默认 10 | 10 |

**结论：数据源、公式、窗口一致。**

#### 3. 逻辑差异
| 项目 | 当前实现 | 旧版/参考 |
|------|----------|-----------|
| **价格字段** | settle 优先，无则 close | **仅 close** |
| **季节性日期范围** | 按 contract year 分组（03 合约：4月~次年**3月**，含交割月） | is_in_seasonal_range 过滤（03 合约：4月~次年**2月**，**排除交割月 3 月**） |
| **序列连续性** | 每年独立计算，跨年断开 | 全序列连续，可跨年取历史算波动率 |

#### 4. 前端预期
`Volatility.vue` 注释：03 合约季节性为 4月1日~次年 2 月最后一日（与 is_in_seasonal_range 一致，排除交割月）。

#### 5. 修复记录（已完成 2026-03-02）
已与旧版完全对齐：
1. **价格**：改为仅用 close
2. **日期过滤**：增加 `is_in_seasonal_range`，排除交割月
3. **序列**：改为「全序列连续 + 输出时按 is_in_seasonal_range 过滤」

#### 6. 问题归类
- 数据源：一致
- 逻辑：**已对齐**

---

## 第四部分：修复优先级建议

### P0（最高）
1. **statistics-bureau/quarterly-data** — 统计局季度数据，列序错位影响大
2. **price-display 核心接口** — national-price/seasonality, fat-std-spread, price-and-spread, slaughter/lunar
3. **supply-demand/curve** — 供需曲线核心图表
4. **enterprise-statistics/*-daily** — 企业日度统计

### P1（高）
5. **multi-source/data** — 多渠道汇总
6. **structure-analysis/data 与 table**
7. **group-price/group-enterprise-price, white-strip-market**
8. **observation/query** — 兼容层映射完整性

### P2（中）
9. **metadata/dim/geo** — dim_geo → dim_region 的兼容
10. **futures 系列** — 列名、仓单企业匹配
11. **production-indicators 系列**
12. **sales-plan/data**
13. **dashboard/default**

### P3（低）
14. 其他 metadata、reconciliation、ingest、export 等

---

## 第五部分：通用对账建议

1. **数据源映射表**：建立「旧表.旧字段 → 新表.新字段」的映射文档，供开发和测试对照。
2. **抽样对比**：对 P0/P1 接口，用相同时间范围、相同参数分别请求旧版（连 hogprice_old）和新版（连 hogprice_v3），对比 JSON 差异。
3. **导入校验**：确保从 Excel/raw 到 fact_* 的导入逻辑与 API 使用的 indicator_code、price_type、spread_type 等完全一致。
4. **默认参数**：检查 months、days、region、metric_type 等默认值是否与旧版一致。
5. **空值处理**：旧版对 NULL/空行的处理是否在新版中保留（如过滤、兜底、默认值）。
