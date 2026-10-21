"""Test setup: no real models are loaded; output goes to a temp folder."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="asr_test_")
os.environ["LIVE_INTERVAL_S"] = "0.05"      # fast previews so live-mode tests run quickly
os.environ["LIVE_MIN_SPEECH_S"] = "0.3"
os.environ["OPEN_BROWSER"] = "0"
