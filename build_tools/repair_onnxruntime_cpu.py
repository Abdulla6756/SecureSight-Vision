"""Repair/test ONNX Runtime CPU import for the Windows EXE build.

ONNX Runtime wheels can fail on Windows with:
"DLL load failed while importing onnxruntime_pybind11_state".
The usual causes are a bad cached wheel, missing VC++ runtime DLLs, or a
wheel version that does not initialize correctly on the target machine.

This helper installs a known-good CPU wheel, tests it in a fresh Python
subprocess, and tries older compatible versions if needed.
"""

from __future__ import annotations

import os
import subprocess
import sys

ORT_VERSIONS = [
    "1.18.1",
    "1.17.3",
    "1.16.3",
]


def run(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(args))
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)


def pip_install(*packages: str) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--force-reinstall", *packages]
    proc = run(cmd)
    print(proc.stdout)
    return proc.returncode == 0


def pip_uninstall() -> None:
    cmd = [sys.executable, "-m", "pip", "uninstall", "-y", "onnxruntime", "onnxruntime-gpu"]
    proc = run(cmd)
    print(proc.stdout)


def test_ort() -> tuple[bool, str]:
    code = (
        "import onnxruntime as ort; "
        "print('onnxruntime', ort.__version__); "
        "print('providers', ort.get_available_providers())"
    )
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-c", code],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    )
    return proc.returncode == 0, proc.stdout


def main() -> int:
    print("SecureSight Vision - ONNX Runtime CPU repair")
    print(f"Python: {sys.version}")

    # Install/repair the VC++ runtime wheel first. The package may expose DLLs
    # through site-packages and helps on clean Windows machines.
    pip_install("msvc-runtime")

    for version in ORT_VERSIONS:
        print("\n" + "=" * 68)
        print(f"Trying onnxruntime=={version}")
        print("=" * 68)
        pip_uninstall()
        if not pip_install(f"onnxruntime=={version}"):
            print(f"Could not install onnxruntime=={version}; trying next version.")
            continue
        ok, output = test_ort()
        print(output)
        if ok:
            print(f"ONNX Runtime CPU import PASSED with version {version}.")
            return 0

    print("\nONNX Runtime CPU import FAILED for all tested versions.")
    print("Recommended fixes:")
    print("1) Install Microsoft Visual C++ Redistributable 2015-2022 x64.")
    print("2) Use 64-bit Python 3.11.")
    print("3) Delete .build_venv and run BUILD_WINDOWS_EXE_CPU.bat again.")
    print("4) If the CPU is very old and lacks AVX, ONNX Runtime may not run on it.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
