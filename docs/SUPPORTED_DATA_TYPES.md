# 系统支持的数据类型总结

## 📊 数据源类型（5种）

### 1. **LH_FTR** - 生猪期货日历史行情
- **文件格式**: Excel (.xlsx)
- **特征**: 包含"日历史行情"sheet，字段包含"合约"等
- **数据内容**:
  - 合约代码（如 lh2603）
  - 交易日期
  - 开盘价、最高价、最低价、收盘价、结算价
  - 成交量、持仓量、成交额
- **存储表**: `fact_futures_daily`, `dim_contract`
- **导入器**: `futures_ingestor.py`

### 2. **LH_OPT** - 生猪期权日历史行情
- **文件格式**: Excel (.xlsx)
- **特征**: 包含"日历史行情"sheet，字段包含"delta"、"iv"、"行权"等
- **数据内容**:
  - 期权代码（如 lh2603-C-10000）
  - 标的合约、期权类型（C/P）、行权价
  - 交易日期
  - 开盘价、最高价、最低价、收盘价、结算价
  - Delta、IV（隐含波动率）
  - 成交量、持仓量、成交额、行权量
- **存储表**: `fact_options_daily`, `dim_option`
- **导入器**: `options_ingestor.py`

### 3. **YONGYI_DAILY** - 涌益咨询日度数据
- **文件格式**: Excel (.xlsx)
- **特征**: 文件名包含"涌益"和"日度"，或sheet名称包含"价格"、"屠宰"、"价差"等
- **数据结构**: 
  - **窄表**: 标准表格格式（日期列 + 数据列）
  - **宽表**: 日期跨列格式（日期作为列标题）
- **支持Sheet示例**:
  - 价格+宰量
  - 各省份均价
  - 屠宰企业日度屠宰量
  - 散户标肥价差
- **存储表**: `fact_indicator_ts`, `dim_indicator`, `dim_region`
- **导入器**: `yongyi_daily_ingestor.py`

### 4. **YONGYI_WEEKLY** - 涌益咨询周度数据
- **文件格式**: Excel (.xlsx)
- **特征**: 文件名包含"涌益"和"周度"，或sheet名称包含"周度"
- **数据结构**: 
  - 多行表头（合并单元格）
  - 宽表格式（日期跨列）
- **支持Sheet示例**:
  - 周度-商品猪出栏价
  - 周度-体重
  - 周度-屠宰厂宰前活猪重
  - 周度-养殖利润最新
  - 育肥全价料价格
  - 周度-冻品库存
  - 周度-毛白价差
- **存储表**: `fact_indicator_ts`, `dim_indicator`, `dim_region`
- **导入器**: `yongyi_weekly_ingestor.py`

### 5. **LEGACY** - 旧格式（向后兼容）
- **说明**: 用于识别旧版本的数据格式
- **状态**: 可通过数据迁移服务迁移到新格式

---

## 📈 指标主题分类（7大类）

### 1. **价格** (Price)
- `hog_price_nation` - 全国出栏均价（日频）
- `hog_price_province` - 省份出栏均价（日频）
- `hog_price_out_week` - 商品猪出栏价（周频）
- `std_price_retail` - 标重猪价（散户标）

### 2. **屠宰** (Slaughter)
- `slaughter_daily` - 日度屠宰量（日频）
- `slaughter_weekly` - 周度屠宰量（周频）

### 3. **均重** (Weight)
- `hog_weight_pre_slaughter` - 宰前均重（日频/周频）
- `hog_weight_out_week` - 出栏均重（周频）
- `hog_weight_scale` - 规模场出栏均重（周频）
- `hog_weight_retail` - 散户出栏均重（周频）
- `hog_weight_90kg` - 90kg出栏占比（周频）
- `hog_weight_150kg` - 150kg出栏占比（周频）

### 4. **价差** (Spread)
- `spread_std_fat` - 标肥价差（日频）
- `spread_region` - 区域价差（日频）
- `spread_hog_carcass` - 毛白价差（周频）
- `spread_150_std` - 150kg较标猪价差（日频）
- `spread_175_std` - 175kg较标猪价差（日频）

