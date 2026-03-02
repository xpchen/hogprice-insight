@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  取消 HogPrice 开机自启动
REM ============================================================

set "SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\HogPrice Insight.lnk"

echo ============================================================
echo   取消 HogPrice 开机自启动
echo ============================================================

if not exist "%SHORTCUT%" (
    echo 未找到自启动快捷方式，可能未注册或已删除。
    pause
    exit /b 0
)

del "%SHORTCUT%"

if %ERRORLEVEL%==0 (
    echo.
    echo ✅ 已取消开机自启动。
) else (
    echo [错误] 删除失败，请手动删除:
    echo   %SHORTCUT%
)

echo.
pause
endlocal
