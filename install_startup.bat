@echo off
setlocal

set "PROJ=%~dp0"
set "PROJ=%PROJ:~0,-1%"
set "STARTUP_BAT=%PROJ%\startup.bat"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP_FOLDER%\HogPrice Insight.lnk"

echo ============================================================
echo   HogPrice Insight - Register Auto Startup
echo ============================================================

if not exist "%STARTUP_BAT%" (
    echo [ERROR] startup.bat not found: %STARTUP_BAT%
    pause
    exit /b 1
)

echo Creating shortcut in Windows Startup folder...
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$sc = $ws.CreateShortcut('%SHORTCUT%');" ^
  "$sc.TargetPath = '%STARTUP_BAT%';" ^
  "$sc.WorkingDirectory = '%PROJ%';" ^
  "$sc.WindowStyle = 7;" ^
  "$sc.Description = 'HogPrice Insight Auto Start';" ^
  "$sc.Save();"

if %ERRORLEVEL%==0 (
    echo.
    echo [OK] Auto startup registered successfully!
    echo      Shortcut: %SHORTCUT%
    echo.
    echo HogPrice will start automatically on next Windows login.
    echo To unregister, run uninstall_startup.bat
) else (
    echo [ERROR] Failed to create shortcut. Please check PowerShell is available.
)

echo.
pause
endlocal
