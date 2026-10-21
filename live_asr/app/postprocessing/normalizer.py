"""
Normalised text (punctuation removed, spaces tidied) saved next to the transcript,
for measuring accuracy (WER / CER) against human references.
"""
import re

from .text_cleaner import clean_pashto, clean_urdu


def normalize_english(text: str) -> str:
    text = re.sub(r"[^\w\s']", " ", (text or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def normalize_urdu(text: str) -> str:
    text = re.sub(r'[،؛؟۔.!?«»"\'():\[\]{}…]', " ", clean_urdu(text))
    return re.sub(r"\s+", " ", text).strip()


def normalize_pashto(text: str) -> str:
    """Exact normalisation from the Katib-ASR Colab."""
    text = re.sub(r'[،؛؟.!?«»"\'():\[\]{}…]', " ", clean_pashto(text))
    return re.sub(r"\s+", " ", text).strip()
