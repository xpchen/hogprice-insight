# 五类数据全量入库自测脚本使用说明

## 脚本功能

`test_import_all_data.py` 脚本用于自动导入以下五类数据：

1. **钢联价格模板** (`1、价格：钢联自动更新模板.xlsx`) - GANGLIAN_DAILY
2. **涌益日度数据** (`2026年2月2日涌益咨询日度数据.xlsx`) - YONGYI_DAILY
3. **DCE 生猪期货** (`lh_ftr.xlsx`) - LH_FTR
4. **DCE 生猪期权** (`lh_opt.xlsx`) - LH_OPT
5. **涌益周度数据** (`2026.1.16-2026.1.22涌益咨询 周度数据.xlsx`) - YONGYI_WEEKLY

## 使用前准备

### 1. 确保数据库已初始化

```bash
# 运行数据库迁移
cd backend
alembic upgrade head

# 初始化基础数据（如果需要）
python scripts/init_base_data.py
python scripts/init_dim_source_data.py
```

### 2. 加载 ingest_profile 配置

```bash
# 加载配置文件到数据库
python scripts/load_ingest_profiles.py
```

### 3. 初始化交割城市数据（可选）

```bash
# 初始化交割城市数据
python scripts/init_delivery_cities.py
```

### 4. 确保文件存在

确保以下文件存在于 `docs/` 目录：

- `1、价格：钢联自动更新模板.xlsx`
- `2026年2月2日涌益咨询日度数据.xlsx`
- `lh_ftr.xlsx`
- `lh_opt.xlsx`
- `2026.1.16-2026.1.22涌益咨询 周度数据.xlsx`

## 运行脚本

```bash
cd backend
python scripts/test_import_all_data.py
```

## 脚本输出

脚本会显示：

1. **准备阶段**
   - 测试用户准备
   - 配置检查

2. **导入阶段**
   - 每个文件的处理进度
   - 模板类型检测结果
   - 导入结果（新增/更新/错误数）
   - 耗时统计

3. **验证阶段**
   - 最近批次列表
   - 各事实表记录数统计

4. **汇总报告**
   - 成功/失败文件数
   - 总新增/更新/错误数
   - 总耗时

## 导入方式说明

- **LH_FTR / LH_OPT**: 使用旧的导入器 (`import_lh_ftr`, `import_lh_opt`)
- **YONGYI_DAILY / YONGYI_WEEKLY / GANGLIAN_DAILY**: 使用统一导入工作流 (`unified_import`)

## 错误处理

- 如果某个文件导入失败，脚本会询问是否继续导入下一个文件
- 所有错误信息都会记录到 `ingest_error` 表
- 批次状态会更新为 `success` / `partial` / `failed`

## 验证导入结果

导入完成后，可以通过以下方式验证：

### 1. 查看批次列表

```sql
SELECT id, filename, status, success_rows, failed_rows, inserted_count, updated_count
FROM import_batch
ORDER BY id DESC
LIMIT 10;
```

### 2. 查看事实表记录数

```sql
-- 观测数据
SELECT COUNT(*) FROM fact_observation;

-- 期货数据
SELECT COUNT(*) FROM fact_futures_daily;

-- 期权数据
SELECT COUNT(*) FROM fact_options_daily;

-- 指标时间序列
SELECT COUNT(*) FROM fact_indicator_ts;
```

### 3. 查看错误信息

```sql
SELECT sheet_name, error_type, message
FROM ingest_error
ORDER BY id DESC
LIMIT 20;
```

## 常见问题

### 1. 配置文件未加载

**错误**: `未找到profile: dataset_type=YONGYI_DAILY`

**解决**: 运行 `python scripts/load_ingest_profiles.py`

### 2. 用户不存在

**错误**: `用户不存在`

**解决**: 运行 `python init_admin_user.py` 创建admin用户

### 3. 文件不存在

**错误**: `文件不存在`

**解决**: 检查文件路径是否正确，文件是否存在于 `docs/` 目录

### 4. 模板类型检测失败

**错误**: `不支持的模板类型`

**解决**: 检查文件名是否符合命名规范，或手动指定模板类型

## 注意事项

1. **数据幂等性**: 重复运行脚本会更新已存在的数据（基于 dedup_key）
2. **数据库连接**: 确保数据库连接配置正确
3. **文件格式**: 确保 Excel 文件格式正确，未被损坏
4. **内存使用**: 大文件导入可能占用较多内存，建议在服务器环境运行

## 下一步

导入完成后，可以：

1. 运行指标抽取任务（如果配置了自动抽取）
2. 在前端查看导入的数据
3. 验证数据完整性和准确性
