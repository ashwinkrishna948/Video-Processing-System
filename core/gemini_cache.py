"""Caching for Gemini file URIs and structured call results.

Two cache types:
  File URI cache  — avoids re-uploading the same video (Gemini files expire after 48h).
  Call result cache — each of the 3 API call results saved as JSON.
                      On pipeline restart, completed calls are skipped.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

FILE_URI_TTL_HOURS = 47   # Gemini files expire at 48h; use 47h to be safe


def cache_path(cache_dir: str, name: str) -> Path:
    return Path(cache_dir) / f"gemini_{name}.json"


def load_cache(cache_dir: str, name: str, schema: type):
    """Return parsed schema instance from JSON cache, or None if not found."""
    path = cache_path(cache_dir, name)
    if path.exists():
        print(f"  [cache] {name} loaded from {path.name}")
        return schema.model_validate_json(path.read_text())
    return None


def save_cache(cache_dir: str, name: str, result) -> None:
    path = cache_path(cache_dir, name)
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(indent=2))
    print(f"  [cache] {name} saved → {path.name}")


def load_file_uri(cache_dir: str) -> tuple[str, str] | None:
    """Return cached (file_uri, file_name) if still within TTL, else None."""
    path = cache_path(cache_dir, "file_uri")
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    uploaded_at = datetime.datetime.fromisoformat(data["uploaded_at"])
    age_hours = (datetime.datetime.utcnow() - uploaded_at).total_seconds() / 3600
    if age_hours > FILE_URI_TTL_HOURS:
        print(f"  [cache] file_uri expired ({age_hours:.1f}h old) — will re-upload")
        path.unlink()
        return None
    print(f"  [cache] Reusing Gemini file URI ({age_hours:.1f}h old)")
    return data["file_uri"], data["file_name"]


def save_file_uri(cache_dir: str, file_uri: str, file_name: str) -> None:
    path = cache_path(cache_dir, "file_uri")
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "file_uri": file_uri,
        "file_name": file_name,
        "uploaded_at": datetime.datetime.utcnow().isoformat(),
    }, indent=2))
