# SecureSight Vision GPU setup

Your log showed:

`Could not locate cudnn_engines_tensor_ir64_9.dll`

That means ONNX Runtime can see the CUDA provider, but Windows cannot load the full cuDNN 9 DLL set required by the CUDA execution provider.

## What the updated launcher does

`backend/start_gpu_backend.bat` now:

1. Installs `onnxruntime-gpu[cuda,cudnn]==1.21.1`.
2. Installs the NVIDIA CUDA 12 / cuDNN 9 runtime wheels.
3. Runs `gpu_environment_preflight.py` before starting the server.
4. Stops if GPU is not ready, instead of silently falling back to CPU.

## How to run

Double-click:

`START_SECURESIGHT_VISION_GPU.bat`

Then check the backend window. You should see:

`GPU preflight PASSED. SecureSight Vision can request CUDAExecutionProvider.`

And later:

`Selected: ['CUDAExecutionProvider', 'CPUExecutionProvider']`

## If it still fails

1. Update your NVIDIA display driver.
2. Delete `backend\.venv`.
3. Run `START_SECURESIGHT_VISION_GPU.bat` again so it builds a fresh environment.
4. If the preflight still says a DLL is missing, copy the exact missing DLL line and send it back.

## Important

Do not install the CPU package `onnxruntime` into the same venv. The launcher removes it automatically, but installing it later can break GPU usage.

## Windows popup: `python.exe - Entry Point Not Found` from `torch\\lib\\cudnn_*.dll`

If Windows shows a popup that mentions a DLL under a global Python path such as:

```text
C:\Users\...\Python311\Lib\site-packages\torch\lib\cudnn_engines_runtime_compiled64_9.dll
```

then ONNX Runtime is accidentally mixing the project's CUDA/cuDNN DLLs with a different cuDNN set from a global PyTorch installation. The launcher in this build fixes that by:

1. Running only `backend\.venv\Scripts\python.exe`.
2. Setting `PYTHONNOUSERSITE=1` and clearing `PYTHONPATH`.
3. Loading CUDA/cuDNN from the virtual environment's NVIDIA packages only.
4. Avoiding `onnxruntime.preload_dlls(directory=None)`, because that default search can find PyTorch DLLs on Windows.

If the popup still appears, delete `backend\.venv` and run `START_SECURESIGHT_VISION_GPU.bat` again so the isolated environment is recreated.

## Frontend install appears stuck

This build no longer runs `npm install` for the frontend. The Node frontend server uses built-in Node.js modules only, so startup should skip dependency installation entirely.


## GPU DLL note: missing cusolver64_11.dll / cusparse64_12.dll

If the GPU preflight says `cusolver64_11.dll` or `cusparse64_12.dll` is missing, the CUDA math/runtime wheels did not finish installing or the dependency list changed after the virtual environment was created. The launcher now uses a dependency-version stamp and will refresh the GPU packages automatically. If the error remains, delete `backend\.venv` and run `START_SECURESIGHT_VISION_GPU.bat` again.

The required packages are included explicitly in `backend/gpu_requirements.txt`:

```text
nvidia-cusolver-cu12
nvidia-cusparse-cu12
```
