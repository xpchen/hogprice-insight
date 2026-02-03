# 完整列映射配置

本文档包含所有sheet的完整列映射配置，可直接用于`ingest_profile`的`table_config`。

## 1. 钢联价格模板 (GANGLIAN DAILY)

### 1.1 分省区猪价

```json
{
  "table_name": "ganglian_daily_province_price",
  "column_mapping": {
    "trade_date": {
      "source": "row_dim.date",
      "type": "DATE",
      "required": true
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
      "type": "VARCHAR(32)"
    },
    "updated_at_time": {
      "source": "meta.update_time_row",
      "type": "DATETIME"
    }
  },
  "unique_key": ["trade_date", "region_code", "indicator_name"]
}
```

### 1.2 集团企业出栏价

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

### 1.3-1.7 其他钢联表

类似结构，根据具体sheet调整`extract_pattern`和字段名。

## 2. 涌益日度数据 (YONGYI DAILY)

### 2.1 出栏价

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
      "cleaner": "clean_numeric_value"
    },
    "yoy_ratio": {
      "source": "value",
      "condition": "subheader = 同比",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "tomorrow_forecast": {
      "source": "value",
      "condition": "subheader = 明日预计",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    }
  },
  "unique_key": ["trade_date", "region_code", "scale"]
}
```

### 2.2 价格+宰量

```json
{
  "table_name": "yongyi_daily_price_slaughter",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true
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

### 2.3 散户标肥价差

```json
{
  "table_name": "yongyi_daily_scatter_fat_spread",
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

### 2.4 各省份均价

```json
{
  "table_name": "yongyi_daily_province_avg",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true
    },
    "region_code": {
      "source": "column_name",
      "type": "VARCHAR(32)",
      "normalizer": "normalize_province_name",
      "required": true
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

### 2.5 市场主流标猪肥猪价格

```json
{
  "table_name": "yongyi_daily_market_std_fat_price",
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
    "std_pig_avg_price": {
      "source": "value",
      "condition": "subheader = 标猪均价",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "std_pig_weight_band": {
      "source": "value",
      "condition": "subheader = 标猪体重段",
      "type": "VARCHAR(32)"
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

### 2.6 屠宰企业日度屠宰量

```json
{
  "table_name": "yongyi_daily_slaughter_vol",
  "column_mapping": {
    "trade_date": {
      "source": "column_name",
      "type": "DATE",
      "required": true
    },
    "region_code": {
      "source": "row_dim.province",
      "type": "VARCHAR(32)",
      "normalizer": "normalize_province_name",
      "required": true
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

### 2.7 市场主流标猪肥猪均价方便作图

```json
{
  "table_name": "yongyi_daily_market_avg_convenient",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true
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

### 2.8 交割地市出栏价

```json
{
  "table_name": "yongyi_daily_delivery_city_price",
  "column_mapping": {
    "trade_date": {
      "source": "date_col",
      "type": "DATE",
      "required": true
    },
    "region_code": {
      "source": "meta.province_row",
      "type": "VARCHAR(32)",
      "normalizer": "normalize_province_name",
      "required": true
    },
    "location_code": {
      "source": "column_name",
      "type": "VARCHAR(32)",
      "required": true
    },
    "city_price": {
      "source": "value",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "premium_lh2505_plus": {
      "source": "meta.premium_row_2",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "premium_lh2409_lh2503": {
      "source": "meta.premium_row_3",
      "type": "DECIMAL(18,6)",
      "cleaner": "clean_numeric_value"
    },
    "weight_band": {
      "source": "meta.weight_row",
      "type": "VARCHAR(64)"
    }
  },
  "unique_key": ["trade_date", "location_code"]
}
```

## 3. DCE期货和期权

DCE期货和期权使用现有的`fact_futures_daily`和`fact_options_daily`表，无需新建表或列映射配置。

## 4. 总结

- **钢联**: 7个表，使用`NARROW_DATE_ROWS`解析器
- **涌益日度**: 8个表，部分使用`WIDE_DATE_GROUPED_SUBCOLS`解析器（日期跨列）
- **DCE**: 使用现有表，无需新建

所有表都包含`batch_id`外键，支持数据追溯和批次管理。
