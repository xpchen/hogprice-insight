# HogPrice Insight（猪价智盘）

一个完整的Python Web数据分析与报表系统，支持Excel数据导入、指标解析、多维查询分析和报表导出。

## 技术栈

- **后端**: FastAPI + SQLAlchemy + Alembic + MySQL
- **前端**: Vue3 + Element-Plus + ECharts + Axios
- **数据处理**: Pandas + openpyxl + xlsxwriter
- **部署**: Docker Compose + Nginx

## 项目结构

```
hogprice-insight/
  backend/
    app/
      api/          # API端点
      core/         # 核心配置（数据库、安全等）
      models/       # SQLAlchemy模型
      services/     # 业务逻辑服务
      utils/        # 工具函数
    alembic/        # 数据库迁移
    main.py         # FastAPI应用入口
  frontend/
    src/
      api/          # API客户端
      views/         # 页面组件
      components/    # 通用组件
      router/       # 路由配置
      store/         # 状态管理
  deploy/           # 部署配置
  docs/             # 项目文档
```

## 快速开始

### 1. 环境要求

- Docker & Docker Compose
- Python 3.11+（本地开发）
- Node.js 18+（前端开发）

### 2. 使用Docker Compose启动（推荐）

```bash
# 启动所有服务
cd deploy
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

服务启动后：
- 前端：http://localhost:8080
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

### 3. 数据库迁移

```bash
cd backend
alembic upgrade head
```

### 4. 初始化数据（可选）

创建初始用户和角色（需要手动执行SQL或通过API）：

```sql
-- 创建角色
INSERT INTO sys_role (code, name) VALUES ('admin', '管理员'), ('analyst', '分析师'), ('viewer', '查看者');

-- 创建用户（密码需要先hash）
-- 使用Python: from app.core.security import get_password_hash; print(get_password_hash('your_password'))
```

### 5. 本地开发

**后端开发：**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**前端开发：**
```bash
cd frontend
npm install
npm run dev
```

## 功能特性

- ✅ 用户认证与权限管理（JWT）
- ✅ Excel数据导入与解析
- ✅ 指标自动解析（支持多维度）
- ✅ 多维数据查询与分析
- ✅ 时间序列图表展示
- ✅ Excel报表导出（含图表）

## 文档

- [项目计划](docs/PROJECT_PLAN.md)
- [指标解析规则](docs/指标解析规则.md)
- [数据库DDL](docs/数据库DDL_Alembic迁移草案.md)

## 下一步开发

1. 完善TopN查询功能
2. 实现报表模板（日报/周报/月报）
3. 添加数据权限细粒度控制
4. 实现定时任务和自动导入
