from typing import Any

# Background analysis jobs live in memory while the backend is running.
JOBS: dict[str, dict[str, Any]] = {}
