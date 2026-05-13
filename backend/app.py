from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from analysis_api import router as analyze_router
from config import FRONTEND_DIR, ensure_data_store
from health_api import router as health_router
from images_api import router as image_router
from people_api import router as people_router
from reports_api import router as reports_router
from unknown_faces_api import router as unknown_router


def create_app() -> FastAPI:
    """Build the FastAPI app and connect all route modules."""
    ensure_data_store()

    app = FastAPI(title="SecureSight Vision API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(people_router)
    app.include_router(image_router)
    app.include_router(analyze_router)
    app.include_router(reports_router)
    app.include_router(unknown_router)

    # Serve the HTML/CSS/JS frontend last so API routes keep priority.
    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
