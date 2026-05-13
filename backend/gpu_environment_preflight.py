"""SecureSight Vision GPU preflight check for ONNX Runtime on Windows.

The check intentionally loads CUDA/cuDNN from the active virtual environment's
NVIDIA wheels only. This avoids the common Windows conflict where a global
PyTorch install contributes a different cuDNN DLL set.
"""
from __future__ import annotations

import os
import site
import sys
from pathlib import Path

REQUIRED_DLLS = [
    "cudart64_12.dll",
    "cublas64_12.dll",
    "cublasLt64_12.dll",
    "cufft64_11.dll",
    "curand64_10.dll",
    "cusolver64_11.dll",
    "cusparse64_12.dll",
    "cudnn64_9.dll",
    "cudnn_engines_tensor_ir64_9.dll",
    "cudnn_engines_precompiled64_9.dll",
    "cudnn_graph64_9.dll",
    "cudnn_heuristic64_9.dll",
    "cudnn_ops64_9.dll",
]


def active_site_roots() -> list[Path]:
    """Return site-packages roots for the active environment only."""
    roots: list[Path] = []
    prefix = Path(sys.prefix).resolve()
    for value in site.getsitepackages():
        p = Path(value).resolve()
        if str(p).lower().startswith(str(prefix).lower()):
            roots.append(p)
    return roots


def nvidia_dll_dirs() -> list[Path]:
    """Find NVIDIA wheel DLL directories inside the current venv."""
    found: list[Path] = []
    seen: set[str] = set()
    for root in active_site_roots():
        nvidia_root = root / "nvidia"
        if not nvidia_root.exists():
            continue
        for folder in nvidia_root.rglob("*"):
            if folder.is_dir() and any(folder.glob("*.dll")):
                key = str(folder.resolve()).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(folder)
    return found


def prepare_dll_search_path() -> list[Path]:
    """Prepend venv NVIDIA DLL directories and register them with Windows."""
    dirs = nvidia_dll_dirs()
    if dirs:
        os.environ["PATH"] = os.pathsep.join(str(d) for d in dirs) + os.pathsep + os.environ.get("PATH", "")
    if os.name == "nt" and hasattr(os, "add_dll_directory"):
        for folder in dirs:
            try:
                os.add_dll_directory(str(folder))
            except OSError:
                pass
    return dirs


def find_dll(name: str) -> Path | None:
    for folder in nvidia_dll_dirs():
        p = folder / name
        if p.exists():
            return p
    return None


def main() -> int:
    print("=" * 80)
    print("SecureSight Vision GPU preflight")
    print("Python:", sys.version.replace("\n", " "))
    print("Executable:", sys.executable)
    print("sys.prefix:", sys.prefix)

    dirs = prepare_dll_search_path()
    print("NVIDIA DLL dirs from active venv:")
    for d in dirs:
        print(" -", d)

    try:
        import onnxruntime as ort
    except Exception as exc:
        print("ERROR: onnxruntime import failed:", exc)
        return 1

    print("ONNX Runtime:", getattr(ort, "__version__", "unknown"))

    if hasattr(ort, "preload_dlls"):
        try:
            # directory="" means: use NVIDIA site-packages. Do not call
            # directory=None here because that can pick up global Torch DLLs.
            ort.preload_dlls(cuda=True, cudnn=True, msvc=True, directory="")
            print("preload_dlls from NVIDIA site-packages: OK")
        except Exception as exc:
            print("preload_dlls from NVIDIA site-packages: FAILED", exc)
    else:
        print("preload_dlls: NOT AVAILABLE. Use onnxruntime-gpu 1.21.0 or newer.")

    if hasattr(ort, "print_debug_info"):
        print("ONNX Runtime debug info:")
        try:
            ort.print_debug_info()
        except Exception as exc:
            print("print_debug_info failed:", exc)

    providers = ort.get_available_providers()
    print("Providers:", providers)

    print("Required DLL check inside venv NVIDIA wheels:")
    missing: list[str] = []
    for dll in REQUIRED_DLLS:
        p = find_dll(dll)
        print(f" - {dll}: {p if p else 'MISSING'}")
        if p is None:
            missing.append(dll)

    if "CUDAExecutionProvider" not in providers:
        print("ERROR: CUDAExecutionProvider is not available.")
        return 2

    if missing:
        print("ERROR: Missing required CUDA/cuDNN DLLs:", ", ".join(missing))
        print("Fix 1: run START_SECURESIGHT_VISION_GPU.bat again. The launcher now refreshes GPU dependencies when the requirement stamp changes.")
        print("Fix 2: if it still fails, delete backend\\.venv and run START_SECURESIGHT_VISION_GPU.bat again.")
        print("Manual install, if needed:")
        print(r"  backend\.venv\Scripts\python.exe -m pip install --upgrade nvidia-cusolver-cu12 nvidia-cusparse-cu12")
        return 3

    print("GPU preflight PASSED. SecureSight Vision can request CUDAExecutionProvider.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
