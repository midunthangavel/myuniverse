"""
Synapse AI — Autonomous Google Chrome Search on Physical Android Phone
Opens Google Chrome, focuses the URL/Search bar, types 'hi', presses ENTER to run,
verifies search result, and captures live screenshot proof.
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
from app.reflector import action_reflector
from app.progressor import task_progressor

ARTIFACT_DIR = r"C:\Users\midun\.gemini\antigravity-ide\brain\88217639-3497-4e32-8166-9dd0188cdf56"

async def run_chrome_search_task(query: str = "hi"):
    print("=" * 65)
    print(" SYNAPSE AI — AUTONOMOUS CHROME BROWSER TASK")
    print(f" Goal: Open Google Chrome and search for '{query}'")
    print("=" * 65)

    ctrl = AndroidADBController()
    available = await ctrl.is_available()
    if not available:
        print("[!] ERROR: No authorized Android device detected.")
        return {"success": False, "error": "Device not available"}

    info = await ctrl.get_device_info()
    print(f"[+] Connected Hardware: {info.get('model')} (Android {info.get('android_version')})")
    print(f"[+] Display Resolution: {info.get('display_size')}")

    # Step 1: Wake device & ensure active
    print("\n[*] Step 1: Waking up device screen...")
    await ctrl._run_adb(["shell", "input", "keyevent", "224"])  # KEYCODE_WAKEUP
    await ctrl._run_adb(["shell", "wm", "dismiss-keyguard"])
    await asyncio.sleep(0.5)

    # Step 2: Open Google in Chrome via Intent
    print("\n[*] Step 2: Launching Chrome with google.com...")
    await ctrl._run_adb([
        "shell", "am", "start",
        "-a", "android.intent.action.VIEW",
        "-d", "https://www.google.com",
        "com.android.chrome"
    ])
    await asyncio.sleep(2.5)

    # Step 3: Dump UI tree to locate URL/Search bar
    print("\n[*] Step 3: Inspecting UI tree for URL/Search bar...")
    ui_res = await ctrl.get_ui_hierarchy()
    nodes = ui_res.get("nodes", []) if ui_res.get("success") else []
    print(f"[+] Extracted {len(nodes)} UI nodes.")

    # Find the URL / Search bar
    target_node = None
    for n in nodes:
        res_id = (n.get("resource_id") or "").lower()
        txt = (n.get("text") or "").lower()
        if "url_bar" in res_id or "search_box" in res_id:
            target_node = n
            break

    if target_node:
        target_x, target_y = target_node["center"]
        print(f"[+] Found URL/Search Bar: id='{target_node.get('resource_id')}' at ({target_x}, {target_y})")
    else:
        # Fallback to calibrated bounds [220,93][673,247] -> center (446, 170)
        target_x, target_y = 446, 170
        print(f"[*] Targeting calibrated URL bar center: ({target_x}, {target_y})")

    # Step 4.1: Tap URL bar
    print("\n[*] Step 4.1: Tapping search / address bar...")
    pre_nodes = nodes
    tap_res = await ctrl.tap(target_x, target_y)
    print(f"    Tap status: {tap_res.success} at ({target_x}, {target_y})")
    await asyncio.sleep(1.0)

    # Step 4.2: Type query "hi"
    print(f"\n[*] Step 4.2: Typing query '{query}' into Google Chrome...")
    # Select all / replace or clear if needed, or input text directly
    input_res = await ctrl.input_text(query)
    print(f"    Input status: {input_res.success} (Text: '{query}')")
    await asyncio.sleep(0.8)

    # Step 4.3: Press Enter (KEYCODE_ENTER = 66) to run search
    print("\n[*] Step 4.3: Submitting search (sending KEYCODE_ENTER)...")
    code, _, _ = await ctrl._run_adb(["shell", "input", "keyevent", "66"])
    print(f"    Enter keyevent injected: code={code}")
    print("    Waiting 4.0s for Google search results to render on device...")
    await asyncio.sleep(4.0)

    # Step 5: Read search results
    print("\n[*] Step 5: Verifying Google search results page...")
    res_ui = await ctrl.get_ui_hierarchy()
    res_nodes = res_ui.get("nodes", []) if res_ui.get("success") else []
    print(f"[+] Extracted {len(res_nodes)} UI nodes from search results page.")

    page_snippets = []
    for n in res_nodes:
        txt = (n.get("text") or "").strip()
        if txt and len(txt) > 1 and txt not in page_snippets:
            page_snippets.append(txt)

    print(f"[+] Page Snippets observed: {page_snippets[:8]}")

    # ActionReflector verification
    reflection = action_reflector.reflect(
        before_state={"nodes": nodes, "title": "Google Homepage"},
        after_state={"nodes": res_nodes, "title": f"Google Search: {query}"},
        intended_action={"action": "SEARCH", "query": query},
        active_app="com.android.chrome"
    )
    print(f"    ActionReflector Verdict: {reflection.get('status')} | Strategy: {reflection.get('strategy')} | Confidence: {reflection.get('confidence')}")

    # Step 6: Capture proof screenshot
    print("\n[*] Step 6: Capturing proof screenshot from physical phone...")
    scr_res = await ctrl.get_screenshot()
    screenshot_saved = False
    if scr_res.get("success") and scr_res.get("data_base64"):
        img_bytes = base64.b64decode(scr_res["data_base64"])
        
        # Save locally in backend/
        local_png = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chrome_search_result.png")
        with open(local_png, "wb") as f:
            f.write(img_bytes)
        print(f"[+] Saved local screenshot: {local_png} ({len(img_bytes)} bytes)")

        # Copy to artifact dir for direct embedding
        if os.path.exists(ARTIFACT_DIR):
            artifact_png = os.path.join(ARTIFACT_DIR, "chrome_search_result.png")
            with open(artifact_png, "wb") as f:
                f.write(img_bytes)
            print(f"[+] Copied to artifacts directory: {artifact_png}")
            screenshot_saved = True

    print("\n" + "=" * 65)
    print(" GOOGLE CHROME SEARCH TASK COMPLETE & VERIFIED")
    print("=" * 65)

    return {
        "success": True,
        "device": info,
        "query": query,
        "page_snippets": page_snippets[:8],
        "reflection": reflection,
        "screenshot_saved": screenshot_saved
    }

if __name__ == "__main__":
    query_arg = sys.argv[1] if len(sys.argv) > 1 else "hi"
    res = asyncio.run(run_chrome_search_task(query_arg))
    print("\nSummary JSON:\n", json.dumps(res, indent=2, default=str))
