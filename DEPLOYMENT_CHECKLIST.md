# 部署检查清单

## 前置条件

- [ ] Python 3.8+ 已安装
- [ ] MySQL 5.7+ 或 8.0+ 已安装并运行
- [ ] Node.js 16+ 已安装（前端）
- [ ] 数据库连接配置正确

## 后端部署步骤

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements_upgrade.txt  # 可选：农历库
```

### 2. 配置环境变量

检查或创建 `.env` 文件，确保包含：
- `DATABASE_URL` - 数据库连接字符串
- `SECRET_KEY` - JWT密钥
- 其他必要的配置

### 3. 运行数据库迁移

```bash
cd backend
alembic upgrade head
```

**预期结果**: 创建所有新表，无错误

### 4. 初始化基础数据

```bash
cd backend
python scripts/init_base_data.py
```

**预期结果**: 
- 初始化区域数据（全国/大区/省份）
- 初始化指标数据（价格/屠宰/均重/价差/冻品/产业链）

### 5. 验证数据库表

检查以下表是否已创建：
- [ ] `dim_indicator`
- [ ] `dim_region`
- [ ] `dim_contract`
- [ ] `dim_option`
- [ ] `fact_indicator_ts`
- [ ] `fact_indicator_metrics`
- [ ] `fact_futures_daily`
- [ ] `fact_options_daily`
- [ ] `ingest_error`
- [ ] `ingest_mapping`

检查 `import_batch` 表是否已扩展：
- [ ] `source_code` 列
- [ ] `date_range` 列
- [ ] `mapping_json` 列

### 6. 启动后端服务

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**验证**:
- [ ] 访问 `http://localhost:8000/docs` 查看API文档
- [ ] 检查所有新API端点是否可见：
  - `/api/v1/ingest/*`
  - `/api/v1/ts`
  - `/api/v1/dashboard/default`
  - `/api/v1/futures/*`
  - `/api/v1/options/*`
  - `/api/v1/reconciliation/*`

## 前端部署步骤

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置API地址

检查 `frontend/src/api/request.ts` 中的 `baseURL` 配置

### 3. 启动开发服务器

```bash
cd frontend
npm run dev
```

**验证**:
- [ ] 访问 `http://localhost:5173`（或配置的端口）
- [ ] 登录功能正常
- [ ] 菜单显示正确（根据用户角色）

## 功能测试清单

### 导入功能测试

1. **期货导入**
   - [ ] 上传 `lh_ftr.xlsx`
   - [ ] 系统识别为 `LH_FTR`
   - [ ] 预览显示正确
   - [ ] 执行导入成功
   - [ ] 数据写入 `fact_futures_daily`

2. **期权导入**
   - [ ] 上传 `lh_opt.xlsx`
   - [ ] 系统识别为 `LH_OPT`
   - [ ] 预览显示正确
   - [ ] 执行导入成功
   - [ ] 数据写入 `fact_options_daily`

3. **涌益日度导入**
   - [ ] 上传日度数据文件
   - [ ] 系统识别为 `YONGYI_DAILY`
   - [ ] 窄表和宽表都能正确解析
   - [ ] 数据写入 `fact_indicator_ts`

4. **涌益周度导入**
   - [ ] 上传周度数据文件
   - [ ] 系统识别为 `YONGYI_WEEKLY`
   - [ ] 多行表头正确解析
   - [ ] 数据写入 `fact_indicator_ts`

### 看板功能测试

1. **默认首页**
   - [ ] 访问 `/dashboard` 显示7个卡片
   - [ ] 卡片1：价格+价差双轴图
   - [ ] 卡片2：屠宰季节性图（支持农历对齐）
   - [ ] 卡片3：价格&屠宰走势
   - [ ] 卡片4：均重专区入口
   - [ ] 卡片5：价差专区入口
   - [ ] 卡片6：冻品库容率
   - [ ] 卡片7：产业链汇总

2. **筛选功能**
   - [ ] 时间范围筛选正常
   - [ ] 区域筛选正常
   - [ ] 年度筛选正常（季节性图）

### API功能测试

