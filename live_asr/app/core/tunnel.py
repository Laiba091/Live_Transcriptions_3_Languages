"""
Cloud tunnel: makes the local server reachable from anywhere through a public
https link (Cloudflare quick tunnel, free, no account needed).

https matters: browsers only allow the microphone on https pages (or localhost),
so the tunnel link works from phones and other laptops too.

The `cloudflared` program is downloaded automatically into  tools/  the first time.
"""
import logging
import os
import platform
import re
import shutil
import stat
import subprocess
import threading
import urllib.request
from pathlib import Path

from app.core.config import PROJECT_ROOT

log = logging.getLogger(__name__)

TOOLS_DIR = PROJECT_ROOT / "tools"
# Real links look like  https://word-word-word-word.trycloudflare.com
# (never match api.trycloudflare.com, which appears in error messages)
URL_PATTERN = re.compile(r"https://(?!api\.)[a-z0-9]+(?:-[a-z0-9]+)+\.trycloudflare\.com")
RELEASE = "https://github.com/cloudflare/cloudflared/releases/latest/download/"


def _download_name() -> tuple[str, str]:
    """(file to download, local file name) for this computer."""
    system, machine = platform.system(), platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
    if system == "Windows":
        return f"cloudflared-windows-{arch}.exe", "cloudflared.exe"
    if system == "Linux":
        return f"cloudflared-linux-{arch}", "cloudflared"
    raise RuntimeError("Automatic download supports Windows and Linux. "
                       "On Mac install it first:  brew install cloudflared")


def find_or_download_cloudflared() -> str:
    existing = shutil.which("cloudflared")
    if existing:
        return existing
    remote, local = _download_name()
    path = TOOLS_DIR / local
    if not path.exists():
        TOOLS_DIR.mkdir(parents=True, exist_ok=True)
        log.info("Downloading cloudflared (one time, ~50 MB)...")
        tmp = path.with_suffix(path.suffix + ".part")
        urllib.request.urlretrieve(RELEASE + remote, tmp)
        os.replace(tmp, path)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def extract_url(line: str) -> str | None:
    match = URL_PATTERN.search(line)
    return match.group(0) if match else None


class Tunnel:
    def __init__(self, port: int):
        self.port = port
        self.url: str | None = None
        self._proc: subprocess.Popen | None = None
        self._found = threading.Event()
        self.last_error = ""

    def start(self, timeout: float = 60) -> str:
        exe = find_or_download_cloudflared()
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._proc = subprocess.Popen(
            [exe, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{self.port}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", creationflags=flags,
        )
        threading.Thread(target=self._read_output, daemon=True).start()
        self._found.wait(timeout)              # set by a link, or by cloudflared exiting
        if self.url is None:
            self.stop()
            detail = f" Last message: {self.last_error}" if self.last_error else ""
            raise RuntimeError("Cloudflare did not return a link (check the internet connection)." + detail)
        return self.url

    def _read_output(self) -> None:
        # Keep reading for the whole run, otherwise cloudflared blocks on a full pipe.
        for line in self._proc.stdout:
            if self.url is None and (url := extract_url(line)):
                self.url = url
                self._found.set()
            elif "ERR" in line or "failed" in line.lower():
                self.last_error = line.strip()
                log.debug("cloudflared: %s", line.strip())
        self._found.set()                      # cloudflared exited: stop waiting

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
