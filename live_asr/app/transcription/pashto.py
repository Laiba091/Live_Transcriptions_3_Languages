"""Pashto transcription with Katib-ASR (cleanup is the same as the Katib-ASR Colab)."""
import numpy as np

from app.models.katib_model import KatibPashtoModel
from app.postprocessing.normalizer import normalize_pashto
from app.postprocessing.text_cleaner import clean_pashto

from .base import BaseTranscriber, TranscriptionResult


class PashtoTranscriber(BaseTranscriber):
    language_code = "ps"
    language_name = "Pashto"
    direction = "rtl"

    def __init__(self, model: KatibPashtoModel):
        self.model = model

    def transcribe(self, audio: np.ndarray, fast: bool = False) -> TranscriptionResult:
        text = clean_pashto(self.model.transcribe(audio))
        return TranscriptionResult(text=text, normalized_text=normalize_pashto(text), model=self.model.name)
