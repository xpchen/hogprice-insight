# 最终表结构定义和列映射规则

## 概述

本文档包含所有sheet的完整表结构定义和列映射规则，基于实际Excel文件分析结果。

## 1. 钢联价格模板 (GANGLIAN DAILY) - 7个表

### 1.1 分省区猪价 (ganglian_daily_province_price)

**表名**: `ganglian_daily_province_price`

**表结构**:
```sql
CREATE TABLE ganglian_daily_province_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    indicator_name VARCHAR(128),
    value DECIMAL(18, 6),
    unit VARCHAR(32),
    updated_at_time DATETIME,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region_indicator (trade_date, region_code, indicator_name),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射配置**:
```json
{
  "table_name": "ganglian_daily_province_price",
  "column_mapping": {
    "trade_date": {
      "source": "row_dim.date",
      "type": "DATE",
      "required": true,
      "note": "第1列，第4行起为日期"
    },
    "region_code": {
      "source": "column_name",
      "type": "VARCHAR(32)",
      "extract_pattern": "商品猪：出栏均价：(.*?)（日）",
      "normalizer": "normalize_province_name",
      "required": true
    },
    "indicator_name": {
      "source": "column_name",
      "type": "VARCHAR(128)",
      "extract_pattern": "(商品猪：出栏均价)",
      "required": false
    },
    "value": {
      "source": "value",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "unit": {
      "source": "meta.unit_row",
      "type": "VARCHAR(32)",
      "note": "第2行"
    },
    "updated_at_time": {
      "source": "meta.update_time_row",
      "type": "DATETIME",
      "note": "第3行"
    }
  },
  "unique_key": ["trade_date", "region_code", "indicator_name"]
}
```

### 1.2 集团企业出栏价 (ganglian_daily_group_enterprise_price)

**表名**: `ganglian_daily_group_enterprise_price`

**表结构**:
```sql
CREATE TABLE ganglian_daily_group_enterprise_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32),
    enterprise_name VARCHAR(128) NOT NULL,
    value DECIMAL(18, 6),
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

**列映射配置**:
```json
{
  "table_name": "ganglian_daily_group_enterprise_price",
  "column_mapping": {
    "trade_date": {
      "source": "row_dim.date",
      "type": "DATE",
      "required": true
    },
    "region_code": {
      "source": "column_name",
      "type": "VARCHAR(32)",
      "extract_pattern": "出栏价：(.*?)：",
      "normalizer": "normalize_province_name"
    },
    "enterprise_name": {
      "source": "column_name",
      "type": "VARCHAR(128)",
      "extract_pattern": "：(.*?)（日）$",
      "required": true
    },
    "value": {
      "source": "value",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "unit": {
      "source": "meta.unit_row",
      "type": "VARCHAR(32)"
    },
    "updated_at_time": {
      "source": "meta.update_time_row",
      "type": "DATETIME"
    }
  },
  "unique_key": ["trade_date", "enterprise_name", "region_code"]
}
```

### 1.3 交割库出栏价 (ganglian_daily_delivery_warehouse_price)

**表名**: `ganglian_daily_delivery_warehouse_price`

