"""
Voice activity detection model (Silero VAD).
A fresh instance per stream, because the model keeps internal state.
"""


def load_vad_model():
    from silero_vad import load_silero_vad

    return load_silero_vad()
