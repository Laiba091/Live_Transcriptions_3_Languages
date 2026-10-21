"""
Multilingual Whisper model (faster-whisper).
One instance is shared by the English and Urdu transcribers.
"""
import logging

import numpy as np

from app.core.config import settings

log = logging.getLogger(__name__)


class WhisperModel:
    def __init__(self):
        from faster_whisper import WhisperModel as _FW

        log.info("Loading Whisper '%s' on %s (%s)", settings.whisper_model, settings.device,
                 settings.whisper_compute_type)
        self._model = _FW(settings.whisper_model, device=settings.device,
                          compute_type=settings.whisper_compute_type)
        self.name = f"faster-whisper/{settings.whisper_model}"

    def transcribe(self, audio: np.ndarray, language: str, initial_prompt: str | None = None,
                   fast: bool = False) -> str:
        """fast=True: greedy decoding for live previews; otherwise beam search for final text."""
        segments, _ = self._model.transcribe(
            audio,
            language=language,
            task="transcribe",               # never translate
            beam_size=1 if fast else settings.whisper_beam_size,
            vad_filter=False,                # segmentation is done upstream
            condition_on_previous_text=False,
            initial_prompt=initial_prompt,
        )
        parts = []
        for seg in segments:
            if seg.no_speech_prob > 0.6 and seg.avg_logprob < -1.0:
                continue                     # drop hallucinations on noise
            parts.append(seg.text.strip())
        return " ".join(p for p in parts if p).strip()

    def language_probs(self, audio: np.ndarray) -> dict:
        _, _, all_probs = self._model.detect_language(audio)
        return dict(all_probs)
