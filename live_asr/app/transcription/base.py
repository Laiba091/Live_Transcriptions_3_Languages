"""
Common interface every language transcriber follows.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class TranscriptionResult:
    text: str                    # text as shown to the user
    normalized_text: str         # cleaned text for evaluation (WER/CER); may equal text
    model: str                   # which model produced it


class BaseTranscriber(ABC):
    language_code: str           # "en" | "ur" | "ps"
    language_name: str
    direction: str               # "ltr" | "rtl"

    @abstractmethod
    def transcribe(self, audio: np.ndarray, fast: bool = False) -> TranscriptionResult:
        """16 kHz mono float32 audio -> TranscriptionResult.
        fast=True is used for live previews (quicker, slightly less accurate)."""
