import os
import sys
from pathlib import Path

# Project paths
BACKEND_ROOT = Path(__file__).parent
PROJECT_ROOT = BACKEND_ROOT.parent

# PyInstaller desktop builds pass explicit paths through environment variables.
# Source/ZIP mode still uses the normal project folders.
FRONTEND_DIR = Path(os.environ.get("SECURESIGHT_FRONTEND_DIR", PROJECT_ROOT / "frontend" / "public"))

# Local data paths. In EXE mode this should be writable next to the executable.
DATA_DIR = Path(os.environ.get("SECURESIGHT_DATA_DIR", BACKEND_ROOT / "data"))
PEOPLE_DIR = DATA_DIR / "people"
UNKNOWN_DIR = DATA_DIR / "unknown"
UPLOADS_DIR = DATA_DIR / "uploads"

PEOPLE_JSON = DATA_DIR / "people.json"
REPORTS_JSON = DATA_DIR / "reports.json"
IGNORED_UNKNOWN_JSON = DATA_DIR / "ignored_unknown.json"


def ensure_data_store():
    """Create required local folders and JSON files on first run."""
    for folder in [DATA_DIR, PEOPLE_DIR, UNKNOWN_DIR, UPLOADS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

    for json_file in [PEOPLE_JSON, REPORTS_JSON, IGNORED_UNKNOWN_JSON]:
        if not json_file.exists():
            json_file.write_text("[]", encoding="utf-8")
