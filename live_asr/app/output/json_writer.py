"""Saves sessions as JSON in data/sessions/json/."""
import json
import os
from pathlib import Path

from app.core.config import settings


class JsonWriter:
    def __init__(self, folder: Path | None = None):
        self.folder = folder or settings.json_dir
        self.folder.mkdir(parents=True, exist_ok=True)

    def path_for(self, session_id: str) -> Path:
        return self.folder / f"session_{session_id}.json"

    def save(self, session) -> Path:
        path = self.path_for(session.id)
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)   # Urdu/Pashto stay readable
        os.replace(tmp, path)                                                # atomic write
        return path
