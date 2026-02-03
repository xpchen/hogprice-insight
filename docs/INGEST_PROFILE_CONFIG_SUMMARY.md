# 涌益数据 ingest_profile 配置总结

> 本文档明确：每个 sheet 的 parser 类型、metric/tags 规范、交割城市列表、指标抽取规则

---

## 1. Parser 类型映射（P1~P6）

根据改进计划文档，6 个通用解析器对应关系：

| Parser ID | Parser 名称 | 对应配置中的 parser 值 | 适用表型 |
|-----------|------------|----------------------|---------|
| P1 | `wide_date_columns` | `NARROW_DATE_ROWS_WIDE_PROVINCES` | 日期行 + 省份列 |
| P2 | `wide_province_columns` | `WIDE_PROVINCE_ROWS_DATE_COLS` | 日期列 + 省份行（屠宰量） |
| P3 | `multiheader_date_group` | `WIDE_DATE_GROUPED_SUBCOLS` | 日期跨列 + 子列（出栏价/标肥价差） |
| P4 | `week_start_end_province_wide` | `PERIOD_START_END_WIDE_PROVINCE` | 周起止 + 省份列（周度多数） |
| P5 | `week_start_end_dim_wide` | `PERIOD_START_END_MULTI_COL_WITH_GROUP_HEADERS` | 周起止 + 规模段/模式列（利润最新） |
| P6 | `delivery_city_matrix` | `DELIVERY_CITY_MATRIX_WITH_META` | 交割地市（省份分组 + 元数据 + 城市矩阵） |

---

## 2. 涌益日度（YONGYI_DAILY_V1）- 8 个 Sheet 配置

### 2.1 Sheet 列表与 Parser 映射

| Sheet 名称 | Parser | Parser ID | 说明 |
|-----------|--------|-----------|------|
| 价格+宰量 | `NARROW_DATE_ROWS` | P1 变体 | 窄表：日期行，多指标列 |
| 各省份均价 | `NARROW_DATE_ROWS_WIDE_PROVINCES` | P1 | 日期行 + 省份列 |
| 屠宰企业日度屠宰量 | `WIDE_PROVINCE_ROWS_DATE_COLS` | P2 | 省份行 + 日期列 |
| 出栏价 | `WIDE_DATE_GROUPED_SUBCOLS` | P3 | 日期跨列 + 子列（规模场/小散/均价/涨跌） |
| 散户标肥价差 | `WIDE_DATE_GROUPED_SUBCOLS` | P3 | 日期跨列 + 子列（标重/150kg/175kg/情绪） |
| 市场主流标猪肥猪价格 | `WIDE_DATE_GROUPED_SUBCOLS` | P3 | 日期跨列 + 子列（标猪/体重段/各体重段均价） |
| 市场主流标猪肥猪均价方便作图 | `NARROW_DATE_ROWS` | P1 变体 | 窄表：日期行，多指标列（全国） |
| 交割地市出栏价 | `DELIVERY_CITY_MATRIX_WITH_META` | P6 | 省份分组 + 升贴水/交易均重元数据 + 城市×日期 |

### 2.2 Metric Key 规范（日度）

