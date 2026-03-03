# D3. 销售计划 — 新旧代码与数据源对比

## 1. 前端页面（当前）

- **路由**: `http://localhost:5173/enterprise-statistics/sales-plan`
- **接口**: `GET /api/v1/sales-plan/data?indicator=全部&region=全部`
- **筛选**:
  - 指标：全部、当月环比、计划环比、计划达成率、当月出栏量
  - 区域：**全部、全国CR20、全国CR5、涌益、钢联、广东、四川、贵州**

## 2. 旧设计（从脚本与 Excel 分析推断）

旧版设计为**三路数据源**，对应三个 Excel 来源：

| 数据源 | Excel 来源 | 区域/维度 | 说明 |
|--------|------------|-----------|------|
| **集团企业** | 《集团企业月度数据跟踪》— **汇总** sheet | 广东、四川、贵州、全国CR20、全国CR5 | 出栏计划、实际出栏量、计划完成率等 |
| **涌益** | 《涌益咨询 周度数据》— **月度计划出栏量** sheet | 涌益 | 月度计划出栏量 |
| **钢联** | 《价格：钢联自动更新模板》— **月度数据** sheet | 钢联 | 月度数据 |

- 旧后端测试脚本 `test_sales_plan_api.py` 依赖三个内部函数：
  - `_get_enterprise_data(db, ['全国CR20','全国CR5','广东','四川','贵州'])`
  - `_get_yongyi_data(db)`
  - `_get_ganglian_data(db)`
- 即：**企业汇总（多区域）+ 涌益 + 钢联** 三路合并后返回，前端按「区域」筛选 全国CR20、全国CR5、涌益、钢联、广东、四川、贵州。

## 3. 当前后端实现（hogprice_v3）

- **文件**: `backend/app/api/sales_plan.py`
- **数据源**: **仅** `fact_enterprise_monthly` 一张表。
- **逻辑**:
  - 按 `company_code` 过滤（牧原、温氏等 `COMPANY_DISPLAY` 映射）。
  - 聚合键为 `(month_date, company_code)`，**未使用 `region_code`**。
  - 返回的 `region` 字段 = 公司中文名（牧原、温氏、新希望等），**没有**「广东、四川、贵州、全国CR20、全国CR5」，也**没有**「涌益、钢联」。

### 3.1 fact_enterprise_monthly 的写入方式（r04 导入）

- **汇总 sheet** 写入时：
  - 广东/四川/贵州：`company_code = 'TOTAL'`，`region_code = 'GUANGDONG'|'SICHUAN'|'GUIZHOU'`，指标如 `planned_output_monthly`, `actual_output_monthly`, `plan_completion_rate_monthly`。
  - 全国CR20/全国CR5：`company_code = 'CR20'|'CR5'`，`region_code = 'NATION'`。
- **四川/广东/贵州/集团企业全国** 等 sheet：按企业写入，`company_code` = MUYUAN、WENS 等，`region_code` = SICHUAN、GUANGDONG、NATION 等。

因此库里**同时存在**：
- 汇总维度：`(TOTAL, GUANGDONG)`、`(TOTAL, SICHUAN)`、`(TOTAL, GUIZHOU)`、`(CR20, NATION)`、`(CR5, NATION)`；
- 企业维度：`(MUYUAN, ...)`、`(WENS, ...)` 等。

当前 API 只按 `company_code` 聚合，且展示名只来自 `COMPANY_DISPLAY`，导致：

1. **广东/四川/贵州** 三条汇总数据都是 `company_code=TOTAL`，被合成一条，且展示为 `"TOTAL"` 而非「广东/四川/贵州」。
2. **全国CR20/全国CR5** 展示为 `"CR20"`/`"CR5"`，与前端期望的「全国CR20」「全国CR5」不一致。
3. **涌益、钢联** 未接入，前端选「涌益」或「钢联」时永远无数据。

## 4. Excel → 库 → 前端列映射（指标名称对齐）

| 数据源 | Excel / Sheet | Excel 列（表头） | fact 表 / indicator_code | 前端列头（中文） |
|--------|----------------|------------------|---------------------------|------------------|
| 涌益 | 涌益周度 / **月度计划出栏量** | 本月计划销售、上月样本企业合计销售 | yongyi_planned_output、yongyi_actual_sample_sales | 计划出栏量、实际出栏量 |
| 钢联 | 钢联模板 / **月度数据** | 猪：计划出栏量/出栏数：中国（月） | hog_planned_output、hog_slaughter_count | 计划出栏量、实际出栏量 |
| 企业汇总 | 集团企业月度 / **汇总** | 出栏计划、实际出栏量、计划完成率 | planned_output_*、actual_output_*、plan_completion_rate_* | 计划出栏量、实际出栏量、计划完成率 |

- 计划完成率：API 内计算 actual/plan；前端列「计划完成率」（与 Excel 汇总 sheet 一致）。
- **当月环比** = 当月实际/上月实际 - 1，**计划环比** = 当月计划/上月计划 - 1：企业、涌益、钢联均为按上月绝对值**计算**，Excel 未单独入库环比列，与旧逻辑（如结构分析）一致。
- **前端列头与旧版一一对应（中文）**：日期、实际出栏量、计划出栏量、当月环比、计划环比、计划完成率。

## 5. 数据源是否一致？— 结论（已对齐）

| 项目 | 旧设计 | 当前实现 | 是否一致 |
|------|--------|----------|----------|
| 集团企业汇总（广东/四川/贵州/全国CR20/全国CR5） | 有 | 有，按 region_code 展示与筛选 | **是** |
| 集团企业（牧原、温氏等） | 有 | 有，fact_enterprise_monthly | **是** |
| 涌益 | 有 | 有，fact_monthly_indicator（实际=hog_output_volume，计划=yongyi_planned_output，r09 月度计划出栏量解析写入） | **是** |
| 钢联 | 有 | 有，fact_monthly_indicator（计划=hog_planned_output，实际=hog_slaughter_count，r01 月度数据 sheet） | **是** |

**总结**：三路数据源已全部接入；Excel 列与 indicator、前端表头已按上表映射。
