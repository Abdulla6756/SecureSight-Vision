# SecureSight Vision CPU EXE Build

This package lets you build a Windows `.exe` for **SecureSight Vision** using PyInstaller.

## What you get

After building, the output is:

```text
dist\SecureSightVision\SecureSightVision.exe
```

Submit or copy the **whole folder**:

```text
dist\SecureSightVision\
```

Do not submit only `SecureSightVision.exe` by itself, because PyInstaller one-folder builds keep required DLLs and Python libraries beside the EXE.

## Build steps on Windows

1. Install Python 3.11.
2. Extract this ZIP.
3. Double-click:

```bat
BUILD_WINDOWS_EXE_CPU.bat
```

4. Wait until the build finishes.
5. Run:

```text
dist\SecureSightVision\SecureSightVision.exe
```

The EXE starts a local FastAPI server and opens the browser automatically.

## CPU parallelization

This EXE build runs in CPU mode for maximum portability, but it still uses safe parallelization:

- `FACE_PROVIDER=cpu` forces CPU runtime.
- `FACE_CPU_WORKERS=auto` enables frame-level CPU parallel scanning.
- Unknown-face crop saving runs in side workers.
- Matching, re-entry logic, unknown deduplication, and report generation stay sequential so reports remain accurate and deterministic.

To reduce CPU usage on weak devices, set this before opening the EXE from Command Prompt:

```bat
set FACE_CPU_WORKERS=1
SecureSightVision.exe
```

To force a specific worker count:

```bat
set FACE_CPU_WORKERS=2
SecureSightVision.exe
```

## Why CPU EXE?

CPU mode is the safest EXE target for submission because it works on most Windows devices without NVIDIA CUDA/cuDNN setup. GPU packaging is possible, but it is machine-sensitive because ONNXRuntime GPU, CUDA, cuDNN, and NVIDIA drivers must match the target device.

## Runtime behavior

- The EXE runs in CPU mode.
- The browser opens at a local address such as `http://127.0.0.1:8000`.
- Keep the console window open while using the app.
- Data is stored next to the EXE in a `data/` folder.

## If Windows Defender warns

Unsigned PyInstaller executables may trigger a warning. For a university/demo submission, this is common. Click **More info** then **Run anyway** only if you built the EXE yourself from this project.
