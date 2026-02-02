# 猪价智盘（HogPrice Insight）——Python Web 数据分析与报表系统 项目 Plan（完整版）

> 目标：将“钢联自动更新模板.xlsx”这类多 Sheet 行情/价差/利润 Excel **统一入库**，支持**多维筛选汇总、生成图表与报表模板**，并支持**登录权限**与**一键导出 Excel（含图表）**。

---

## 1. 项目命名

- 中文名（推荐）：**猪价智盘**
- 英文名：**HogPrice Insight** / **HogPrice Dashboard**
- 备选：
  - 生猪价差罗盘（Basis Compass）
  - 猪价数据中台（Hog Data Hub）

---

## 2. 背景与数据范围（Excel 模板概览）

### 2.1 数据来源结构（典型特征）
Excel 文件包含多个 Sheet，各 Sheet 结构高度一致：
- 第 1 行：标题
- 第 2 行：指标名称（每列一个指标定义，含维度信息，使用“：”分段）
- 第 3 行：单位
- 第 4 行：更新时间
- 第 5 行起：日期 + 数值（含空值、NA、异常值）

### 2.2 Sheet/指标组（示例）
- 分省区猪价（日度）
- 集团企业出栏价（日度）
- 交割库出栏价（日度）
- 区域价差（日度）
- 肥标价差（日度）
- 毛白价差（日度）
- 养殖利润（周度）

> 关键：不能按 sheet 写死逻辑，必须通过解析“指标名称”将列统一抽象为**指标 + 维度**，形成通用分析与导出能力。

---

## 3. 业务目标与使用场景

### 3.1 核心目标（一句话）
将模板 Excel 统一入库，按省区/企业/交割库/指标/时间维度筛选汇总，生成图表与报表，并导出含图表的 Excel。

### 3.2 典型使用场景
1. **日度复盘**：全国/重点省区/重点企业价格走势 + 价差变化 + 异常点
2. **周度复盘**：价格 + 价差 + 利润（猪粮比、饲料比价、成本结构）形成周报
3. **月度复盘**：区域结构变化、集团价差策略、交割库差异、利润周期
4. **对比分析**：同一指标多地区/多企业对比；同比/环比；TopN 排名
5. **报表输出**：按模板一键生成 Excel（含透视表+折线/柱状/双轴图）

---

## 4. 产品功能范围（功能分解）

## 4.1 用户与权限（必须）
- 登录/退出（账号/密码）
- Token（JWT）
- 角色（至少三种）：
  - Admin：全权限（用户管理、数据导入、指标管理、系统配置）
  - Analyst：分析/报表/导出
  - Viewer：只读（看板与查询）

> 可选：按“指标组/地区/企业”分配数据访问权限（MVP 可先不做细粒度）。

---

## 4.2 数据导入与管理（必须）
### 4.2.1 Excel 导入
- 上传 xlsx
- 自动识别所有 sheet 并入库
- 数据清洗：
  - 统一日期解析（YYYY/MM/DD、YYYY-MM-DD、Excel serial）
  - 处理 NA/空值/异常字符串 -> NULL
  - 数值列转 float，保留原始字符串用于审计（可选）
- 导入校验：
  - 日期列必须可解析
  - 指标名称（第2行）必须存在
  - 单位/更新时间允许为空但记录
- 导入结果：
  - 导入成功/失败统计
  - 错误清单（sheet、行列、原因）

### 4.2.2 导入版本与审计（建议）
- 每次导入生成 import_batch（批次）
- 保留源文件摘要（文件名、hash、上传者、时间、sheet 列数）
- 可回滚（可选：逻辑删除批次数据）

---

## 4.3 指标库与维度解析（必须）
### 4.3.1 指标名称解析（关键）
指标列名示例：
- `商品猪：出栏均价：黑龙江（日）`
- `外三元猪：每头重110-125kg：出栏价：辽宁：辽宁大北农（日）`

