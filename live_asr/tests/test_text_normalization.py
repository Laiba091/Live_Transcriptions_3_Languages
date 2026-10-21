from app.postprocessing.normalizer import normalize_english, normalize_pashto
from app.postprocessing.text_cleaner import clean_pashto, clean_urdu, is_hallucination, strip_special_tokens


def test_pashto_letter_variants_and_punctuation():
    raw = "زه  ښه يم، ته څنګه يې؟ كور"
    assert clean_pashto(raw) == "زه ښه یم، ته څنګه یې؟ کور"
    assert normalize_pashto(raw) == "زه ښه یم ته څنګه یې کور"


def test_urdu_keeps_english_words():
    assert clean_urdu("آج  meeting ہے") == "آج meeting ہے"


def test_english_normalization():
    assert normalize_english("Hello, World!  It's fine.") == "hello world it's fine"


def test_katib_control_tokens_are_removed():
    raw = "<|startoftranscript|><|ps|><|transcribe|><|notimestamps|>دی نه کړي، دی ماله لیکل او"
    assert strip_special_tokens(raw) == "دی نه کړي، دی ماله لیکل او"
    assert "<|" not in clean_pashto(raw)
    assert clean_urdu("<|ur|> آج meeting ہے <|endoftext|>") == "آج meeting ہے"


def test_music_and_noise_hallucinations_are_dropped():
    for noise in ["موسیقی", "[Music]", "♪♪", "Thanks for watching!", "   "]:
        assert is_hallucination(strip_special_tokens(noise)), noise
    for real in ["مرحبا، میں حمید علی خان ہوں", "Thank you very much", "ستاسو نوم څه دی؟"]:
        assert not is_hallucination(real), real
