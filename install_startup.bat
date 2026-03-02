@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  注册 HogPrice 开机自启动
REM  将 startup.bat 的快捷方式添加到 Windows 启动文件夹
REM ============================================================

set "PROJ=%~dp0"
set "PROJ=%PROJ:~0,-1%"
set "STARTUP_BAT=%PROJ%\startup.bat"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP_FOLDER%\HogPrice Insight.lnk"

echo ============================================================
echo   注册 HogPrice 开机自启动
echo ============================================================

REM 检查 startup.bat 是否存在
if not exist "%STARTUP_BAT%" (
    echo [错误] 未找到启动脚本: %STARTUP_BAT%
    pause
    exit /b 1
)

REM 使用 PowerShell 创建快捷方式
echo 正在创建快捷方式...
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$sc = $ws.CreateShortcut('%SHORTCUT%');" ^
  "$sc.TargetPath = '%STARTUP_BAT%';" ^
  "$sc.WorkingDirectory = '%PROJ%';" ^
  "$sc.WindowStyle = 7;" ^
  "$sc.Description = 'HogPrice Insight 自动启动';" ^
  "$sc.Save();"

if %ERRORLEVEL%==0 (
    echo.
    echo ✅ 开机自启动注册成功！
    echo    快捷方式位置: %SHORTCUT%
    echo.
    echo 下次开机登录后将自动启动前后端服务。
    echo 如需取消，请运行 uninstall_startup.bat
) else (
    echo [错误] 注册失败，请检查 PowerShell 是否可用。
)

echo.
pause
endlocal
