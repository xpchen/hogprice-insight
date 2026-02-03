@echo off
echo Testing login API...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

REM Check if requests is installed
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo requests not installed, installing...
    python -m pip install requests
    if errorlevel 1 (
        echo Failed to install requests!
        pause
        exit /b 1
    )
)

REM Run test
python test_login_api.py

pause
