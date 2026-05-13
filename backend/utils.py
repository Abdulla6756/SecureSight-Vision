import shutil
from pathlib import Path

import numpy as np
from fastapi import UploadFile


def save_upload(upload: UploadFile, dest: Path):
    """Save an uploaded file without loading the full file into memory."""
    with dest.open("wb") as out:
        shutil.copyfileobj(upload.file, out)


def normalize(vec):
    """L2-normalize a vector before cosine comparison."""
    arr = np.asarray(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    return arr if norm == 0 else arr / norm


def cosine(a, b) -> float:
    """Cosine similarity for face embeddings."""
    return float(np.dot(normalize(a), normalize(b)))


def timecode(seconds: float) -> str:
    """Convert seconds to HH:MM:SS."""
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def person_image_url(person_id: str, filename: str) -> str:
    return f"/api/person-image/{person_id}/{filename}"


def unknown_image_url(filename: str) -> str:
    return f"/api/unknown-image/{filename}"
