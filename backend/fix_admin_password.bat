@echo off
echo Fixing admin user password...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

REM Run fix script
python fix_admin_password.py

pause
