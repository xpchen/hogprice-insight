@echo off
echo Generating SQL script with admin user...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

REM Generate SQL with admin user
echo Generating SQL with admin user password hash...
python generate_admin_sql.py

if errorlevel 1 (
    echo ERROR: Failed to generate SQL script!
    pause
    exit /b 1
)

echo.
echo Running SQL script...
echo Please enter MySQL root password when prompted
echo.

mysql -u root -p < init_all_tables_with_admin.sql

if errorlevel 1 (
    echo.
    echo ERROR: SQL script execution failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo SQL script executed successfully!
echo ========================================
echo.
echo Default login credentials:
echo   Username: admin
echo   Password: Admin@123
echo.
pause
