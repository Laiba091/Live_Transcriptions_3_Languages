"""WebSocket route, both modes, with stand-in models (no downloads)."""
import time
from datetime import datetime

import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.preprocessing.segmenter import StreamingSegmenter
from app.output.schema import SegmentRecord

SR = 16000


class EnergySegmenter(StreamingSegmenter):
    def _speech_prob(self, window):
        return 1.0 if np.abs(window).mean() > 0.05 else 0.0


class FakePipeline:
    def __init__(self):
        self.previews = 0

    def new_segmenter(self):
        return EnergySegmenter(vad_model=None)

    def process(self, utt, previous_language, session_start: datetime):
        time.sleep(0.05)
        return [SegmentRecord(
            clock_time="2026-10-19 10:00:00", start_s=utt.start, end_s=utt.end, language="ur",
            language_name="Urdu", confidence=0.9, text=f"جملہ {utt.index}", normalized_text="",
            direction="rtl", prob_en=0.05, prob_ur=0.9, prob_ps=0.05, code_switch_split=False,
            model="fake", processing_s=0.05)]

    def preview(self, current, previous_language):
        self.previews += 1
        return {"index": current.index, "language": "ur", "language_name": "Urdu",
                "confidence": 0.9, "direction": "rtl", "text": f"جملہ {current.index} ..."}


def pcm(seconds, loud):
    audio = np.full(int(seconds * SR), 0.3 if loud else 0.0, np.float32)
    return (audio * 32767).astype(np.int16).tobytes()


def stream(ws, plan):
    """plan = [(seconds, loud)], sent in 100 ms chunks at ~real-time/4 speed."""
    for seconds, loud in plan:
        for _ in range(int(seconds * 10)):
            ws.send_bytes(pcm(0.1, loud))
            time.sleep(0.025)


def collect(mode):
    app.state.pipeline = FakePipeline()
    client = TestClient(app)
    msgs = []
    with client.websocket_connect(f"/ws/transcribe?mode={mode}") as ws:
        assert ws.receive_json()["mode"] == mode
        stream(ws, [(0.5, False), (2.0, True), (1.0, False), (2.0, True), (1.0, False)])
        ws.send_json({"type": "stop"})
        while True:
            m = ws.receive_json()
            msgs.append(m)
            if m["type"] == "saved":
                break
    return msgs


def test_sentence_mode_unchanged():
    msgs = collect("sentence")
    types = [m["type"] for m in msgs]
    assert "partial" not in types
    assert [m["index"] for m in msgs if m["type"] == "segment"] == [1, 2]
    assert types[-1] == "saved"


def test_live_mode_sends_previews_then_finals():
    msgs = collect("live")
    partial_idx = {m["index"] for m in msgs if m["type"] == "partial"}
    assert partial_idx == {1, 2}                                  # text while speaking
    assert [m["index"] for m in msgs if m["type"] == "segment"] == [1, 2]
    for i in (1, 2):                                              # no preview after its final
        final_pos = next(k for k, m in enumerate(msgs) if m["type"] == "done" and m["index"] == i)
        assert not any(m["type"] == "partial" and m["index"] == i for m in msgs[final_pos:])
