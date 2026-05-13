import ctypes
import os
import site
import sys
import traceback
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from utils import cosine, normalize

FACE_APP = None
FACE_INFO: dict[str, Any] = {}
FACE_ERROR: str | None = None

# Matching is slightly more forgiving for CCTV/profile angles.
# The second-best margin keeps the lower threshold from matching the wrong person
# when two registered profiles look similar.
MATCH_THRSVHOLD = float(os.getenv("FACE_MATCH_THRSVHOLD", "0.38"))
BORDERLINE_THRSVHOLD = float(os.getenv("FACE_BORDERLINE_THRSVHOLD", "0.33"))
BORDERLINE_MARGIN = float(os.getenv("FACE_BORDERLINE_MARGIN", "0.035"))


CUDA_DLL_NAMSV = [
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


def nvidia_site_package_dirs() -> list[str]:
    """Find NVIDIA DLL folders inside the active virtual environment only.

    Using only sys.prefix prevents a global PyTorch install from injecting a
    mismatched cuDNN DLL set into ONNXRuntime on Windows.
    """
    paths: list[str] = []
    seen = set()
    prefix = Path(sys.prefix).resolve()

    for root_value in site.getsitepackages():
        root = Path(root_value).resolve()
        if not str(root).lower().startswith(str(prefix).lower()):
            continue

        nvidia_root = root / "nvidia"
        if not nvidia_root.exists():
            continue

        for candidate in nvidia_root.rglob("*"):
            if candidate.is_dir() and any(candidate.glob("*.dll")):
                value = str(candidate.resolve())
                key = value.lower()
                if key not in seen:
                    seen.add(key)
                    paths.append(value)

    return paths


def add_nvidia_dll_directories() -> list[str]:
    """Register NVIDIA DLL directories with Windows loader."""
    added = []

    if os.name != "nt":
        return added

    folders = nvidia_site_package_dirs()

    if folders:
        os.environ["PATH"] = os.pathsep.join(folders) + os.pathsep + os.environ.get("PATH", "")

    for folder in folders:
        try:
            os.add_dll_directory(folder)
            added.append(folder)
        except Exception:
            pass

    return added


def find_cuda_dlls() -> dict[str, str | None]:
    """Report where important CUDA DLLs are found."""
    search_dirs = []

    try:
        search_dirs.extend(nvidia_site_package_dirs())
    except Exception:
        pass

    path_env = os.environ.get("PATH", "")
    search_dirs.extend([p for p in path_env.split(os.pathsep) if p])

    found: dict[str, str | None] = {}

    for dll in CUDA_DLL_NAMSV:
        found[dll] = None
        for folder in search_dirs:
            path = Path(folder) / dll
            if path.exists():
                found[dll] = str(path)
                break

    return found


def try_load_cuda_dlls() -> dict[str, str]:
    """Try loading important CUDA DLLs and return per-DLL status."""
    results: dict[str, str] = {}

    if os.name != "nt":
        return {"platform": "not-windows"}

    # Use full paths when possible, because that gives clearer errors.
    found = find_cuda_dlls()

    for dll, full_path in found.items():
        target = full_path or dll
        try:
            ctypes.WinDLL(target)
            results[dll] = f"loaded: {target}"
        except Exception as exc:
            results[dll] = f"failed: {target} -> {exc}"

    return results


def preload_cuda_dlls():
    """Preload CUDA/cuDNN/MSVC DLLs for ONNX Runtime on Windows.

    Fixes common Windows errors:
    - LoadLibrary failed with error 126
    - missing cufft64_11.dll
    - missing cudnn_engines_tensor_ir64_9.dll
    - onnxruntime_providers_cuda.dll falls back to CPU

    The important fix for your log is installing the ONNX Runtime CUDA/cuDNN
    extras and adding every NVIDIA wheel DLL folder with os.add_dll_directory
    before InsightFace creates sessions.
    """
    added_dirs = add_nvidia_dll_directories()
    found_dlls = find_cuda_dlls()

    try:
        import onnxruntime as ort

        preload_result = "not available"
        if hasattr(ort, "preload_dlls"):
            # directory="" searches NVIDIA site-packages. Do not call
            # directory=None because it may pick up global Torch/cuDNN DLLs.
            ort.preload_dlls(cuda=True, cudnn=True, msvc=True, directory="")
            preload_result = "ok-nvidia-site-packages"

        return {
            "ok": True,
            "onnxruntime_version": getattr(ort, "__version__", "unknown"),
            "preload_result": preload_result,
            "added_dll_directories": added_dirs,
            "found_cuda_dlls": found_dlls,
            "load_test": try_load_cuda_dlls(),
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "added_dll_directories": added_dirs,
            "found_cuda_dlls": found_dlls,
            "load_test": try_load_cuda_dlls(),
        }


def choose_face_provider():
    """Select the face-recognition runtime.

    FACE_PROVIDER controls portability:
    - cuda/gpu: require NVIDIA CUDA and fail loudly if GPU is not ready
    - auto: use CUDA when available, otherwise use CPU
    - cpu: force CPU for classroom/submission machines without NVIDIA GPU
    """
    requested = os.getenv("FACE_PROVIDER", "cuda").strip().lower()

    preload_info = {"mode": "skipped", "reason": "CPU provider requested"}
    if requested in {"cuda", "gpu", "auto"}:
        preload_info = preload_cuda_dlls()

    import onnxruntime as ort
    available = ort.get_available_providers()
    has_cuda = "CUDAExecutionProvider" in available

    if requested in {"cuda", "gpu"}:
        if not has_cuda:
            raise RuntimeError(
                "CUDAExecutionProvider is not available. This usually means "
                "onnxruntime-gpu or CUDA/cuDNN DLLs are not installed correctly. "
                f"Available providers: {available}. Preload info: {preload_info}"
            )
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        ctx_id = 0
    elif requested == "auto" and has_cuda:
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        ctx_id = 0
    else:
        providers = ["CPUExecutionProvider"]
        ctx_id = -1

    return providers, ctx_id, {
        "requested": requested,
        "available_onnx_providers": available,
        "selected_providers": providers,
        "ctx_id": ctx_id,
        "device": "GPU" if ctx_id == 0 else "CPU",
        "portable_mode": requested in {"cpu", "auto"},
        "cuda_dll_preload": preload_info,
    }


def model_session_providers(face_app) -> dict[str, list[str]]:
    """Return actual ONNX providers used by each loaded InsightFace model."""
    result = {}

    for name, model in getattr(face_app, "models", {}).items():
        session = getattr(model, "session", None)
        if session is not None and hasattr(session, "get_providers"):
            try:
                result[name] = session.get_providers()
            except Exception as exc:
                result[name] = [f"provider-check-error: {exc}"]
        else:
            result[name] = ["no-session-found"]

    return result


def assert_cuda_really_applied(face_app, ctx_id: int):
    """Fail loudly if CUDA was requested but ORT silently fell back to CPU."""
    if ctx_id != 0:
        return

    providers_by_model = model_session_providers(face_app)
    bad = {
        name: providers
        for name, providers in providers_by_model.items()
        if "CUDAExecutionProvider" not in providers
    }

    FACE_INFO["actual_model_providers"] = providers_by_model

    if bad:
        raise RuntimeError(
            "CUDA was requested, but InsightFace loaded one or more models without "
            "CUDAExecutionProvider. Make sure onnxruntime-gpu[cuda,cudnn] installed "
            "the full CUDA 12 + cuDNN 9 DLL set, especially "
            "cudnn_engines_tensor_ir64_9.dll. Actual model providers: "
            f"{providers_by_model}. CUDA DLL status: "
            f"{FACE_INFO.get('cuda_dll_preload')}"
        )


def get_face_app():
    """Load InsightFace once and reuse it."""
    global FACE_APP, FACE_INFO, FACE_ERROR

    if FACE_APP is not None:
        return FACE_APP

    try:
        from insightface.app import FaceAnalysis

        providers, ctx_id, info = choose_face_provider()
        FACE_INFO = info

        print("=" * 80)
        print("SecureSight Vision Face Engine")
        print("Requested:", info["requested"])
        print("Available:", info["available_onnx_providers"])
        print("Selected:", info["selected_providers"])
        print("ctx_id:", info["ctx_id"])
        print("Device:", info["device"])
        print("CUDA DLL preload:", info.get("cuda_dll_preload"))
        print("=" * 80)

        FACE_APP = FaceAnalysis(
            name="buffalo_l",
            providers=providers,
            allowed_modules=["detection", "recognition"],
        )
        FACE_APP.prepare(ctx_id=ctx_id, det_size=(640, 640), det_thresh=0.35)

        assert_cuda_really_applied(FACE_APP, ctx_id)

        FACE_ERROR = None
        return FACE_APP

    except Exception as exc:
        FACE_APP = None
        FACE_ERROR = traceback.format_exc()
        print("=" * 80)
        print("FACE ENGINE ERROR")
        print(FACE_ERROR)
        print("=" * 80)
        raise RuntimeError(f"Face recognition engine is not ready. Details: {exc}") from exc


def get_face_info():
    """Return current face-provider info, without forcing model load."""
    if FACE_INFO:
        return FACE_INFO

    try:
        _, _, info = choose_face_provider()
        return info
    except Exception as exc:
        return {"error": str(exc), "cuda_dll_preload": preload_cuda_dlls()}


def get_face_error():
    return FACE_ERROR


def _largest_face_embedding(img):
    """Return the largest face embedding from an already-loaded image."""
    face_app = get_face_app()
    faces = face_app.get(img)
    if not faces:
        return None

    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    return normalize(face.embedding).astype(float).tolist()


def embeddings_from_image(path: Path):
    """Create multiple reference embeddings from one profile image.

    CCTV often captures a person from the side, while profile pictures are usually
    front-facing.  We keep the uploaded photo as-is, but create a few safe
    embedding variants in memory: original, mirrored, and mild brightness/contrast
    changes.  This improves side/lighting matching without asking the user to
    manually upload many near-duplicate photos.
    """
    img = cv2.imread(str(path))
    if img is None:
        return []

    variants = [
        img,
        cv2.flip(img, 1),
        cv2.convertScaleAbs(img, alpha=1.08, beta=10),
        cv2.convertScaleAbs(img, alpha=0.92, beta=-8),
    ]

    embeddings = []
    seen = set()
    for variant in variants:
        emb = _largest_face_embedding(variant)
        if not emb:
            continue
        # Avoid storing exact duplicates from easy images.
        key = tuple(round(float(v), 4) for v in emb[:24])
        if key in seen:
            continue
        seen.add(key)
        embeddings.append(emb)

    return embeddings


def embedding_from_image(path: Path):
    """Compatibility helper: return the first embedding from an image."""
    embeddings = embeddings_from_image(path)
    return embeddings[0] if embeddings else None


def build_match_index(registered_people):
    """Pre-compute a compact embedding matrix for faster per-face matching."""
    embeddings = []
    owners = []

    for person in registered_people:
        for ref in person.get("embeddings", []):
            embeddings.append(normalize(ref))
            owners.append(person)

    if not embeddings:
        return {"embeddings": None, "owners": []}

    return {
        "embeddings": np.asarray(embeddings, dtype=np.float32),
        "owners": owners,
    }


def best_match_from_index(embedding, match_index, threshold=None):
    """Return the closest registered person using vectorized matching.

    A normal match requires FACE_MATCH_THRSVHOLD.  A lower borderline match is
    accepted only when the best person is clearly ahead of the second-best score;
    this helps recognize side-angle CCTV faces while limiting false positives.
    """
    matrix = match_index.get("embeddings")
    owners = match_index.get("owners", [])

    if matrix is None or not owners:
        return None, -1.0

    threshold = MATCH_THRSVHOLD if threshold is None else float(threshold)
    vector = normalize(embedding).astype(np.float32)
    scores = matrix @ vector
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])
    best_person = owners[best_idx]

    if best_score >= threshold:
        return best_person, best_score

    if best_score >= BORDERLINE_THRSVHOLD:
        if len(scores) == 1:
            return best_person, best_score
        second_score = float(np.partition(scores, -2)[-2])
        if best_score - second_score >= BORDERLINE_MARGIN:
            return best_person, best_score

    return None, best_score



def is_embedding_known(embedding, stored_embeddings, threshold=0.56):
    """Return True when an embedding is similar to any stored embedding.

    Used for unknown deduplication and future-ignore matching. It intentionally
    accepts a raw list of embeddings so it can be used without creating fake
    person records.
    """
    if not stored_embeddings:
        return False

    matrix = np.asarray([normalize(e) for e in stored_embeddings], dtype=np.float32)
    if matrix.size == 0:
        return False

    vector = normalize(embedding).astype(np.float32)
    return float(np.max(matrix @ vector)) >= float(threshold)

def best_match(embedding, registered_people, threshold=None):
    """Compatibility wrapper for routes that still pass raw people records."""
    return best_match_from_index(embedding, build_match_index(registered_people), threshold)


def crop_face(frame, bbox, output_path: Path):
    """Crop a face from a video frame and save it."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]
    pad = 24
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)

    crop = frame[y1:y2, x1:x2]
    if crop.size:
        cv2.imwrite(str(output_path), crop)
