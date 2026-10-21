"""
Session manager: runs one live recording from Start to Stop.

It owns everything that happens between the WebSocket and the models:
  - the sentence segmenter for this stream
  - final_worker   : accurate text for each finished sentence (saved)
  - preview_worker : text while the person is still speaking (Live mode, not saved)

The WebSocket layer only feeds audio in (push_audio) and forwards the messages
this class produces through `send`.
"""
import asyncio
import logging
from typing import Awaitable, Callable

import numpy as np

from app.core.config import settings
from app.pipeline import TranscriptionPipeline
from app.preprocessing.segmenter import Utterance
from app.output.schema import SegmentRecord

from .session import TranscriptSession

log = logging.getLogger(__name__)

# One model call at a time across all sessions, so two streams don't overflow memory.
model_lock = asyncio.Lock()

Send = Callable[[dict], Awaitable[None]]


async def transcribe_utterance(pipeline: TranscriptionPipeline, utt: Utterance,
                               session: TranscriptSession) -> list[SegmentRecord]:
    """Final text for one sentence, added to the session (and saved)."""
    async with model_lock:
        records = await asyncio.to_thread(pipeline.process, utt, session.last_language, session.started)
    session.add(records)
    return records


class LiveSessionManager:
    def __init__(self, pipeline: TranscriptionPipeline, send: Send, live_mode: bool):
        self.pipeline = pipeline
        self.send = send
        self.live_mode = live_mode
        self.session = TranscriptSession(source="live-realtime" if live_mode else "live")
        self.segmenter = pipeline.new_segmenter()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._final_busy = False
        self._finalized = 0           # highest sentence number with final text
        self._stopped = False
        self._tasks: list[asyncio.Task] = []

    # ---------- lifecycle ----------
    async def start(self) -> None:
        await self.send({"type": "session", "session_id": self.session.id,
                         "mode": "live" if self.live_mode else "sentence"})
        self._tasks.append(asyncio.create_task(self._final_worker()))
        if self.live_mode:
            self._tasks.append(asyncio.create_task(self._preview_worker()))

    async def push_audio(self, audio: np.ndarray) -> None:
        """New audio from the stream; finished sentences go to the final worker."""
        for utt in self.segmenter.push(audio):
            await self._queue.put(utt)

    async def finish(self) -> dict:
        """Stop: transcribe what is left, save JSON + Excel, report the files."""
        self._stopped = True
        for utt in self.segmenter.flush():
            await self._queue.put(utt)
        await self._queue.put(None)
        await asyncio.gather(*self._tasks)
        paths = await asyncio.to_thread(self.session.close)
        log.info("Session %s saved -> %s", self.session.id, paths)
        msg = {"type": "saved", "session_id": self.session.id,
               "json": f"/sessions/{self.session.id}/json",
               "excel": f"/sessions/{self.session.id}/excel"}
        await self.send(msg)
        return msg

    # ---------- workers ----------
    async def _final_worker(self) -> None:
        while (utt := await self._queue.get()) is not None:
            self._final_busy = True
            try:
                for record in await transcribe_utterance(self.pipeline, utt, self.session):
                    await self.send({"type": "segment", "index": utt.index, **record.to_dict()})
            except Exception as exc:             # one bad sentence must not stop the session
                log.exception("Sentence failed")
                await self.send({"type": "error", "message": str(exc)})
            finally:
                self._finalized = max(self._finalized, utt.index)
                self._final_busy = False
                await self.send({"type": "done", "index": utt.index})

    async def _preview_worker(self) -> None:
        sr = settings.sample_rate
        last = (0, 0)                             # (sentence number, audio length) last previewed
        while not self._stopped:
            await asyncio.sleep(settings.live_interval_s)
            if self._final_busy or not self._queue.empty():
                continue                          # finishing sentences always go first
            current = self.segmenter.current()
            if current is None or current.voiced_s < settings.live_min_speech_s:
                continue
            if current.index <= self._finalized:
                continue
            if current.index == last[0] and len(current.audio) - last[1] < 0.4 * sr:
                continue                          # nothing new said since the last preview
            last = (current.index, len(current.audio))
            try:
                async with model_lock:
                    result = await asyncio.to_thread(self.pipeline.preview, current, self.session.last_language)
            except Exception:
                log.exception("Preview failed")
                continue
            if result and result["index"] > self._finalized:
                await self.send({"type": "partial", **result})