1. **时序接口**
   - [ ] `GET /api/v1/ts?indicator_code=hog_price_nation` 返回数据
   - [ ] 支持 `region_code` 参数
   - [ ] 支持 `freq` 参数
   - [ ] 支持 `from_date` 和 `to_date` 参数
   - [ ] 可选返回 `metrics`（同比/环比）

2. **看板接口**
   - [ ] `GET /api/v1/dashboard/default` 返回7个卡片数据
   - [ ] 每个卡片包含正确的数据结构

3. **期货接口**
   - [ ] `GET /api/v1/futures/daily?contract=lh2603` 返回数据
   - [ ] 支持日期范围筛选

4. **期权接口**
   - [ ] `GET /api/v1/options/daily?underlying=lh2603&type=C&strike=10000` 返回数据

5. **对账接口**
   - [ ] `GET /api/v1/reconciliation/missing?indicator_code=hog_price_nation` 返回缺失日期
   - [ ] `GET /api/v1/reconciliation/duplicates?indicator_code=hog_price_nation` 返回重复记录
   - [ ] `GET /api/v1/reconciliation/anomalies?indicator_code=hog_price_nation` 返回异常值

### 权限测试

1. **管理员用户**
   - [ ] 可以看到所有菜单（A-F组）
   - [ ] 可以访问数据中心
   - [ ] 可以访问系统管理

2. **运营用户**
   - [ ] 可以看到A-E组菜单
   - [ ] 可以访问数据中心
   - [ ] 不能访问系统管理（F组）

3. **客户用户**
   - [ ] 只能看到A-D组菜单
   - [ ] 不能访问数据中心（E组）
   - [ ] 不能访问系统管理（F组）

## 数据迁移测试（可选）

如果需要迁移旧数据：

1. **预览迁移**
   ```bash
   cd backend
   python scripts/migrate_to_new_schema.py
   ```
   - [ ] 预览显示迁移统计
   - [ ] 确认迁移计划

2. **执行迁移**
   - [ ] 确认后执行实际迁移
   - [ ] 验证数据正确性

3. **验证迁移结果**
   - [ ] 检查 `fact_indicator_ts` 表中有数据
   - [ ] 对比旧表和新表的数据量

## 性能测试

1. **导入性能**
   - [ ] 测试大文件导入（>10MB）
   - [ ] 导入时间在可接受范围内
   - [ ] 内存使用正常

2. **查询性能**
   - [ ] 看板加载时间 < 3秒
   - [ ] 时序查询响应时间 < 1秒
   - [ ] 大数据量查询正常

## 常见问题排查

### 导入失败

1. **检查文件格式**
   - [ ] 文件是否为有效的Excel格式
   - [ ] Sheet名称是否正确

2. **检查映射配置**
   - [ ] `indicator_mappings.json` 配置是否正确
   - [ ] 字段名称是否匹配

3. **查看错误日志**
   - [ ] 检查批次详情中的错误列表
   - [ ] 查看后端日志

### 看板无数据

1. **检查数据**
   - [ ] 确认已导入数据
   - [ ] 检查 `fact_indicator_ts` 表

2. **检查指标代码**
   - [ ] 确认指标代码正确
   - [ ] 检查 `dim_indicator` 表

3. **检查API**
   - [ ] 直接调用API测试
   - [ ] 查看API返回的错误信息

### 权限问题

1. **检查用户角色**
   - [ ] 确认用户角色配置正确
   - [ ] 检查 `sys_user_role` 表

2. **检查前端逻辑**
   - [ ] 查看 `Layout.vue` 中的权限判断
   - [ ] 确认 `userStore.user.roles` 正确

## 完成标志

- [ ] 所有数据库表已创建
- [ ] 基础数据已初始化
- [ ] 后端API正常运行
- [ ] 前端页面正常显示
- [ ] 导入功能测试通过
- [ ] 看板功能测试通过
- [ ] 权限控制正常
- [ ] 性能满足要求

## 后续优化建议

1. **文件存储**: 实现文件持久化存储系统
2. **导入调度**: 支持定时自动导入
3. **缓存机制**: 看板数据缓存优化
4. **监控告警**: 添加系统监控和告警
5. **日志系统**: 完善日志记录和分析
