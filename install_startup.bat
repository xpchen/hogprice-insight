@echo off
setlocal

set "PROJ=%~dp0"
set "PROJ=%PROJ:~0,-1%"
set "SILENT_VBS=%PROJ%\startup_silent.vbs"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP_FOLDER%\HogPrice Insight.lnk"

echo ============================================================
echo   HogPrice Insight - Register Auto Startup
echo ============================================================

if not exist "%SILENT_VBS%" (
    echo [ERROR] startup_silent.vbs not found: %SILENT_VBS%
    pause
    exit /b 1
)

echo Creating shortcut in Windows Startup folder...
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$sc = $ws.CreateShortcut('%SHORTCUT%');" ^
  "$sc.TargetPath = 'wscript.exe';" ^
  "$sc.Arguments = '\""%SILENT_VBS%\""';" ^
  "$sc.WorkingDirectory = '%PROJ%';" ^
  "$sc.WindowStyle = 7;" ^
  "$sc.Description = 'HogPrice Insight Auto Start';" ^
  "$sc.Save();"

if %ERRORLEVEL%==0 (
    echo.
    echo [OK] Auto startup registered successfully!
    echo      Shortcut: %SHORTCUT%
    echo.
    echo HogPrice will start silently on next Windows login.
    echo No windows will pop up. Browser opens automatically after ~10s.
    echo To unregister, run uninstall_startup.bat
) else (
    echo [ERROR] Failed to create shortcut.
)

echo.
pause
endlocal
