@echo off
echo Installing project dependencies...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create it first: python -m venv env
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call env\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing project dependencies (this may take a few minutes)...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo Dependency installation failed! Please check error messages.
    pause
    exit /b 1
)

echo.
echo Dependencies installation completed!
echo.
echo Next steps:
echo 1. Run init_db.bat to create database
echo 2. Run migrate.bat to run database migration
echo 3. Run run.bat to start development server
pause
