#!/usr/bin/env bash
# Synapse AI — Platform Launcher for Linux / macOS

echo "======================================================="
echo "         SYNAPSE AI PERSONAL AGENT PLATFORM"
echo "======================================================="

# Check virtual environment
if [ ! -d "backend/.venv" ]; then
    echo "[Setup] Creating Python virtual environment in backend/.venv..."
    python3 -m venv backend/.venv
    source backend/.venv/bin/activate
    pip install -r backend/requirements.txt
fi

echo "[1/2] Starting Synapse FastAPI + ChromaDB Cloud Backend (:8000)..."
./backend/.venv/bin/python -m uvicorn backend.app.main:app --port 8000 --host 0.0.0.0 --reload &
BACKEND_PID=$!

echo "[2/2] Starting Synapse Web Companion Simulator (:5173)..."
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo "======================================================="
echo "Synapse AI is live!"
echo "  - Web Studio:      http://localhost:5173/"
echo "  - Backend API:     http://localhost:8000/"
echo "  - API Docs:        http://localhost:8000/docs"
echo "Press Ctrl+C to terminate both servers."
echo "======================================================="

trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
