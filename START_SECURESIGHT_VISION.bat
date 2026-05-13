@echo off
setlocal EnableExtensions

title SecureSight Vision Launcher - Auto Mode

echo.
echo ================================================================
echo SecureSight Vision Auto Launcher
echo ================================================================
echo.
echo This launcher chooses GPU mode when nvidia-smi is available.
echo If GPU mode fails because CUDA/cuDNN is not ready, use CPU mode.
echo.

where nvidia-smi >nul 2>nul
if errorlevel 1 (
    echo NVIDIA GPU tools not found. Starting portable CPU mode...
    call "%~dp0START_SECURESIGHT_VISION_CPU.bat"
) else (
    echo NVIDIA tools detected. Starting GPU mode...
    call "%~dp0START_SECURESIGHT_VISION_GPU.bat"
)
