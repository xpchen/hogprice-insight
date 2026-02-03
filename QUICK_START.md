# 快速启动指南

## 一键启动（推荐）

### Windows

```bash
cd backend
scripts\quick_start.bat
```

### Linux/Mac

```bash
cd backend
chmod +x scripts/quick_start.sh
./scripts/quick_start.sh
```

## 手动启动步骤

### 1. 后端启动

```bash
# 进入后端目录
cd backend

# 安装依赖
pip install -r requirements.txt
pip install -r requirements_upgrade.txt  # 可选：农历库

# 运行数据库迁移
alembic upgrade head

# 初始化基础数据
python scripts/init_base_data.py

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 验证安装

1. **后端API**: 访问 http://localhost:8000/docs
2. **前端页面**: 访问 http://localhost:5173（或配置的端口）

## 常见问题

### 数据库连接失败

检查 `.env` 文件中的 `DATABASE_URL` 配置

### 迁移失败

确保数据库用户有创建表的权限

### 端口被占用

修改启动命令中的端口号

## 下一步

- 查看 [README_UPGRADE.md](README_UPGRADE.md) 了解详细功能
- 查看 [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) 进行完整测试
