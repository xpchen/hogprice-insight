@echo off
echo Fixing bcrypt dependency issue...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

echo Step 1: Uninstalling passlib...
python -m pip uninstall -y passlib

echo Step 2: Installing bcrypt...
python -m pip install bcrypt

echo Step 3: Testing bcrypt import...
python -c "import bcrypt; print('bcrypt imported successfully')"

if errorlevel 1 (
    echo ERROR: bcrypt installation failed!
    pause
    exit /b 1
)

echo.
echo bcrypt fixed successfully!
echo You can now run init_admin_user.bat
pause