### 5. **冻品** (Frozen)
- `frozen_capacity_rate` - 冻品库容率（周频）

### 6. **产业链** (Industry Chain)
- `profit_breeding` - 养殖利润（周频）
- `feed_price_full` - 全价料价格（周频）

### 7. **期货/期权** (Futures/Options)
- 期货合约数据（日频）
- 期权合约数据（日频）

---

## 🗓️ 数据频率（2种）

### 1. **D** - 日频 (Daily)
- 每日更新
- 支持农历对齐
- 适用于：价格、屠宰量、价差等

### 2. **W** - 周频 (Weekly)
- 每周更新
- 适用于：均重、利润、冻品库存等

---

## 🌍 区域层级（3级）

### 0级 - 全国
- `NATION` - 全国

### 1级 - 大区（7个）
- `NORTHEAST` - 东北
- `NORTH` - 华北
- `EAST` - 华东
- `CENTRAL` - 华中
- `SOUTH` - 华南
- `SOUTHWEST` - 西南
- `NORTHWEST` - 西北

### 2级 - 省份（34个）
- `BEIJING` - 北京
- `TIANJIN` - 天津
- `HEBEI` - 河北
- `SHANXI` - 山西
- `INNER_MONGOLIA` - 内蒙古
- `LIAONING` - 辽宁
- `JILIN` - 吉林
- `HEILONGJIANG` - 黑龙江
- `SHANGHAI` - 上海
- `JIANGSU` - 江苏
- `ZHEJIANG` - 浙江
- `ANHUI` - 安徽
- `FUJIAN` - 福建
- `JIANGXI` - 江西
- `SHANDONG` - 山东
- `HENAN` - 河南
- `HUBEI` - 湖北
- `HUNAN` - 湖南
- `GUANGDONG` - 广东
- `GUANGXI` - 广西
- `HAINAN` - 海南
- `CHONGQING` - 重庆
- `SICHUAN` - 四川
- `GUIZHOU` - 贵州
- `YUNNAN` - 云南
- `TIBET` - 西藏
- `SHAANXI` - 陕西
- `GANSU` - 甘肃
- `QINGHAI` - 青海
- `NINGXIA` - 宁夏
- `XINJIANG` - 新疆

---

## 📋 指标映射配置

系统通过 `indicator_mappings.json` 配置文件，将Excel中的Sheet名称和字段名称映射到标准化的指标代码。

**当前配置的映射数量**: 12个主要映射规则（支持通配符和占位符）

**映射规则示例**:
```json
{
  "sheet_name": "价格+宰量",
  "field_name": "全国均价",
  "indicator_code": "hog_price_nation",
  "freq": "D",
  "region_code": "NATION",
  "unit": "元/公斤",
  "topic": "价格"
}
```

---

## 🔧 数据源代码标识

- `YONGYI` - 涌益咨询数据
- `DCE` - 大连商品交易所（期货/期权）
- `LEGACY` - 旧系统数据（迁移来源）

---

## 📊 统计总结

| 类别 | 数量 | 说明 |
|------|------|------|
| **数据源类型** | 5种 | LH_FTR, LH_OPT, YONGYI_DAILY, YONGYI_WEEKLY, LEGACY |
| **指标主题** | 7大类 | 价格、屠宰、均重、价差、冻品、产业链、期货/期权 |
| **数据频率** | 2种 | 日频(D)、周频(W) |
| **区域层级** | 3级 | 全国、大区、省份 |
| **大区数量** | 7个 | 东北、华北、华东、华中、华南、西南、西北 |
| **省份数量** | 34个 | 全国34个省级行政区 |
| **基础指标** | 16个 | 系统初始化时创建的基础指标 |
| **指标映射规则** | 12+ | 支持通配符和占位符的动态映射 |

---

## 🎯 扩展性

系统设计支持轻松扩展：
1. **新增数据源**: 添加新的导入器和模板检测规则
2. **新增指标**: 在 `indicator_mappings.json` 中添加映射规则
3. **新增区域**: 在 `init_base_data.py` 中添加区域定义
4. **新增主题**: 在 `dim_indicator.topic` 中添加新主题分类

---

**最后更新**: 2026-02-01
