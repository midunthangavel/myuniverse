# Synapse — Autonomous Phone-Native Personal AI Agent

Synapse is an autonomous, phone-native personal AI agent featuring multimodal vision perception, proactive routines, vector memory, interactive voice/character interfaces, and an Android automation bridge.

---

## 🌟 Key Features

- **Autonomous Phone Control & Vision:** Connects via ADB bridge and Android accessibility services to inspect screens, perform visual grounding, tap, type, swipe, and automate device workflows.
- **Fast Multimodal Architecture:** Dual-engine reasoning (System 1 fast classifier & System 2 deep planner/vision operator).
- **Interactive Web Cockpit:** Cyberpunk/Glassmorphic dashboard with live phone mirroring, canvas-rendered animated assistant avatar, real-time audio visualization, vector memory explorer, and execution logs.
- **Memory & Recall:** Long-term episodic and semantic memory powered by ChromaDB vector storage and SQLite database.
- **Voice & TTS:** Integrated Edge TTS speech synthesis and Web Speech recognition.
- **Proactive Agent Routines:** Background habit analyzer, scheduled briefings, and event notifications.

---

## 🏗️ Architecture

```
project/
├── android/               # Android Accessibility Service & Kotlin Overlay
│   ├── app/               # Native Android accessibility and floating client
│   └── bridge/            # ADB python bridge interface
├── backend/               # FastAPI Backend & Agent Core
│   ├── app/               # Agent loops, tools, vector memory, LLM factory
│   ├── prompts/           # YAML system prompts & templates
│   ├── scripts/           # Standalone verification and task test runners
│   └── tests/             # Unit and integration test suites
├── src/                   # Frontend logic (Vite vanilla JS)
│   ├── agent.js           # Agent interaction & telemetry
│   ├── audio.js           # Audio capture and synthesis hooks
│   ├── character.js       # Assistant avatar animation canvas
│   ├── main.js            # Dashboard controller & UI events
│   ├── memory.js          # Memory inspection UI
│   └── phone.js           # Phone screen mirror & touch handler
├── index.html             # Futuristic cockpit interface
├── style.css              # Cyberpunk glassmorphic styling
├── docker-compose.yml     # Containerized deployment
└── Dockerfile             # Multi-stage container build
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Node.js** (v18+)
- **Python** (3.11+)
- **Android SDK / Platform Tools (ADB)** (optional, for real device automation)

### 2. Backend Setup
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Setup
```bash
# In the project root
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 📱 Android Device Automation Setup

1. Enable **Developer Options** and **USB Debugging** on your Android device.
2. Connect your device via USB or WiFi (`adb tcpip 5555` followed by `adb connect <device-ip>`).
3. Verify connection:
   ```bash
   adb devices
   ```
4. Run the device bridge or test scripts:
   ```bash
   python backend/scripts/device_bridge_cli.py
   ```

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
```
