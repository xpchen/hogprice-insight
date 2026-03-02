@echo off
setlocal

set "SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\HogPrice Insight.lnk"

echo ============================================================
echo   HogPrice Insight - Remove Auto Startup
echo ============================================================

if not exist "%SHORTCUT%" (
    echo Auto startup shortcut not found. Already removed or never registered.
    pause
    exit /b 0
)

del "%SHORTCUT%"

if %ERRORLEVEL%==0 (
    echo.
    echo [OK] Auto startup removed successfully.
) else (
    echo [ERROR] Failed to delete shortcut. Please delete manually:
    echo   %SHORTCUT%
)

echo.
pause
endlocal
