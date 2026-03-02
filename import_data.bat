@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  HogPrice 数据导入脚本 (Windows)
REM  使用方法：
REM    双击运行                    → 增量导入默认数据目录
REM    import_data.bat D:\数据\    → 增量导入指定目录
REM    import_data.bat --bulk      → 全量导入（清空重建）
REM ============================================================

REM 脚本所在目录（即项目根目录）
set "PROJ=%~dp0"
set "PROJ=%PROJ:~0,-1%"

REM 虚拟环境路径
set "VENV=%PROJ%\backend\env\Scripts\activate.bat"

REM 默认数据目录（Windows 路径）
set "DATA_DIR=%PROJ%\docs\生猪 2"

echo ============================================================
echo   HogPrice 数据导入
echo   项目目录: %PROJ%
echo ============================================================

REM 检查虚拟环境是否存在
if not exist "%VENV%" (
    echo.
    echo [错误] 未找到虚拟环境: %VENV%
    echo 请先在 backend 目录执行: python -m venv env
    echo 再执行: env\Scripts\activate ^&^& pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM 激活虚拟环境
call "%VENV%"

REM 解析参数
set "MODE_ARG="
set "DIR_ARG="

if "%~1"=="--bulk" (
    set "MODE_ARG=--mode bulk"
) else if not "%~1"=="" (
    set "DIR_ARG=%~1"
) else (
    set "DIR_ARG=%DATA_DIR%"
)

REM 检查数据目录
if not "%DIR_ARG%"=="" (
    if not exist "%DIR_ARG%" (
        echo.
        echo [错误] 数据目录不存在: %DIR_ARG%
        echo 请确认目录路径是否正确，或将数据放入:
        echo   %DATA_DIR%
        echo.
        pause
        exit /b 1
    )
)

REM 切换到项目根目录执行
cd /d "%PROJ%"

REM 运行导入脚本
if "%DIR_ARG%"=="" (
    echo 执行: python import_data.py %MODE_ARG%
    python import_data.py %MODE_ARG%
) else (
    echo 执行: python import_data.py "%DIR_ARG%" %MODE_ARG%
    python import_data.py "%DIR_ARG%" %MODE_ARG%
)

echo.
if %ERRORLEVEL%==0 (
    echo ============================================================
    echo   导入完成！
    echo ============================================================
) else (
    echo ============================================================
    echo   [警告] 脚本退出码: %ERRORLEVEL%，请检查上方日志
    echo ============================================================
)

pause
endlocal
