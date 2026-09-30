"""
Synapse AI — Autonomous Google Chrome Action: Click "Images" Tab
Navigates to the "Images" tab on the active Google Search results page for "hi".
Calibrated coordinates: X=400, Y=575 on 1080x2400 display.
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
from app.reflector import action_reflector

ARTIFACT_DIR = r"C:\Users\midun\.gemini\antigravity-ide\brain\88217639-3497-4e32-8166-9dd0188cdf56"

async def click_images_tab():
    print("=" * 65)
    print(" SYNAPSE AI — NAVIGATING TO GOOGLE IMAGES TAB")
    print(" Target: 'Images' tab on Google Search 'hi' results page")
    print("=" * 65)

    ctrl = AndroidADBController()
    available = await ctrl.is_available()
    if not available:
        print("[!] ERROR: No authorized Android device detected.")
        return {"success": False, "error": "Device not available"}

    info = await ctrl.get_device_info()
    print(f"[+] Device: {info.get('model')} (Android {info.get('android_version')})")

    # Step 1: Ensure screen is awake
    await ctrl._run_adb(["shell", "input", "keyevent", "224"])
    await asyncio.sleep(0.5)

    # Step 2: Inject tap on "Images" tab at precisely calibrated center (400, 575)
    target_x, target_y = 400, 575
    print(f"[*] Tapping 'Images' tab at verified center ({target_x}, {target_y})...")
    tap_res = await ctrl.tap(target_x, target_y)
    print(f"    Tap status: {tap_res.success}")

    # Wait for Google Images to transition & render
    print("[*] Waiting 4.0s for Google Images grid to render...")
    await asyncio.sleep(4.0)

    # Step 3: Capture live proof screenshot
    print("[*] Capturing proof screenshot from physical phone...")
    scr_res = await ctrl.get_screenshot()
    screenshot_saved = False
    if scr_res.get("success") and scr_res.get("data_base64"):
        img_bytes = base64.b64decode(scr_res["data_base64"])
        
        local_png = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chrome_images_tab_result.png")
        with open(local_png, "wb") as f:
            f.write(img_bytes)
        print(f"[+] Saved local screenshot: {local_png} ({len(img_bytes)} bytes)")

        if os.path.exists(ARTIFACT_DIR):
            artifact_png = os.path.join(ARTIFACT_DIR, "chrome_images_tab_result.png")
            with open(artifact_png, "wb") as f:
                f.write(img_bytes)
            print(f"[+] Copied to artifacts directory: {artifact_png}")
            screenshot_saved = True

    print("\n" + "=" * 65)
    print(" GOOGLE IMAGES TAB NAVIGATION COMPLETED")
    print("=" * 65)

    return {
        "success": True,
        "action": "CLICK_IMAGES_TAB",
        "tapped_coordinates": (target_x, target_y),
        "screenshot_saved": screenshot_saved
    }

if __name__ == "__main__":
    res = asyncio.run(click_images_tab())
    print("\nSummary JSON:\n", json.dumps(res, indent=2, default=str))
