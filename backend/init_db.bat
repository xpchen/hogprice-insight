@echo off
echo Activating virtual environment and initializing database...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found! Please create it first.
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

REM Check if pymysql is installed
python -c "import pymysql" >nul 2>&1
if errorlevel 1 (
    echo pymysql not installed, installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed!
        pause
        exit /b 1
    )
)

echo Creating database (if not exists)...
python init_db.py
if errorlevel 1 (
    echo Database initialization failed! Please check error messages.
    pause
    exit /b 1
)

echo Database initialization completed!
pause
