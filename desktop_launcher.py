"""Desktop launcher for SecureSight Vision.

This file is intended to be packaged with PyInstaller on Windows. It starts the
FastAPI app in CPU mode and serves the frontend from the same local server, so
users only open one executable and one browser URL.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _base_dir() -> Path:
    """Return the PyInstaller extraction folder, or the source folder in dev."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def _runtime_dir() -> Path:
    """Return the writable folder next to the EXE, or the source folder in dev."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _find_free_port(preferred: int = 8000) -> int:
    """Use port 8000 when possible, otherwise pick a free local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(url: str, timeout_seconds: int = 45) -> None:
    """Wait briefly so the browser opens after the local server is ready."""
    import urllib.request

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.5)


def main() -> int:
    base_dir = _base_dir()
    runtime_dir = _runtime_dir()
    backend_dir = base_dir / "backend"
    frontend_dir = base_dir / "frontend" / "public"
    data_dir = runtime_dir / "data"

    # Force a portable CPU build. GPU is intentionally kept for source/zip mode
    # because CUDA/cuDNN DLL bundling is machine-sensitive.
    os.environ.setdefault("FACE_PROVIDER", "cpu")
    os.environ.setdefault("FACE_CPU_WORKERS", "auto")
    os.environ.setdefault("OMP_NUM_THREADS", "2")
    os.environ.setdefault("MKL_NUM_THREADS", "2")
    # InsightFace imports matplotlib indirectly; force a non-GUI backend for EXE mode.
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ["SECURESIGHT_FRONTEND_DIR"] = str(frontend_dir)
    os.environ["SECURESIGHT_DATA_DIR"] = str(data_dir)
    os.environ.setdefault("PYTHONNOUSERSITE", "1")

    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    port = _find_free_port(8000)
    url = f"http://127.0.0.1:{port}"

    print("SecureSight Vision desktop launcher")
    print(f"Mode: CPU portable EXE")
    print(f"CPU frame workers: {os.environ.get('FACE_CPU_WORKERS', 'auto')}")
    print(f"Data folder: {data_dir}")
    print(f"Opening: {url}")
    print("Keep this window open while using the app.")
    print("Press Ctrl+C to stop.\n")

    def open_when_ready() -> None:
        _wait_for_server(url)
        webbrowser.open(url)

    threading.Thread(target=open_when_ready, daemon=True).start()

    import uvicorn
    from app import app

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
