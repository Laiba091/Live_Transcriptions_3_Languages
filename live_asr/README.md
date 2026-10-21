# Live Transcription API — English · Urdu · Pashto

Live speech-to-text with automatic language detection and code-switching.
Each sentence is detected as English, Urdu or Pashto and sent to the right model;
results are saved as **JSON** and **Excel**.

| Language | Model |
|---|---|
| English | Whisper large-v3 (faster-whisper) |
| Urdu | Whisper large-v3, forced to Urdu (English words kept in English letters) |
| Pashto | **Katib-ASR** (`uzair0/Katib-ASR`, Whisper large-v3 fine-tuned for Pashto) |
| Language ID | SpeechBrain VoxLingua107, restricted to en / ur / ps |
| Speech detection | Silero VAD |

---

## Project structure

Each folder is one layer of the pipeline, in the order audio travels through it.

```
live_asr/
├── run.py                      start: python run.py   (add --tunnel for a public link)
├── setup.bat / start.bat / start_public.bat
├── requirements.txt
│
├── app/
│   ├── main.py                 creates the app, loads models, registers routes
│   ├── pipeline.py             the full flow for one sentence (calls the layers below)
│   │
│   ├── input/                  1. INPUT       browser page (index.html), terminal mic client
│   ├── websocket/              2. TRANSPORT   WebSocket /ws/transcribe (live_socket.py)
│   ├── session/                3. SESSION     one recording (session.py), its workers (manager.py)
│   ├── preprocessing/          4. AUDIO       PCM decode + loudness (audio.py), VAD sentence cutting (segmenter.py)
│   ├── models/                 5. MODELS      Whisper, Katib-ASR, VoxLingua107, Silero VAD, registry.py
│   ├── transcription/          6. ASR         language detection + code-switch, english / urdu / pashto, router
│   ├── postprocessing/         7. CLEANUP     remove model tokens + hallucinations (text_cleaner.py), WER text (normalizer.py)
│   ├── output/                 8. OUTPUT      row schema, JSON + Excel writers, saved-session lookup
│   ├── api/                    REST           file upload, session downloads, health check
│   └── core/                   settings (config.py), logging, Cloudflare tunnel
│
├── data/sessions/              saved transcripts: json/ and excel/
└── tests/                      automated tests (no model download needed)
```

**How a sentence flows:**
`input → websocket → session → preprocessing → transcription (+ models) → postprocessing → output (JSON + Excel)`

---

## Two modes — Sentence and Live

Pick one with the switch next to **Start**:

| Mode | What you see | Best for |
|---|---|---|
| **Sentence** (default) | Text appears after each pause | Most accurate, lowest CPU use |
| **Live** | One **continuous transcript** that grows while you talk: the sentence being spoken shows in grey, then turns into the accurate final text when you pause. A new paragraph starts only when the language changes | Watching the transcript build in real time |

Both modes save the same final text to JSON / Excel. Live previews use faster settings and are never saved.
On CPU, English/Urdu previews update about every 1–2 s; Pashto previews are slower (Katib-ASR is a large model).
Settings: `LIVE_INTERVAL_S` (how often the preview refreshes, default 1.0), `LIVE_MIN_SPEECH_S` (default 0.8).

## Public link (cloud tunnel)

To open the page from a phone or another laptop, start with a public link:

- Double-click **`start_public.bat`**, or run `python run.py --tunnel`
- When it says READY, it prints **Public link: https://xxxx-xxxx.trycloudflare.com** — open that anywhere.
  The page also shows the link with a **Copy** button.

How it works: a free Cloudflare quick tunnel (no account). The `cloudflared` program downloads automatically
into `tools/` the first time. The link is `https`, so the microphone works on phones too.
The link changes every time you start, and **anyone with the link can use the page and download saved
transcripts** — close the window when you are done.

---

## How code-switching is handled

1. **Sentence cutting** — speech is split at natural pauses (600 ms by default).
2. **Language per sentence** — VoxLingua107 picks English, Urdu or Pashto. Short or unclear clips keep
   the speaker's previous language, so a one-word "ہاں" doesn't flip it.
