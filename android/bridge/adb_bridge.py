"""
Synapse AI — Real-Device ADB Automation Bridge
Connects any physical Android smartphone or Android Emulator directly to Synapse AI Cloud Backend.
Performs:
1. Real-time screen capture via 'adb exec-out screencap -p'
2. Real-time UI hierarchy dump via 'adb shell uiautomator dump'
3. Physical touch injection via 'adb shell input tap <x> <y>'
4. Physical text typing via 'adb shell input text <text>'
5. Direct bi-directional WebSocket connection to FastAPI backend.
"""

import subprocess
import shutil
import base64
import json
import time
import os
import sys
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import httpx

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class ADBBridge:
    def __init__(self, backend_url: str = "http://127.0.0.1:8000"):
        self.backend_url = backend_url
        self.adb_bin = self._find_adb()
        self.device_id = None
        self.client = httpx.Client(base_url=self.backend_url, timeout=30.0)

    def _find_adb(self) -> Optional[str]:
        adb = shutil.which("adb")
        if adb:
            return adb

        # Common Android SDK paths on Windows
        possible_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
            r"C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe",
            r"C:\Android\platform-tools\adb.exe"
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        return "adb" # fallback to path

    def list_devices(self) -> List[str]:
        """Lists connected Android devices via ADB."""
        try:
            res = subprocess.run([self.adb_bin, "devices"], capture_output=True, text=True, check=True)
            lines = res.stdout.strip().split("\n")[1:]
            devices = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
            return devices
        except Exception as e:
            print(f"[ADB Warning] Could not list devices: {e}")
            return []

    def select_device(self) -> bool:
        devices = self.list_devices()
        if not devices:
            print("[ADB] No physical or emulated Android device detected via USB/WiFi.")
            print("[ADB] Running in Simulated Phone Mode (connected to Synapse Simulator).")
            return False

        self.device_id = devices[0]
        print(f"[ADB] Connected to real Android device: {self.device_id}")
        return True

    def capture_screenshot_base64(self) -> Optional[str]:
        """Captures real screen frame from Android device as PNG base64."""
        if not self.device_id:
            return None
        try:
            cmd = [self.adb_bin, "-s", self.device_id, "exec-out", "screencap", "-p"]
            res = subprocess.run(cmd, capture_output=True, check=True)
            return base64.b64encode(res.stdout).decode("utf-8")
        except Exception as e:
            print(f"[ADB Error] Screenshot capture failed: {e}")
            return None

    def dump_ui_nodes(self) -> List[Dict[str, Any]]:
        """Dumps Accessibility UI hierarchy from active Android window."""
        if not self.device_id:
            # Fallback simulated nodes
            return [
                {"id": "com.cinepass:id/btn_book", "text": "Book IMAX Laser", "bounds": [180, 520, 240, 560], "clickable": True},
                {"id": "com.cinepass:id/seat_g12", "text": "Seat G12", "bounds": [190, 360, 210, 380], "clickable": True}
            ]

        try:
            # Run uiautomator dump on device
            subprocess.run([self.adb_bin, "-s", self.device_id, "shell", "uiautomator", "dump", "/sdcard/synapse_dump.xml"], check=True)
            res = subprocess.run([self.adb_bin, "-s", self.device_id, "shell", "cat", "/sdcard/synapse_dump.xml"], capture_output=True, text=True, check=True)
            xml_data = res.stdout

            root = ET.fromstring(xml_data)
            nodes = []
            for elem in root.iter("node"):
                text = elem.get("text", "")
                desc = elem.get("content-desc", "")
                res_id = elem.get("resource-id", "")
                bounds_str = elem.get("bounds", "[0,0][0,0]")

                # Parse bounds format "[x1,y1][x2,y2]"
                try:
                    coords = bounds_str.replace("][", ",").replace("[", "").replace("]", "").split(",")
                    bounds = [int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])]
                except:
                    bounds = [0, 0, 0, 0]

                if text or desc or res_id:
                    nodes.append({
                        "id": res_id,
                        "text": text,
                        "desc": desc,
                        "class": elem.get("class", ""),
                        "clickable": elem.get("clickable", "false") == "true",
                        "bounds": bounds,
                        "package": elem.get("package", "")
                    })
            return nodes
        except Exception as e:
            print(f"[ADB Warning] UI dump failed: {e}")
            return []

    def tap(self, x: int, y: int):
        """Injects physical touch tap on Android screen."""
        if not self.device_id:
            print(f"[Simulated Tap] -> ({x}, {y})")
            return
        cmd = [self.adb_bin, "-s", self.device_id, "shell", "input", "tap", str(x), str(y)]
        subprocess.run(cmd)
        print(f"[ADB Gesture] Tapped ({x}, {y}) on {self.device_id}")

    def type_text(self, text: str):
        """Injects text typing into focused field on Android screen."""
        if not self.device_id:
            print(f"[Simulated Type] -> '{text}'")
            return
        # Escape spaces for ADB shell
        escaped = text.replace(" ", "%s")
        cmd = [self.adb_bin, "-s", self.device_id, "shell", "input", "text", escaped]
        subprocess.run(cmd)
        print(f"[ADB Input] Typed '{text}' on {self.device_id}")

    def execute_agent_task(self, prompt: str):
        """Sends real-device context to Synapse backend and executes returned plan."""
        print(f"\n==========================================")
        print(f"🚀 Synapse Task: \"{prompt}\"")
        print(f"==========================================")

        # 1. Capture screen context
        print("[1] Capturing device screen hierarchy...")
        nodes = self.dump_ui_nodes()
        screenshot_b64 = self.capture_screenshot_base64()
        print(f"    Captured {len(nodes)} interactive UI nodes.")

        # 2. Call Synapse Cloud Backend
        print("[2] Sending request to Synapse Cloud Backend...")
        payload = {
            "prompt": prompt,
            "user_id": "user_default",
            "screen_context": {
                "app": "active_window",
                "title": "Mobile View",
                "visible_nodes": nodes
            }
        }

        try:
            resp = self.client.post("/api/agent/task", json=payload)
            events = resp.json().get("events", [])
            print(f"    Received {len(events)} agent reasoning & execution events.\n")

            for event in events:
                step = event.get("step") or event.get("type")
                title = event.get("title") or event.get("state")
                print(f"  [{step}] {title}")

                # If action requires physical touch injection
                if step == "ACTION":
                    target_grounding = event.get("payload", {}).get("target_grounding", {})
                    coords = target_grounding.get("click_coordinates", [200, 400])
                    if isinstance(coords, dict):
                        tx, ty = int(coords.get("x", 200)), int(coords.get("y", 400))
                    elif isinstance(coords, (list, tuple)) and len(coords) >= 2:
                        tx, ty = int(coords[0]), int(coords[1])
                    else:
                        tx, ty = 200, 400
                    print(f"    👉 Injecting tap at ({tx}, {ty})...")
                    self.tap(tx, ty)

                elif step == "EXPLAIN":
                    print(f"\n🗣️ Agent: \"{event.get('description')}\"")

        except Exception as e:
            print(f"[Error] Backend task execution failed: {e}")

if __name__ == "__main__":
    bridge = ADBBridge()
    has_device = bridge.select_device()

    print("\n[Synapse AI] Real-Device Android Bridge Initialized.")
    print("Commands:")
    print("  '1' -> 'Book IMAX tickets for Dune tonight'")
    print("  '2' -> 'Find high rated biryani nearby'")
    print("  '3' -> 'What is on my screen right now?'")
    print("  'exit' -> Quit\n")

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        bridge.execute_agent_task(query)
    else:
        # Quick demonstration run
        bridge.execute_agent_task("Book IMAX tickets for Dune tonight")
