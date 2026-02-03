# 基于Sheet的独立表架构设计文档

## 概述

本文档描述了将统一写入`fact_observation`表的架构重构为每个sheet对应独立表的架构设计。

## 架构优势

1. **存储压力分散**：每个表独立存储，互不影响
2. **查询性能好**：每个表有针对性索引，无需JSON过滤
3. **表结构清晰**：每个表结构对应sheet结构，易于理解
4. **扩展性强**：新增sheet只需新增表，不影响现有表

## 表命名规范

格式：`{source_code}_{dataset_type}_{sheet_name_snake_case}`

示例：
- `yongyi_daily_price_slaughter` - 价格+宰量
- `yongyi_daily_out_price` - 出栏价
- `yongyi_weekly_frozen_inventory` - 冻品库存

## 实施状态

- ✅ 表结构设计完成
- ✅ Alembic迁移脚本已创建
- ✅ Sheet表映射服务已实现
- ✅ 列映射转换器已实现
- ✅ Sheet表导入器已实现
- ✅ unified_ingestor已集成新架构
- ✅ 配置文件已扩展table_config
- ⏳ 测试验证中

## 使用说明

### 1. 运行迁移

```bash
cd backend
alembic upgrade head
```

### 2. 配置table_config

在`ingest_profile`配置文件中为每个sheet添加`table_config`：

```json
{
  "sheet_name": "出栏价",
  "table_name": "yongyi_daily_out_price",
  "table_config": {
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
      }
    },
    "unique_key": ["trade_date", "region_code", "scale"]
  }
}
```

### 3. 导入数据

使用`unified_import`函数导入数据，系统会自动检测是否有`table_config`：
- 如果有`table_config`，导入到独立表
- 如果没有，导入到`fact_observation`（向后兼容）

## 注意事项

1. 表名长度限制：MySQL表名最长64字符
2. 唯一键设计：每个表需要设计合适的唯一键
3. 向后兼容：保持Parser和unified_import接口不变
