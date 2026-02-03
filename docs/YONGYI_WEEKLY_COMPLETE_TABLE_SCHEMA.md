# 涌益周度数据完整表结构定义

## 概述

本文档定义涌益周度数据文件中所有56个数据sheet的表结构、列名和列映射规则。

**文件**: `2026.1.16-2026.1.22涌益咨询 周度数据.xlsx`  
**数据sheet数量**: 56个  
**说明sheet**: 9个（样本点选取、目录、数据说明等）

## 表命名规范

格式：`yongyi_weekly_{sheet_name_snake_case}`

规则：
- 移除"周度-"前缀
- 中文转snake_case
- 特殊字符替换为下划线
- 长度限制64字符

## Sheet分类

### 1. 周度数据Sheet（主要数据）

#### 1.1 周度-商品猪出栏价 (yongyi_weekly_out_price)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_out_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    price DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_region (period_end, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射**:
- `period_start`: 第1列（起始日期）
- `period_end`: 第2列（结束日期）
- `region_code`: 列名（省份），使用`normalize_province_name`
- `price`: 列值

#### 1.2 周度-体重 (yongyi_weekly_weight)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_weight (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    indicator VARCHAR(64) NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    weight_value DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_indicator_region (period_end, indicator, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end),
    INDEX idx_indicator (indicator),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射**:
- `period_start`: 第1列
- `period_end`: 第2列
- `indicator`: 第3列（指标名称，行维度）
- `region_code`: 列名（省份）
- `weight_value`: 列值

