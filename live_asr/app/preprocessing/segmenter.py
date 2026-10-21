"""
Streaming speech segmenter.
Feed 16 kHz float32 audio in any chunk size; get back finished utterances
(one per sentence / pause), each with start/end time.
"""
from dataclasses import dataclass

import numpy as np

from app.core.config import settings

WINDOW = 512  # Silero VAD window at 16 kHz (32 ms)


@dataclass
class Utterance:
    audio: np.ndarray
    start: float      # seconds from session start
    end: float
    index: int = 0    # sentence number in this stream (links live previews to the final text)


@dataclass
class InProgress:
    """The sentence that is still being spoken (used by Live mode)."""
    index: int
    audio: np.ndarray
    start: float
    voiced_s: float   # seconds of actual speech so far


class StreamingSegmenter:
    def __init__(self, vad_model):
        sr = settings.sample_rate
        self._vad = vad_model
        self._buf = np.zeros(0, dtype=np.float32)
        self._preroll = np.zeros(0, dtype=np.float32)
        self._speech: list[np.ndarray] = []
        self._in_speech = False
        self._silent_windows = 0
        self._voiced = 0                      # samples that were actually speech
        self._samples_seen = 0
        self._utt_start = 0
        self._index = 0                       # current / last sentence number
        self._pad = int(settings.speech_pad_ms / 1000 * sr)
        self._silence_limit = int(settings.min_silence_ms / 1000 * sr / WINDOW)
        self._max_len = int(settings.max_utterance_s * sr)
        self._min_len = int(settings.min_utterance_s * sr)
        if hasattr(self._vad, "reset_states"):
            self._vad.reset_states()

    def _speech_prob(self, window: np.ndarray) -> float:
        import torch
        return float(self._vad(torch.from_numpy(window), settings.sample_rate).item())

    def _finish(self) -> Utterance | None:
        audio = np.concatenate(self._speech) if self._speech else np.zeros(0, np.float32)
        start = self._utt_start
        voiced = self._voiced
        self._speech, self._in_speech, self._silent_windows, self._voiced = [], False, 0, 0
        if voiced < self._min_len:            # coughs / clicks
            return None
        sr = settings.sample_rate
        return Utterance(audio=audio, start=start / sr, end=(start + len(audio)) / sr, index=self._index)

    def current(self) -> InProgress | None:
        """Snapshot of the sentence being spoken right now, or None during silence."""
        if not self._in_speech or not self._speech:
            return None
        sr = settings.sample_rate
        return InProgress(index=self._index, audio=np.concatenate(self._speech),
                          start=self._utt_start / sr, voiced_s=self._voiced / sr)

    def push(self, chunk: np.ndarray) -> list[Utterance]:
        """Add audio; returns any utterances that just finished (often none)."""
        done: list[Utterance] = []
        self._buf = np.concatenate([self._buf, chunk.astype(np.float32)])
        while len(self._buf) >= WINDOW:
            window, self._buf = self._buf[:WINDOW], self._buf[WINDOW:]
            prob = self._speech_prob(window)
            self._samples_seen += WINDOW

            if prob >= settings.vad_threshold:
                if not self._in_speech:
                    self._in_speech = True
                    self._index += 1
                    self._utt_start = max(0, self._samples_seen - WINDOW - len(self._preroll))
                    self._speech = [self._preroll.copy()]
                self._speech.append(window)
                self._voiced += WINDOW
                self._silent_windows = 0
            elif self._in_speech:
                self._speech.append(window)
                self._silent_windows += 1
                if self._silent_windows >= self._silence_limit:
                    if (u := self._finish()) is not None:
                        done.append(u)

            self._preroll = np.concatenate([self._preroll, window])[-self._pad:]

            if self._in_speech and sum(len(s) for s in self._speech) >= self._max_len:
                if (u := self._finish()) is not None:       # long monologue: force a cut
                    done.append(u)
                self._preroll = np.zeros(0, dtype=np.float32)
        return done

    def flush(self) -> list[Utterance]:
        """Call when the stream ends."""
        if self._in_speech and (u := self._finish()) is not None:
            return [u]
        return []
