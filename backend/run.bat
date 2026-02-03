@echo off
echo Activating virtual environment and starting development server...
cd /d D:\Workspace\hogprice-insight\backend

REM Check if virtual environment exists
if not exist "env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found! Please create it first.
    pause
    exit /b 1
)

REM Activate virtual environment
call env\Scripts\activate.bat

REM Check if uvicorn is installed by trying to import it
python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo uvicorn not installed, installing dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed!
        pause
        exit /b 1
    )
)

echo Starting FastAPI development server...
echo API Documentation: http://localhost:8000/docs
echo Press Ctrl+C to stop the server
echo.
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 --timeout-keep-alive 600
pause
