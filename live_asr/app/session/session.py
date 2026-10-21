"""
One recording session: collects transcript rows and saves them.
JSON is rewritten after every sentence (crash-safe); Excel is written when the session closes.
"""
import threading
from datetime import datetime

from app.output.excel_writer import ExcelWriter
from app.output.json_writer import JsonWriter
from app.output.schema import SegmentRecord


class TranscriptSession:
    def __init__(self, source: str = "live"):
        self.started = datetime.now()
        self.id = self.started.strftime("%Y%m%d_%H%M%S_%f")[:-3]
        self.source = source
        self.records: list[SegmentRecord] = []
        self.last_language: str | None = None
        self._lock = threading.Lock()
        self._json = JsonWriter()
        self._excel = ExcelWriter()

    def add(self, records: list[SegmentRecord]) -> None:
        with self._lock:
            for r in records:
                r.id = len(self.records) + 1
                self.records.append(r)
                self.last_language = r.language
            self._json.save(self)

    def summary(self) -> dict:
        out: dict = {}
        for r in self.records:
            s = out.setdefault(r.language_name, {"segments": 0, "seconds": 0.0})
            s["segments"] += 1
            s["seconds"] = round(s["seconds"] + r.end_s - r.start_s, 2)
        return out

    def to_dict(self) -> dict:
        return {
            "session_id": self.id,
            "source": self.source,
            "started_at": self.started.isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "summary": self.summary(),
            "segments": [r.to_dict() for r in self.records],
        }

    def close(self) -> dict:
        """Final save. Returns the file paths."""
        with self._lock:
            json_path = self._json.save(self)
            excel_path = self._excel.save(self)
        return {"json": str(json_path), "excel": str(excel_path)}
