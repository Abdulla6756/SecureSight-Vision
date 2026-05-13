# Build Options

## Option A: ZIP launcher mode

Use the existing BAT files. This is easiest to debug and supports CPU/GPU modes.

## Option B: CPU EXE mode

Use `BUILD_WINDOWS_EXE_CPU.bat` on Windows. This creates:

```text
dist/SecureSightVision/SecureSightVision.exe
```

This is the best option for submission because it does not require Node.js at runtime and does not require CUDA/cuDNN.

## Option C: GPU EXE mode

Not recommended for general submission. GPU EXE packaging is possible but fragile because every target device needs compatible NVIDIA driver, CUDA runtime, cuDNN, and ONNXRuntime GPU DLLs. For GPU demo, use the normal `START_SECURESIGHT_VISION_GPU.bat` source/ZIP launcher.
