@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title SecureSight Vision - Windows CPU EXE Builder

echo ============================================================
echo  SecureSight Vision - CPU EXE Builder with Parallel Analysis
echo ============================================================
echo.
echo This builds a Windows CPU EXE on this Windows machine.
echo Output will be created in: dist\SecureSightVision\
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found. Install 64-bit Python 3.11 first.
  pause
  exit /b 1
)

set BUILD_STAMP=.build_venv\SSV_CPU_BUILD_V6_MATPLOTLIB_AGG.txt
if exist .build_venv if not exist "%BUILD_STAMP%" (
  echo Old build environment detected. Recreating it to avoid broken DLLs...
  rmdir /S /Q .build_venv
)

if not exist .build_venv (
  echo [1/7] Creating clean build virtual environment...
  python -m venv .build_venv
  if errorlevel 1 goto :fail
)

call .build_venv\Scripts\activate.bat
if errorlevel 1 goto :fail

set PYTHONNOUSERSITE=1
set PYTHONPATH=
set FACE_PROVIDER=cpu
set FACE_CPU_WORKERS=auto

echo [2/7] Upgrading pip tools...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :fail

echo [3/7] Removing GPU/conflicting ONNX packages...
python -m pip uninstall -y onnxruntime-gpu onnxruntime >nul 2>nul

echo [4/7] Installing CPU runtime and PyInstaller...
python -m pip install --no-cache-dir -r backend\cpu_requirements.txt pyinstaller==6.11.1
if errorlevel 1 goto :fail

echo [5/7] Repairing/testing ONNX Runtime CPU DLL import...
python build_tools\repair_onnxruntime_cpu.py
if errorlevel 1 goto :ortfail

echo [6/7] Running full CPU runtime preflight...
python backend\cpu_runtime_preflight.py
if errorlevel 1 goto :fail

echo [7/7] Building SecureSightVision.exe with lean PyInstaller spec + matplotlib Agg...
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist
pyinstaller --clean --noconfirm SecureSightVision.spec
if errorlevel 1 goto :fail

if not exist dist\SecureSightVision mkdir dist\SecureSightVision
copy /Y EXE_README.md dist\SecureSightVision\EXE_README.md >nul
if exist docs xcopy /E /I /Y docs dist\SecureSightVision\docs >nul

echo ok>"%BUILD_STAMP%"

echo.
echo ============================================================
echo  DONE
echo ============================================================
echo Your EXE is here:
echo   dist\SecureSightVision\SecureSightVision.exe
echo.
echo For submission, zip the whole folder:
echo   dist\SecureSightVision\
echo Do not submit only the EXE file by itself.
echo.
pause
exit /b 0

:ortfail
echo.
echo ERROR: ONNX Runtime CPU could not initialize.
echo Most common fix: install Microsoft Visual C++ Redistributable 2015-2022 x64,
echo then delete .build_venv and run this builder again.
echo If this is a very old CPU without AVX support, ONNX Runtime may not run.
echo.
pause
exit /b 1

:fail
echo.
echo ERROR: Build failed. Check the message above.
pause
exit /b 1
