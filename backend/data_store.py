import json
from pathlib import Path
from typing import Any

from config import PEOPLE_JSON, REPORTS_JSON, IGNORED_UNKNOWN_JSON


def read_json(path: Path, fallback: Any):
    """Read JSON safely. Return fallback if file is missing/corrupted."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, data: Any):
    """Write JSON in readable format for easy debugging."""
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_people() -> list[dict[str, Any]]:
    return read_json(PEOPLE_JSON, [])


def save_people(items: list[dict[str, Any]]):
    write_json(PEOPLE_JSON, items)


def load_reports() -> list[dict[str, Any]]:
    return read_json(REPORTS_JSON, [])


def save_reports(items: list[dict[str, Any]]):
    write_json(REPORTS_JSON, items)


def load_ignored_unknown() -> list[dict[str, Any]]:
    return read_json(IGNORED_UNKNOWN_JSON, [])


def save_ignored_unknown(items: list[dict[str, Any]]):
    write_json(IGNORED_UNKNOWN_JSON, items)
