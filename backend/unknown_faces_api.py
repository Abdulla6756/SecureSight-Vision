import shutil
import time
import uuid

from fastapi import APIRouter, HTTPException

from config import PEOPLE_DIR, UNKNOWN_DIR
from face_recognition_engine import embeddings_from_image, is_embedding_known
from models import CreatePersonFromUnknownBody, IgnoreUnknownBody, LinkUnknownBody
from data_store import load_ignored_unknown, load_people, load_reports, save_ignored_unknown, save_people, save_reports
from utils import person_image_url

router = APIRouter(prefix="/api")


def _embeddings_from_saved_unknown(snapshot: str) -> list:
    """Get the original detection embedding stored in saved reports.

    Re-detecting a face from a small unknown crop is unreliable. The report now
    stores the embedding from the video frame, so linking/ignoring an unknown card
    uses the exact vector that was classified as unknown.
    """
    embeddings = []
    for report in load_reports():
        for item in report.get("unknown", []):
            if item.get("snapshot") != snapshot:
                continue
            if item.get("embedding"):
                embeddings.append(item["embedding"])
            for emb in item.get("embeddings", []):
                embeddings.append(emb)
    return embeddings


def _dedupe_embeddings(embeddings: list, threshold: float = 0.985) -> list:
    unique = []
    for emb in embeddings:
        if emb and not is_embedding_known(emb, unique, threshold=threshold):
            unique.append(emb)
    return unique


def _remove_snapshot_from_reports(snapshot: str) -> bool:
    """Remove a reviewed unknown card from every saved report."""
    reports = load_reports()
    changed = False
    for report in reports:
        unknown = report.get("unknown", [])
        filtered = [item for item in unknown if item.get("snapshot") != snapshot]
        if len(filtered) != len(unknown):
            report["unknown"] = filtered
            if isinstance(report.get("summary"), dict):
                report["summary"]["unknown_count"] = len(filtered)
            changed = True
    if changed:
        save_reports(reports)
    return changed


@router.post("/unknown/link")
def link_unknown(body: LinkUnknownBody):
    """Save an unknown snapshot into an existing known person's profile."""
    items = load_people()
    person = next((p for p in items if p["id"] == body.person_id), None)

    if not person:
        raise HTTPException(404, "Person not found")

    src = UNKNOWN_DIR / body.snapshot
    if not src.exists():
        raise HTTPException(404, "Unknown snapshot not found")

    person_dir = PEOPLE_DIR / person["id"]
    person_dir.mkdir(parents=True, exist_ok=True)

    filename = f"linked-{uuid.uuid4().hex}.jpg"
    dest = person_dir / filename
    shutil.copyfile(src, dest)

    person.setdefault("images", []).append(filename)

    # Prefer the original video-frame embedding. It fixes side/profile faces and
    # cases where the saved crop cannot be detected a second time.
    new_embeddings = _embeddings_from_saved_unknown(body.snapshot)
    if not new_embeddings:
        new_embeddings = embeddings_from_image(dest)
    new_embeddings = _dedupe_embeddings(new_embeddings)

    if new_embeddings:
        person.setdefault("embeddings", []).extend(new_embeddings)

    save_people(items)
    _remove_snapshot_from_reports(body.snapshot)
    return {"ok": True, "filename": filename, "embedding_created": bool(new_embeddings), "embedding_count": len(new_embeddings)}


@router.post("/unknown/create-person")
def create_person_from_unknown(body: CreatePersonFromUnknownBody):
    """Create a new known person using one unknown snapshot."""
    if not body.name.strip():
        raise HTTPException(400, "Name is required")

    src = UNKNOWN_DIR / body.snapshot
    if not src.exists():
        raise HTTPException(404, "Unknown snapshot not found")

    items = load_people()
    person_id = str(uuid.uuid4())
    person_dir = PEOPLE_DIR / person_id
    person_dir.mkdir(parents=True, exist_ok=True)

    ext = src.suffix or ".jpg"
    filename = f"from-unknown-{uuid.uuid4().hex}{ext}"
    dest = person_dir / filename
    shutil.copyfile(src, dest)

    embeddings = _embeddings_from_saved_unknown(body.snapshot)
    if not embeddings:
        embeddings = embeddings_from_image(dest)
    embeddings = _dedupe_embeddings(embeddings)

    person = {
        "id": person_id,
        "name": body.name.strip(),
        "employee_id": body.employee_id.strip(),
        "role": body.role.strip(),
        "department": body.department.strip(),
        "images": [filename],
        "embeddings": embeddings,
        "created_at": int(time.time()),
        "created_from_unknown": body.snapshot,
    }

    items.append(person)
    save_people(items)
    _remove_snapshot_from_reports(body.snapshot)

    clean_person = dict(person)
    clean_person.pop("embeddings", None)
    clean_person["image_urls"] = [person_image_url(person_id, filename)]
    clean_person["image_count"] = 1

    return {"ok": True, "person": clean_person, "embedding_created": bool(embeddings)}


@router.post("/unknown/ignore")
def ignore_unknown(body: IgnoreUnknownBody):
    """Hide a false unknown face now and suppress visually similar detections later."""
    src = UNKNOWN_DIR / body.snapshot
    if not src.exists():
        raise HTTPException(404, "Unknown snapshot not found")

    embeddings = _embeddings_from_saved_unknown(body.snapshot)
    if not embeddings:
        embeddings = embeddings_from_image(src)
    embeddings = _dedupe_embeddings(embeddings)

    ignored = load_ignored_unknown()

    # Do not add duplicate ignored vectors for the same false face.
    existing_embeddings = []
    for item in ignored:
        existing_embeddings.extend(item.get("embeddings", []))

    fresh_embeddings = [emb for emb in embeddings if not is_embedding_known(emb, existing_embeddings, threshold=0.985)]
    if fresh_embeddings:
        ignored.append(
            {
                "id": f"ignored-{uuid.uuid4().hex}",
                "snapshot": body.snapshot,
                "embeddings": fresh_embeddings,
                "created_at": int(time.time()),
            }
        )
        save_ignored_unknown(ignored)

    _remove_snapshot_from_reports(body.snapshot)

    return {"ok": True, "embedding_created": bool(embeddings), "embedding_count": len(fresh_embeddings)}
