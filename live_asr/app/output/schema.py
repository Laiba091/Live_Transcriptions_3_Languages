"""The shape of one transcript row, used by JSON, Excel and the live API."""
from dataclasses import asdict, dataclass, fields


@dataclass
class SegmentRecord:
    clock_time: str
    start_s: float
    end_s: float
    language: str             # en | ur | ps
    language_name: str
    confidence: float
    text: str
    normalized_text: str
    direction: str            # ltr | rtl
    prob_en: float
    prob_ur: float
    prob_ps: float
    code_switch_split: bool
    model: str
    processing_s: float
    id: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# Column order for Excel
EXCEL_COLUMNS = ["id", "clock_time", "start_s", "end_s", "language", "language_name", "confidence",
                 "text", "normalized_text", "prob_en", "prob_ur", "prob_ps", "code_switch_split",
                 "model", "processing_s"]

assert set(EXCEL_COLUMNS) <= {f.name for f in fields(SegmentRecord)}
