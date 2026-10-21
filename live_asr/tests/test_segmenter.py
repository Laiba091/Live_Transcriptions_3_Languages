import numpy as np

from app.preprocessing.segmenter import StreamingSegmenter

SR = 16000


class EnergySegmenter(StreamingSegmenter):
    """Uses loudness instead of the Silero model, so the test needs no download."""
    def _speech_prob(self, window):
        return 1.0 if np.abs(window).mean() > 0.05 else 0.0


def run(signal):
    seg = EnergySegmenter(vad_model=None)
    utts = []
    for i in range(0, len(signal), 1600):
        utts += seg.push(signal[i:i + 1600])
    return utts + seg.flush()


def tone(seconds):
    return 0.3 * np.ones(int(seconds * SR), dtype=np.float32)


def silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.float32)


def test_two_sentences_split_on_pause():
    utts = run(np.concatenate([silence(1), tone(2), silence(1), tone(3), silence(1)]))
    assert len(utts) == 2
    assert abs(utts[0].start - 1.0) < 0.3 and abs(utts[1].start - 4.0) < 0.3


def test_long_monologue_is_cut_without_overlap():
    utts = run(np.concatenate([tone(15), silence(1)]))
    assert len(utts) == 2
    assert utts[0].end <= utts[1].start + 1e-6


def test_tiny_click_is_ignored():
    assert run(np.concatenate([silence(1), tone(0.1), silence(1)])) == []


def test_sentences_are_numbered_and_in_progress_snapshot_works():
    seg = EnergySegmenter(vad_model=None)
    assert seg.current() is None
    seg.push(np.concatenate([silence(0.5), tone(1.0)]))         # still speaking
    cur = seg.current()
    assert cur is not None and cur.index == 1 and cur.voiced_s > 0.8
    done = seg.push(silence(1)) + seg.push(tone(1.0)) + seg.push(silence(1))
    assert [u.index for u in done] == [1, 2]
    assert seg.current() is None
