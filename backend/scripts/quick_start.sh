#!/bin/bash
# 快速启动脚本（Linux/Mac）

set -e

echo "=========================================="
echo "生猪行情洞察系统 - 快速启动"
echo "=========================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.8+"
    exit 1
fi

# 检查数据库连接（需要根据实际情况修改）
echo ""
echo "步骤1: 检查数据库连接..."
# TODO: 添加数据库连接检查

# 安装依赖
echo ""
echo "步骤2: 安装Python依赖..."
pip install -r requirements.txt
if [ -f requirements_upgrade.txt ]; then
    pip install -r requirements_upgrade.txt
fi

# 运行数据库迁移
echo ""
echo "步骤3: 运行数据库迁移..."
alembic upgrade head

# 初始化基础数据
echo ""
echo "步骤4: 初始化基础数据..."
python scripts/init_base_data.py

# 启动服务
echo ""
echo "步骤5: 启动后端服务..."
echo "服务将在 http://localhost:8000 启动"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="

uvicorn main:app --reload --host 0.0.0.0 --port 8000