解析目标：抽出维度字段（尽量通用）
- pig_type（猪种，如 商品猪/外三元/内三元 等）
- weight_range（体重段，如 110-125kg）
- metric_name（指标名，如 出栏价/出栏均价/价差/利润/猪粮比）
- geo（省/区域，如 黑龙江/辽宁/华东）
- company（企业，如 辽宁大北农）
- warehouse（交割库/库点）
- freq（频率：日/周）
- metric_group（指标组：分省/集团/交割库/价差/利润）

### 4.3.2 统一指标字典
- 将 raw_header（原始指标名）写入 dim_metric.raw_header
- 解析后的维度写入结构化字段（或 tags_json）

> 原则：**保留原始字段**用于追溯，同时实现结构化查询与汇总。

---

## 4.4 分析查询与可视化（必须）
### 4.4.1 通用筛选器（左侧）
- 时间范围（起止日期）
- 频率（日/周）
- 指标组（分省/集团/交割库/价差/利润）
- 指标（出栏价、出栏均价、区域价差、肥标价差、毛白价差、利润等）
- 地区（省、区域）
- 企业（集团企业）
- 交割库/库点
- Tags（猪种、体重段、均价/报价、移动平均等）

### 4.4.2 图表类型
- 折线图（时间序列，支持多条线对比）
- 柱状图（TopN、分组对比）
- 双轴图（例如：标猪价格 vs 利润/价差）
- 表格（明细、汇总、透视）
- 异常点标记（可选：阈值/波动率）

### 4.4.3 分析能力（MVP 起步）
- 多指标对比（同图多线）
- group_by 汇总（按省/企业/区域/猪种）
- TopN（按最近值/均值/涨跌幅）
- 同比/环比（MVP 可先做环比、同比后置）

---

## 4.5 报表模板（建议，MVP-2）
### 4.5.1 日报模板
- 全国标猪/重点省区/重点企业
- 区域价差、肥标价差、毛白价差
- 结论与备注（可编辑）
- 导出 Excel（含图表）

### 4.5.2 周报模板
- 周均价/周趋势（价格、价差）
- 养殖利润（周度）、猪粮比、饲料比价
- 周重点（可手工输入）

### 4.5.3 月报模板
- 省区结构（热力/排行）
- 集团出栏价策略变化
- 交割库差异
- 利润周期与驱动因子（可选：关联分析）

---

## 4.6 Excel 导出（必须）
导出内容（可选勾选）：
- 明细数据（长表/宽表）
- 汇总表（group_by 结果）
- 透视表（pivot）
- 图表（折线/柱状/双轴图）
- 报表封面（时间范围、筛选条件、生成时间、作者）

技术实现建议：
- 后端生成 xlsx：`xlsxwriter`（强图表）优先
- 复杂排版可引入模板（后置）

---

## 5. 技术架构与选型

## 5.1 总体架构
- 前端：Vue3 + Element-Plus + ECharts
- 后端：FastAPI + SQLAlchemy + Alembic
- 数据处理：Pandas
- 数据库：PostgreSQL（推荐）/ MySQL（二选一）
- 缓存/队列（可选）：Redis + Celery（定时任务/导出异步）

## 5.2 部署
- Docker Compose：
  - api（FastAPI）
  - web（Nginx + 前端静态文件）
  - db（Postgres）
  - redis（可选）
- 反向代理与静态：
  - /api -> FastAPI
  - / -> 前端

---

## 6. 数据模型设计（核心：统一长表）

> 目标：所有 sheet 数据都进入统一事实表 `fact_observation`，避免 7 张表碎片化导致分析困难。

## 6.1 用户与权限
- `sys_user`
  - id, username, password_hash, is_active, created_at
- `sys_role`
  - id, code, name
- `sys_user_role`
  - user_id, role_id

（可选：数据权限）
- `sys_perm_scope`
  - user_id, scope_type(metric_group/geo/company), scope_value

## 6.2 指标与维度
- `dim_metric`
  - id
  - metric_group（分省/集团/交割库/价差/利润）
  - metric_name（出栏价/出栏均价/利润/价差等）
  - unit
  - freq（daily/weekly）
  - raw_header（原始列名）
  - source_updated_at（可空）
  - created_at

- `dim_geo`
  - id, province, region

