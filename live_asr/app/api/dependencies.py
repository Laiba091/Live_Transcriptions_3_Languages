"""Shared lookup for routes: the transcription pipeline created at startup in app/main.py."""
from fastapi import HTTPException, Request, WebSocket

from app.pipeline import TranscriptionPipeline


def get_pipeline(conn: Request | WebSocket) -> TranscriptionPipeline:
    pipeline = getattr(conn.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(503, "Models are still loading, try again shortly.")
    return pipeline