| Metric Key | Metric Name | Unit | Tags 规范 | 数据来源 Sheet |
|-----------|-------------|------|----------|---------------|
| `YY_D_PRICE_NATION_AVG` | 全国均价 | 元/公斤 | `scope=nation` | 价格+宰量 |
| `YY_D_SLAUGHTER_TOTAL_1` | 日屠宰量合计1 | 头 | `scope=nation` | 价格+宰量 |
| `YY_D_SLAUGHTER_TOTAL_2` | 日度屠宰量合计2 | 头 | `scope=nation` | 价格+宰量 |
| `YY_D_PRICE_PROVINCE_AVG` | 商品猪出栏均价 | 元/公斤 | `scope=province` | 各省份均价 |
| `YY_D_SLAUGHTER_VOL` | 屠宰企业日度屠宰量 | 头 | `province={省份}` | 屠宰企业日度屠宰量 |
| `YY_D_OUT_PRICE` | 商品猪出栏价 | 元/公斤 | `scale={规模场\|小散户\|all}`, `stat={price\|avg\|chg}` | 出栏价 |
| `YY_D_MARKET_SCATTER_STD_PIG_PRICE` | 市场散户标重猪 | 元/公斤 | `crowd=散户`, `pig_type=标重猪`, `field=price` | 散户标肥价差 |
| `YY_D_SPREAD_150_VS_STD` | 150公斤左右较标猪价差 | 元/公斤 | `spread=150-vs-std`, `weight_band=150kg` | 散户标肥价差 |
| `YY_D_SPREAD_175_VS_STD` | 175公斤左右较标猪价差 | 元/公斤 | `spread=175-vs-std`, `weight_band=175kg` | 散户标肥价差 |
| `YY_D_SECOND_FATTENING_SENTIMENT` | 二育采购情绪较昨日 | - | `topic=二育`, `field=sentiment` | 散户标肥价差（存 raw_value） |
| `YY_D_STD_PIG_AVG_PRICE` | 标猪均价 | 元/公斤 | `pig_type=标猪`, `stat=avg` | 市场主流标猪肥猪价格 |
| `YY_D_STD_PIG_WEIGHT_BAND` | 标猪体重段 | kg | `pig_type=标猪`, `field=weight_band` | 市场主流标猪肥猪价格（存 raw_value） |
| `YY_D_PIG_PRICE_90_100` | 90-100kg均价 | 元/公斤 | `weight_band=90-100kg`, `stat=avg` | 市场主流标猪肥猪价格 |
| `YY_D_PIG_PRICE_130_140` | 130-140kg均价 | 元/公斤 | `weight_band=130-140kg`, `stat=avg` | 市场主流标猪肥猪价格 |
| `YY_D_PIG_PRICE_150_AROUND` | 150kg左右均价 | 元/公斤 | `weight_band=150kg左右`, `stat=avg` | 市场主流标猪肥猪价格 |
| `YY_D_MARKET_NATION_AVG` | 全国均价 | 元/公斤 | `scope=nation` | 市场主流标猪肥猪均价方便作图 |
| `YY_D_MARKET_90_100_AVG` | 90-100kg均价 | 元/公斤 | `weight_band=90-100kg`, `scope=nation` | 市场主流标猪肥猪均价方便作图 |
| `YY_D_MARKET_130_140_AVG` | 130-140kg均价 | 元/公斤 | `weight_band=130-140kg`, `scope=nation` | 市场主流标猪肥猪均价方便作图 |
| `YY_D_MARKET_150_170_AVG` | 150-170kg均价 | 元/公斤 | `weight_band=150-170kg`, `scope=nation` | 市场主流标猪肥猪均价方便作图 |
| `YY_D_DELIVERY_CITY_OUT_PRICE` | 交割地市出栏价 | 元/公斤 | `province={省份}`, `city={城市}`, `weight_band={体重段}`, `premium_lh2505_plus={升贴水}`, `premium_lh2409_lh2503={升贴水}` | 交割地市出栏价 |

### 2.3 Tags 规范说明

- **scale**: `规模场` / `小散户` / `all`（均价）
- **stat**: `price`（价格） / `avg`（均价） / `chg`（涨跌）
- **scope**: `nation`（全国） / `province`（省份）
- **crowd**: `散户` / `集团`
- **pig_type**: `标猪` / `标重猪` / `肥猪`
- **weight_band**: `90-100kg` / `130-140kg` / `150kg左右` / `150-170kg`
- **field**: `price` / `weight_band` / `sentiment` / `chg`
- **topic**: `二育`
- **spread**: `150-vs-std` / `175-vs-std`
- **province**: 省份名称（标准化后）
- **city**: 城市名称（交割地市）
- **weight_band**: 交易均重（交割地市）
- **premium_lh2505_plus**: 升贴水（LH2505及以后），单位：元/吨
- **premium_lh2409_lh2503**: 升贴水（LH2409-LH2503），单位：元/吨

---

## 3. 涌益周度（YONGYI_WEEKLY_V1）- 主要 Sheet 配置

### 3.1 主要 Sheet 列表与 Parser 映射

