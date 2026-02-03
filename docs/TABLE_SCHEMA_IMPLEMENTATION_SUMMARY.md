# 表结构定义和列映射规则实施总结

## 完成情况

✅ **所有任务已完成**

1. ✅ 确认钢联7个sheet的详细列结构和列名
2. ✅ 确认涌益日度8个sheet的详细列结构
3. ✅ 分析DCE期货和期权文件的结构
4. ✅ 创建完整的Alembic迁移脚本
5. ✅ 创建完整的列映射配置

## 文件清单

### 1. 分析结果文件

- `docs/sheet_columns_analysis.json` - Excel文件结构分析结果
- `docs/dce_files_analysis.json` - DCE期货和期权文件分析结果

### 2. 设计文档

- `docs/FINAL_TABLE_SCHEMA_AND_COLUMN_MAPPING.md` - 最终表结构定义和列映射规则
- `docs/COMPLETE_COLUMN_MAPPING_CONFIG.md` - 完整列映射配置（可直接使用）

### 3. 数据库迁移脚本

- `backend/alembic/versions/e1f2a3b4c5d6_create_all_sheet_based_tables.py` - 创建所有15个表的迁移脚本

### 4. 分析工具脚本

- `backend/scripts/analyze_sheet_columns.py` - 详细分析sheet列结构
- `backend/scripts/analyze_out_price_sheet.py` - 专门分析出栏价sheet
- `backend/scripts/analyze_dce_files.py` - 分析DCE文件结构

## 表结构汇总

### 钢联日度表（7个）

1. `ganglian_daily_province_price` - 分省区猪价
2. `ganglian_daily_group_enterprise_price` - 集团企业出栏价
3. `ganglian_daily_delivery_warehouse_price` - 交割库出栏价
4. `ganglian_daily_region_spread` - 区域价差
5. `ganglian_daily_fat_std_spread` - 肥标价差
6. `ganglian_daily_live_white_spread` - 毛白价差
7. `ganglian_weekly_farm_profit` - 养殖利润（周度）

### 涌益日度表（8个）

1. `yongyi_daily_out_price` - 出栏价
2. `yongyi_daily_price_slaughter` - 价格+宰量
3. `yongyi_daily_scatter_fat_spread` - 散户标肥价差
4. `yongyi_daily_province_avg` - 各省份均价
5. `yongyi_daily_market_std_fat_price` - 市场主流标猪肥猪价格
6. `yongyi_daily_slaughter_vol` - 屠宰企业日度屠宰量
7. `yongyi_daily_market_avg_convenient` - 市场主流标猪肥猪均价方便作图
8. `yongyi_daily_delivery_city_price` - 交割地市出栏价

### DCE表（使用现有表）

- `fact_futures_daily` - 期货日度数据（已存在）
- `fact_options_daily` - 期权日度数据（已存在）

## 日期跨列处理

以下sheet需要特殊处理日期跨列：

1. **出栏价**: 日期跨4列（规模场、小散户、均价、涨跌）
2. **散户标肥价差**: 日期跨3列（场散户标重猪、150公斤左右较标猪、175公斤左右较标猪）
3. **市场主流标猪肥猪价格**: 日期跨5列（标猪均价、标猪体重段、90-100kg均价、130-140kg均价、150kg左右均价）

这些sheet需要使用`WIDE_DATE_GROUPED_SUBCOLS`解析器。

## 待确认问题

1. **出栏价sheet**: "去年同期"、"同比"、"明日预计"的具体列位置和结构（可能是另一个日期组，需要进一步分析）

## 下一步

1. 运行Alembic迁移脚本创建所有表
2. 更新`ingest_profile`配置文件，添加`table_config`
3. 测试导入功能
4. 确认"去年同期"、"同比"、"明日预计"的列结构并更新配置

## 使用说明

### 1. 运行迁移脚本

```bash
cd backend
alembic upgrade head
```

### 2. 更新ingest_profile配置

参考`docs/COMPLETE_COLUMN_MAPPING_CONFIG.md`中的配置，更新对应的`ingest_profile` JSON文件。

### 3. 测试导入

使用现有的导入接口测试各个sheet的数据导入功能。

## 注意事项

1. 所有表都包含`batch_id`外键，用于数据追溯
2. 所有表都有唯一键约束，防止重复数据
3. 日期跨列的sheet需要正确配置解析器和列映射
4. 列映射中的`condition`字段用于过滤和条件赋值
