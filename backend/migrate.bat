@echo off
echo Activating virtual environment and running database migration...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found! Please create it first.
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

REM Check if alembic is installed by trying to import it
python -c "import alembic" >nul 2>&1
if errorlevel 1 (
    echo alembic not installed, installing dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed!
        pause
        exit /b 1
    )
)

echo Running database migration...
python -m alembic upgrade head
if errorlevel 1 (
    echo Migration failed! Please check error messages.
    pause
    exit /b 1
)

echo Migration completed!
pause
