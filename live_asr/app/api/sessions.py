"""Saved sessions: list and download."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.output.repository import SessionRepository

router = APIRouter(prefix="/sessions", tags=["sessions"])
repo = SessionRepository()

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("")
def list_sessions():
    return [{"session_id": sid, "json": f"/sessions/{sid}/json", "excel": f"/sessions/{sid}/excel"}
            for sid in repo.list_ids()]


def _file(session_id: str, kind: str):
    try:
        path = repo.file(session_id, kind)
    except ValueError:
        raise HTTPException(400, "Invalid session id")
    if path is None:
        raise HTTPException(404, "Not found")
    return path


@router.get("/{session_id}/json")
def download_json(session_id: str):
    return FileResponse(_file(session_id, "json"), media_type="application/json")


@router.get("/{session_id}/excel")
def download_excel(session_id: str):
    path = _file(session_id, "excel")
    return FileResponse(path, media_type=XLSX, filename=path.name)
