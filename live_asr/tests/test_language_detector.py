import numpy as np

from app.transcription.language_detector import LanguageDetector

SR = 16000


class FakeLID:
    """Audio value encodes the language: 0 = Urdu, 1 = Pashto, 0.5 = unclear."""
    def log_probs(self, audio):
        v = float(audio.mean())
        if v < 0.4:
            p = {"ur": 0.9, "ps": 0.05, "en": 0.05}
        elif v > 0.6:
            p = {"ps": 0.9, "ur": 0.05, "en": 0.05}
        else:
            p = {"ur": 0.4, "ps": 0.4, "en": 0.2}
        return {k: float(np.log(x)) for k, x in p.items()}


detector = LanguageDetector(FakeLID())


def test_detects_switch_inside_sentence():
    audio = np.zeros(10 * SR, np.float32)
    audio[4 * SR:] = 1                                    # Urdu 0-4 s, Pashto 4-10 s
    spans = detector.split_code_switch(audio)
    assert [(s.start / SR, s.end / SR, s.language) for s in spans] == [(0.0, 4.0, "ur"), (4.0, 10.0, "ps")]


def test_short_sentence_is_not_split():
    assert len(detector.split_code_switch(np.zeros(3 * SR, np.float32))) == 1


def test_unclear_short_clip_keeps_previous_language():
    clip = np.full(SR // 2, 0.5, np.float32)
    assert detector.detect(clip, previous="ps").language == "ps"


def test_clear_clip_switches_language():
    clip = np.ones(3 * SR, np.float32)
    assert detector.detect(clip, previous="ur").language == "ps"
