"""
Spoken language identification model: SpeechBrain VoxLingua107 (107 languages,
restricted here to English / Urdu / Pashto). Much better than Whisper at telling
Pashto and Urdu apart.
"""
import logging

import numpy as np

from app.core.config import PROJECT_ROOT, settings

log = logging.getLogger(__name__)


class VoxLinguaModel:
    def __init__(self, languages=settings.languages):
        import torch
        try:
            from speechbrain.inference.classifiers import EncoderClassifier
            from speechbrain.utils.fetching import LocalStrategy
            extra = {"local_strategy": LocalStrategy.COPY}   # avoids Windows symlink errors
        except ImportError:                                   # older speechbrain
            from speechbrain.pretrained import EncoderClassifier
            extra = {}

        self._torch = torch
        log.info("Loading language-ID model '%s'", settings.lid_model)
        kwargs = dict(
            source=settings.lid_model,
            savedir=str(PROJECT_ROOT / "pretrained_models" / "lang-id-voxlingua107"),
            run_opts={"device": settings.device},
        )
        try:
            self._clf = EncoderClassifier.from_hparams(**kwargs, **extra)
        except TypeError:                                     # version without local_strategy
            self._clf = EncoderClassifier.from_hparams(**kwargs)
        labels = self._clf.hparams.label_encoder.ind2lab       # {index: "ps: Pashto", ...}
        self._index = {}
        for idx, label in labels.items():
            code = label.split(":")[0].strip()
            if code in languages:
                self._index[code] = idx
        missing = set(languages) - set(self._index)
        if missing:
            raise RuntimeError(f"Language-ID model does not support: {missing}")

    def log_probs(self, audio: np.ndarray) -> dict:
        """Raw log-probabilities for the configured languages."""
        with self._torch.inference_mode():
            out = self._clf.classify_batch(self._torch.from_numpy(audio).unsqueeze(0))[0][0]
        return {code: float(out[idx]) for code, idx in self._index.items()}