| Sheet 名称 | Parser | Parser ID | 说明 |
|-----------|--------|-----------|------|
| 周度-商品猪出栏价 | `PERIOD_START_END_WIDE_PROVINCE` | P4 | 周起止 + 省份列 |
| 周度-体重 | `PERIOD_START_END_WIDE_PROVINCE_WITH_ROW_DIM` | P4 变体 | 周起止 + 省份列 + 行维度（指标） |
| 周度-屠宰厂宰前活猪重 | `PERIOD_START_END_PROVINCE_GROUPED_SUBCOLS` | P4 变体 | 周起止 + 省份列 + 子列（值/较上周） |
| 周度-各体重段价差 | `PERIOD_END_FROM_COL2_START_DERIVED` | P4 变体 | 周结束日期 + 省份列 + 行维度 |
| 周度-养殖利润最新 | `PERIOD_START_END_MULTI_COL_WITH_GROUP_HEADERS` | P5 | 周起止 + 规模段/模式列 |
| 周度-冻品库存 | `PERIOD_START_END_WIDE_PROVINCE` | P4 | 周起止 + 省份列 |
| 周度-冻品库存多样本 | `NARROW_DATE_WIDE_DIM_COLS` | P1 变体 | 日期列 + 大区列 |
| 周度-毛白价差 | `NARROW_PERIOD_END_MULTI_METRIC` | P1 变体 | 周结束日期 + 多指标列 |
| 周度-猪肉价（前三等级白条均价） | `PERIOD_START_END_WIDE_PROVINCE` | P4 | 周起止 + 省份列 |
| 周度-屠宰企业日度屠宰量 | `NARROW_DATE_ROWS_WIDE_PROVINCES_TRANSPOSED` | P1 变体 | 日期行 + 省份列（日度数据） |
| 周度-屠宰新* | `PERIOD_START_END_MULTI_METRIC` | P4 变体 | 周起止 + 多指标列（全国） |
| 高频仔猪、母猪 | `NARROW_DATE_WITH_ROW_DIM_WIDE_PROVINCE` | P1 变体 | 日期列 + 行维度（指标） + 省份列 |

### 3.2 主要 Metric Key 规范（周度）

| Metric Key | Metric Name | Unit | Tags 规范 | 数据来源 Sheet |
|-----------|-------------|------|----------|---------------|
| `YY_W_OUT_PRICE` | 商品猪出栏价 | 元/公斤 | `period_type=week`, `province={省份}` | 周度-商品猪出栏价 |
| `YY_W_OUT_WEIGHT` | 商品猪出栏体重 | kg | `period_type=week`, `province={省份}`, `indicator={指标}` | 周度-体重 |
| `YY_W_SLAUGHTER_PRELIVE_WEIGHT` | 宰前活猪重 | kg | `period_type=week`, `province={省份}`, `indicator={指标}` | 周度-屠宰厂宰前活猪重 |
| `YY_W_SLAUGHTER_PRELIVE_WEIGHT_WOW` | 宰前活猪重较上周 | kg | `period_type=week`, `province={省份}`, `indicator={指标}` | 周度-屠宰厂宰前活猪重 |
| `YY_W_PRICE_BY_WEIGHT` | 各体重段价格 | 元/斤 | `period_type=week`, `province={省份}`, `indicator={指标}` | 周度-各体重段价差 |
| `YY_W_FARM_PROFIT_LATEST` | 养殖利润最新 | 元/头 | `period_type=week`, `mode={自繁自养\|外购仔猪\|合同农户}`, `scale_band={规模段}` | 周度-养殖利润最新 |
| `YY_W_FROZEN_INVENTORY_RATIO` | 冻品库存库容率 | ratio | `period_type=week`, `province={省份\|大区}` | 周度-冻品库存 / 周度-冻品库存多样本 |
| `YY_W_WHITE_PRICE_TOP3` | 前三等级白条价 | 元/公斤 | `period_type=week`, `scope=nation` | 周度-毛白价差 |
| `YY_W_OUT_PRICE_NATION` | 生猪出栏价 | 元/公斤 | `period_type=week`, `scope=nation` | 周度-毛白价差 |
| `YY_W_LIVE_WHITE_SPREAD` | 毛白价差 | 元/公斤 | `period_type=week`, `scope=nation` | 周度-毛白价差（计算） |
| `YY_W_PORK_WHITE_TOP3` | 前三等级白条均价 | 元/公斤 | `period_type=week`, `province={省份}` | 周度-猪肉价（前三等级白条均价） |
| `YY_D_SLAUGHTER_VOL` | 屠宰企业日度屠宰量 | 头 | `period_type=day`, `province={省份}` | 周度-屠宰企业日度屠宰量 |
| `YY_W_SLAUGHTER_TOP10` | 规模屠宰厂全国前10家宰杀量 | 头 | `period_type=week`, `scope=nation` | 周度-屠宰新* |
| `YY_W_SLAUGHTER_TOP10_MOM` | 规模屠宰厂全国前10家环比 | ratio | `period_type=week`, `scope=nation` | 周度-屠宰新* |
| `YY_W_SLAUGHTER_100` | 各省规模屠宰厂100家宰杀量 | 头 | `period_type=week`, `province={省份}` | 周度-屠宰新* |
| `YY_W_SLAUGHTER_100_MOM` | 各省规模屠宰厂100家环比 | ratio | `period_type=week`, `province={省份}` | 周度-屠宰新* |
| `YY_W_SLAUGHTER_TOWN` | 县区+乡镇宰杀70家 | 头 | `period_type=week`, `scope=nation` | 周度-屠宰新* |
| `YY_W_SLAUGHTER_TOWN_MOM` | 县区+乡镇宰杀环比 | ratio | `period_type=week`, `scope=nation` | 周度-屠宰新* |
| `YY_D_PIGLET_SOW_PRICE` | 高频仔猪/母猪价格 | 元/头 | `period_type=day`, `province={省份}`, `indicator={指标}` | 高频仔猪、母猪 |

