"""
Language decisions on top of the language-ID model:
  - detect():            pick en / ur / ps for one clip, with stickiness to the previous language
  - split_code_switch(): find where the language changes inside one long utterance
"""
from dataclasses import dataclass

import numpy as np

from app.core.config import settings


@dataclass
class LanguageDecision:
    language: str
    confidence: float
    probs: dict


@dataclass
class LanguageSpan:
    start: int        # sample index within the utterance
    end: int
    language: str | None


class LanguageDetector:
    def __init__(self, lid_model):
        self._model = lid_model

    def probs(self, audio: np.ndarray) -> dict:
        """Probabilities over the configured languages only (sum to 1)."""
        logp = self._model.log_probs(audio)
        top = max(logp.values())
        ex = {code: float(np.exp(v - top)) for code, v in logp.items()}
        total = sum(ex.values())
        return {code: v / total for code, v in ex.items()}

    def detect(self, audio: np.ndarray, previous: str | None = None) -> LanguageDecision:
        p = self.probs(audio)
        lang = max(p, key=p.get)
        duration = len(audio) / settings.sample_rate
        if previous and previous in p and lang != previous:
            unsure = p[lang] < settings.lid_min_confidence
            short = duration < settings.short_utterance_s and p[lang] < 0.85
            if unsure or short:                       # don't flip language on weak evidence
                return LanguageDecision(previous, p[previous], p)
        return LanguageDecision(lang, p[lang], p)

    def split_code_switch(self, audio: np.ndarray, win_s=2.0, hop_s=1.0, min_run_s=2.0) -> list[LanguageSpan]:
        sr = settings.sample_rate
        n = len(audio)
        if n < int(settings.code_switch_min_s * sr):
            return [LanguageSpan(0, n, None)]

        win, hop, min_run = int(win_s * sr), int(hop_s * sr), int(min_run_s * sr)

        # 1. label sliding windows (None = unsure)
        labels = []
        for s in range(0, max(1, n - win + 1), hop):
            p = self.probs(audio[s:s + win])
            lang = max(p, key=p.get)
            labels.append((s, lang if p[lang] >= 0.75 else None))

        # 2. fill unsure windows with the previous confident label
        last = next((lang for _, lang in labels if lang), None)
        filled = []
        for s, lang in labels:
            last = lang or last
            filled.append((s, last))

        # 3. merge into runs
        runs: list[list] = []
        for s, lang in filled:
            if not runs or runs[-1][2] != lang:
                runs.append([s, None, lang])
        for i in range(len(runs) - 1):
            runs[i][1] = runs[i + 1][0]
        runs[0][0], runs[-1][1] = 0, n

        # 4. absorb runs that are too short to be a real switch
        merged: list[list] = []
        for r in runs:
            if merged and (r[1] - r[0]) < min_run:
                merged[-1][1] = r[1]
            else:
                merged.append(r)
        if len(merged) > 1 and (merged[0][1] - merged[0][0]) < min_run:
            merged[1][0] = 0
            merged.pop(0)
        for i in range(1, len(merged)):
            merged[i][0] = merged[i - 1][1]

        # 5. join neighbours with the same language
        spans: list[LanguageSpan] = []
        for s, e, lang in merged:
            if spans and spans[-1].language == lang:
                spans[-1].end = e
            else:
                spans.append(LanguageSpan(s, e, lang))
        return spans
