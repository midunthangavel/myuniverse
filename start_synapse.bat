@echo off
title Synapse AI — Platform Launcher
color 0B

echo =======================================================
echo          SYNAPSE AI PERSONAL AGENT PLATFORM
echo =======================================================
echo.
echo [1/3] Checking Python virtual environment...
if not exist "backend\.venv\Scripts\python.exe" (
    echo [Setup] Creating Python virtual environment in backend\.venv...
    python -m venv backend\.venv
    call backend\.venv\Scripts\activate.bat
    pip install -r backend\requirements.txt
) else (
    echo [OK] Python environment verified.
)

echo.
echo [2/3] Starting Synapse FastAPI + ChromaDB Cloud Backend (:8000)...
start "Synapse Backend Server" cmd /k ".\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000 --host 0.0.0.0 --reload"

echo.
echo [3/3] Starting Synapse Web Companion Simulator (:5173)...
start "Synapse Web Studio" cmd /k "npm run dev"

echo.
echo =======================================================
echo Synapse AI is starting up!
echo   - Web Studio:      http://localhost:5173/
echo   - Backend API:     http://localhost:8000/
echo   - API Docs:        http://localhost:8000/docs
echo.
echo To connect a real physical Android phone via USB/WiFi:
echo   .\backend\.venv\Scripts\python.exe .\android\bridge\adb_bridge.py
echo =======================================================
pause
