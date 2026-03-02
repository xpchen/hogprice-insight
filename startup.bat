@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  HogPrice 启动脚本
REM  同时启动后端（端口 8000）和前端（端口 5173）
REM  后端和前端各在独立的最小化窗口中运行
REM ============================================================

set "PROJ=%~dp0"
set "PROJ=%PROJ:~0,-1%"

set "BACKEND=%PROJ%\backend"
set "VENV=%BACKEND%\env\Scripts\activate.bat"
set "FRONTEND=%PROJ%\frontend"

echo ============================================================
echo   HogPrice Insight 启动中...
echo   项目目录: %PROJ%
echo ============================================================

REM 检查虚拟环境
if not exist "%VENV%" (
    echo [错误] 虚拟环境不存在: %VENV%
    echo 请先执行安装步骤：cd backend ^&^& python -m venv env
    pause
    exit /b 1
)

REM 检查前端依赖
if not exist "%FRONTEND%\node_modules" (
    echo [错误] 前端依赖未安装，请先执行：cd frontend ^&^& npm install
    pause
    exit /b 1
)

echo.
echo [1/2] 启动后端服务 (http://localhost:8000)...
start "HogPrice Backend" /min cmd /k "chcp 65001 >nul && cd /d "%BACKEND%" && call env\Scripts\activate && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

REM 等待后端启动
timeout /t 3 /nobreak >nul

echo [2/2] 启动前端服务 (http://localhost:5173)...
start "HogPrice Frontend" /min cmd /k "chcp 65001 >nul && cd /d "%FRONTEND%" && npm run dev"

echo.
echo ============================================================
echo   启动完成！
echo   后端: http://localhost:8000
echo   前端: http://localhost:5173
echo   请稍等几秒后打开浏览器访问前端地址
echo ============================================================

REM 等待前端启动后自动打开浏览器
timeout /t 5 /nobreak >nul
start http://localhost:5173

endlocal
