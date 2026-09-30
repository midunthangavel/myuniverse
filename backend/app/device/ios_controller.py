"""
iOS WebDriverAgent (WDA) Device Controller
Inspired by minitap-ai ios_controller.py.
Controls connected iOS devices or simulators via WebDriverAgent REST endpoints.
"""

import httpx
from typing import Dict, Any, Optional
from .base_controller import BaseDeviceController, ActionResult

class IOSWDAController(BaseDeviceController):
    """Controls physical iPhone / iPad or Simulator via WebDriverAgent."""

    device_type = "ios"

    def __init__(self, wda_url: str = "http://127.0.0.1:8100", session_id: Optional[str] = None):
        self.wda_url = wda_url.rstrip("/")
        self.session_id = session_id

    async def _get_session(self) -> Optional[str]:
        if self.session_id:
            return self.session_id
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.wda_url}/status")
                if res.status_code == 200:
                    self.session_id = res.json().get("sessionId")
                    return self.session_id
        except Exception:
            pass
        return None

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.wda_url}/status")
                return res.status_code == 200
        except Exception:
            return False

    async def get_device_info(self) -> Dict[str, Any]:
        avail = await self.is_available()
        if not avail:
            return {
                "device_type": "ios",
                "connected": False,
                "endpoint": self.wda_url,
                "note": "WebDriverAgent offline on port 8100. Ready when WDA is launched."
            }
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.wda_url}/status")
                data = res.json().get("value", {})
                return {
                    "device_type": "ios",
                    "connected": True,
                    "model": data.get("device", "iPhone"),
                    "os_version": data.get("os", {}).get("version", "iOS"),
                    "endpoint": self.wda_url
                }
        except Exception as e:
            return {"device_type": "ios", "connected": False, "error": str(e)}

    async def tap(self, x: int, y: int) -> ActionResult:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(f"{self.wda_url}/wda/tap/nil", json={"x": x, "y": y})
                return ActionResult(success=(res.status_code == 200), action="TAP", details={"x": x, "y": y})
        except Exception as e:
            return ActionResult(success=False, action="TAP", error=str(e))

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 250) -> ActionResult:
        try:
            payload = {
                "fromX": x1,
                "fromY": y1,
                "toX": x2,
                "toY": y2,
                "duration": duration_ms / 1000.0
            }
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(f"{self.wda_url}/wda/dragfromtoforduration", json=payload)
                return ActionResult(success=(res.status_code == 200), action="SWIPE", details=payload)
        except Exception as e:
            return ActionResult(success=False, action="SWIPE", error=str(e))

    async def input_text(self, text: str) -> ActionResult:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(f"{self.wda_url}/wda/keys", json={"value": list(text)})
                return ActionResult(success=(res.status_code == 200), action="INPUT_TEXT", details={"text": text})
        except Exception as e:
            return ActionResult(success=False, action="INPUT_TEXT", error=str(e))

    async def press_back(self) -> ActionResult:
        # iOS back gesture or navigation
        return await self.swipe(10, 400, 300, 400, 200)

    async def press_home(self) -> ActionResult:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(f"{self.wda_url}/wda/homescreen")
                return ActionResult(success=(res.status_code == 200), action="GO_HOME")
        except Exception as e:
            return ActionResult(success=False, action="GO_HOME", error=str(e))

    async def launch_app(self, package_or_name: str) -> ActionResult:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(f"{self.wda_url}/wda/apps/launch", json={"bundleId": package_or_name})
                return ActionResult(success=(res.status_code == 200), action="LAUNCH_APP", details={"bundleId": package_or_name})
        except Exception as e:
            return ActionResult(success=False, action="LAUNCH_APP", error=str(e))

    async def get_screenshot(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.wda_url}/screenshot")
                if res.status_code == 200:
                    data = res.json()
                    return {"success": True, "format": "png", "data_base64": data.get("value", "")}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "WDA screenshot failed"}

    async def get_ui_hierarchy(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.wda_url}/source?format=json")
                if res.status_code == 200:
                    return {"success": True, "tree": res.json().get("value", {})}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "WDA source tree failed"}
