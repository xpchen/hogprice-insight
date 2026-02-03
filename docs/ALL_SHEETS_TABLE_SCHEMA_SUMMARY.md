# 所有Sheet表结构定义总结

## 概述

本文档汇总了5类Excel文件中所有sheet的表结构定义情况。

## 1. 钢联价格模板 (GANGLIAN DAILY)

**文件**: `1、价格：钢联自动更新模板.xlsx`  
**Sheet数量**: 7个  
**状态**: ✅ 已完成详细表结构定义

### Sheet列表

1. ✅ 分省区猪价 → `ganglian_daily_province_price`
2. ✅ 集团企业出栏价 → `ganglian_daily_group_enterprise_price`
3. ✅ 交割库出栏价 → `ganglian_daily_delivery_warehouse_price`
4. ✅ 区域价差 → `ganglian_daily_region_spread`
5. ✅ 肥标价差 → `ganglian_daily_fat_std_spread`
6. ✅ 毛白价差 → `ganglian_daily_live_white_spread`
7. ✅ 养殖利润（周度） → `ganglian_weekly_farm_profit`

**详细定义**: 见 `docs/COMPLETE_TABLE_SCHEMA_AND_MAPPING.md` 第1节

## 2. 涌益日度数据 (YONGYI DAILY)

**文件**: `2026年2月2日涌益咨询日度数据.xlsx`  
**Sheet数量**: 8个  
**状态**: ✅ 已完成详细表结构定义

### Sheet列表

1. ✅ 出栏价 → `yongyi_daily_out_price`
2. ✅ 价格+宰量 → `yongyi_daily_price_slaughter`
3. ✅ 散户标肥价差 → `yongyi_daily_scatter_fat_spread`
4. ✅ 各省份均价 → `yongyi_daily_province_avg`
5. ✅ 市场主流标猪肥猪价格 → `yongyi_daily_market_std_fat_price`
6. ✅ 屠宰企业日度屠宰量 → `yongyi_daily_slaughter_vol`
7. ✅ 市场主流标猪肥猪均价方便作图 → `yongyi_daily_market_avg_convenient`
8. ✅ 交割地市出栏价 → `yongyi_daily_delivery_city_price`

**详细定义**: 见 `docs/COMPLETE_TABLE_SCHEMA_AND_MAPPING.md` 第2节

## 3. 涌益周度数据 (YONGYI WEEKLY)

**文件**: `2026.1.16-2026.1.22涌益咨询 周度数据.xlsx`  
**Sheet数量**: 65个（其中数据sheet 56个）  
**状态**: ⏳ 已完成列表和主要sheet结构定义，部分sheet需要进一步详细分析

### 主要周度数据Sheet（13个）

1. ✅ 周度-商品猪出栏价 → `yongyi_weekly_out_price`
2. ✅ 周度-体重 → `yongyi_weekly_weight`
3. ✅ 周度-屠宰厂宰前活猪重 → `yongyi_weekly_slaughter_prelive_weight`
4. ✅ 周度-各体重段价差 → `yongyi_weekly_weight_spread`
5. ✅ 周度-养殖利润最新 → `yongyi_weekly_farm_profit_latest`
6. ✅ 周度-冻品库存 → `yongyi_weekly_frozen_inventory`
7. ✅ 周度-毛白价差 → `yongyi_weekly_live_white_spread`
8. ✅ 周度-50公斤二元母猪价格 → `yongyi_weekly_sow_50kg_price`
9. ✅ 周度-规模场15公斤仔猪出栏价 → `yongyi_weekly_piglet_15kg_price`
10. ✅ 周度-淘汰母猪价格 → `yongyi_weekly_cull_sow_price`
11. ✅ 周度-宰后结算价 → `yongyi_weekly_post_slaughter_settle_price`
12. ✅ 周度-猪肉价（前三等级白条均价） → `yongyi_weekly_pork_price`
13. ✅ 周度-屠宰企业日度屠宰量 → `yongyi_weekly_slaughter_daily`

### 其他周度数据Sheet（约17个）

- ⏳ 周度-体重拆分 → `yongyi_weekly_weight_split`
- ⏳ 周度-当期、预期成本 → `yongyi_weekly_current_expected_cost`
- ⏳ 周度-河南屠宰白条成本 → `yongyi_weekly_henan_slaughter_cost`
- ⏳ 周度-冻品库存多样本 → `yongyi_weekly_frozen_inventory_multi`
- ⏳ 周度-猪肉产品价格 → `yongyi_weekly_pork_product_price`
- ⏳ 周度-养殖利润 → `yongyi_weekly_farm_profit`
- ⏳ 二育成本 → `yongyi_weekly_second_breeding_cost`
- ⏳ 二育销量 → `yongyi_weekly_second_breeding_sales`
- ⏳ 二育栏舍利用率 → `yongyi_weekly_second_breeding_utilization`
- ⏳ 高频仔猪、母猪 → `yongyi_weekly_high_freq_piglet_sow`
- ⏳ 鲜销率 → `yongyi_weekly_fresh_sales_ratio`
- ⏳ 华东冻品价格 → `yongyi_weekly_east_china_frozen_price`
- ⏳ 国产冻品2-4号肉价格 → `yongyi_weekly_domestic_frozen_price`
- ⏳ 进口肉 → `yongyi_weekly_imported_meat`
- ⏳ MSY → `yongyi_weekly_msy`
- ⏳ 各存栏规模 → `yongyi_weekly_inventory_scale`
- ⏳ 不同规模市占率（按生猪出栏划分） → `yongyi_weekly_market_share_by_output`
- ⏳ 不同规模市占率（按母猪存栏划分） → `yongyi_weekly_market_share_by_sow`
- ⏳ 仔猪与商品猪利润对比 → `yongyi_weekly_profit_comparison`
- ⏳ 育肥全价料价格 → `yongyi_weekly_feed_price`
- ⏳ 猪料原料占比 → `yongyi_weekly_feed_ingredient_ratio`
- ⏳ 运费 → `yongyi_weekly_freight`
- ⏳ 重要部位冻品进口 → `yongyi_weekly_important_part_frozen_import`
- ⏳ 周&月度-三元母猪价格 → `yongyi_weekly_monthly_ternary_sow_price`
- ⏳ 减产能较2018年7月30日 → `yongyi_weekly_capacity_reduction`
- ⏳ 新增猪场 → `yongyi_weekly_new_farm`
- ⏳ 历史出栏体重 → `yongyi_historical_out_weight`

