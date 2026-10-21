"""
Application settings.

Every value can be overridden with an environment variable or a `.env` file
in the project root, e.g.  PASHTO_MODEL=uzair0/Katib-ASR
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env = PROJECT_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def _env(name: str, default, cast=str):
    value = os.getenv(name)
    return default if value is None or value == "" else cast(value)


def _device() -> str:
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


@dataclass(frozen=True)
class Settings:
    # ---- General ----
    device: str = field(default_factory=_device)
    sample_rate: int = 16000
    languages: tuple = ("en", "ur", "ps")
    language_names: dict = field(default_factory=lambda: {"en": "English", "ur": "Urdu", "ps": "Pashto"})

    # ---- English + Urdu model (faster-whisper) ----
    whisper_model: str = ""
    whisper_compute_type: str = ""
    whisper_beam_size: int = _env("WHISPER_BEAM_SIZE", 5, int)
    urdu_prompt: str = _env(
        "URDU_PROMPT",
        "یہ ایک عام گفتگو ہے جس میں کبھی کبھی English words جیسے meeting, office, phone بھی استعمال ہوتے ہیں۔",
    )

    # ---- Pashto model (Katib-ASR) ----
    pashto_model: str = _env("PASHTO_MODEL", "uzair0/Katib-ASR")
    pashto_model_type: str = _env("PASHTO_MODEL_TYPE", "auto")   # auto | whisper | ctc

    # ---- Language identification ----
    lid_model: str = _env("LID_MODEL", "speechbrain/lang-id-voxlingua107-ecapa")
    lid_min_confidence: float = _env("LID_MIN_CONFIDENCE", 0.60, float)
    short_utterance_s: float = _env("SHORT_UTTERANCE_S", 1.5, float)
    code_switch_min_s: float = _env("CODE_SWITCH_MIN_S", 6.0, float)

    # ---- Voice activity detection / segmentation ----
    vad_threshold: float = _env("VAD_THRESHOLD", 0.5, float)
    min_silence_ms: int = _env("MIN_SILENCE_MS", 600, int)
    speech_pad_ms: int = _env("SPEECH_PAD_MS", 200, int)
    min_utterance_s: float = _env("MIN_UTTERANCE_S", 0.4, float)
    max_utterance_s: float = _env("MAX_UTTERANCE_S", 12.0, float)
    silence_rms: float = _env("SILENCE_RMS", 0.008, float)

    # ---- Live mode (text while speaking) ----
    live_interval_s: float = _env("LIVE_INTERVAL_S", 1.0, float)      # how often the preview refreshes
    live_min_speech_s: float = _env("LIVE_MIN_SPEECH_S", 0.8, float)  # speech needed before first preview

    # ---- Cloud tunnel (public https link via Cloudflare) ----
    tunnel: bool = _env("TUNNEL", False, lambda v: v.strip().lower() in ("1", "true", "yes"))

    # ---- Storage ----
    data_dir: Path = Path(_env("DATA_DIR", str(PROJECT_ROOT / "data" / "sessions")))

    # ---- Server ----
    host: str = _env("HOST", "0.0.0.0")
    port: int = _env("PORT", 8000, int)
    open_browser: bool = _env("OPEN_BROWSER", True, lambda v: v.strip().lower() not in ("0", "false", "no"))

    def __post_init__(self):
        gpu = self.device == "cuda"
        if not self.whisper_model:
            object.__setattr__(self, "whisper_model", _env("WHISPER_MODEL", "large-v3" if gpu else "large-v3-turbo"))
        if not self.whisper_compute_type:
            object.__setattr__(self, "whisper_compute_type", _env("WHISPER_COMPUTE_TYPE", "float16" if gpu else "int8"))

    @property
    def json_dir(self) -> Path:
        return self.data_dir / "json"

    @property
    def excel_dir(self) -> Path:
        return self.data_dir / "excel"


settings = Settings()
