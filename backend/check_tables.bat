@echo off
echo Checking database tables...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

REM Run check script
python check_tables.py

pause