3. **Switch inside a sentence** — sentences of 6 s or longer are scanned with a 2 s sliding window; if the
   language changes (e.g. Urdu → Pashto), the sentence is split there and each part goes to its own model.
4. **Urdu + English mixing** — a prompt keeps English words like *meeting*, *office* in English letters
   inside Urdu sentences.

---

## Setup (Windows, CPU — no GPU needed)

**Easiest — double-click, no typing:**
1. Double-click **`setup.bat`** (one time). It installs Python 3.11 if missing, creates the
   project environment with it, and installs every package from `requirements.txt`. Takes 10–20 min.
2. Double-click **`start.bat`**. First start downloads ~6 GB of models.
   When you see `Ready - open http://localhost:8000`, open that in Chrome → **Start** → speak → **Stop**.
   JSON and Excel files are saved in `data/sessions/`.

Every time after that: just double-click `start.bat`.

> Python 3.13 / 3.14 / 3.15 will NOT work (PyTorch isn't available for them yet).
> `setup.bat` always uses Python 3.11, even if a newer Python is installed.

**Manual (same thing, typed):**
```
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python run.py
```

---

## API

| Method | Path | Purpose |
|---|---|---|
| WS | `/ws/transcribe?mode=sentence` or `?mode=live` | Send 16 kHz mono int16 PCM. Receive `segment` (final, saved) per sentence; in live mode also `partial` (preview while speaking) and `done`. Send `{"type":"stop"}` to finish and save |
| POST | `/transcribe` | Upload an audio file (form field `file`) → full transcript, saved as JSON + Excel |
| GET | `/sessions` | List saved sessions |
| GET | `/sessions/{id}/json` · `/sessions/{id}/excel` | Download |
| GET | `/health` | Models loaded, device |
| GET | `/docs` | Interactive API documentation |

### Output row (JSON and Excel)
```json
{ "id": 3, "clock_time": "2026-10-18 22:41:07", "start_s": 12.4, "end_s": 15.9,
  "language": "ps", "language_name": "Pashto", "confidence": 0.93,
  "text": "زه ښه یم، ته څنګه یې؟",
  "normalized_text": "زه ښه یم ته څنګه یې",
  "direction": "rtl", "prob_en": 0.02, "prob_ur": 0.05, "prob_ps": 0.93,
  "code_switch_split": false, "model": "uzair0/Katib-ASR", "processing_s": 0.71 }
```
`normalized_text` has punctuation removed (Katib-ASR Colab normalisation) — use it for WER/CER.
Excel has two sheets: **Transcript** (Urdu/Pashto right-aligned) and **Summary** (time per language).

---

## Settings

Copy `.env.example` to `.env` and edit. Most useful:

| Setting | Default | When to change |
|---|---|---|
| `MIN_SILENCE_MS` | 600 | Raise if sentences get cut mid-way |
| `LID_MIN_CONFIDENCE` | 0.60 | Raise if the language flips too easily |
| `VAD_THRESHOLD` | 0.5 | Raise in a noisy room |
| `WHISPER_MODEL` | large-v3 (GPU) / large-v3-turbo (CPU) | Smaller = faster, less accurate Urdu |
| `PASHTO_MODEL` | uzair0/Katib-ASR | Try another Pashto model |

## Hardware

Runs on CPU by default (English/Urdu use the faster `large-v3-turbo` in int8 automatically).
- **RAM:** 16 GB recommended (Katib-ASR alone uses ~6–7 GB on CPU).
- **Speed on CPU:** English/Urdu ~1–3 s per sentence; Pashto ~5–15 s per sentence (Katib-ASR is a 1.5B model).
  Sentences queue up and appear in order, nothing is lost.
- A GPU later makes it near-instant with no code changes (just install the CUDA build of PyTorch).

## Tests

```
python -m pytest
```
Covers sentence cutting, code-switch splitting, text normalisation and JSON/Excel saving — no model download needed.

## Known limits

- Labels the **language**, not **who** is speaking (speaker diarization can be added later).
- Overlapping speech from two people is transcribed as one stream.
