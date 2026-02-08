@echo off
setlocal enabledelayedexpansion

echo [INFO] Activating virtual environment and starting development server...

REM ---- Project root ----
set "PROJ=D:\Workspace\hogprice-insight\backend"
cd /d "%PROJ%" || (echo [ERROR] cd failed: "%PROJ%" & pause & exit /b 1)

REM ---- Check venv ----
set "ACT=%PROJ%\env\Scripts\activate.bat"
if not exist "%ACT%" (
    echo [ERROR] Virtual environment not found: "%ACT%"
    echo [HINT] Create it with:
    echo        python -m venv env
    echo        env\Scripts\python -m pip install -U pip
    pause
    exit /b 1
)

REM ---- Activate venv ----
call "%ACT%"

REM ---- Use venv python/pip explicitly (avoid system python confusion) ----
set "PY=%PROJ%\env\Scripts\python.exe"
set "PIP=%PROJ%\env\Scripts\pip.exe"

if not exist "%PY%" (
    echo [ERROR] venv python not found: "%PY%"
    pause
    exit /b 1
)

REM ---- Ensure requirements exists ----
if not exist "%PROJ%\requirements.txt" (
    echo [ERROR] requirements.txt not found in: "%PROJ%"
    pause
    exit /b 1
)

REM ---- Check uvicorn installed in venv ----
"%PY%" -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [WARN] uvicorn not installed in venv, installing dependencies...
    "%PY%" -m pip install -U pip
    if errorlevel 1 (
        echo [ERROR] pip upgrade failed!
        pause
        exit /b 1
    )

    "%PY%" -m pip install -r "%PROJ%\requirements.txt"
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed!
        echo [HINT] Try:
        echo        "%PY%" -m pip install -r "%PROJ%\requirements.txt" -v
        pause
        exit /b 1
    )
)

REM ---- Start server ----
echo [INFO] Starting FastAPI development server...
echo [INFO] API Documentation: http://localhost:8000/docs
echo [INFO] Press Ctrl+C to stop the server
echo.

REM host:
REM - local dev only: 127.0.0.1
REM - LAN access:     0.0.0.0
set "HOST=0.0.0.0"
set "PORT=8000"

REM Limit reload scanning to project folder (faster & fewer surprises)
"%PY%" -m uvicorn main:app --reload --reload-dir "%PROJ%" --host %HOST% --port %PORT% --timeout-keep-alive 600

echo.
echo [INFO] Server stopped.
pause
endlocal