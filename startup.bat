@echo off
setlocal

set "PROJ=%~dp0"
set "PROJ=%PROJ:~0,-1%"
set "BACKEND=%PROJ%\backend"
set "VENV=%BACKEND%\env\Scripts\activate.bat"
set "FRONTEND=%PROJ%\frontend"

echo ============================================================
echo   HogPrice Insight - Starting...
echo   Project: %PROJ%
echo ============================================================

if not exist "%VENV%" (
    echo [ERROR] Virtual environment not found: %VENV%
    echo Please run: cd backend ^&^& python -m venv env ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "%FRONTEND%\node_modules" (
    echo [ERROR] Frontend dependencies not installed.
    echo Please run: cd frontend ^&^& npm install
    pause
    exit /b 1
)

echo [1/2] Starting backend (http://localhost:8000)...
start "HogPrice Backend" /min cmd /k "cd /d "%BACKEND%" && call env\Scripts\activate && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting frontend (http://localhost:5173)...
start "HogPrice Frontend" /min cmd /k "cd /d "%FRONTEND%" && npm run dev"

echo.
echo ============================================================
echo   Done! Opening browser in 5 seconds...
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo ============================================================

timeout /t 5 /nobreak >nul
start http://localhost:5173

endlocal