### 3.3 周度 Tags 规范补充

- **period_type**: `week`（周度） / `day`（日度，周度文件中的日度数据）
- **mode**: `自繁自养` / `外购仔猪` / `合同农户`
- **scale_band**: 规模段（如 `500头以下` / `500-3000头` / `3000头以上`）
- **indicator**: 指标类型（如 `均重` / `集团` / `散户`）
- **region**: 大区（如 `东北` / `华北` / `华东` / `华中` / `西南` / `华南`）

---

## 4. 交割城市列表（需要新增到 dim_location + dim_location_alias）

### 4.1 交割城市清单（基于"交割地市出栏价" Sheet）

**注意**：实际城市列表需要从 Excel 文件中提取。以下是常见交割城市（需要根据实际文件补充）：

| 省份 | 城市名称（Excel 中） | location_code（标准） | level | parent_code |
|------|-------------------|---------------------|-------|-------------|
| 河南 | 郑州 | `LOC_410100` | city | `LOC_410000` |
| 河南 | 新乡 | `LOC_410700` | city | `LOC_410000` |
| 河南 | 开封 | `LOC_410200` | city | `LOC_410000` |
| 山东 | 济南 | `LOC_370100` | city | `LOC_370000` |
| 山东 | 青岛 | `LOC_370200` | city | `LOC_370000` |
| 山东 | 潍坊 | `LOC_370700` | city | `LOC_370000` |
| 江苏 | 南京 | `LOC_320100` | city | `LOC_320000` |
| 江苏 | 苏州 | `LOC_320500` | city | `LOC_320000` |
| 安徽 | 合肥 | `LOC_340100` | city | `LOC_340000` |
| 安徽 | 蚌埠 | `LOC_340300` | city | `LOC_340000` |
| 湖北 | 武汉 | `LOC_420100` | city | `LOC_420000` |
| 湖北 | 襄阳 | `LOC_420600` | city | `LOC_420000` |
| 湖南 | 长沙 | `LOC_430100` | city | `LOC_430000` |
| 湖南 | 株洲 | `LOC_430200` | city | `LOC_430000` |
| 江西 | 南昌 | `LOC_360100` | city | `LOC_360000` |
| 四川 | 成都 | `LOC_510100` | city | `LOC_510000` |
| 四川 | 绵阳 | `LOC_510700` | city | `LOC_510000` |
| 重庆 | 重庆 | `LOC_500100` | city | `LOC_500000` |
| 广东 | 广州 | `LOC_440100` | city | `LOC_440000` |
| 广东 | 深圳 | `LOC_440300` | city | `LOC_440000` |
| 广西 | 南宁 | `LOC_450100` | city | `LOC_450000` |
| 辽宁 | 沈阳 | `LOC_210100` | city | `LOC_210000` |
| 辽宁 | 大连 | `LOC_210200` | city | `LOC_210000` |
| 吉林 | 长春 | `LOC_220100` | city | `LOC_220000` |
| 黑龙江 | 哈尔滨 | `LOC_230100` | city | `LOC_230000` |
| 河北 | 石家庄 | `LOC_130100` | city | `LOC_130000` |
| 河北 | 唐山 | `LOC_130200` | city | `LOC_130000` |
| 天津 | 天津 | `LOC_120100` | city | `LOC_120000` |
| 北京 | 北京 | `LOC_110100` | city | `LOC_110000` |

