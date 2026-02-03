#!/bin/bash
# 运行数据库迁移和初始化（Linux/Mac）

set -e

echo "=========================================="
echo "运行数据库迁移和初始化"
echo "=========================================="

cd "$(dirname "$0")/.."

echo ""
echo "步骤1: 运行数据库迁移..."
python -m alembic upgrade head

echo ""
echo "步骤2: 初始化基础数据..."
export PYTHONIOENCODING=utf-8
python scripts/init_base_data.py

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="
