"""
Pashto speech model: Katib-ASR (uzair0/Katib-ASR, Whisper large-v3 fine-tuned for Pashto).
Loaded the same way as the Katib-ASR Colab app. CTC models (wav2vec2 / MMS) also supported
if PASHTO_MODEL is pointed at one.
"""
import logging

import numpy as np

from app.core.config import settings

log = logging.getLogger(__name__)

_FEATURE_KEYS = ("feature_size", "sampling_rate", "hop_length", "chunk_length", "n_fft",
                 "padding_value", "return_attention_mask")


def feature_extractor_settings(processor_config: dict, num_mel_bins: int) -> dict:
    """Newer models keep audio settings inside processor_config.json
    (under "feature_extractor"); older ones use preprocessor_config.json."""
    data = processor_config.get("feature_extractor", processor_config)
    kwargs = {k: data[k] for k in _FEATURE_KEYS if k in data}
    kwargs.setdefault("feature_size", num_mel_bins)
    return kwargs


def load_feature_extractor(model_id: str, num_mel_bins: int):
    """Audio settings for a Whisper model, whichever file format the model ships with."""
    import json
    import os

    from transformers import WhisperFeatureExtractor

    try:                                            # older format: preprocessor_config.json
        return WhisperFeatureExtractor.from_pretrained(model_id)
    except (OSError, ValueError):
        pass
    try:                                            # newer format: processor_config.json
        if os.path.isdir(model_id):
            path = os.path.join(model_id, "processor_config.json")
        else:
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(model_id, "processor_config.json")
        with open(path, encoding="utf-8") as f:
            kwargs = feature_extractor_settings(json.load(f), num_mel_bins)
        log.info("Audio settings read from processor_config.json (%s mel bins)", kwargs["feature_size"])
        return WhisperFeatureExtractor(**kwargs)
    except Exception as exc:                        # last resort: Whisper defaults for this model
        log.warning("Using default Whisper audio settings (%s)", exc)
        return WhisperFeatureExtractor(feature_size=num_mel_bins)


class KatibPashtoModel:
    def __init__(self):
        import torch
        from transformers import AutoConfig

        self._torch = torch
        model_id = settings.pashto_model
        model_type = settings.pashto_model_type
        if model_type == "auto":
            model_type = "whisper" if AutoConfig.from_pretrained(model_id).model_type == "whisper" else "ctc"

        self.name = model_id
        self.type = model_type
        log.info("Loading Pashto model '%s' (%s) on %s", model_id, model_type, settings.device)

        if model_type == "whisper":
            self._load_whisper(model_id)
        else:
            self._load_ctc(model_id)

    # ---------------- loading ----------------
    def _load_whisper(self, model_id: str) -> None:
        from transformers import AutoTokenizer, WhisperForConditionalGeneration, pipeline

        torch = self._torch
        dtype = torch.float16 if settings.device == "cuda" else torch.float32
        model = WhisperForConditionalGeneration.from_pretrained(model_id, torch_dtype=dtype)
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        feature_extractor = load_feature_extractor(model_id, model.config.num_mel_bins)

        self._pipe = pipeline(
            task="automatic-speech-recognition",
            model=model,
            tokenizer=tokenizer,
            feature_extractor=feature_extractor,
            device=0 if settings.device == "cuda" else -1,
            torch_dtype=dtype,
        )
        gen = self._pipe.model.generation_config     # settings from the model card
        gen.forced_decoder_ids = None
        gen.suppress_tokens = []

    def _load_ctc(self, model_id: str) -> None:
        from transformers import AutoModelForCTC, AutoProcessor

        if "mms" in model_id.lower():
            self._processor = AutoProcessor.from_pretrained(model_id, target_lang="pus")
            self._model = AutoModelForCTC.from_pretrained(model_id, target_lang="pus", ignore_mismatched_sizes=True)
        else:
            self._processor = AutoProcessor.from_pretrained(model_id)
            self._model = AutoModelForCTC.from_pretrained(model_id)
        self._model.to(settings.device).eval()

    # ---------------- inference ----------------
    def transcribe(self, audio: np.ndarray) -> str:
        """16 kHz float32 audio -> raw Pashto text."""
        if self.type == "whisper":
            out = self._pipe(
                {"raw": audio.astype(np.float32), "sampling_rate": settings.sample_rate},
                chunk_length_s=30,
                generate_kwargs={"language": "pashto", "task": "transcribe"},
            )
            # Some Whisper fine-tunes return control tokens (<|startoftranscript|><|ps|>...);
            # app/postprocessing/text_cleaner.py removes them.
            return out["text"].strip()

        torch = self._torch
        with torch.inference_mode():
            inputs = self._processor(audio, sampling_rate=settings.sample_rate, return_tensors="pt", padding=True)
            logits = self._model(inputs.input_values.to(settings.device)).logits
        if hasattr(self._processor, "decoder"):          # KenLM decoder bundled with the model
            return self._processor.batch_decode(logits.cpu().numpy()).text[0].strip()
        return self._processor.batch_decode(torch.argmax(logits, dim=-1))[0].strip()
