"""English transcription (multilingual Whisper, forced to English)."""
import numpy as np

from app.models.whisper_model import WhisperModel
from app.postprocessing.normalizer import normalize_english
from app.postprocessing.text_cleaner import clean_english

from .base import BaseTranscriber, TranscriptionResult


class EnglishTranscriber(BaseTranscriber):
    language_code = "en"
    language_name = "English"
    direction = "ltr"

    def __init__(self, model: WhisperModel):
        self.model = model

    def transcribe(self, audio: np.ndarray, fast: bool = False) -> TranscriptionResult:
        text = clean_english(self.model.transcribe(audio, language="en", fast=fast))
        return TranscriptionResult(text=text, normalized_text=normalize_english(text), model=self.model.name)
