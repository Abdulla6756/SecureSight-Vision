import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import PEOPLE_DIR
from face_recognition_engine import embeddings_from_image
from models import PersonUpdate
from data_store import load_people, save_people
from utils import person_image_url, save_upload

router = APIRouter(prefix="/api")


@router.get("/people")
def list_people():
    items = load_people()
    for p in items:
        p["image_urls"] = [person_image_url(p["id"], fn) for fn in p.get("images", [])]
        p["image_count"] = len(p.get("images", []))
        p.pop("embeddings", None)
    return items


@router.post("/people")
def add_person(
    name: str = Form(...),
    employee_id: str = Form(""),
    role: str = Form(""),
    department: str = Form(""),
    images: list[UploadFile] = File(default=[]),
):
    items = load_people()
    person_id = str(uuid.uuid4())
    person_dir = PEOPLE_DIR / person_id
    person_dir.mkdir(parents=True, exist_ok=True)

    image_names = []
    embeddings = []

    for image in images:
        ext = Path(image.filename or "face.jpg").suffix or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = person_dir / filename
        save_upload(image, dest)
        image_names.append(filename)

        embeddings.extend(embeddings_from_image(dest))

    person = {
        "id": person_id,
        "name": name,
        "employee_id": employee_id,
        "role": role,
        "department": department,
        "images": image_names,
        "embeddings": embeddings,
        "created_at": int(time.time()),
    }

    items.append(person)
    save_people(items)

    clean_person = dict(person)
    clean_person.pop("embeddings", None)
    return clean_person


@router.put("/people/{person_id}")
def update_person(person_id: str, body: PersonUpdate):
    items = load_people()

    for p in items:
        if p["id"] == person_id:
            p.update(body.model_dump())
            save_people(items)
            clean = dict(p)
            clean.pop("embeddings", None)
            return clean

    raise HTTPException(404, "Person not found")


@router.delete("/people/{person_id}")
def delete_person(person_id: str):
    items = load_people()
    remaining = [p for p in items if p["id"] != person_id]

    if len(remaining) == len(items):
        raise HTTPException(404, "Person not found")

    save_people(remaining)
    shutil.rmtree(PEOPLE_DIR / person_id, ignore_errors=True)
    return {"ok": True}


@router.post("/people/{person_id}/images")
def add_person_images(person_id: str, images: list[UploadFile] = File(default=[])):
    items = load_people()
    person = next((p for p in items if p["id"] == person_id), None)

    if not person:
        raise HTTPException(404, "Person not found")

    person_dir = PEOPLE_DIR / person_id
    person_dir.mkdir(parents=True, exist_ok=True)

    for image in images:
        ext = Path(image.filename or "face.jpg").suffix or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = person_dir / filename
        save_upload(image, dest)

        person.setdefault("images", []).append(filename)
        person.setdefault("embeddings", []).extend(embeddings_from_image(dest))

    save_people(items)
    return {"ok": True}


@router.delete("/people/{person_id}/images/{filename}")
def delete_person_image(person_id: str, filename: str):
    items = load_people()
    person = next((p for p in items if p["id"] == person_id), None)

    if not person:
        raise HTTPException(404, "Person not found")

    images = person.get("images", [])
    embeddings = person.get("embeddings", [])

    if filename in images:
        index = images.index(filename)
        images.pop(index)
        if index < len(embeddings):
            embeddings.pop(index)

    path = PEOPLE_DIR / person_id / filename
    if path.exists():
        path.unlink()

    save_people(items)
    return {"ok": True}
