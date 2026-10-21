@echo off
setlocal
cd /d "%~dp0"
title Live Transcription - Setup

echo ============================================================
echo   Live Transcription - one-time setup (CPU)
echo ============================================================
echo.

REM ---------- 1. Make sure Python 3.11 exists ----------
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo [1/3] Python 3.11 not found - installing it...
    py install 3.11
    py -3.11 --version >nul 2>&1
    if errorlevel 1 (
        echo       Trying winget...
        winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
    )
    py -3.11 --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo [!] Could not install Python 3.11 automatically.
        echo     Download "Windows installer 64-bit" from:
        echo     https://www.python.org/downloads/release/python-3119/
        echo     Tick "Add Python to PATH", install, then run setup.bat again.
        pause
        exit /b 1
    )
)
for /f "delims=" %%v in ('py -3.11 --version') do echo [1/3] Using %%v

REM ---------- 2. Create the project environment with Python 3.11 ----------
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,11) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo [2/3] Old environment uses the wrong Python - recreating it...
        rmdir /s /q venv
    )
)
if not exist "venv\Scripts\python.exe" (
    echo [2/3] Creating environment...
    py -3.11 -m venv venv
    if errorlevel 1 (
        echo [!] Could not create the environment.
        pause
        exit /b 1
    )
) else (
    echo [2/3] Environment already exists.
)

REM ---------- 3. Install all packages ----------
echo [3/3] Installing packages - this takes 10-20 minutes the first time...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [!] Package installation failed. Copy the red error lines above and send them.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Setup complete.  Now double-click  start.bat
echo ============================================================
pause