- `dim_company`
  - id, company_name, province

- `dim_warehouse`
  - id, warehouse_name, province

- `import_batch`
  - id, filename, file_hash, uploader_id, created_at
  - status, total_rows, success_rows, failed_rows, error_json

## 6.3 事实表（最关键）
- `fact_observation`
  - id
  - batch_id（import_batch.id）
  - metric_id（dim_metric.id）
  - obs_date（date）
  - value（numeric）
  - geo_id（nullable）
  - company_id（nullable）
  - warehouse_id（nullable）
  - tags_json（jsonb，可选：pig_type, weight_range, ma, etc）
  - created_at

索引建议：
- (metric_id, obs_date)
- (geo_id, obs_date)
- (company_id, obs_date)
- GIN(tags_json)（Postgres）

---

## 7. Excel 导入解析方案（落地规则）

## 7.1 读取规则
对每个 sheet：
1) 读取整个 sheet（不设 header）
2) row[1] 作为指标列定义（第二行）
3) row[2] 作为单位（第三行）
4) row[3] 作为更新时间（第四行）
5) row[4:] 为数据区：A 列为日期，其余列为数值

## 7.2 melt 成长表
将宽表转成长表：
- obs_date
- raw_header
- value

## 7.3 raw_header 解析策略
- 分隔符：`：`（中文冒号），末尾可能含（`（日）` / `（周）`）
- 解析顺序（建议，可兼容缺失字段）：
  1) 频率 freq：从括号提取
  2) 最后 1~2 段可能是 company/geo/warehouse（按 sheet 类型做优先级推断）
  3) 中间段识别 weight_range（含 kg 或 “每头重”）
  4) 第一段识别 pig_type（含“猪”字或常见猪种）
  5) 指标名 metric_name：出栏价/均价/价差/利润/猪粮比等（字典匹配）

> 输出：metric_group + metric_name + freq + geo/company/warehouse + tags_json

## 7.4 upsert 规则
- dim_metric：以 raw_header 唯一（或 raw_header + sheet_name）
- dim_geo/company/warehouse：名称唯一（可附 province）
- fact_observation：以（metric_id + obs_date + geo_id + company_id + warehouse_id + tags_json）去重

---

## 8. API 设计（可直接开工）

## 8.1 Auth
- `POST /api/auth/login`
  - req: { username, password }
  - resp: { token, user }

- `GET /api/me`
  - resp: user profile + roles

## 8.2 Import
- `POST /api/data/import-excel`
  - multipart upload
  - resp: { batch_id, summary, errors[] }

- `GET /api/data/batches`
  - 导入批次列表

- `GET /api/data/batches/{id}`
  - 批次详情 + 错误明细

## 8.3 Metadata
- `GET /api/metrics?group=&freq=`
- `GET /api/dim/geo`
- `GET /api/dim/company`
- `GET /api/dim/warehouse`
- `GET /api/dim/tags?tag_type=`

## 8.4 Query（核心）
- `POST /api/query/timeseries`
  - req:
    - date_range: {start, end}
    - metrics: [metric_id...]
    - filters: { geo_ids[], company_ids[], warehouse_ids[], tags{} }
    - group_by: ["geo"|"company"|"warehouse"|"tag:pig_type"...]（可选）
  - resp: series data（适配 ECharts）

- `POST /api/query/topn`
  - req: { metric_id, date, group_by, n, sort_by(last/avg/change) }

- `POST /api/query/pivot`
  - req: { rows, cols, metric_id, date_range, filters }

## 8.5 Report & Export
- `POST /api/report/generate`
  - req: { template: daily/weekly/monthly, params... }
  - resp: report_id + dataset summary

- `POST /api/export/excel`
  - req: 同 query + export options（是否透视、是否图表、是否封面）
  - resp: xlsx file stream

---

## 9. 前端页面规划（Vue3 + ElementPlus）

1) 登录页  
2) 首页 Dashboard（快捷入口：日报/周报/月报、最近导入批次）  
3) 数据导入页（上传、导入历史、错误明细）  
4) 多维分析页（筛选器 + 图表区 + 表格区 + 导出）  
5) 报表页（模板生成、编辑结论、导出）  
6) 系统管理（用户/角色）（Admin）  

