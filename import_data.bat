@echo off
setlocal

REM ============================================================
REM  HogPrice Data Import (Windows)
REM  Usage:
REM    Double-click                 -> incremental import (default dir)
REM    import_data.bat D:\data\     -> incremental import (custom dir)
REM    import_data.bat --bulk       -> full import (truncate + insert)
REM ============================================================

set "PROJ=%~dp0"
set "PROJ=%PROJ:~0,-1%"
set "VENV=%PROJ%\backend\env\Scripts\activate.bat"
set "DATA_DIR=%PROJ%\docs\生猪 2"

echo ============================================================
echo   HogPrice Data Import
echo   Project: %PROJ%
echo ============================================================

if not exist "%VENV%" (
    echo.
    echo [ERROR] Virtual environment not found: %VENV%
    echo Please run: cd backend ^&^& python -m venv env ^&^& pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

call "%VENV%"

set "MODE_ARG="
set "DIR_ARG="

if "%~1"=="--bulk" (
    set "MODE_ARG=--mode bulk"
) else if not "%~1"=="" (
    set "DIR_ARG=%~1"
) else (
    set "DIR_ARG=%DATA_DIR%"
)

if not "%DIR_ARG%"=="" (
    if not exist "%DIR_ARG%" (
        echo.
        echo [ERROR] Data directory not found: %DIR_ARG%
        echo.
        pause
        exit /b 1
    )
)

cd /d "%PROJ%"

if "%DIR_ARG%"=="" (
    echo Running: python import_data.py %MODE_ARG%
    python import_data.py %MODE_ARG%
) else (
    echo Running: python import_data.py "%DIR_ARG%" %MODE_ARG%
    python import_data.py "%DIR_ARG%" %MODE_ARG%
)

echo.
if %ERRORLEVEL%==0 (
    echo ============================================================
    echo   Import complete!
    echo ============================================================
) else (
    echo ============================================================
    echo   [WARNING] Exit code: %ERRORLEVEL%, check the log above.
    echo ============================================================
)

pause
endlocal
