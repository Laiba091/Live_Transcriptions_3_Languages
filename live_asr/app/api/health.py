from fastapi import APIRouter, Request

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request):
    return {
        "ready": getattr(request.app.state, "pipeline", None) is not None,
        "device": settings.device,
        "public_url": getattr(request.app.state, "public_url", None),
        "models": {
            "english_urdu": settings.whisper_model,
            "pashto": settings.pashto_model,
            "language_id": settings.lid_model,
        },
    }
