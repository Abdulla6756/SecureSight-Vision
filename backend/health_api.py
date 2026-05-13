from fastapi import APIRouter

from face_recognition_engine import get_face_app, get_face_error, get_face_info

router = APIRouter()


@router.get("/api/health")
@router.get("/health")
def health():
    return {"ok": True, "face_provider": get_face_info(), "face_app_error": get_face_error()}


@router.get("/api/face/test")
@router.get("/face/test")
def face_test():
    face_app = get_face_app()
    return {
        "ok": True,
        "message": "Face engine loaded successfully.",
        "face_provider": get_face_info(),
        "loaded_models": sorted(list(getattr(face_app, "models", {}).keys())),
    }
