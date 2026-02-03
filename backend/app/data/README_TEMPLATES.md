# 8套客户常用模板使用说明

## 模板列表

1. **T01 - 标肥价差季节性**：每周判断标肥价差处于历史什么位置
2. **T02 - 毛白价差季节性**：用于屠宰/白条环节分析
3. **T03 - 生猪价格季节性**：看猪价季节性（管理层/研究必备）
4. **T04 - 价格+标肥价差（区间双轴）**：复盘某段时间内价格与价差联动
5. **T05 - 区域价差季节性**：判断区域结构变化（南北/东西/主销主产）
6. **T06 - 分省价格对比**：周报里经常要重点省份排名/分化
7. **T07 - 集团企业价格对比**：企业专题（Top5/Top10企业价格对比）
8. **T08 - 周报核心包**：一键生成报告包（4-6张图一次性生成）

## 初始化模板到数据库

### 方式1：通过API（推荐）

```bash
# 需要admin权限
POST /api/v1/templates/init-preset
```

### 方式2：通过Python脚本

```bash
cd backend
python -m app.api.init_templates
```

## 指标代码映射

模板中使用占位符（如 `HOG_PRICE_NATIONAL`），系统会自动映射到实际的 `metric_id`。

映射规则在 `app/models/metric_code_map.py` 中定义，通过关键词匹配 `DimMetric.raw_header`。

### 当前支持的占位符

- `HOG_PRICE_NATIONAL` - 全国标猪价格
- `SPREAD_STANDARD_FATTY` - 标肥价差
- `SPREAD_MAO_BAI` - 毛白价差
- `REGIONAL_SPREAD_NORTH_SOUTH` - 南北价差
- `PRICE_BY_PROVINCE` - 分省价格
- `PRICE_BY_GROUP` - 集团企业价格
- `PROFIT_SELF_BREED` - 自繁自养利润
- `PROFIT_PURCHASE_PIGLET` - 外购仔猪利润

## 前端使用

### 获取预设模板列表

```typescript
import { templatesApi } from '@/api/templates'

// 获取8套预设模板配置（JSON格式）
const presetTemplates = await templatesApi.getPresetTemplates()
```

### 从模板加载配置

在 ChartBuilder 页面：
1. 点击"从模板加载"按钮
2. 选择模板
3. 系统自动填充配置
4. 点击"生成图表"查看结果

### 保存当前配置为模板

在 ChartBuilder 页面：
1. 配置好图表参数
2. 点击"保存为模板"按钮
3. 输入模板名称
4. 模板保存到数据库

## 模板结构说明

每个模板包含：

- `template_id`: 唯一ID（T01-T08）
- `name`: 模板名称
- `category`: 分类（价差/价格/利润/区域/企业/管理看板）
- `description`: 用途说明
- `chart_type`: 图表类型（seasonality/timeseries/composite）
- `params`: 用户可调参数
- `blocks`: 图表/表格块配置
- `export`: 导出章节配置
- `acceptance`: 验收点

## 注意事项

1. **指标映射**：如果数据库中没有匹配的指标，模板会使用该指标组的第一个指标作为默认值
2. **参数默认值**：
   - `YTD` = 本年迄今
   - `last_90_days` = 最近90天
   - `last_180_days` = 最近180天
   - `top10`/`top5` = 需要后续处理（TopN选择）
3. **年份默认值**：如果未指定，自动使用最近6年
