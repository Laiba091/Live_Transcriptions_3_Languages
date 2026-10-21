@echo off
setlocal
cd /d "%~dp0"
title Live Transcription - Server

if not exist "venv\Scripts\python.exe" (
    echo [!] Setup has not been run yet. Double-click setup.bat first.
    pause
    exit /b 1
)

echo Starting... the first start downloads the models (~6 GB), later starts take about a minute.
echo When you see "Ready - open http://localhost:8000", open that address in Chrome.
echo Keep this window open. Close it to stop the server.
echo.
"venv\Scripts\python.exe" run.py
pause
