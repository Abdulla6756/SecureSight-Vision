@echo off
setlocal EnableExtensions

title SecureSight Vision Launcher - Portable CPU Mode

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

set "BACKEND_PORT=8000"
set "FRONTEND_PORT=3000"
set "API_URL=http://127.0.0.1:%BACKEND_PORT%"

echo.
echo ================================================================
echo SecureSight Vision portable CPU launcher
echo Project: %PROJECT_DIR%
echo ================================================================
echo.

if not exist "%PROJECT_DIR%\backend\main.py" (
    echo ERROR: backend\main.py not found.
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%\frontend\server.js" (
    echo ERROR: frontend\server.js not found.
    pause
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not available in PATH.
    echo Install Node.js LTS, then run this launcher again.
    pause
    exit /b 1
)

echo Node.js detected:
node --version

echo.
echo Starting backend in CPU mode. This is the most portable mode.
echo No NVIDIA GPU or CUDA installation is required.
echo.

start "SecureSight Vision CPU Backend" cmd /k "cd /d ""%PROJECT_DIR%\backend"" && call start_cpu_backend.bat"

echo Waiting for backend window to start...
timeout /t 5 /nobreak >nul

start "SecureSight Vision Node Frontend" cmd /k "cd /d ""%PROJECT_DIR%\frontend"" && set ""API_URL=%API_URL%"" && set ""FRONTEND_PORT=%FRONTEND_PORT%"" && node server.js"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:%FRONTEND_PORT%"

echo.
echo SecureSight Vision is starting in portable CPU mode.
echo Frontend:  http://127.0.0.1:%FRONTEND_PORT%
echo Backend:   %API_URL%
echo.
echo Keep both command windows open while using the app.
echo.
pause
