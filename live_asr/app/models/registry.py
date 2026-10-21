"""
Loads every model once at startup and hands out the shared instances.
"""
import logging

from .katib_model import KatibPashtoModel
from .language_id_model import VoxLinguaModel
from .vad_model import load_vad_model
from .whisper_model import WhisperModel

log = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(self):
        self.whisper = WhisperModel()          # English + Urdu
        self.pashto = KatibPashtoModel()       # Pashto
        self.language_id = VoxLinguaModel()    # en / ur / ps detection
        log.info("All models loaded.")

    @staticmethod
    def new_vad():
        return load_vad_model()
