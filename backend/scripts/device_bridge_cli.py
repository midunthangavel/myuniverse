"""
Synapse AI — Real Device Bridge Interactive CLI & Diagnostics Tool
Run this tool to:
1. Detect physical Android devices via USB or Wireless ADB
2. Capture live screen frames and save to disk
3. Dump live accessibility UI trees via UIAutomator
4. Test physical touch and keyevent injection
"""

import sys
import os
import argparse
import asyncio
import time

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.device.controller_factory import device_factory
from app.device.android_controller import AndroidADBController
from app.device.ui_parser import UIAutomatorParser

def print_banner():
    print("=" * 60)
    print("   SYNAPSE AI — REAL ANDROID DEVICE BRIDGE (ADB)   ")
    print("=" * 60)

async def detect_device():
    print_banner()
    ctrl = AndroidADBController()
    print(f"[*] ADB Binary: {ctrl.adb_bin}")
    
    code, out, _ = await ctrl._run_adb(["devices", "-l"])
    print(f"[*] Raw 'adb devices' output:\n{out.strip()}\n")

    avail = await ctrl.is_available()
    if avail:
        info = await ctrl.get_device_info()
        print("[+] SUCCESS: Android device is CONNECTED and READY!")
        print(f"    - Model: {info.get('model')}")
        print(f"    - Android Version: {info.get('android_version')}")
        print(f"    - Display Size: {info.get('display_size')}")
        print(f"    - Serial: {info.get('serial')}")
        return True
    else:
        print("[-] NO ACTIVE ANDROID DEVICE DETECTED YET.")
        print("\n--> How to connect your Android phone:")
        print("    1. Connect phone to PC via USB cable.")
        print("    2. On phone: Go to Settings -> About Phone -> Tap 'Build Number' 7 times to enable Developer Options.")
        print("    3. In Developer Options: Turn ON 'USB Debugging'.")
        print("    4. If prompted on phone screen: Check 'Always allow from this computer' and tap 'Allow'.")
        print("\n--> Or connect via Wireless ADB:")
        print("    Run: adb connect <phone_ip_address>:<port>")
        return False

async def capture_screen(output_path="device_screen.png"):
    ctrl = AndroidADBController()
    if not await ctrl.is_available():
        print("[-] No device connected to capture screenshot.")
        return
    print(f"[*] Capturing screenshot from connected Android device...")
    res = await ctrl.get_screenshot()
    if res.get("success"):
        import base64
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(res["data_base64"]))
        print(f"[+] Screenshot saved successfully: {os.path.abspath(output_path)}")
    else:
        print(f"[-] Screenshot failed: {res.get('error')}")

async def dump_ui():
    ctrl = AndroidADBController()
    if not await ctrl.is_available():
        print("[-] No device connected to dump UI.")
        return
    print(f"[*] Dumping UIAutomator hierarchy...")
    res = await ctrl.get_ui_hierarchy()
    if res.get("success"):
        nodes = res.get("nodes", [])
        print(f"[+] Successfully extracted {len(nodes)} UI nodes from active phone screen:")
        for idx, n in enumerate(nodes[:15]):
            clickable = "CLICKABLE" if n.get("clickable") else "STATIC"
            print(f"    [{idx+1}] {n.get('text', '<no text>')} ({n.get('bounds')}) [{clickable}]")
        if len(nodes) > 15:
            print(f"    ... and {len(nodes) - 15} more nodes.")
    else:
        print(f"[-] UI dump failed: {res.get('error')}")

async def listen_loop():
    print_banner()
    print("[*] Listening for USB or Wireless Android connection... (Press Ctrl+C to stop)")
    ctrl = AndroidADBController()
    connected = False
    
    while True:
        is_now = await ctrl.is_available()
        if is_now and not connected:
            connected = True
            info = await ctrl.get_device_info()
            print(f"\n[+] DEVICE ATTACHED: {info.get('model')} (Android {info.get('android_version')})!")
            print(f"    Display resolution: {info.get('display_size')}")
            print(f"    Active mode: REAL HARDWARE CONTROLLER ACTIVATED.")
        elif not is_now and connected:
            connected = False
            print("\n[-] Device detached. Reverting to web simulator...")
        time.sleep(2)

def main():
    parser = argparse.ArgumentParser(description="Synapse AI Real Device Bridge CLI")
    parser.add_argument("--detect", action="store_true", help="Detect connected devices")
    parser.add_argument("--screenshot", type=str, nargs="?", const="device_screen.png", help="Capture screenshot")
    parser.add_argument("--ui", action="store_true", help="Dump UIAutomator accessibility tree")
    parser.add_argument("--listen", action="store_true", help="Poll continuously for attached devices")
    parser.add_argument("--tap", type=int, nargs=2, metavar=("X", "Y"), help="Tap coordinates on real device")
    
    args = parser.parse_args()

    if args.screenshot:
        asyncio.run(capture_screen(args.screenshot))
    elif args.ui:
        asyncio.run(dump_ui())
    elif args.tap:
        x, y = args.tap
        ctrl = AndroidADBController()
        res = asyncio.run(ctrl.tap(x, y))
        print(f"Tap result: {res.to_dict()}")
    elif args.listen:
        asyncio.run(listen_loop())
    else:
        asyncio.run(detect_device())

if __name__ == "__main__":
    main()
