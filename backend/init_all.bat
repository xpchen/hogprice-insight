@echo off
echo ========================================
echo HogPrice Insight - Complete Initialization
echo ========================================
echo.

cd /d D:\Workspace\hogprice-insight\backend

REM Check virtual environment
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create it first: python -m venv env
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/4] Activating virtual environment...
call env\Scripts\activate.bat

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

REM Create database
echo [2/4] Creating database (if not exists)...
python init_db.py
if errorlevel 1 (
    echo ERROR: Database creation failed!
    pause
    exit /b 1
)

REM Run database migration
echo [3/4] Running database migration...
alembic upgrade head
if errorlevel 1 (
    echo ERROR: Database migration failed!
    pause
    exit /b 1
)

REM Initialize admin user
echo [4/4] Initializing admin user...
python init_admin_user.py
if errorlevel 1 (
    echo ERROR: User initialization failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Initialization completed!
echo ========================================
echo.
echo Default login credentials:
echo   Username: admin
echo   Password: Admin@123
echo.
echo You can now run run.bat to start the server
echo ========================================
pause
