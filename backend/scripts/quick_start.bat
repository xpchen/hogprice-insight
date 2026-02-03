@echo off
REM 快速启动脚本（Windows）

echo ==========================================
echo 生猪行情洞察系统 - 快速启动
echo ==========================================

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 安装依赖
echo.
echo 步骤1: 安装Python依赖...
pip install -r requirements.txt
if exist requirements_upgrade.txt (
    pip install -r requirements_upgrade.txt
)

REM 运行数据库迁移
echo.
echo 步骤2: 运行数据库迁移...
alembic upgrade head

REM 初始化基础数据
echo.
echo 步骤3: 初始化基础数据...
python scripts\init_base_data.py

REM 启动服务
echo.
echo 步骤4: 启动后端服务...
echo 服务将在 http://localhost:8000 启动
echo API文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo ==========================================

uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
