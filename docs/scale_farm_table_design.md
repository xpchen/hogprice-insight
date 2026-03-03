# E1 规模场数据汇总 - 表格数据源与重设计

## 一、实现方式（当前）

- **表格**：规模场数据汇总**仅用现有 fact 数据**实现，不再依赖 `raw_sheet` / `raw_file` / `raw_table`（当前环境无 raw 层）。
- **接口**：`GET /api/v1/production-indicators/a1-supply-forecast-table` 只从 **fact_monthly_indicator** 按固定 7 列组装并返回。

## 二、当前数据源（统一导入下）

在**仅使用 import_tool 全量导入**的前提下：

| 内容           | 数据源 |
|----------------|--------|
| **表格**       | 由 `fact_monthly_indicator` 按固定列组装（见下「表格结构」），**不再**从 A1 整表 raw 读取。 |
| **母猪效能**   | 优先 **A1供给预测 F列**（r02 解析，source=A1），无则 涌益 月度-生产指标（source=YONGYI）。 |
| **压栏系数**   | 优先 **A1供给预测 N列**（r02 解析，source=A1），无则 涌益 月度-生产指标（source=YONGYI）。 |
| **能繁/新生仔猪/存栏/出栏** | **NYB**（2、【生猪产业数据】.xlsx 内 NYB sheet）→ fact_monthly_indicator，环比%。 |

即：表格 = 同一数据源文件下的 **A1（F/N）+ NYB** 等在 fact 表中的汇总展示，而不是 A1 整表截图。

## 三、表格重设计（fact 表组装方案）

### 3.1 列定义（规模场供给预测 + 定点屠宰）

**1. 规模场供给预测**

| 表头（行1） | 表头（行2） | 指标 / 来源 | 说明 |
|-------------|------------|-------------|------|
| 能繁存栏 | (空) | - | 月度绝对值暂无 |
| 能繁环比 | 环比 | breeding_sow_inventory NYB nation mom_pct | 有 |
| 能繁同比 | 同比 | - | 暂无 |
| 母猪效能 | (空) | prod_farrowing_count A1/YONGYI | 有 |
| 新生仔猪 | (空) | - | 暂无 |
| 新生仔猪环比 | 环比 | piglet_inventory NYB nation mom_pct | 有 |
| 新生仔猪同比 | 同比 | - | 暂无 |
| 5月大猪 | (空) | - | 暂无 |
| 5月大猪环比 | 环比 | medium_large_hog NYB nation mom_pct | 有 |
| 5月大猪同比 | 同比 | - | 暂无 |
| 残差率 | (空) | - | 暂无 |
| 生猪出栏 | (空) | - | 暂无 |
| 生猪出栏环比 | 环比 | hog_turnover NYB nation mom_pct | 有 |
| 生猪出栏同比 | 同比 | - | 暂无 |
| 累计出栏 | 累计 | - | 暂无月度 |
| 累同 | 累同 | - | 暂无 |
| 定点屠宰 | (空) | designated_slaughter STATISTICS_BUREAU abs | 有（定点屠宰 sheet） |
| 定点屠宰环比 | 环比 | - | 暂无 |
| 定点屠宰同比 | 同比 | - | 暂无 |

### 3.2 表头结构

- **header_row_0**：`["月度", "能繁母猪存栏", "新生仔猪", "生猪存栏", "出栏", "母猪效能", "压栏系数"]`
- **header_row_1**：`["", "环比%", "环比%", "环比%", "环比%", "绝对值", "绝对值"]`  
  用于区分环比与绝对值，前端已有双行表头与样式（如环比列样式）。

### 3.3 数据行

- 按**月份**排序（如倒序展示最近在前）。
- 每列从 `fact_monthly_indicator` 取对应 (indicator_code, source, sub_category, value_type)；母猪效能、压栏系数先取 source=A1，缺失再取 YONGYI。
- 环比列可保留 1 位小数；母猪效能/压栏系数按需格式化（小数位或整数）。

### 3.4 与旧版差异

- **旧**：A1 整表（多列、多行表头、合并单元格）原样输出。
- **新**：固定 7 列、双行表头、无合并单元格，全部来自 fact 表，口径与 A1 的 F/N 及 NYB 一致，便于统一导入与维护。

## 四、前端

- 仍使用现有 `getA1SupplyForecastTable()` 与 `A1SupplyForecastTableResponse` 结构（`header_row_0`、`header_row_1`、`rows`、`column_count`、`merged_cells_json` 可为 []）。
- 已有 `headerGrid`、`displayRows`、环比/绝对值样式逻辑，**无需改组件**，只需后端按上表返回双行表头与 7 列数据。
- 空数据提示可保持：「请先导入 2、【生猪产业数据】.xlsx 并确保包含 A1供给预测」；数据来源说明可写：A1供给预测（F/N）+ NYB 等 fact 汇总。

## 五、小结

- **旧表格数据源**：A1供给预测 **整表**（raw_table，仅模板/统一导入时有）。
- **新表格数据源**：**fact_monthly_indicator** 中 A1（F/N）+ NYB 等按上表 7 列组装；母猪效能、压栏系数与 E1 图表一致，**以 A1 供给预测 F列、N列为准**。