### 4.2 城市别名映射（dim_location_alias）

需要为每个城市创建别名映射，支持：
- Excel 中的城市名称（可能有变体）
- 可能的简称或别名

示例：
```json
{
  "alias": "郑州",
  "source_code": "YONGYI",
  "location_code": "LOC_410100"
}
```

**实施建议**：
1. 从 Excel "交割地市出栏价" Sheet 中提取所有城市名称
2. 标准化城市名称（去除空格、统一格式）
3. 创建 `dim_location` 记录（如果不存在）
4. 创建 `dim_location_alias` 映射记录

---

## 5. 指标抽取规则（fact_observation → fact_indicator_ts）

### 5.1 核心指标清单（需要抽取到 indicator_ts）

| Indicator Code | Indicator Name | Source Metric Pattern | 过滤条件 | 聚合方法 | Freq | Topic |
|---------------|----------------|---------------------|---------|---------|------|-------|
| `YY_D_PRICE_NATION_AVG` | 全国出栏均价 | `YY_D_PRICE.*` | `tags.scale=均价`, `tags.scope=nation`, `geo_code=NATION` | mean | D | 价格 |
| `YY_D_PRICE_PROVINCE_AVG` | 各省出栏均价 | `YY_D_PRICE.*` | `tags.scale=均价`, `geo_code=省份` | mean (按省份) | D | 价格 |
| `YY_D_SLAUGHTER_TOTAL` | 全国屠宰量合计 | `YY_D_SLAUGHTER.*` | `tags.scope=nation`, `geo_code=NATION` | sum | D | 屠宰 |
| `YY_D_SLAUGHTER_PROVINCE` | 各省屠宰量 | `YY_D_SLAUGHTER.*` | `geo_code=省份` | sum (按省份) | D | 屠宰 |
| `YY_W_PRICE_NATION_AVG` | 全国出栏均价（周度） | `YY_W_OUT_PRICE` | `tags.scope=nation`, `geo_code=NATION`, `period_type=week` | mean | W | 价格 |
| `YY_W_PRICE_PROVINCE_AVG` | 各省出栏均价（周度） | `YY_W_OUT_PRICE` | `geo_code=省份`, `period_type=week` | mean (按省份) | W | 价格 |
| `YY_W_FROZEN_INVENTORY_TOTAL` | 冻品库存合计 | `YY_W_FROZEN_INVENTORY_RATIO` | `tags.scope=nation`, `geo_code=NATION`, `period_type=week` | sum | W | 库存 |
| `YY_W_LIVE_WHITE_SPREAD` | 毛白价差 | `YY_W_LIVE_WHITE_SPREAD` | `tags.scope=nation`, `geo_code=NATION`, `period_type=week` | mean | W | 价差 |
| `YY_W_FARM_PROFIT_LATEST` | 养殖利润最新 | `YY_W_FARM_PROFIT_LATEST` | `period_type=week`, `tags.mode=自繁自养` | mean | W | 利润 |
| `YY_D_DELIVERY_CITY_PRICE_AVG` | 交割地市出栏价（平均） | `YY_D_DELIVERY_CITY_OUT_PRICE` | `tags.city=*` | mean (按城市) | D | 价格 |

### 5.2 抽取规则配置（indicator_extraction_rules.json）

已存在的规则见 `backend/app/config/indicator_extraction_rules.json`，需要补充：

