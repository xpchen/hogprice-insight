@echo off
echo Running SQL initialization script...
echo.
echo Please enter MySQL root password when prompted
echo.

mysql -u root -p < init_all_tables.sql

if errorlevel 1 (
    echo.
    echo ERROR: SQL script execution failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo SQL script executed successfully!
echo.
echo Next step: Run init_admin_user.bat to create admin user
pause
