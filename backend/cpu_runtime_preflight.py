"""Preflight checks for the portable CPU/EXE build.

This script is intentionally small and import-heavy. It catches broken binary
wheels before PyInstaller builds the application, especially SciPy extension
module failures such as "extension modules cannot be imported".
"""

from __future__ import annotations

import importlib
import os
import sys

os.environ.setdefault("MPLBACKEND", "Agg")

REQUIRED_IMPORTS = [
    "numpy",
    "scipy",
    "scipy.linalg",
    "scipy.spatial",
    "scipy.spatial.transform",
    "skimage",
    "sklearn",
    "matplotlib",
    "matplotlib.pyplot",
    "cv2",
    "onnxruntime",
    "insightface",
]


def main() -> int:
    print("SecureSight Vision CPU runtime preflight")
    print(f"Python: {sys.version}")
    failed: list[tuple[str, str]] = []

    for module_name in REQUIRED_IMPORTS:
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "ok")
            print(f"OK: {module_name} ({version})")
        except Exception as exc:  # noqa: BLE001 - preflight should show any import failure
            failed.append((module_name, str(exc)))
            print(f"FAIL: {module_name}: {exc}")

    if failed:
        print("\nCPU runtime preflight FAILED.")
        print("Fix: delete .build_venv and run BUILD_WINDOWS_EXE_CPU.bat again.")
        return 1

    print("\nCPU runtime preflight PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
