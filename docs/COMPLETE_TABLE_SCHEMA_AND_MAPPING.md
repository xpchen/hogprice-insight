# 完整表结构定义和列映射规则

## 概述

本文档定义所有sheet对应的表结构、列名和列映射规则。

## 1. 钢联价格模板 (GANGLIAN DAILY) - 7个表

### 1.1 分省区猪价 (ganglian_daily_province_price)

**表结构**：
```sql
CREATE TABLE ganglian_daily_province_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,  -- 省份代码（从列名提取：如"黑龙江"）
    indicator_name VARCHAR(128),  -- 指标名称（如"商品猪：出栏均价"）
    value DECIMAL(18, 6),  -- 价格值
    unit VARCHAR(32),  -- 单位（元/千克）
    updated_at_time DATETIME,  -- 更新时间（第3行）
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region_indicator (trade_date, region_code, indicator_name),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 第1列（"指标名称"列），第4行起为日期
- `region_code`: 从列名提取（如"商品猪：出栏均价：黑龙江（日）" -> "黑龙江"），使用`normalize_province_name`
- `indicator_name`: 从列名提取指标部分（如"商品猪：出栏均价"）
- `value`: 列值（第4行起）
- `unit`: 第2行（"单位"行）
- `updated_at_time`: 第3行（"更新时间"行）

**Excel结构**：
- 第1行：标题行（"钢联数据"）
- 第2行：指标名称（如"商品猪：出栏均价：黑龙江（日）"）
- 第3行：单位（"元/千克"）
- 第4行：更新时间
- 第5行起：日期 + 价格值

### 1.2 集团企业出栏价 (ganglian_daily_group_enterprise_price)

**表结构**：
```sql
CREATE TABLE ganglian_daily_group_enterprise_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32),  -- 省份（可选，从列名提取）
    enterprise_name VARCHAR(128) NOT NULL,  -- 集团企业名称（从列名提取）
    value DECIMAL(18, 6),  -- 出栏价
    unit VARCHAR(32),
    updated_at_time DATETIME,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_enterprise (trade_date, enterprise_name, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_enterprise (enterprise_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 第1列，第4行起为日期
- `region_code`: 从列名提取省份（如果存在）
- `enterprise_name`: 从列名提取企业名称
- `value`: 列值
- `unit`: 第2行
- `updated_at_time`: 第3行

### 1.3 交割库出栏价 (ganglian_daily_delivery_warehouse_price)

**表结构**：
```sql
CREATE TABLE ganglian_daily_delivery_warehouse_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32),  -- 省份（可选）
    warehouse_name VARCHAR(128) NOT NULL,  -- 交割库名称（从列名提取）
    value DECIMAL(18, 6),  -- 出栏价
    unit VARCHAR(32),
    updated_at_time DATETIME,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_warehouse (trade_date, warehouse_name, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_warehouse (warehouse_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 第1列，第4行起为日期
- `region_code`: 从列名提取省份（如果存在）
- `warehouse_name`: 从列名提取交割库名称
- `value`: 列值
- `unit`: 第2行
- `updated_at_time`: 第3行

### 1.4 区域价差 (ganglian_daily_region_spread)

**表结构**：
```sql
CREATE TABLE ganglian_daily_region_spread (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    spread_type VARCHAR(64) NOT NULL,  -- 价差类型（从列名提取，如"华东-华北"）
    value DECIMAL(18, 6),  -- 价差值
    unit VARCHAR(32),
    updated_at_time DATETIME,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_spread_type (trade_date, spread_type),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 第1列，第4行起为日期
- `spread_type`: 从列名提取价差类型
- `value`: 列值
- `unit`: 第2行
- `updated_at_time`: 第3行

### 1.5 肥标价差 (ganglian_daily_fat_std_spread)

**表结构**：
```sql
CREATE TABLE ganglian_daily_fat_std_spread (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32),  -- 区域（可选，从列名提取）
    value DECIMAL(18, 6),  -- 肥标价差
    unit VARCHAR(32),
    updated_at_time DATETIME,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region (trade_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 第1列，第4行起为日期
- `region_code`: 从列名提取区域（如果存在）
- `value`: 列值
- `unit`: 第2行
- `updated_at_time`: 第3行

### 1.6 毛白价差 (ganglian_daily_live_white_spread)

**表结构**：
```sql
CREATE TABLE ganglian_daily_live_white_spread (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32),  -- 区域（可选）
    value DECIMAL(18, 6),  -- 毛白价差
    unit VARCHAR(32),
    updated_at_time DATETIME,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region (trade_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 第1列，第4行起为日期
- `region_code`: 从列名提取区域（如果存在）
- `value`: 列值
- `unit`: 第2行
- `updated_at_time`: 第3行

### 1.7 养殖利润（周度） (ganglian_weekly_farm_profit)

**表结构**：
```sql
CREATE TABLE ganglian_weekly_farm_profit (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    profit_type VARCHAR(64) NOT NULL,  -- 利润类型（从列名提取，如"自繁自养"、"外购仔猪"）
    value DECIMAL(18, 6),  -- 利润值（元/头）
    unit VARCHAR(32),
    updated_at_time DATETIME,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_period_profit_type (period_end, profit_type),
    INDEX idx_batch (batch_id),
    INDEX idx_period (period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `period_start`: 从日期列解析周期开始
- `period_end`: 从日期列解析周期结束
- `profit_type`: 从列名提取利润类型
- `value`: 列值
- `unit`: 第2行
- `updated_at_time`: 第3行

## 2. 涌益日度数据 (YONGYI DAILY) - 8个sheet

### 2.1 出栏价 (yongyi_daily_out_price)

**表结构**：
```sql
CREATE TABLE yongyi_daily_out_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,  -- 省份
    scale VARCHAR(16) NOT NULL,  -- 规模场/小散户/均价
    price DECIMAL(18, 6),  -- 价格
    change_amount DECIMAL(18, 6),  -- 较昨日涨跌
    last_year_price DECIMAL(18, 6),  -- 去年同期
    yoy_ratio DECIMAL(18, 6),  -- 同比
    tomorrow_forecast DECIMAL(18, 6),  -- 明日预计
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region_scale (trade_date, region_code, scale),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code),
    INDEX idx_scale (scale)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 日期列（第1行，跨4列：规模场、小散户、均价、涨跌）
- `region_code`: 行维度（第1列，省份），使用`normalize_province_name`
- `scale`: 子列名（规模场/小散户/均价），值映射：规模场->scale_farm, 小散户->scatter, 均价->avg
- `price`: 当scale为"规模场"/"小散户"/"均价"时的值
- `change_amount`: 当scale为"涨跌"时的值
- `last_year_price`: 需要识别对应的列（可能是另一个日期组）
- `yoy_ratio`: 需要识别对应的列
- `tomorrow_forecast`: 需要识别对应的列

**日期跨列**：日期在第1行，跨4列（规模场、小散户、均价、涨跌）

**注意**：如果"去年同期"、"同比"、"明日预计"也是日期跨列结构，需要单独处理

### 2.2 价格+宰量 (yongyi_daily_price_slaughter)

**表结构**：
```sql
CREATE TABLE yongyi_daily_price_slaughter (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    nation_avg_price DECIMAL(18, 6),  -- 全国均价
    slaughter_total_1 INT,  -- 日屠宰量合计1
    slaughter_total_2 INT,  -- 日度屠宰量合计2
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date (trade_date),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 第1列（"日期"列）
- `nation_avg_price`: 第2列（"全国均价"列）
- `slaughter_total_1`: 第3列（"日屠宰量合计1"列）
- `slaughter_total_2`: 第4列（"日度屠宰量合计2"列）

**Excel结构**：
- 第1列：日期
- 第2列：全国均价
- 第3列：日屠宰量合计1
- 第4列：日度屠宰量合计2

### 2.3 散户标肥价差 (yongyi_daily_scatter_fat_spread)

**表结构**：
```sql
CREATE TABLE yongyi_daily_scatter_fat_spread (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,  -- 省份
    scatter_std_price DECIMAL(18, 6),  -- 市场散户标重猪价格
    spread_150_vs_std DECIMAL(18, 6),  -- 150公斤左右较标猪价差
    spread_175_vs_std DECIMAL(18, 6),  -- 175公斤左右较标猪价差
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region (trade_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 日期列（第1行，跨3列：场散户标重猪、150公斤左右较标猪、175公斤左右较标猪）
- `region_code`: 行维度（第1列，省份）
- `scatter_std_price`: 当子列为"场散户标重猪"时的值
- `spread_150_vs_std`: 当子列为"150公斤左右较标猪"时的值
- `spread_175_vs_std`: 当子列为"175公斤左右较标猪"时的值

**日期跨列**：日期在第1行，跨3列（场散户标重猪、150公斤左右较标猪、175公斤左右较标猪）

**入库示例**：河南，2023/8/2，16.9，0.4，0.4

### 2.4 各省份均价 (yongyi_daily_province_avg)

**表结构**：
```sql
CREATE TABLE yongyi_daily_province_avg (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,  -- 省份
    avg_price DECIMAL(18, 6),  -- 商品猪出栏均价
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region (trade_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 第1列（"日期"列）
- `region_code`: 从列名提取省份（如"河南"、"湖南"等）
- `avg_price`: 列值

**Excel结构**：
- 第1列：日期
- 第2列起：各省份列（河南、湖南、湖北等）

### 2.5 市场主流标猪肥猪价格 (yongyi_daily_market_std_fat_price)

**表结构**：
```sql
CREATE TABLE yongyi_daily_market_std_fat_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,  -- 省份
    std_pig_avg_price DECIMAL(18, 6),  -- 标猪均价
    std_pig_weight_band VARCHAR(32),  -- 标猪体重段（文本）
    price_90_100 DECIMAL(18, 6),  -- 90-100kg均价
    price_130_140 DECIMAL(18, 6),  -- 130-140kg均价
    price_150_around DECIMAL(18, 6),  -- 150kg左右均价
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region (trade_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 日期列（第1行，跨5列：标猪均价、标猪体重段、90-100kg均价、130-140kg均价、150kg左右均价）
- `region_code`: 行维度（第1列，省份）
- `std_pig_avg_price`: 当子列为"标猪均价"时的值
- `std_pig_weight_band`: 当子列为"标猪体重段"时的值（文本）
- `price_90_100`: 当子列为"90-100kg均价"时的值
- `price_130_140`: 当子列为"130-140kg均价"时的值
- `price_150_around`: 当子列为"150kg左右均价"时的值

**日期跨列**：日期在第1行，跨5列（标猪均价、标猪体重段、90-100kg均价、130-140kg均价、150kg左右均价）

### 2.6 屠宰企业日度屠宰量 (yongyi_daily_slaughter_vol)

**表结构**：
```sql
CREATE TABLE yongyi_daily_slaughter_vol (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,  -- 省份
    slaughter_volume INT,  -- 屠宰量（头）
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region (trade_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 日期列（第1行，日期作为列）
- `region_code`: 行维度（第1列，省份）
- `slaughter_volume`: 列值

**Excel结构**：
- 第1列：省份
- 第2列起：日期列

**入库示例**：辽宁，2026/1/22，14638

### 2.7 市场主流标猪肥猪均价方便作图 (yongyi_daily_market_avg_convenient)

**表结构**：
```sql
CREATE TABLE yongyi_daily_market_avg_convenient (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    nation_avg_price DECIMAL(18, 6),  -- 全国均价
    price_90_100 DECIMAL(18, 6),  -- 90-100kg均价
    price_130_140 DECIMAL(18, 6),  -- 130-140kg均价
    price_150_170 DECIMAL(18, 6),  -- 150-170kg均价
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date (trade_date),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 第1列（"日期"列）
- `nation_avg_price`: 第2列（"全国均价"列）
- `price_90_100`: 第3列（"90-100kg均价"列）
- `price_130_140`: 第4列（"130-140kg均价"列）
- `price_150_170`: 第5列（"150-170kg均价"列）

**Excel结构**：
- 第1列：日期
- 第2列：全国均价
- 第3列：90-100kg均价
- 第4列：130-140kg均价
- 第5列：150-170kg均价

### 2.8 交割地市出栏价 (yongyi_daily_delivery_city_price)

**表结构**：
```sql
CREATE TABLE yongyi_daily_delivery_city_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,  -- 省份
    location_code VARCHAR(32) NOT NULL,  -- 城市
    city_price DECIMAL(18, 6),  -- 城市出栏价
    premium_lh2505_plus DECIMAL(18, 6),  -- 升贴水（LH2505及以后）
    premium_lh2409_lh2503 DECIMAL(18, 6),  -- 升贴水（LH2409-LH2503）
    weight_band VARCHAR(64),  -- 交易均重（文本）
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_city (trade_date, location_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code),
    INDEX idx_location (location_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射规则**：
- `trade_date`: 日期列（第1列）
- `region_code`: 从元数据行提取省份（第1行，合并单元格）
- `location_code`: 城市列名（第5行）
- `city_price`: 城市出栏价值
- `premium_lh2505_plus`: 从元数据行提取（第2行）
- `premium_lh2409_lh2503`: 从元数据行提取（第3行）
- `weight_band`: 从元数据行提取（第4行）

**Excel结构**：
- 第1行：省份（合并单元格）
- 第2行：升贴水（LH2505及以后）
- 第3行：升贴水（LH2409-LH2503）
- 第4行：交易均重
- 第5行：城市名称
- 第6行起：日期 + 价格值

## 3. 涌益周度数据 (YONGYI WEEKLY) - 56个sheet

**文件**: `2026.1.16-2026.1.22涌益咨询 周度数据.xlsx`  
**数据sheet数量**: 56个

### 3.1 主要周度数据Sheet（13个）

详细表结构定义请参考：`docs/YONGYI_WEEKLY_COMPLETE_TABLE_SCHEMA.md`

主要sheet列表：
1. 周度-商品猪出栏价 (yongyi_weekly_out_price)
2. 周度-体重 (yongyi_weekly_weight)
3. 周度-屠宰厂宰前活猪重 (yongyi_weekly_slaughter_prelive_weight)
4. 周度-各体重段价差 (yongyi_weekly_weight_spread)
5. 周度-养殖利润最新 (yongyi_weekly_farm_profit_latest)
6. 周度-冻品库存 (yongyi_weekly_frozen_inventory)
7. 周度-毛白价差 (yongyi_weekly_live_white_spread)
8. 周度-50公斤二元母猪价格 (yongyi_weekly_sow_50kg_price)
9. 周度-规模场15公斤仔猪出栏价 (yongyi_weekly_piglet_15kg_price)
10. 周度-淘汰母猪价格 (yongyi_weekly_cull_sow_price)
11. 周度-宰后结算价 (yongyi_weekly_post_slaughter_settle_price)
12. 周度-猪肉价（前三等级白条均价） (yongyi_weekly_pork_price)
13. 周度-屠宰企业日度屠宰量 (yongyi_weekly_slaughter_daily)

### 3.2 其他周度数据Sheet（17个）

- 周度-体重拆分
- 周度-当期、预期成本
- 周度-河南屠宰白条成本
- 周度-冻品库存多样本
- 周度-猪肉产品价格
- 周度-养殖利润
- 二育成本
- 二育销量
- 二育栏舍利用率
- 高频仔猪、母猪
- 鲜销率
- 华东冻品价格
- 国产冻品2-4号肉价格
- 进口肉
- MSY
- 各存栏规模
- 不同规模市占率（按生猪出栏划分）
- 不同规模市占率（按母猪存栏划分）
- 仔猪与商品猪利润对比
- 育肥全价料价格
- 猪料原料占比
- 运费
- 重要部位冻品进口
- 周&月度-三元母猪价格
- 减产能较2018年7月30日
- 新增猪场
- 历史出栏体重

### 3.3 月度数据Sheet（15个）

- 月度-商品猪出栏量
- 月度-能繁母猪存栏量
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

**注意**: 所有周度数据的详细表结构定义请参考 `docs/YONGYI_WEEKLY_COMPLETE_TABLE_SCHEMA.md`

## 4. DCE期货 (DCE DAILY) - 待分析

### 4.1 期货日度数据 (dce_daily_futures)

**表结构**（基于现有fact_futures_daily）：
```sql
-- 使用现有的fact_futures_daily表，无需新建
```

**列映射规则**：
- 使用现有的futures_ingestor逻辑

## 5. DCE期权 (DCE DAILY) - 待分析

### 5.1 期权日度数据 (dce_daily_options)

**表结构**（基于现有fact_options_daily）：
```sql
-- 使用现有的fact_options_daily表，无需新建
```

**列映射规则**：
- 使用现有的options_ingestor逻辑

## 5. 日期跨列识别总结

需要特别处理的日期跨列情况：

1. **出栏价**: 日期跨4列（规模场、小散户、均价、涨跌）
2. **散户标肥价差**: 日期跨3列（场散户标重猪、150公斤左右较标猪、175公斤左右较标猪）
3. **市场主流标猪肥猪价格**: 日期跨5列（标猪均价、标猪体重段、90-100kg均价、130-140kg均价、150kg左右均价）

这些都需要使用`WIDE_DATE_GROUPED_SUBCOLS`解析器，通过`extract_date_grouped_subcols`函数识别日期跨列结构。

## 6. 列映射配置格式

每个sheet的`table_config`需要包含：

```json
{
  "table_name": "yongyi_daily_out_price",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true
    },
    "region_code": {
      "source": "row_dim.province",
      "type": "VARCHAR(32)",
      "normalizer": "normalize_province_name",
      "required": true
    },
    "scale": {
      "source": "subheader",
      "type": "VARCHAR(16)",
      "value_map": {
        "规模场": "scale_farm",
        "小散户": "scatter",
        "均价": "avg"
      },
      "required": true
    },
    "price": {
      "source": "value",
      "condition": "subheader in [规模场, 小散户, 均价]",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "change_amount": {
      "source": "value",
      "condition": "subheader = 涨跌",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    }
  },
  "unique_key": ["trade_date", "region_code", "scale"]
}
```

## 6. 待确认问题

1. **出栏价sheet**: "去年同期"、"同比"、"明日预计"的具体列位置和结构（可能是另一个日期组）
2. **钢联各sheet**: 需要确认列名提取规则是否准确
3. **涌益周度数据**: 56个sheet中部分sheet的结构需要进一步详细分析，特别是月度数据sheet
4. **DCE期货/期权**: 需要分析文件结构

## 7. 下一步

1. ✅ 确认钢联7个sheet的表结构和列映射规则
2. ✅ 确认涌益日度8个sheet的表结构和列映射规则
3. ✅ 确认涌益周度56个sheet的列表和基本结构
4. ⏳ 为涌益周度数据创建详细的表结构定义（部分完成，见YONGYI_WEEKLY_COMPLETE_TABLE_SCHEMA.md）
5. ⏳ 创建完整的Alembic迁移脚本，定义所有表（已创建部分）
6. ⏳ 更新ingest_profile配置文件，添加table_config
7. ⏳ 测试导入功能

## 8. 表数量统计

- **钢联日度**: 7个表
- **涌益日度**: 8个表
- **涌益周度**: 56个表（需要进一步详细定义）
- **DCE期货**: 使用现有表
- **DCE期权**: 使用现有表
- **总计**: 约71个独立表
