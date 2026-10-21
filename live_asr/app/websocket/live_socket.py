"""
WebSocket  /ws/transcribe?mode=sentence|live

Streaming transport only: receives audio from the browser, hands it to the
session manager, and sends the manager's messages back.

  mode=sentence (default) : text appears after each pause
  mode=live               : text also appears while speaking, as one continuous transcript

  client -> server : binary 16 kHz mono 16-bit PCM chunks (~100 ms); text {"type": "stop"} to finish
  server -> client :
      {"type": "session", "session_id", "mode"}
      {"type": "partial", "index", "language", "language_name", "direction", "text"}   live mode only
      {"type": "segment", "index", ...row}      final, saved text for sentence `index`
      {"type": "done", "index"}                 sentence `index` finished
      {"type": "saved", "json", "excel"}
      {"type": "error", "message"}
"""
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.dependencies import get_pipeline
from app.preprocessing.audio import pcm16_to_float
from app.session.manager import LiveSessionManager

log = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/transcribe")
async def live_transcribe(ws: WebSocket, mode: str = "sentence"):
    await ws.accept()

    async def send(msg: dict) -> None:
        try:
            await ws.send_json(msg)
        except Exception:
            pass                                   # browser already gone; keep saving

    manager = LiveSessionManager(get_pipeline(ws), send, live_mode=(mode == "live"))
    await manager.start()

    try:
        while True:
            msg = await ws.receive()
            if msg.get("bytes"):
                await manager.push_audio(pcm16_to_float(msg["bytes"]))
            elif msg.get("text") and json.loads(msg["text"]).get("type") == "stop":
                break
            elif msg.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass

    await manager.finish()
    try:
        await ws.close()
    except Exception:
        pass
