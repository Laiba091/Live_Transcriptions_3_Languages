"""
The full flow for one sentence, through every layer:

  preprocessing (silence check) -> transcription (language detection, code-switch split,
  language transcriber) -> postprocessing (hallucination filter) -> output (records)
"""
import logging
import time
from datetime import datetime, timedelta

from app.core.config import settings
from app.models.registry import ModelRegistry
from app.output.schema import SegmentRecord
from app.postprocessing.text_cleaner import is_hallucination
from app.preprocessing.audio import is_too_quiet
from app.preprocessing.segmenter import InProgress, StreamingSegmenter, Utterance
from app.transcription.language_detector import LanguageDetector
from app.transcription.router import TranscriberRouter

log = logging.getLogger(__name__)


class TranscriptionPipeline:
    def __init__(self, models: ModelRegistry):
        self.models = models
        self.detector = LanguageDetector(models.language_id)
        self.router = TranscriberRouter(models)

    def new_segmenter(self) -> StreamingSegmenter:
        return StreamingSegmenter(self.models.new_vad())

    def process(self, utt: Utterance, previous_language: str | None,
                session_start: datetime) -> list[SegmentRecord]:
        sr = settings.sample_rate
        spans = self.detector.split_code_switch(utt.audio)
        records: list[SegmentRecord] = []
        previous = previous_language

        for span in spans:
            audio = utt.audio[span.start:span.end]
            if is_too_quiet(audio, settings.silence_rms):
                continue                                       # too quiet to transcribe

            t0 = time.perf_counter()
            decision = self.detector.detect(audio, previous)
            transcriber = self.router.get(decision.language)
            result = transcriber.transcribe(audio)
            if is_hallucination(result.text):
                continue

            start = utt.start + span.start / sr
            end = utt.start + span.end / sr
            records.append(SegmentRecord(
                clock_time=(session_start + timedelta(seconds=start)).strftime("%Y-%m-%d %H:%M:%S"),
                start_s=round(start, 2),
                end_s=round(end, 2),
                language=decision.language,
                language_name=transcriber.language_name,
                confidence=round(decision.confidence, 3),
                text=result.text,
                normalized_text=result.normalized_text,
                direction=transcriber.direction,
                prob_en=round(decision.probs.get("en", 0.0), 3),
                prob_ur=round(decision.probs.get("ur", 0.0), 3),
                prob_ps=round(decision.probs.get("ps", 0.0), 3),
                code_switch_split=len(spans) > 1,
                model=result.model,
                processing_s=round(time.perf_counter() - t0, 2),
            ))
            previous = decision.language
        return records

    def preview(self, current: InProgress, previous_language: str | None) -> dict | None:
        """Live mode: quick transcript of the sentence still being spoken.
        Not saved - the final text replaces it when the sentence ends."""
        if is_too_quiet(current.audio, settings.silence_rms):
            return None
        decision = self.detector.detect(current.audio, previous_language)
        transcriber = self.router.get(decision.language)
        result = transcriber.transcribe(current.audio, fast=True)
        if is_hallucination(result.text):
            return None
        return {
            "index": current.index,
            "language": decision.language,
            "language_name": transcriber.language_name,
            "confidence": round(decision.confidence, 3),
            "direction": transcriber.direction,
            "text": result.text,
        }
