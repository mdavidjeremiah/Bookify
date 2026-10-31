"""Persist reading positions, bookmarks and user preferences."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Optional

from platformdirs import user_data_dir, user_config_dir

log = logging.getLogger(__name__)

APP_NAME = "readaloud"
APP_AUTHOR = "readaloud"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _data_dir() -> Path:
    p = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _config_dir() -> Path:
    p = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    p.mkdir(parents=True, exist_ok=True)
    return p


def file_hash(path: str | Path, chunk: int = 65536) -> str:
    """Return a short SHA-256 hex digest of the file (first 1 MB)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while data := f.read(chunk):
            h.update(data)
            if f.tell() >= 1_048_576:
                break
    return h.hexdigest()[:16]


# ---------------------------------------------------------------------------
# Position store
# ---------------------------------------------------------------------------

class PositionStore:
    """JSON-backed store for per-book reading positions."""

    def __init__(self) -> None:
        self._path = _data_dir() / "positions.json"
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception as exc:
                log.warning("Could not read positions file: %s", exc)
        return {}

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(self._data, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            log.warning("Could not save positions: %s", exc)

    def get(self, fhash: str) -> Optional[dict]:
        return self._data.get(fhash)

    def save(self, fhash: str, page: int, sentence: int, filename: str) -> None:
        self._data[fhash] = {
            "filename": filename,
            "page": page,
            "sentence": sentence,
        }
        self._save()

    def clear(self, fhash: str) -> None:
        self._data.pop(fhash, None)
        self._save()


# ---------------------------------------------------------------------------
# Config store
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    "speed": 1.0,
    "voice": None,
    "volume": 1.0,
    "mic": None,
    "voice_enabled": True,
    "push_to_talk": False,
}


class ConfigStore:
    """JSON-backed user preferences."""

    def __init__(self) -> None:
        self._path = _config_dir() / "config.json"
        self._data: dict[str, Any] = {**DEFAULT_CONFIG, **self._load()}

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception as exc:
                log.warning("Could not read config: %s", exc)
        return {}

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(self._data, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            log.warning("Could not save config: %s", exc)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def update(self, **kwargs: Any) -> None:
        self._data.update(kwargs)
        self._save()
