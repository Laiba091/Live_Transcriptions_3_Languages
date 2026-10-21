"""Finds saved sessions on disk (for listing and downloads)."""
import re
from pathlib import Path

from .excel_writer import ExcelWriter
from .json_writer import JsonWriter

_SESSION_ID = re.compile(r"^\d{8}_\d{6}(_\d{3})?$")


class SessionRepository:
    def __init__(self):
        self.json = JsonWriter()
        self.excel = ExcelWriter()

    def list_ids(self) -> list[str]:
        ids = [p.stem[len("session_"):] for p in self.json.folder.glob("session_*.json")]
        return sorted(ids, reverse=True)

    def file(self, session_id: str, kind: str) -> Path | None:
        if not _SESSION_ID.match(session_id):
            raise ValueError("invalid session id")
        path = self.json.path_for(session_id) if kind == "json" else self.excel.path_for(session_id)
        return path if path.exists() else None
