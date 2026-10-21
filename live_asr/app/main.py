"""
FastAPI application: loads the models at startup and registers the routes.
Start it with:  python run.py
"""
import asyncio
import logging
import webbrowser
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api import files, health, sessions
from app.websocket import live_socket
from app.core.config import PROJECT_ROOT, settings
from app.core.logging import setup_logging

setup_logging()
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.models.registry import ModelRegistry
    from app.pipeline import TranscriptionPipeline

    models = await asyncio.to_thread(ModelRegistry)
    app.state.pipeline = TranscriptionPipeline(models)
    app.state.public_url = None

    tunnel = None
    if settings.tunnel:
        from app.core.tunnel import Tunnel
        try:
            tunnel = Tunnel(settings.port)
            app.state.public_url = await asyncio.to_thread(tunnel.start)
        except Exception as exc:
            log.error("Cloud tunnel failed: %s  (local link still works)", exc)
            tunnel = None

    url = f"http://localhost:{settings.port}"
    log.info("=" * 64)
    log.info("READY")
    log.info("  On this laptop : %s", url)
    if app.state.public_url:
        log.info("  Public link    : %s   (works on any phone/laptop)", app.state.public_url)
    log.info("  Ignore the 0.0.0.0 address Uvicorn prints - that is not a page address.")
    log.info("=" * 64)
    if settings.open_browser:
        webbrowser.open(url)
    yield
    if tunnel:
        tunnel.stop()


app = FastAPI(title="Live Transcription API - English / Urdu / Pashto", version="1.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(live_socket.router)
app.include_router(files.router)
app.include_router(sessions.router)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(PROJECT_ROOT / "app" / "input" / "index.html")