```json
{
  "indicator_code": "YY_D_PRICE_PROVINCE_AVG",
  "indicator_name": "各省出栏均价",
  "source_code": "YONGYI",
  "freq": "D",
  "topic": "价格",
  "unit": "元/公斤",
  "conditions": {
    "metric_key_pattern": "YY_D_PRICE.*|YY_D_OUT_PRICE",
    "tags": {
      "scale": "均价"
    },
    "geo_code_pattern": ".*",
    "period_type": "day"
  },
  "agg_method": "mean",
  "group_by": "geo_code"
},
{
  "indicator_code": "YY_W_PRICE_PROVINCE_AVG",
  "indicator_name": "各省出栏均价（周度）",
  "source_code": "YONGYI",
  "freq": "W",
  "topic": "价格",
  "unit": "元/公斤",
  "conditions": {
    "metric_key_pattern": "YY_W_OUT_PRICE",
    "geo_code_pattern": ".*",
    "period_type": "week"
  },
  "agg_method": "mean",
  "group_by": "geo_code"
},
{
  "indicator_code": "YY_W_FROZEN_INVENTORY_TOTAL",
  "indicator_name": "冻品库存合计",
  "source_code": "YONGYI",
  "freq": "W",
  "topic": "库存",
  "unit": "ratio",
  "conditions": {
    "metric_key_pattern": "YY_W_FROZEN_INVENTORY_RATIO",
    "tags": {
      "scope": "nation"
    },
    "geo_code": "NATION",
    "period_type": "week"
  },
  "agg_method": "sum"
},
{
  "indicator_code": "YY_W_FARM_PROFIT_LATEST",
  "indicator_name": "养殖利润最新",
  "source_code": "YONGYI",
  "freq": "W",
  "topic": "利润",
  "unit": "元/头",
  "conditions": {
    "metric_key_pattern": "YY_W_FARM_PROFIT_LATEST",
    "tags": {
      "mode": "自繁自养"
    },
    "period_type": "week"
  },
  "agg_method": "mean"
}
```

---

## 6. 实施步骤

### 6.1 数据模型准备
- [x] `dim_location` 表已创建
- [x] `dim_location_alias` 表已创建
- [x] `fact_observation` 周期字段已添加
- [x] `fact_observation_tag` 表已创建
- [x] `ingest_profile` 表已创建

### 6.2 交割城市数据准备
1. 从 Excel "交割地市出栏价" Sheet 提取城市列表
2. 创建 `dim_location` 记录（城市级）
3. 创建 `dim_location_alias` 映射记录

### 6.3 配置文件加载
1. 运行 `backend/scripts/load_ingest_profiles.py` 加载配置到数据库
2. 验证配置是否正确加载

### 6.4 指标抽取规则配置
1. 更新 `backend/app/config/indicator_extraction_rules.json`
2. 实现指标抽取服务（从 `fact_observation` 抽取到 `fact_indicator_ts`）

### 6.5 测试导入
1. 使用测试 Excel 文件验证导入流程
2. 检查 `fact_observation` 数据是否正确
3. 检查 `fact_observation_tag` 标签是否正确
4. 验证指标抽取是否正常工作

---

## 7. 注意事项

1. **城市名称标准化**：Excel 中的城市名称可能有变体（如"郑州" vs "郑州市"），需要在 `dim_location_alias` 中建立映射。

2. **周期字段**：周度数据使用 `period_start` 和 `period_end`，日度数据使用 `obs_date`。

3. **Tags 索引**：`fact_observation_tag` 表用于高性能维度筛选，确保所有重要维度都写入 tag 表。

4. **幂等性**：使用 `dedup_key` 确保同一条数据不会重复导入。

5. **指标抽取时机**：
   - 导入后同步触发（小批量）
   - 或定时任务（大批量/回补）

---

## 8. 参考文件

- 配置文件：`docs/ingest_profile_yongyi_daily_v1.json`
- 配置文件：`docs/ingest_profile_yongyi_weekly_v1.json`
- 指标抽取规则：`backend/app/config/indicator_extraction_rules.json`
- 改进计划：`docs/五类数据全量入库与展示改进计划.md`
