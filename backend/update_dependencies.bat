@echo off
echo Updating dependencies...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip

REM Uninstall passlib to avoid conflicts
echo Uninstalling passlib...
python -m pip uninstall -y passlib

REM Install bcrypt directly
echo Installing bcrypt...
python -m pip install bcrypt

REM Install/update all dependencies
echo Installing/updating all dependencies...
python -m pip install -r requirements.txt

echo.
echo Dependencies updated successfully!
echo.
pause
