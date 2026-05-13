@echo off
setlocal EnableExtensions

title SecureSight Vision CPU Backend
cd /d "%~dp0"

REM Portable mode: do not load global/user Python packages.
set "PYTHONNOUSERSITE=1"
set "PYTHONPATH="
set "FACE_PROVIDER=cpu"
set "FACE_CPU_WORKERS=auto"
set "OMP_NUM_THREADS=2"
set "MKL_NUM_THREADS=2"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"

set "VENV_DIR=%CD%\.venv-cpu"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REQ_FILE=%CD%\cpu_requirements.txt"
set "REQ_STAMP=%VENV_DIR%\.securesight-vision_cpu_requirements_installed"
set "REQ_VERSION=2026-05-12-cpu-parallel-exe"

echo.
echo ================================================================
echo SecureSight Vision CPU backend
echo Backend folder: %CD%
echo ================================================================
echo.

if not exist "%VENV_PY%" (
    echo Creating isolated CPU Python virtual environment...
    where py >nul 2>nul
    if errorlevel 1 (
        python -m venv "%VENV_DIR%"
    ) else (
        py -3.11 -m venv "%VENV_DIR%"
        if errorlevel 1 py -3 -m venv "%VENV_DIR%"
    )
    if errorlevel 1 (
        echo ERROR: Could not create Python virtual environment.
        echo Install Python 3.11 or Python 3.x and try again.
        pause
        exit /b 1
    )
)

if not exist "%VENV_PY%" (
    echo ERROR: Virtual environment Python was not found: %VENV_PY%
    pause
    exit /b 1
)

echo Using Python:
"%VENV_PY%" -c "import sys; print(sys.executable)"

echo.
set "NEED_INSTALL=0"
if not exist "%REQ_STAMP%" set "NEED_INSTALL=1"
if exist "%REQ_STAMP%" (
    set /p INSTALLED_REQ_VERSION=<"%REQ_STAMP%"
    if not "%INSTALLED_REQ_VERSION%"=="%REQ_VERSION%" set "NEED_INSTALL=1"
)

if "%NEED_INSTALL%"=="1" (
    echo Installing or refreshing CPU backend dependencies.
    echo This can take several minutes on first run.
    echo.
    "%VENV_PY%" -m pip install --upgrade pip setuptools wheel
    if errorlevel 1 goto install_failed
    "%VENV_PY%" -m pip uninstall -y onnxruntime-gpu
    "%VENV_PY%" -m pip install --upgrade --force-reinstall -r "%REQ_FILE%"
    if errorlevel 1 goto install_failed
    > "%REQ_STAMP%" echo %REQ_VERSION%
) else (
    echo CPU backend dependencies already installed. Skipping pip install.
)

echo.
echo Starting SecureSight Vision backend on http://127.0.0.1:8000
echo CPU mode is portable but slower than GPU mode.
echo CPU parallel frame workers: %FACE_CPU_WORKERS%
echo Face test: http://127.0.0.1:8000/face/test
echo.
"%VENV_PY%" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
exit /b 0

:install_failed
echo.
echo ERROR: Failed to install CPU requirements.
echo Check your internet connection, then run again.
echo You can also delete backend\.venv-cpu for a clean reinstall.
pause
exit /b 1
