"""
Transcript cleanup applied to every model output before it is shown or saved.

  1. strip_special_tokens  - removes model control tokens like <|startoftranscript|><|ps|>
  2. letter forms           - Arabic letter variants -> Urdu / Pashto forms
  3. is_hallucination       - drops text Whisper "hears" in noise or music
"""
import re
import unicodedata

# Whisper / Katib control tokens, e.g. <|startoftranscript|> <|ps|> <|transcribe|> <|notimestamps|> <|0.00|>
_SPECIAL_TOKEN = re.compile(r"<\|[^|<>]*\|>")
# Leftover bracket tags such as [Music] (music) [BLANK_AUDIO]
_SOUND_TAG = re.compile(r"[\[(（]\s*(music|music playing|applause|laughter|blank_audio|silence|noise|موسیقی)\s*[\])）]",
                        re.IGNORECASE)

# Whole outputs that are known noise/music hallucinations, not real speech.
_HALLUCINATIONS = {
    "موسیقی", "موسیقی۔", "میوزک", "music", "music.", "♪", "♪♪", "...",
    "thanks for watching!", "thanks for watching.", "please subscribe",
    "subtitles by the amara.org community",
    "سبسکرائب کریں", "ہمارے چینل کو سبسکرائب کریں",
}


def strip_special_tokens(text: str) -> str:
    text = _SPECIAL_TOKEN.sub(" ", text or "")
    text = _SOUND_TAG.sub(" ", text)
    return " ".join(text.split())


def is_hallucination(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    if t in _HALLUCINATIONS:
        return True
    return all(ch in "♪.… -–" for ch in t)       # only music notes / dots


def clean_english(text: str) -> str:
    return strip_special_tokens(text)


def clean_urdu(text: str) -> str:
    """Unify Arabic letter variants to their Urdu forms (ك→ک, ي/ى→ی, ه→ہ)."""
    text = unicodedata.normalize("NFKC", strip_special_tokens(text))
    text = text.replace("ك", "ک").replace("ي", "ی").replace("ى", "ی").replace("ه", "ہ")
    return " ".join(text.split())


def clean_pashto(text: str) -> str:
    """Same cleanup as the Katib-ASR Colab (ك→ک, ي/ى→ی). Keeps punctuation."""
    text = unicodedata.normalize("NFKC", strip_special_tokens(text))
    text = text.replace("ك", "ک").replace("ي", "ی").replace("ى", "ی")
    return " ".join(text.split())