#### 1.3 周度-屠宰厂宰前活猪重 (yongyi_weekly_slaughter_prelive_weight)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_slaughter_prelive_weight (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    indicator VARCHAR(64) NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    weight_value DECIMAL(18, 6),
    change_from_last_week DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_indicator_region (period_end, indicator, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射**:
- `period_start`: 第1列
- `period_end`: 第2列
- `indicator`: 第3列
- `region_code`: 列名（省份）
- `weight_value`: 当子列为省份名时的值
- `change_from_last_week`: 当子列为"较上周"时的值

**注意**: 此sheet有子列结构（省份/较上周）

#### 1.4 周度-各体重段价差 (yongyi_weekly_weight_spread)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_weight_spread (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    indicator VARCHAR(64) NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    spread_value DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_indicator_region (period_end, indicator, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end),
    INDEX idx_indicator (indicator),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.5 周度-养殖利润最新 (yongyi_weekly_farm_profit_latest)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_farm_profit_latest (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    scale_type VARCHAR(32) NOT NULL,
    profit_mode VARCHAR(32) NOT NULL,
    profit_value DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_scale_mode (period_end, scale_type, profit_mode),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射**:
- `period_start`: 第1列
- `period_end`: 第2列
- `scale_type`: 规模段（从列名提取）
- `profit_mode`: 利润模式（自繁自养/外购仔猪等）
- `profit_value`: 利润值

#### 1.6 周度-冻品库存 (yongyi_weekly_frozen_inventory)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_frozen_inventory (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    region_code VARCHAR(32),
    inventory_ratio DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_region (period_end, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.7 周度-毛白价差 (yongyi_weekly_live_white_spread)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_live_white_spread (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_end DATE NOT NULL,
    metric_name VARCHAR(64) NOT NULL,
    spread_value DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_metric (period_end, metric_name),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.8 周度-50公斤二元母猪价格 (yongyi_weekly_sow_50kg_price)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_sow_50kg_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    region_code VARCHAR(32),
    price DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_region (period_end, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.9 周度-规模场15公斤仔猪出栏价 (yongyi_weekly_piglet_15kg_price)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_piglet_15kg_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    region_code VARCHAR(32),
    price DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_region (period_end, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.10 周度-淘汰母猪价格 (yongyi_weekly_cull_sow_price)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_cull_sow_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    region_code VARCHAR(32),
    price DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_region (period_end, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.11 周度-宰后结算价 (yongyi_weekly_post_slaughter_settle_price)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_post_slaughter_settle_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    region_code VARCHAR(32),
    settle_price DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_region (period_end, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.12 周度-猪肉价（前三等级白条均价） (yongyi_weekly_pork_price)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_pork_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    region_code VARCHAR(32),
    avg_price DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_region (period_end, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.13 周度-屠宰企业日度屠宰量 (yongyi_weekly_slaughter_daily)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_slaughter_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    slaughter_volume INT,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region (trade_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**注意**: 此sheet包含日度数据，使用`trade_date`而非`period_start/period_end`

### 2. 其他周度数据Sheet

#### 2.1 周度-体重拆分 (yongyi_weekly_weight_split)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_weight_split (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_end DATE NOT NULL,
    nation_avg_weight DECIMAL(18, 6),
    group_weight DECIMAL(18, 6),
    scatter_weight DECIMAL(18, 6),
    group_ratio DECIMAL(18, 6),
    scatter_ratio DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period (period_end),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.2 周度-当期、预期成本 (yongyi_weekly_current_expected_cost)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_current_expected_cost (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    cost_type VARCHAR(32) NOT NULL,
    cost_value DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_cost_type (period_end, cost_type),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.3 周度-河南屠宰白条成本 (yongyi_weekly_henan_slaughter_cost)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_henan_slaughter_cost (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    cost_value DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period (period_end),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.4 周度-冻品库存多样本 (yongyi_weekly_frozen_inventory_multi)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_frozen_inventory_multi (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_type VARCHAR(32) NOT NULL,
    inventory_ratio DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region_type (trade_date, region_type),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.5 周度-猪肉产品价格 (yongyi_weekly_pork_product_price)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_pork_product_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    product_type VARCHAR(64) NOT NULL,
    price DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_product (period_end, product_type),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2.6 周度-养殖利润 (yongyi_weekly_farm_profit)

**表结构**:
```sql
CREATE TABLE yongyi_weekly_farm_profit (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    metric_name VARCHAR(64) NOT NULL,
    profit_value DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_metric (period_end, metric_name),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 3. 月度数据Sheet

#### 3.1 月度-商品猪出栏量 (yongyi_monthly_out_volume)

**表结构**:
```sql
CREATE TABLE yongyi_monthly_out_volume (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    month_date DATE NOT NULL,
    region_code VARCHAR(32),
    out_volume DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_month_region (month_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_month (month_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 3.2 月度-能繁母猪存栏量 (yongyi_monthly_breeding_sow_inventory)

**表结构**:
```sql
CREATE TABLE yongyi_monthly_breeding_sow_inventory (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    month_date DATE NOT NULL,
    region_code VARCHAR(32),
    inventory_value DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_month_region (month_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_month (month_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 3.3-3.15 其他月度Sheet

类似结构，包括：
- 月度-小猪存栏
- 月度-大猪存栏
- 月度-小猪（50公斤以下）存栏
- 月度-能繁母猪存栏（2020年2月新增）
- 月度-淘汰母猪屠宰厂宰杀量
- 月度-猪料销量
- 月度-屠宰厂公母比例
- 月度-屠宰企业开工率
- 月度-生产指标（2021.5.7新增）
- 月度-生产指标2
- 月度-二元三元能繁比例
- 月度-原种场二元后备母猪销量及出栏日龄
- 月度出栏完成率
- 月度计划出栏量
- 月度猪肉供应占比

### 4. 其他数据Sheet

#### 4.1 二育成本 (yongyi_weekly_second_breeding_cost)

#### 4.2 二育销量 (yongyi_weekly_second_breeding_sales)

#### 4.3 二育栏舍利用率 (yongyi_weekly_second_breeding_utilization)

#### 4.4 高频仔猪、母猪 (yongyi_weekly_high_freq_piglet_sow)

#### 4.5 鲜销率 (yongyi_weekly_fresh_sales_ratio)

#### 4.6 华东冻品价格 (yongyi_weekly_east_china_frozen_price)

#### 4.7 国产冻品2-4号肉价格 (yongyi_weekly_domestic_frozen_price)

#### 4.8 进口肉 (yongyi_weekly_imported_meat)

#### 4.9 MSY (yongyi_weekly_msy)

#### 4.10 各存栏规模 (yongyi_weekly_inventory_scale)

#### 4.11 不同规模市占率（按生猪出栏划分） (yongyi_weekly_market_share_by_output)

#### 4.12 不同规模市占率（按母猪存栏划分） (yongyi_weekly_market_share_by_sow)

#### 4.13 仔猪与商品猪利润对比 (yongyi_weekly_profit_comparison)

#### 4.14 育肥全价料价格 (yongyi_weekly_feed_price)

#### 4.15 猪料原料占比 (yongyi_weekly_feed_ingredient_ratio)

#### 4.16 运费 (yongyi_weekly_freight)

#### 4.17 重要部位冻品进口 (yongyi_weekly_important_part_frozen_import)

#### 4.18 周&月度-三元母猪价格 (yongyi_weekly_monthly_ternary_sow_price)

#### 4.19 减产能较2018年7月30日 (yongyi_weekly_capacity_reduction)

#### 4.20 新增猪场 (yongyi_weekly_new_farm)

#### 4.21 历史出栏体重 (yongyi_historical_out_weight)

## 总结

- **周度数据sheet**: 约30个
- **月度数据sheet**: 约15个
- **其他数据sheet**: 约11个
- **总计**: 56个数据sheet

每个sheet都需要：
1. 定义表结构（SQL DDL）
2. 定义列映射规则
3. 确定唯一键
4. 创建索引

## 下一步

1. 为每个sheet创建详细的表结构定义
2. 定义列映射配置
3. 创建Alembic迁移脚本
4. 更新ingest_profile配置文件
