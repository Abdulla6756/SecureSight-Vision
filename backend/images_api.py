from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import PEOPLE_DIR, UNKNOWN_DIR

router = APIRouter(prefix="/api")


@router.get("/person-image/{person_id}/{filename}")
def person_image(person_id: str, filename: str):
    path = PEOPLE_DIR / person_id / filename
    if not path.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(path)


@router.get("/unknown-image/{filename}")
def unknown_image(filename: str):
    path = UNKNOWN_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(path)
