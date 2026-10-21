import json

import pandas as pd

from app.output.repository import SessionRepository
from app.output.schema import SegmentRecord
from app.session.session import TranscriptSession


def record(lang, name, text, start, end):
    return SegmentRecord(
        clock_time="2026-10-18 22:00:00", start_s=start, end_s=end, language=lang, language_name=name,
        confidence=0.9, text=text, normalized_text=text, direction="rtl" if lang != "en" else "ltr",
        prob_en=0.05, prob_ur=0.9, prob_ps=0.05, code_switch_split=False, model="test", processing_s=0.1)


def test_session_saves_json_and_excel():
    s = TranscriptSession("test")
    s.add([record("ur", "Urdu", "آج meeting ہے", 0, 2),
           record("ps", "Pashto", "زه ښه یم", 2, 5),
           record("en", "English", "see you tomorrow", 5, 6)])
    paths = s.close()

    data = json.load(open(paths["json"], encoding="utf-8"))
    assert [seg["id"] for seg in data["segments"]] == [1, 2, 3]
    assert data["summary"]["Pashto"] == {"segments": 1, "seconds": 3.0}

    df = pd.read_excel(paths["excel"], sheet_name="Transcript")
    assert list(df["text"]) == ["آج meeting ہے", "زه ښه یم", "see you tomorrow"]
    assert set(pd.read_excel(paths["excel"], sheet_name="Summary")["language"]) == {"Urdu", "Pashto", "English"}

    repo = SessionRepository()
    assert s.id in repo.list_ids()
    assert repo.file(s.id, "excel").exists()
