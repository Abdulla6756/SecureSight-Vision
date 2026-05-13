@echo off
setlocal EnableExtensions

title SecureSight Vision GPU Backend
cd /d "%~dp0"

REM Prevent Python from loading global/user site-packages such as a system Torch install.
set "PYTHONNOUSERSITE=1"
set "PYTHONPATH="
set "FACE_PROVIDER=cuda"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"

set "VENV_DIR=%CD%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REQ_FILE=%CD%\gpu_requirements.txt"
set "REQ_STAMP=%VENV_DIR%\.securesight-vision_gpu_requirements_installed"
set "REQ_VERSION=2026-05-12-gpu-cusolver-cusparse"

echo.
echo ================================================================
echo SecureSight Vision GPU backend
echo Backend folder: %CD%
echo ================================================================
echo.

where nvidia-smi >nul 2>nul
if errorlevel 1 (
    echo WARNING: nvidia-smi was not found in PATH.
    echo Install or update the NVIDIA driver if CUDA cannot start.
) else (
    nvidia-smi
)

if not exist "%VENV_PY%" (
    echo.
    echo Creating isolated Python virtual environment...
    where py >nul 2>nul
    if errorlevel 1 (
        python -m venv "%VENV_DIR%"
    ) else (
        py -3.11 -m venv "%VENV_DIR%"
        if errorlevel 1 py -3 -m venv "%VENV_DIR%"
    )
    if errorlevel 1 (
        echo ERROR: Could not create Python virtual environment.
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
    echo Installing or refreshing backend GPU dependencies.
    echo Reason: first run or GPU dependency list changed.
    echo This can take several minutes on first run.
    echo.
    "%VENV_PY%" -m pip install --upgrade pip setuptools wheel
    if errorlevel 1 goto install_failed
    "%VENV_PY%" -m pip uninstall -y onnxruntime onnxruntime-gpu
    if errorlevel 1 goto install_failed
    "%VENV_PY%" -m pip install --upgrade --force-reinstall -r "%REQ_FILE%"
    if errorlevel 1 goto install_failed
    > "%REQ_STAMP%" echo %REQ_VERSION%
) else (
    echo Backend GPU dependencies already installed and version stamp matches. Skipping pip install.
    echo To force reinstall, delete: %REQ_STAMP%
)

echo.
echo GPU preflight check:
"%VENV_PY%" gpu_environment_preflight.py
if errorlevel 1 (
    echo.
    echo ERROR: GPU preflight failed. SecureSight Vision requires GPU and will not run on CPU silently.
    echo If you changed CUDA/Python packages, delete backend\.venv and run START_SECURESIGHT_VISION_GPU.bat again.
    pause
    exit /b 1
)

echo.
echo Starting SecureSight Vision backend on http://127.0.0.1:8000
echo Face test: http://127.0.0.1:8000/face/test
echo.
"%VENV_PY%" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
exit /b 0

:install_failed
echo.
echo ERROR: Failed to install GPU requirements.
echo Check your internet connection, then run again.
echo You can also delete backend\.venv for a clean reinstall.
pause
exit /b 1