**表结构**:
```sql
CREATE TABLE ganglian_daily_delivery_warehouse_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32),
    warehouse_name VARCHAR(128) NOT NULL,
    value DECIMAL(18, 6),
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

**列映射配置**: 类似集团企业出栏价，但提取交割库名称

### 1.4 区域价差 (ganglian_daily_region_spread)

**表名**: `ganglian_daily_region_spread`

**表结构**:
```sql
CREATE TABLE ganglian_daily_region_spread (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    spread_type VARCHAR(64) NOT NULL,
    value DECIMAL(18, 6),
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

### 1.5 肥标价差 (ganglian_daily_fat_std_spread)

**表名**: `ganglian_daily_fat_std_spread`

**表结构**:
```sql
CREATE TABLE ganglian_daily_fat_std_spread (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32),
    value DECIMAL(18, 6),
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

### 1.6 毛白价差 (ganglian_daily_live_white_spread)

**表名**: `ganglian_daily_live_white_spread`

**表结构**:
```sql
CREATE TABLE ganglian_daily_live_white_spread (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32),
    value DECIMAL(18, 6),
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

### 1.7 养殖利润（周度） (ganglian_weekly_farm_profit)

**表名**: `ganglian_weekly_farm_profit`

**表结构**:
```sql
CREATE TABLE ganglian_weekly_farm_profit (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    profit_type VARCHAR(64) NOT NULL,
    value DECIMAL(18, 6),
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

## 2. 涌益日度数据 (YONGYI DAILY) - 8个sheet

### 2.1 出栏价 (yongyi_daily_out_price)

**表名**: `yongyi_daily_out_price`

**表结构**:
```sql
CREATE TABLE yongyi_daily_out_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    scale VARCHAR(16) NOT NULL,
    price DECIMAL(18, 6),
    change_amount DECIMAL(18, 6),
    last_year_price DECIMAL(18, 6),
    yoy_ratio DECIMAL(18, 6),
    tomorrow_forecast DECIMAL(18, 6),
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

**列映射配置**:
```json
{
  "table_name": "yongyi_daily_out_price",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true,
      "note": "第1行，跨4列（规模场、小散户、均价、涨跌）"
    },
    "region_code": {
      "source": "row_dim.province",
      "type": "VARCHAR(32)",
      "normalizer": "normalize_province_name",
      "required": true,
      "note": "第1列，第3行起"
    },
    "scale": {
      "source": "subheader",
      "type": "VARCHAR(16)",
      "value_map": {
        "规模场": "scale_farm",
        "小散户": "scatter",
        "均价": "avg",
        "涨跌": "change"
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
    },
    "last_year_price": {
      "source": "value",
      "condition": "subheader = 去年同期",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value",
      "note": "需要确认列位置"
    },
    "yoy_ratio": {
      "source": "value",
      "condition": "subheader = 同比",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value",
      "note": "需要确认列位置"
    },
    "tomorrow_forecast": {
      "source": "value",
      "condition": "subheader = 明日预计",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value",
      "note": "需要确认列位置"
    }
  },
  "unique_key": ["trade_date", "region_code", "scale"]
}
```

**日期跨列**: 日期在第1行，跨4列（规模场、小散户、均价、涨跌）

**注意**: "去年同期"、"同比"、"明日预计"可能是另一个日期组，需要进一步确认结构

### 2.2 价格+宰量 (yongyi_daily_price_slaughter)

**表名**: `yongyi_daily_price_slaughter`

**表结构**:
```sql
CREATE TABLE yongyi_daily_price_slaughter (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    nation_avg_price DECIMAL(18, 6),
    slaughter_total_1 INT,
    slaughter_total_2 INT,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date (trade_date),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射配置**:
```json
{
  "table_name": "yongyi_daily_price_slaughter",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true,
      "note": "第1列"
    },
    "nation_avg_price": {
      "source": "value",
      "condition": "metric_key == YY_D_PRICE_NATION_AVG",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "slaughter_total_1": {
      "source": "value",
      "condition": "metric_key == YY_D_SLAUGHTER_TOTAL_1",
      "type": "INTEGER",
      "cleaner": "clean_numeric_value"
    },
    "slaughter_total_2": {
      "source": "value",
      "condition": "metric_key == YY_D_SLAUGHTER_TOTAL_2",
      "type": "INTEGER",
      "cleaner": "clean_numeric_value"
    }
  },
  "unique_key": ["trade_date"]
}
```

### 2.3 散户标肥价差 (yongyi_daily_scatter_fat_spread)

**表名**: `yongyi_daily_scatter_fat_spread`

**表结构**:
```sql
CREATE TABLE yongyi_daily_scatter_fat_spread (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    scatter_std_price DECIMAL(18, 6),
    spread_150_vs_std DECIMAL(18, 6),
    spread_175_vs_std DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region (trade_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射配置**:
```json
{
  "table_name": "yongyi_daily_scatter_fat_spread",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true,
      "note": "第1行，跨3列"
    },
    "region_code": {
      "source": "row_dim.province",
      "type": "VARCHAR(32)",
      "normalizer": "normalize_province_name",
      "required": true
    },
    "scatter_std_price": {
      "source": "value",
      "condition": "subheader = 场散户标重猪",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "spread_150_vs_std": {
      "source": "value",
      "condition": "subheader = 150公斤左右较标猪",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "spread_175_vs_std": {
      "source": "value",
      "condition": "subheader = 175公斤左右较标猪",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    }
  },
  "unique_key": ["trade_date", "region_code"]
}
```

**日期跨列**: 日期在第1行，跨3列（场散户标重猪、150公斤左右较标猪、175公斤左右较标猪）

### 2.4 各省份均价 (yongyi_daily_province_avg)

**表名**: `yongyi_daily_province_avg`

**表结构**:
```sql
CREATE TABLE yongyi_daily_province_avg (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    avg_price DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region (trade_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射配置**:
```json
{
  "table_name": "yongyi_daily_province_avg",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true,
      "note": "第1列"
    },
    "region_code": {
      "source": "column_name",
      "type": "VARCHAR(32)",
      "normalizer": "normalize_province_name",
      "required": true,
      "note": "从列名提取省份"
    },
    "avg_price": {
      "source": "value",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    }
  },
  "unique_key": ["trade_date", "region_code"]
}
```

### 2.5 市场主流标猪肥猪价格 (yongyi_daily_market_std_fat_price)

**表名**: `yongyi_daily_market_std_fat_price`

**表结构**:
```sql
CREATE TABLE yongyi_daily_market_std_fat_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    std_pig_avg_price DECIMAL(18, 6),
    std_pig_weight_band VARCHAR(32),
    price_90_100 DECIMAL(18, 6),
    price_130_140 DECIMAL(18, 6),
    price_150_around DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date_region (trade_date, region_code),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date),
    INDEX idx_region (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射配置**:
```json
{
  "table_name": "yongyi_daily_market_std_fat_price",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true,
      "note": "第1行，跨5列"
    },
    "region_code": {
      "source": "row_dim.province",
      "type": "VARCHAR(32)",
      "normalizer": "normalize_province_name",
      "required": true
    },
    "std_pig_avg_price": {
      "source": "value",
      "condition": "subheader = 标猪均价",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "std_pig_weight_band": {
      "source": "value",
      "condition": "subheader = 标猪体重段",
      "type": "VARCHAR(32)",
      "note": "文本字段"
    },
    "price_90_100": {
      "source": "value",
      "condition": "subheader = 90-100kg均价",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "price_130_140": {
      "source": "value",
      "condition": "subheader = 130-140kg均价",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "price_150_around": {
      "source": "value",
      "condition": "subheader = 150kg左右均价",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    }
  },
  "unique_key": ["trade_date", "region_code"]
}
```

**日期跨列**: 日期在第1行，跨5列（标猪均价、标猪体重段、90-100kg均价、130-140kg均价、150kg左右均价）

### 2.6 屠宰企业日度屠宰量 (yongyi_daily_slaughter_vol)

**表名**: `yongyi_daily_slaughter_vol`

**表结构**:
```sql
CREATE TABLE yongyi_daily_slaughter_vol (
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

**列映射配置**:
```json
{
  "table_name": "yongyi_daily_slaughter_vol",
  "column_mapping": {
    "trade_date": {
      "source": "column_name",
      "type": "DATE",
      "required": true,
      "note": "日期作为列名"
    },
    "region_code": {
      "source": "row_dim.province",
      "type": "VARCHAR(32)",
      "normalizer": "normalize_province_name",
      "required": true,
      "note": "第1列"
    },
    "slaughter_volume": {
      "source": "value",
      "type": "INTEGER",
      "cleaner": "clean_numeric_value"
    }
  },
  "unique_key": ["trade_date", "region_code"]
}
```

**Excel结构**: 第1列是省份，第2列起是日期列

### 2.7 市场主流标猪肥猪均价方便作图 (yongyi_daily_market_avg_convenient)

**表名**: `yongyi_daily_market_avg_convenient`

**表结构**:
```sql
CREATE TABLE yongyi_daily_market_avg_convenient (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    nation_avg_price DECIMAL(18, 6),
    price_90_100 DECIMAL(18, 6),
    price_130_140 DECIMAL(18, 6),
    price_150_170 DECIMAL(18, 6),
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    FOREIGN KEY (batch_id) REFERENCES import_batch(id) ON DELETE SET NULL,
    UNIQUE KEY uk_date (trade_date),
    INDEX idx_batch (batch_id),
    INDEX idx_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**列映射配置**:
```json
{
  "table_name": "yongyi_daily_market_avg_convenient",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true,
      "note": "第1列"
    },
    "nation_avg_price": {
      "source": "value",
      "condition": "column_name = 全国均价",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "price_90_100": {
      "source": "value",
      "condition": "column_name = 90-100kg均价",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "price_130_140": {
      "source": "value",
      "condition": "column_name = 130-140kg均价",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "price_150_170": {
      "source": "value",
      "condition": "column_name = 150-170kg均价",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    }
  },
  "unique_key": ["trade_date"]
}
```

### 2.8 交割地市出栏价 (yongyi_daily_delivery_city_price)

**表名**: `yongyi_daily_delivery_city_price`

**表结构**:
```sql
CREATE TABLE yongyi_daily_delivery_city_price (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id BIGINT,
    trade_date DATE NOT NULL,
    region_code VARCHAR(32) NOT NULL,
    location_code VARCHAR(32) NOT NULL,
    city_price DECIMAL(18, 6),
    premium_lh2505_plus DECIMAL(18, 6),
    premium_lh2409_lh2503 DECIMAL(18, 6),
    weight_band VARCHAR(64),
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

**列映射配置**:
```json
{
  "table_name": "yongyi_daily_delivery_city_price",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true,
      "note": "第1列"
    },
    "region_code": {
      "source": "meta.province_row",
      "type": "VARCHAR(32)",
      "normalizer": "normalize_province_name",
      "required": true,
      "note": "第1行，合并单元格"
    },
    "location_code": {
      "source": "column_name",
      "type": "VARCHAR(32)",
      "required": true,
      "note": "第5行，城市名称"
    },
    "city_price": {
      "source": "value",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "premium_lh2505_plus": {
      "source": "meta.premium_row_2",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value",
      "note": "第2行"
    },
    "premium_lh2409_lh2503": {
      "source": "meta.premium_row_3",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value",
      "note": "第3行"
    },
    "weight_band": {
      "source": "meta.weight_row",
      "type": "VARCHAR(64)",
      "note": "第4行，文本"
    }
  },
  "unique_key": ["trade_date", "location_code"]
}
```

## 3. 日期跨列总结

需要特别处理的日期跨列情况：

1. **出栏价**: 日期跨4列（规模场、小散户、均价、涨跌）
2. **散户标肥价差**: 日期跨3列（场散户标重猪、150公斤左右较标猪、175公斤左右较标猪）
3. **市场主流标猪肥猪价格**: 日期跨5列（标猪均价、标猪体重段、90-100kg均价、130-140kg均价、150kg左右均价）

## 4. 待确认问题

1. **出栏价sheet**: "去年同期"、"同比"、"明日预计"的具体列位置和结构（可能是另一个日期组）
2. **钢联各sheet**: 需要确认列名提取规则是否准确
3. **DCE期货/期权**: 需要分析文件结构

## 5. 下一步

1. 确认"去年同期"、"同比"、"明日预计"的列结构
2. 分析DCE期货和期权文件
3. 创建完整的Alembic迁移脚本
4. 创建完整的列映射配置文件
