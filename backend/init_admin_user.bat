@echo off
echo Initializing admin user...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

REM Run Python script
python init_admin_user.py

pause
