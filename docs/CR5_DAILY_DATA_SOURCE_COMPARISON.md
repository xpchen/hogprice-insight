# D1. CR5企业日度出栏统计 — 四图数据源与新旧逻辑对比

## 一、四个图表与当前 API 数据源

| 图表 | 前端系列名 | 当前 API | 查询表 | 查询条件（metric_type / region / company） |
|------|------------|----------|--------|--------------------------------------------|
| (1) CR5企业日度出栏 | 日度出栏、计划量、价格 | `/cr5-daily` | fact_enterprise_daily | company_code=CR5, region=NATION；output_cumulative → 日度出栏，planned_volume → 计划量，avg_price → 价格 |
| (2) 四川重点企业日度出栏 | 日度出栏、计划出栏、成交率 | `/sichuan-daily` | fact_enterprise_daily | **与西南一致**：优先 西南汇总 SAMPLE+SICHUAN：actual_volume→日度出栏，deal_rate→成交率；计划出栏仍为 region=SICHUAN 的 planned_volume(SUM)。无则回退 actual_sales(SUM)/region deal_rate(AVG)。 |
| (3) 广西重点企业日度出栏 | 日度出栏、成交率 | `/guangxi-daily` | fact_enterprise_daily | **与西南一致**：优先 西南汇总 SAMPLE+GUANGXI：actual_volume→日度出栏，deal_rate→成交率。无则回退 actual_sales(SUM)/region deal_rate(AVG)。 |
| (4) 西南样本企业日度出栏 | 出栏量、均重 | `/southwest-sample-daily` | fact_enterprise_daily | company=SAMPLE, region=SOUTHWEST：sample_volume→出栏量，sample_weight→均重；若无则退化为 region=SOUTHWEST 的 actual_sales(SUM)→出栏量 |

**当前逻辑统一从 `fact_enterprise_daily` 读数，由 r03（企业集团出栏跟踪 Excel）导入写入。**

---

## 二、r03 写入与 Excel 对应关系

- **CR5日度**  
  - col2 实际出栏 → output_cumulative，单位 万头  
  - col3 月度计划 → planned_volume，单位 万头（已补入 r03）  
  - col4 全国均价 → avg_price，元/公斤  
  - col5–9 各企业 → output_cumulative（万头）  
- **四川**  
  - 四川 sheet：各企业 actual_sales、planned_volume（头）  
  - 四川日度类 sheet：计划订购量、实际销售量、成交率 → planned_volume、actual_sales、deal_rate  
  - **西南汇总**：col4 实际成交 → SAMPLE+SICHUAN actual_volume，col5 成交率 → SAMPLE+SICHUAN deal_rate（与四川/广西图一致用此口径）  
- **广西**  
  - 广西 sheet：各企业 actual_sales、planned_volume  
  - 广西日度类 sheet：成交率等 → deal_rate  
  - **西南汇总**：col10 实际成交 → SAMPLE+GUANGXI actual_volume，col11 成交率 → SAMPLE+GUANGXI deal_rate  
- **西南汇总**  
  - col15 量 → SAMPLE, SOUTHWEST, sample_volume（头）  
  - col16 重 → SAMPLE, SOUTHWEST, sample_weight（公斤）  

---

## 三、与「旧」数据源/逻辑的差异（导致曲线差异的原因）

### 1. 数据表与口径

- **旧逻辑可能**：部分来自模板解析入库的 `fact_observation`（P8 解析器、dim_metric + fact_observation），或直接读 Excel/其他表。  
- **现逻辑**：仅从 `fact_enterprise_daily` 读，且仅使用 r03 导入的数据。  
- 若历史上有过「旧导入」或「旧表」，而当前库只跑 r03 → fact_enterprise_daily，则**数据源不一致**，曲线会不同。

### 2. CR5 单位与计划量（已按旧版对齐）

- **万头 vs 头**  
  - r03 将 CR5 出栏/计划存为 **万头**。若旧版按 **头** 展示，则数量级会差约 1 万倍，曲线会「极大不同」。  
  - **已做**：接口层将 CR5 的 日度出栏、计划量 由万头转为头（×10000）再返回，与旧版图表尺度一致。  
- **计划量**  
  - 旧版有「计划量」曲线，r03 此前未写 col3 月度计划。  
  - **已做**：r03 已增加 col3 → planned_volume（万头），接口同样转为头并返回「计划量」系列。

### 3. 四川 / 广西（已对齐）

- **原因**：旧版四川/广西图与 CR5、西南样本一样，用的是**同一份「西南汇总」sheet**：四川 col4 实际成交、col5 成交率，广西 col10 实际成交、col11 成交率。当前实现曾用「四川」「广西」分省 sheet 的 actual_sales 按企业 SUM，口径不同导致曲线完全不同。  
- **已做**：四川、广西接口改为**优先**使用 西南汇总 的 actual_volume、deal_rate（SAMPLE+SICHUAN / SAMPLE+GUANGXI），与 CR5/西南样本数据源一致；并已在 r03 中写入 西南汇总 的 四川/广西 成交率（col5、col11）。无 西南汇总 数据时再回退到 四川/广西 sheet 的 SUM(actual_sales)、AVG(deal_rate)。

### 4. 西南样本

- 当前：优先 SAMPLE + SOUTHWEST 的 sample_volume / sample_weight；没有则用 SOUTHWEST 的 actual_sales(SUM)。  
- 若旧版仅用「西南汇总」的样本量/均重，而当前某段时间只有 actual_sales 汇总，则两条曲线口径会不同，曲线也会不同。

---

## 四、已做修改小结

1. **r03**  
   - CR5日度 col3 月度计划 → 写入 `planned_volume`（万头）。  

2. **CR5-daily API**  
   - 出栏、计划量：DB 为万头时，在接口中转为头（×10000）再返回。  
   - 增加「计划量」系列：查询 CR5 的 `planned_volume`，同样按头返回。  

3. **文档**  
   - 本说明：四图数据来源、r03 对应关系、与旧逻辑差异及曲线差异原因。

---

## 五、建议核对项

- 确认当前环境是否**只**用 r03 导入「企业集团出栏跟踪」到 fact_enterprise_daily；若有旧导入或 P8→fact_observation 的报表，需确认旧版图表当时读的是哪张表、哪些字段。  
- 若四川/广西/西南仍与旧版不一致，可对比同一日期在 Excel、fact_enterprise_daily、以及（若存在）fact_observation 中的数值，确认是否表/口径/批次不一致。