---

## 10. 非功能需求（NFR）

### 10.1 性能
- 查询：常用维度组合 1~3 秒内返回（中等数据量：几十万~百万行）
- 导出：大导出可异步（MVP 可同步，后续上 Celery）

### 10.2 稳定性与可追溯
- 每个值能追溯到：导入批次、源文件、sheet、raw_header
- 导入错误可复盘（错误表/JSON）

### 10.3 安全
- 密码 hash（bcrypt/argon2）
- JWT 过期与刷新（可选）
- 访问控制（角色控制）

---

## 11. 里程碑与交付（建议）

### MVP-1（最小可用）
- 登录
- Excel 导入 + 指标解析入库
- 多维筛选 + 时间序列折线图
- 导出 Excel（数据 + 简单图）

### MVP-2（产品化增强）
- 日/周/月报表模板
- TopN、涨跌幅、环比
- 权限细粒度（按指标组/地区）

### MVP-3（自动化）
- 定时更新（自动拉取/自动导入目录）
- 报表订阅（每天/每周自动生成并推送）
- 缓存与大数据优化

---

## 12. 项目目录结构（建议标准）

```
hogprice-insight/
  backend/
    app/
      api/
        auth.py
        import_excel.py
        query.py
        export.py
        report.py
      core/
        config.py
        security.py
        database.py
      models/
        sys_user.py
        dim_metric.py
        fact_observation.py
        import_batch.py
      services/
        excel_import_service.py
        metric_parse_service.py
        query_service.py
        export_service.py
      utils/
        dt_parse.py
        logger.py
    alembic/
    main.py
    requirements.txt
    Dockerfile
  frontend/
    src/
      api/
      views/
      components/
      router/
      store/
    vite.config.ts
    package.json
    Dockerfile
  deploy/
    nginx/
      default.conf
    docker-compose.yml
  docs/
    数据字典.md
    指标解析规则.md
    报表模板说明.md
  README.md
```

---

## 13. 风险与对策

1) **指标列名格式不统一**  
- 对策：保留 raw_header + 逐步完善解析字典；解析失败进入 tags_json 的 raw_parts

2) **缺失值/异常值多**  
- 对策：清洗规则统一，保留异常日志；图表默认断点或插值选项

3) **数据量增长**  
- 对策：事实表索引、分区（按月/按年），常用 query 缓存；导出走异步任务

4) **导出图表复杂**  
- 对策：MVP 先做 2-3 个最常用图（折线/柱状/双轴），后续模板化增强

---

## 14. 验收标准（可作为需求确认）

- 能登录并按角色访问页面
- 上传该 Excel 能成功导入，且能看到指标列表（不少于原始列数-日期列）
- 能按时间范围筛选并画出至少 2 条指标折线
- 能按省/企业过滤后得到不同结果
- 能导出 Excel：
  - 含数据表
  - 含汇总（至少一个 group_by）
  - 含至少一个图表（折线或双轴）
- 导入失败时能输出错误明细（sheet、行列、原因）

---

## 15. 下一步执行清单（从 0 到可用）

1) 初始化仓库与目录（backend/frontend/deploy）  
2) 建库与迁移（dim_metric、fact_observation、sys_user、import_batch）  
3) 完成 Excel 导入服务：读取/清洗/melt/解析/upsert  
4) 完成查询 API：timeseries + filters + group_by  
5) 前端完成分析页：筛选器 + 折线图 + 表格  
6) 完成导出 Excel：xlsxwriter 生成数据+图  
7) 完成 Docker Compose 部署  

---

## 16. 附：核心“维度字典”（建议先准备一份）

- 猪种：商品猪/外三元/内三元/土杂…  
- 指标：出栏价/出栏均价/区域价差/肥标价差/毛白价差/利润/猪粮比/饲料比价…  
- 区域：华北/东北/华东/华中/华南/西南/西北…  
- 体重段：110-125kg、115-125kg 等（统一规范）  

> 该字典用于解析增强与前端筛选展示。
