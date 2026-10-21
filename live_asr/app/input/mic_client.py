"""
Terminal client: streams the laptop mic to the API and prints the transcript live.
(Alternative to the browser page.)

    python app/input/mic_client.py                      # server on this laptop
    python app/input/mic_client.py --url ws://192.168.1.20:8000/ws/transcribe
    python app/input/mic_client.py --device 2           # pick a specific microphone (see --list)
    python app/input/mic_client.py --mode live          # text appears while you speak
"""
import argparse
import asyncio
import json
import queue

import sounddevice as sd
import websockets

SR = 16000
BLOCK = 1600  # 100 ms


async def run(url, device, mode="sentence"):
    q: queue.Queue = queue.Queue()

    def cb(indata, frames, t, status):
        q.put(bytes(indata))

    sep = "&" if "?" in url else "?"
    async with websockets.connect(f"{url}{sep}mode={mode}", max_size=None) as ws:
        async def reader():
            async for msg in ws:
                m = json.loads(msg)
                if m["type"] == "partial":
                    print(f"\r  ... {m['language_name']:<7}: {m['text'][-90:]}", end="", flush=True)
                elif m["type"] == "segment":
                    print(f"\r[{m['clock_time'][11:]}] {m['language_name']:<7} ({m['confidence']:.0%}): {m['text']}", flush=True)
                elif m["type"] == "saved":
                    print(f"\nSaved -> JSON {m['json']}  |  Excel {m['excel']}")
                elif m["type"] == "session":
                    print(f"Session {m['session_id']} started. Speak... (Ctrl+C to stop)\n")

        rtask = asyncio.create_task(reader())
        with sd.RawInputStream(samplerate=SR, blocksize=BLOCK, channels=1, dtype="int16", device=device, callback=cb):
            try:
                while True:
                    chunk = await asyncio.to_thread(q.get)
                    await ws.send(chunk)
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass
        await ws.send(json.dumps({"type": "stop"}))
        try:
            await asyncio.wait_for(rtask, timeout=60)
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://localhost:8000/ws/transcribe")
    ap.add_argument("--device", type=int, default=None)
    ap.add_argument("--list", action="store_true", help="list microphones and exit")
    ap.add_argument("--mode", choices=["sentence", "live"], default="sentence",
                    help="live = show text while speaking")
    a = ap.parse_args()
    if a.list:
        print(sd.query_devices())
    else:
        try:
            asyncio.run(run(a.url, a.device, a.mode))
        except KeyboardInterrupt:
            pass
