@echo off
setlocal
cd /d "%~dp0"
title Live Transcription - Server + Public Link

if not exist "venv\Scripts\python.exe" (
    echo [!] Setup has not been run yet. Double-click setup.bat first.
    pause
    exit /b 1
)

echo Starting with a PUBLIC LINK (Cloudflare tunnel)...
echo When it says READY, the "Public link" line is the address to open on any phone or laptop.
echo Anyone with that link can use the page - close this window when you are done.
echo.
"venv\Scripts\python.exe" run.py --tunnel
pause
