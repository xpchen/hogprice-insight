# 母猪效能、压栏系数 数据源对比分析

## 结论摘要（已按 A1 为准修正）

- **规范数据源**：E1 规模场「母猪效能」「压栏系数」以 **A1供给预测**（2、【生猪产业数据】.xlsx）**F列=母猪效能、N列=压栏系数** 为准。
- **当前实现**：
  - **r02** 在导入 2、【生猪产业数据】.xlsx 时解析 **A1供给预测** sheet，将 F 列、N 列写入 `fact_monthly_indicator`，**source=A1**。
  - **API** 查询时**优先使用 source=A1**，若无 A1 数据再回退到 source=YONGYI（涌益 月度-生产指标）。
- **历史**：此前 API 仅用 **source=YONGYI**（涌益 周度 月度-生产指标），与「A1 F/N」口径不一致；已改为以 A1 为准、YONGYI 仅作回退。

## 不一致原因：r09 列号取错

涌益「月度-生产指标」sheet 表头（第 2 行）实际列为：

| 列号 | 表头       | 含义           | r09 原映射 | 正确映射 |
|------|------------|----------------|------------|----------|
| 5    | 配种数环比 | 小数环比       | 误作 母猪效能 | -        |
| 6    | 分娩窝数   | 绝对值（约百万）| -          | **母猪效能** |
| 7    | 分娩窝数环比 | 小数环比     | 误作 压栏系数 | -        |
| 8    | 窝均健仔数 | 绝对值（约 9~11）| -        | **压栏系数** |
| 9    | 产房存活率 | -              | 原用 col8  | 改为 col9 |

- **原逻辑**：r09 用 **col5、col7** 写入 `prod_farrowing_count`、`prod_healthy_piglets_per_litter`，对应的是「配种数环比」「分娩窝数环比」，数值为小数，与页面期望的「母猪效能=分娩窝数、压栏系数=窝均健仔数」不一致。
- **库中现有数据**：若之前某次导入用的是正确列（col6/col8），则库中会出现百万级母猪效能、10~11 的压栏系数；若用的是错误列（col5/col7），则会出现小数，与旧版 A1 F/N 不一致。

## 已做修改

- **r09_yongyi_weekly.py** 中 `_parse_production_metrics` 的 `COL_MAP` 已改为：
  - **母猪效能**：`prod_farrowing_count` ← **col6**（分娩窝数）
  - **压栏系数**：`prod_healthy_piglets_per_litter` ← **col8**（窝均健仔数）
  - 产房存活率：`prod_farrowing_survival_rate` ← **col9**

重新用 **import_tool** 全量或仅导入「涌益咨询 周度数据.xlsx」后，`fact_monthly_indicator` 中的 母猪效能/压栏系数 将与 涌益 月度-生产指标 的 F列(分娩窝数)、H列(窝均健仔数) 一致。

## A1 与 涌益 的差异（可选）

- **A1供给预测**（2、【生猪产业数据】.xlsx）F列、N列 若与 涌益 月度-生产指标 的 分娩窝数、窝均健仔数 **不是同一套数**，则即使用正确列导入涌益，与「旧版用 A1 的数据」仍可能不完全一致。
- 若产品要求 E1 必须与旧版一致（即必须用 A1 表 F/N），则需在 r02 中增加对「A1供给预测」的解析，将 F/N 写入 `fact_monthly_indicator`（如 source=INDUSTRY_DATA 或 A1），且 API 优先取 A1 再回退涌益。

## 如何复验

1. 运行对比脚本（需本地有 2、【生猪产业数据】.xlsx 与 涌益 周度数据）：
   ```bash
   cd backend && python scripts/compare_sow_efficiency_pressure_sources.py
   ```
2. 重新导入涌益周度后，再查库：
   ```bash
   python scripts/check_production_indicator_db.py
   ```
   查看 `prod_farrowing_count`、`prod_healthy_piglets_per_litter` 的数值量级（应为百万级与 9~11）及时间范围。