### 月度数据Sheet（约15个）

- ⏳ 月度-商品猪出栏量 → `yongyi_monthly_out_volume`
- ⏳ 月度-能繁母猪存栏量 → `yongyi_monthly_breeding_sow_inventory`
- ⏳ 月度-小猪存栏 → `yongyi_monthly_piglet_inventory`
- ⏳ 月度-大猪存栏 → `yongyi_monthly_big_pig_inventory`
- ⏳ 月度-小猪（50公斤以下）存栏 → `yongyi_monthly_piglet_under_50kg_inventory`
- ⏳ 月度-能繁母猪存栏（2020年2月新增） → `yongyi_monthly_breeding_sow_inventory_v2`
- ⏳ 月度-淘汰母猪屠宰厂宰杀量 → `yongyi_monthly_cull_sow_slaughter`
- ⏳ 月度-猪料销量 → `yongyi_monthly_feed_sales`
- ⏳ 月度-屠宰厂公母比例 → `yongyi_monthly_slaughter_male_female_ratio`
- ⏳ 月度-屠宰企业开工率 → `yongyi_monthly_slaughter_utilization`
- ⏳ 月度-生产指标（2021.5.7新增） → `yongyi_monthly_production_indicator_v1`
- ⏳ 月度-生产指标2 → `yongyi_monthly_production_indicator_v2`
- ⏳ 月度-二元三元能繁比例 → `yongyi_monthly_binary_ternary_ratio`
- ⏳ 月度-原种场二元后备母猪销量及出栏日龄 → `yongyi_monthly_breeding_sow_sales_age`
- ⏳ 月度出栏完成率 → `yongyi_monthly_out_completion_rate`
- ⏳ 月度计划出栏量 → `yongyi_monthly_planned_out_volume`
- ⏳ 月度猪肉供应占比 → `yongyi_monthly_pork_supply_ratio`

**详细定义**: 见 `docs/YONGYI_WEEKLY_COMPLETE_TABLE_SCHEMA.md`

## 4. DCE期货 (DCE DAILY)

**文件**: `lh_ftr.xlsx`  
**Sheet数量**: 1个  
**状态**: ✅ 使用现有表

### Sheet列表

1. ✅ 日历史行情 → 使用现有表 `fact_futures_daily`

**说明**: 无需新建表，使用现有的期货日度数据表

## 5. DCE期权 (DCE DAILY)

**文件**: `lh_opt.xlsx`  
**Sheet数量**: 1个  
**状态**: ✅ 使用现有表

### Sheet列表

1. ✅ 日历史行情 → 使用现有表 `fact_options_daily`

**说明**: 无需新建表，使用现有的期权日度数据表

## 统计汇总

| 数据源 | Sheet数量 | 需要新建表数 | 状态 |
|--------|----------|------------|------|
| 钢联日度 | 7 | 7 | ✅ 已完成 |
| 涌益日度 | 8 | 8 | ✅ 已完成 |
| 涌益周度 | 56 | 56 | ⏳ 部分完成 |
| DCE期货 | 1 | 0 | ✅ 使用现有表 |
| DCE期权 | 1 | 0 | ✅ 使用现有表 |
| **总计** | **73** | **71** | |

## 文档索引

1. **完整表结构定义**: `docs/COMPLETE_TABLE_SCHEMA_AND_MAPPING.md`
   - 包含钢联7个表和涌益日度8个表的详细定义
   - 包含涌益周度56个sheet的列表和主要sheet结构

2. **涌益周度详细定义**: `docs/YONGYI_WEEKLY_COMPLETE_TABLE_SCHEMA.md`
   - 包含涌益周度数据所有sheet的详细表结构定义

3. **列映射配置**: `docs/COMPLETE_COLUMN_MAPPING_CONFIG.md`
   - 包含所有sheet的列映射配置示例

4. **实施总结**: `docs/TABLE_SCHEMA_IMPLEMENTATION_SUMMARY.md`
   - 包含实施进度和下一步计划

## 下一步工作

1. ⏳ 为涌益周度数据的所有sheet创建详细的表结构定义
2. ⏳ 创建完整的Alembic迁移脚本（包含所有71个表）
3. ⏳ 为每个sheet创建完整的列映射配置
4. ⏳ 更新ingest_profile配置文件
5. ⏳ 测试导入功能
