"""POST /transcribe - upload an audio file, get the full transcript (also saved as JSON + Excel)."""
import asyncio
import os
import tempfile

from fastapi import APIRouter, File, Request, UploadFile

from app.api.dependencies import get_pipeline
from app.core.config import settings
from app.session.manager import transcribe_utterance
from app.session.session import TranscriptSession

router = APIRouter(tags=["files"])


def _decode(path: str):
    from faster_whisper.audio import decode_audio      # ffmpeg-free decoder (PyAV)
    return decode_audio(path, sampling_rate=settings.sample_rate)


@router.post("/transcribe")
async def transcribe_file(request: Request, file: UploadFile = File(...)):
    pipeline = get_pipeline(request)
    suffix = os.path.splitext(file.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
    try:
        audio = await asyncio.to_thread(_decode, tmp.name)
    finally:
        os.unlink(tmp.name)

    session = TranscriptSession(source=f"file:{file.filename}")
    segmenter = pipeline.new_segmenter()
    utterances = []
    step = settings.sample_rate                         # feed 1 s at a time, like a live stream
    for i in range(0, len(audio), step):
        utterances += segmenter.push(audio[i:i + step])
    utterances += segmenter.flush()

    for utt in utterances:
        await transcribe_utterance(pipeline, utt, session)
    await asyncio.to_thread(session.close)

    data = session.to_dict()
    data["json"] = f"/sessions/{session.id}/json"
    data["excel"] = f"/sessions/{session.id}/excel"
    return data
