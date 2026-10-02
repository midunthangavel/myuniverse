"""
Synapse AI — Fetch Recent 3 Emails from Gmail on Connected Physical Android Device
"""

import sys
import os
import asyncio
import time
import json
import base64

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.device.android_controller import AndroidADBController
from app.device.ui_parser import UIAutomatorParser

ARTIFACT_DIR = os.environ.get("ARTIFACT_DIR", os.path.join(os.path.dirname(__file__), "output"))

async def fetch_gmail_emails():
    print("=" * 65)
    print(" SYNAPSE AI — FETCHING RECENT 3 EMAILS FROM GMAIL")
    print("=" * 65)

    ctrl = AndroidADBController()
    available = await ctrl.is_available()
    if not available:
        print("[!] ERROR: No authorized Android device detected.")
        return {"success": False, "error": "Device not available"}

    info = await ctrl.get_device_info()
    print(f"[+] Connected Hardware: {info.get('model')} (Android {info.get('android_version')})")

    # Wake screen & dismiss lockscreen
    print("\n[*] Step 1: Waking up device screen...")
    await ctrl._run_adb(["shell", "input", "keyevent", "224"])  # KEYCODE_WAKEUP
    await ctrl._run_adb(["shell", "wm", "dismiss-keyguard"])
    await asyncio.sleep(0.5)

    # Launch Gmail
    print("\n[*] Step 2: Launching Gmail app (com.google.android.gm)...")
    code, out, err = await ctrl._run_adb([
        "shell", "monkey", "-p", "com.google.android.gm",
        "-c", "android.intent.category.LAUNCHER", "1"
    ])
    print(f"    Launch status: code={code}, out={out.strip()}")
    await asyncio.sleep(3.0)

    # Get UI hierarchy
    print("\n[*] Step 3: Dumping live UI hierarchy from Gmail...")
    ui_res = await ctrl.get_ui_hierarchy()
    nodes = ui_res.get("nodes", []) if ui_res.get("success") else []
    print(f"[+] Extracted {len(nodes)} UI nodes.")

    # Capture live screenshot
    print("\n[*] Step 4: Capturing live screenshot...")
    scr_res = await ctrl.get_screenshot()
    screenshot_path = None
    if scr_res.get("success") and scr_res.get("data_base64"):
        img_bytes = base64.b64decode(scr_res["data_base64"])
        os.makedirs(ARTIFACT_DIR, exist_ok=True)
        screenshot_path = os.path.join(ARTIFACT_DIR, "gmail_inbox.png")
        with open(screenshot_path, "wb") as f:
            f.write(img_bytes)
        print(f"[+] Saved screenshot to: {screenshot_path} ({len(img_bytes)} bytes)")

    # Print out interesting nodes to inspect Gmail structure
    print("\n[*] Step 5: Analyzing UI Nodes for Email Items...")
    email_candidates = []
    for idx, node in enumerate(nodes):
        txt = (node.get("text") or "").strip()
        desc = (node.get("content_desc") or "").strip()
        res_id = (node.get("resource_id") or "").strip()
        clazz = (node.get("class_name") or "").strip()
        bounds = node.get("bounds", [])
        
        # Look for conversation list items or nodes with subject / sender
        combined = f"{txt} | {desc}"
        if any(term in res_id.lower() for term in ["conversation", "subject", "sender", "snippet", "viewholder", "mail", "thread"]):
            print(f"  [Match res_id] {res_id} -> txt: '{txt}', desc: '{desc}', bounds: {bounds}")
        elif desc and len(desc) > 10:
            print(f"  [Match desc] id={res_id} -> desc: '{desc[:100]}...', bounds: {bounds}")
        elif txt and len(txt) > 5:
            # print sample
            pass

    return {
        "success": True,
        "nodes_count": len(nodes),
        "screenshot_path": screenshot_path,
        "raw_nodes": nodes
    }

if __name__ == "__main__":
    res = asyncio.run(fetch_gmail_emails())
    print("\nComplete.")
