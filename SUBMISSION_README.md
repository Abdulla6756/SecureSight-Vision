# SecureSight Vision - Submission Package

This package is prepared for delivery/demo on Windows machines.

## Recommended launcher

Double-click:

```bat
START_SECURESIGHT_VISION.bat
```

It will choose GPU mode if NVIDIA tools are available, otherwise it starts portable CPU mode.

## Most compatible launcher

For school/lab devices or any machine without NVIDIA GPU, use:

```bat
START_SECURESIGHT_VISION_CPU.bat
```

CPU mode requires Python and Node.js only. It is slower, but it is the safest option for running on most devices.

## Fast NVIDIA launcher

For your machine or a machine with NVIDIA GPU and working CUDA/cuDNN runtime, use:

```bat
START_SECURESIGHT_VISION_GPU.bat
```

GPU mode is faster but depends on NVIDIA driver/CUDA/cuDNN compatibility.

## Required software

- Windows 10/11
- Python 3.11 recommended, or Python 3.x with `py` launcher
- Node.js LTS
- Internet connection on first run to install Python packages
- NVIDIA driver only for GPU mode

## What is included

- Frontend: dependency-free Node.js static server on port 3000
- Backend: FastAPI on port 8000
- CPU dependency set: `backend/cpu_requirements.txt`
- GPU dependency set: `backend/gpu_requirements.txt`
- Persistent local data folder: `backend/data/`

## First run notes

The first launch may take several minutes because Python packages are installed into an isolated virtual environment. After that, startup is faster.

Do not move files out of the project folder. Keep the folder structure as delivered.
