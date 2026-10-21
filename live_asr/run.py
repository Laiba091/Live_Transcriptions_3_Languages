"""Start the server:
    python run.py            local only  -> http://localhost:8000
    python run.py --tunnel   + public https link (Cloudflare) for phones / other laptops
"""
import importlib.util
import sys

REQUIRED = {
    "torch": "torch",
    "faster_whisper": "faster-whisper",
    "transformers": "transformers",
    "speechbrain": "speechbrain",
    "silero_vad": "silero-vad",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pandas": "pandas",
    "openpyxl": "openpyxl",
    "multipart": "python-multipart",
}


def preflight() -> None:
    """Clear messages instead of long error traces when setup is incomplete."""
    v = sys.version_info
    if not ((3, 10) <= (v.major, v.minor) <= (3, 12)):
        sys.exit(
            f"\n[!] You are running Python {v.major}.{v.minor}. This project needs Python 3.10, 3.11 or 3.12\n"
            "    (the speech libraries do not support newer versions yet).\n"
            "    Install Python 3.11, then create the venv with it - see README, 'Setup'.\n")

    if sys.prefix == sys.base_prefix:
        print("[i] Tip: you are not inside the venv. Run  venv\\Scripts\\activate  first.\n")

    missing = [pkg for mod, pkg in REQUIRED.items() if importlib.util.find_spec(mod) is None]
    if missing:
        sys.exit(
            f"\n[!] Missing packages: {', '.join(missing)}\n"
            "    Run:  pip install -r requirements.txt\n"
            "    (install PyTorch first if 'torch' is in the list - see README, 'Setup').\n")


if __name__ == "__main__":
    # python run.py           -> local only (http://localhost:8000)
    # python run.py --tunnel  -> also a public https link (Cloudflare) for phones / other laptops
    if "--tunnel" in sys.argv:
        import os
        os.environ["TUNNEL"] = "1"
    preflight()
    import uvicorn

    from app.core.config import settings

    uvicorn.run("app.main:app", host=settings.host, port=settings.port)
