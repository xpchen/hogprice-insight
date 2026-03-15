@echo off
setlocal

REM ============================================================
REM  HogPrice Data Import (Windows) - Full import
REM  Usage:
REM    Double-click                 -> full import (data dir: docs)
REM    import_data.bat D:\data\     -> full import (custom dir)
REM ============================================================
REM  Full import = truncate fact tables then insert from Excel;
REM  includes 3.2 enterprise monthly.
REM  Default data dir: docs\0306_*\* (e.g. docs\0306_??\??) via short path, no Chinese in file.
REM ============================================================

set "PROJ=%~dp0"
set "PROJ=%PROJ:~0,-1%"
set "VENV=%PROJ%\backend\env\Scripts\activate.bat"
set "DATA_DIR=%PROJ%\docs"
for /d %%A in ("%PROJ%\docs\0306_*") do for /d %%B in ("%%A\*") do set "DATA_DIR=%%~sB"

echo ============================================================
echo   HogPrice Data Import (full)
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

set "DIR_ARG=%DATA_DIR%"
if not "%~1"=="" set "DIR_ARG=%~1"

if not exist "%DIR_ARG%" (
    echo.
    echo [ERROR] Data directory not found: %DIR_ARG%
    echo.
    pause
    exit /b 1
)

cd /d "%PROJ%"

echo Running: python import_data.py "%DIR_ARG%" --mode bulk
python import_data.py "%DIR_ARG%" --mode bulk

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
