"""
Audio preprocessing helpers.

The browser already does: echo cancellation, noise suppression, gain control,
mono, resampling to 16 kHz and 16-bit PCM (see app/input/index.html).
Here we turn those bytes into model-ready audio and measure loudness.
"""
import numpy as np


def pcm16_to_float(data: bytes) -> np.ndarray:
    """16-bit PCM bytes -> float32 samples in [-1, 1] (what every model expects)."""
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0


def rms(audio: np.ndarray) -> float:
    """Loudness of a clip (root mean square)."""
    return float(np.sqrt(np.mean(np.square(audio, dtype=np.float64)))) if len(audio) else 0.0


def is_too_quiet(audio: np.ndarray, threshold: float) -> bool:
    """Same silence check as the Katib-ASR Colab: skip clips below the RMS threshold."""
    return rms(audio) < threshold
