"""
Urdu transcription (multilingual Whisper, forced to Urdu).
A short prompt keeps mixed-in English words (meeting, office...) in English letters.
"""
import numpy as np

from app.core.config import settings
from app.models.whisper_model import WhisperModel
from app.postprocessing.normalizer import normalize_urdu
from app.postprocessing.text_cleaner import clean_urdu

from .base import BaseTranscriber, TranscriptionResult


class UrduTranscriber(BaseTranscriber):
    language_code = "ur"
    language_name = "Urdu"
    direction = "rtl"

    def __init__(self, model: WhisperModel):
        self.model = model

    def transcribe(self, audio: np.ndarray, fast: bool = False) -> TranscriptionResult:
        raw = self.model.transcribe(audio, language="ur", initial_prompt=settings.urdu_prompt, fast=fast)
        text = clean_urdu(raw)
        return TranscriptionResult(text=text, normalized_text=normalize_urdu(text), model=self.model.name)
