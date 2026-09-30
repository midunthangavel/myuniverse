"""
Android ADB Device Controller
Inspired by minitap-ai android_controller.py.
Controls connected physical Android phones or emulators via Android Debug Bridge (ADB).
"""

import asyncio
import os
import shutil
import base64
from typing import Dict, Any, Optional, List
from .base_controller import BaseDeviceController, ActionResult
from .ui_parser import UIAutomatorParser

class AndroidADBController(BaseDeviceController):
    """Controls physical or emulated Android devices via ADB."""
    
    device_type = "android"

    @staticmethod
    def _find_adb() -> str:
        adb = shutil.which("adb")
        if adb:
            return adb

        env_adb = os.getenv("ADB_PATH")
        if env_adb and os.path.exists(env_adb):
            return env_adb

        candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
            os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
            r"C:\Android\Sdk\platform-tools\adb.exe",
            r"C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe"
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return "adb"

    def __init__(self, serial: Optional[str] = None):
        self.serial = serial
        self.adb_bin = self._find_adb()

    def _cmd_prefix(self) -> list:
        prefix = [self.adb_bin]
        if self.serial:
            prefix.extend(["-s", self.serial])
        return prefix

    async def _run_adb(self, args: list, timeout: float = 10.0) -> tuple:
        cmd = self._cmd_prefix() + args
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode, stdout.decode("utf-8", errors="ignore"), stderr.decode("utf-8", errors="ignore")
        except Exception as e:
            return -1, "", str(e)

    async def is_available(self) -> bool:
        code, out, _ = await self._run_adb(["devices"])
        if code != 0:
            return False
        lines = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith("List of devices")]
        return len(lines) > 0

    async def get_device_info(self) -> Dict[str, Any]:
        avail = await self.is_available()
        if not avail:
            return {
                "device_type": "android",
                "connected": False,
                "serial": self.serial,
                "note": "No active ADB device detected. Ready to attach via USB or TCP/IP."
            }
        
        _, model, _ = await self._run_adb(["shell", "getprop", "ro.product.model"])
        _, android_ver, _ = await self._run_adb(["shell", "getprop", "ro.build.version.release"])
        _, wm_size, _ = await self._run_adb(["shell", "wm", "size"])

        return {
            "device_type": "android",
            "connected": True,
            "serial": self.serial or "primary_device",
            "model": model.strip(),
            "android_version": android_ver.strip(),
            "display_size": wm_size.strip().replace("Physical size: ", "")
        }

    async def tap(self, x: int, y: int) -> ActionResult:
        code, out, err = await self._run_adb(["shell", "input", "tap", str(x), str(y)])
        return ActionResult(
            success=(code == 0),
            action="TAP",
            details={"x": x, "y": y, "platform": "android"},
            error=err if code != 0 else None
        )

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 250) -> ActionResult:
        code, out, err = await self._run_adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])
        return ActionResult(
            success=(code == 0),
            action="SWIPE",
            details={"from": (x1, y1), "to": (x2, y2), "duration_ms": duration_ms},
            error=err if code != 0 else None
        )

    async def input_text(self, text: str) -> ActionResult:
        escaped = text.replace(" ", "%s").replace("&", "\\&").replace("'", "\\'")
        code, out, err = await self._run_adb(["shell", "input", "text", escaped])
        return ActionResult(
            success=(code == 0),
            action="INPUT_TEXT",
            details={"text": text},
            error=err if code != 0 else None
        )

    async def press_back(self) -> ActionResult:
        code, out, err = await self._run_adb(["shell", "input", "keyevent", "4"])
        return ActionResult(success=(code == 0), action="NAVIGATE_BACK", error=err if code != 0 else None)

    async def press_home(self) -> ActionResult:
        code, out, err = await self._run_adb(["shell", "input", "keyevent", "3"])
        return ActionResult(success=(code == 0), action="GO_HOME", error=err if code != 0 else None)

    async def launch_app(self, package_or_name: str) -> ActionResult:
        if "/" in package_or_name:
            code, out, err = await self._run_adb(["shell", "am", "start", "-n", package_or_name])
        else:
            code, out, err = await self._run_adb(["shell", "monkey", "-p", package_or_name, "-c", "android.intent.category.LAUNCHER", "1"])
            if code != 0:
                code, out, err = await self._run_adb(["shell", "monkey", "-p", package_or_name, "1"])
        return ActionResult(
            success=(code == 0),
            action="LAUNCH_APP",
            details={"package": package_or_name},
            error=err if code != 0 else None
        )

    async def get_screenshot(self) -> Dict[str, Any]:
        cmd = self._cmd_prefix() + ["exec-out", "screencap", "-p"]
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await proc.communicate()
            if proc.returncode == 0 and len(stdout) > 0:
                b64 = base64.b64encode(stdout).decode("utf-8")
                return {"success": True, "format": "png", "data_base64": b64, "bytes_count": len(stdout)}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "screencap failed"}

    async def get_ui_hierarchy(self) -> Dict[str, Any]:
        await self._run_adb(["shell", "uiautomator", "dump", "/sdcard/window_dump.xml"])
        code, out, _ = await self._run_adb(["shell", "cat", "/sdcard/window_dump.xml"])
        if code == 0 and out:
            nodes = UIAutomatorParser.parse_xml(out)
            return {"success": True, "total_nodes": len(nodes), "nodes": nodes}
        return {"success": False, "error": "Failed to dump uiautomator tree"}
