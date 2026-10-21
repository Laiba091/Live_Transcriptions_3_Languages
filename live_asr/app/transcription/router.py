"""Sends audio to the right language transcriber."""
from app.models.registry import ModelRegistry

from .base import BaseTranscriber
from .english import EnglishTranscriber
from .pashto import PashtoTranscriber
from .urdu import UrduTranscriber


class TranscriberRouter:
    def __init__(self, models: ModelRegistry):
        self._by_language: dict[str, BaseTranscriber] = {
            "en": EnglishTranscriber(models.whisper),
            "ur": UrduTranscriber(models.whisper),
            "ps": PashtoTranscriber(models.pashto),
        }

    def get(self, language_code: str) -> BaseTranscriber:
        try:
            return self._by_language[language_code]
        except KeyError:
            raise ValueError(f"No transcriber for language '{language_code}'")
