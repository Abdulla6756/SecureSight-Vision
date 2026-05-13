@echo off
title SecureSight Vision CUDA / cuFFT Diagnostic

cd /d "%~dp0"

if not exist ".venv" (
    echo ERROR: .venv not found. Run start_gpu_backend.bat first.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo ============================================================
echo Python
echo ============================================================
python --version

echo.
echo ============================================================
echo NVIDIA driver
echo ============================================================
nvidia-smi

echo.
echo ============================================================
echo ONNX Runtime providers and DLL preload
echo ============================================================
python -c "import onnxruntime as ort; print('ORT:', ort.__version__); print('Providers:', ort.get_available_providers()); print('Has preload_dlls:', hasattr(ort, 'preload_dlls')); print('preload empty:', ort.preload_dlls(cuda=True,cudnn=True,msvc=True,directory='') if hasattr(ort,'preload_dlls') else 'not available'); print('preload none:', ort.preload_dlls(cuda=True,cudnn=True,msvc=True,directory=None) if hasattr(ort,'preload_dlls') else 'not available')"

echo.
echo ============================================================
echo Check CUDA DLL files inside NVIDIA Python packages
echo ============================================================
python -c "import site, pathlib; names=['cufft64_11.dll','cudart64_12.dll','cublas64_12.dll','cudnn64_9.dll']; roots=site.getsitepackages()+[site.getusersitepackages()]; print('site roots:', roots); [print(n, [str(p) for r in roots for p in pathlib.Path(r).glob('nvidia/**/'+n)]) for n in names]"

echo.
echo ============================================================
echo Installed NVIDIA packages
echo ============================================================
python -m pip show onnxruntime-gpu
python -m pip show nvidia-cufft-cu12
python -m pip show nvidia-cudnn-cu12
python -m pip show nvidia-cublas-cu12
python -m pip show nvidia-cuda-runtime-cu12
python -m pip show nvidia-cuda-nvrtc-cu12
python -m pip show nvidia-curand-cu12
python -m pip show nvidia-cusolver-cu12
python -m pip show nvidia-cusparse-cu12
python -m pip show nvidia-nvjitlink-cu12

echo.
pause
