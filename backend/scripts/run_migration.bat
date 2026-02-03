@echo off
chcp 65001 >nul
REM 运行数据库迁移和初始化

echo ==========================================
echo 运行数据库迁移和初始化
echo ==========================================

cd /d %~dp0\..

echo.
echo 步骤1: 运行数据库迁移...
python -m alembic upgrade head
if errorlevel 1 (
    echo 迁移失败！
    pause
    exit /b 1
)

echo.
echo 步骤2: 初始化基础数据...
set PYTHONIOENCODING=utf-8
python scripts\init_base_data.py
if errorlevel 1 (
    echo 初始化失败！
    pause
    exit /b 1
)

echo.
echo ==========================================
echo 完成！
echo ==========================================
pause
