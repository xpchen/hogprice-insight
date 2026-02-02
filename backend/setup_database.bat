@echo off
echo Setting up database...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

echo Step 1: Checking database tables...
python check_tables.py

if errorlevel 1 (
    echo.
    echo Tables are missing. Creating tables...
    echo.
    echo Option 1: Run SQL script (recommended)
    echo   mysql -u root -p < init_all_tables.sql
    echo.
    echo Option 2: Run Alembic migration
    echo   alembic upgrade head
    echo.
    echo Please choose an option:
    echo   1. Run SQL script
    echo   2. Run Alembic migration
    echo   3. Exit
    echo.
    set /p choice="Enter choice (1/2/3): "
    
    if "%choice%"=="1" (
        echo.
        echo Please enter MySQL root password when prompted...
        mysql -u root -p < init_all_tables.sql
        if errorlevel 1 (
            echo SQL script execution failed!
            pause
            exit /b 1
        )
        echo SQL script executed successfully!
    ) else if "%choice%"=="2" (
        echo Running Alembic migration...
        python -m alembic upgrade head
        if errorlevel 1 (
            echo Migration failed!
            pause
            exit /b 1
        )
        echo Migration completed!
    ) else (
        echo Exiting...
        pause
        exit /b 0
    )
    
    echo.
    echo Verifying tables...
    python check_tables.py
)

echo.
echo Step 2: Checking admin user...
python check_user.py

if errorlevel 1 (
    echo.
    echo Admin user not found or password incorrect. Creating/updating...
    python init_admin_user.py
)

echo.
echo Database setup completed!
pause
