"""
Web Simulator Device Controller
Controls the active virtual phone simulator in the browser.
Ensures zero-dependency standalone execution when no real hardware is connected.
"""

from typing import Dict, Any, List, Optional
from .base_controller import BaseDeviceController, ActionResult
import time

class SimulatorController(BaseDeviceController):
    """Controls the local Synapse phone web simulator."""

    device_type = "simulator"

    def __init__(self):
        self.active_app = "home"
        self.last_action_time = time.time()

    async def get_device_info(self) -> Dict[str, Any]:
        return {
            "device_type": "simulator",
            "connected": True,
            "model": "Synapse Neural Virtual Phone Pro",
            "os_version": "SynapseOS 2.0 (Simulated)",
            "resolution": "1080x2400 (FHD+)",
            "supported_apps": ["cinema", "food", "pulse_ride", "orbit_maps", "calendar", "spark_mail"],
            "active_app": self.active_app,
            "status": "online"
        }

    async def tap(self, x: int, y: int) -> ActionResult:
        self.last_action_time = time.time()
        return ActionResult(
            success=True,
            action="TAP",
            details={"x": x, "y": y, "target_type": "simulated_touch"}
        )

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 250) -> ActionResult:
        self.last_action_time = time.time()
        direction = "up" if y2 < y1 else "down" if y2 > y1 else "left" if x2 < x1 else "right"
        return ActionResult(
            success=True,
            action="SWIPE",
            details={"direction": direction, "from": (x1, y1), "to": (x2, y2), "duration_ms": duration_ms}
        )

    async def input_text(self, text: str) -> ActionResult:
        self.last_action_time = time.time()
        return ActionResult(
            success=True,
            action="INPUT_TEXT",
            details={"text": text, "target": "focused_input"}
        )

    async def press_back(self) -> ActionResult:
        self.last_action_time = time.time()
        return ActionResult(success=True, action="NAVIGATE_BACK")

    async def press_home(self) -> ActionResult:
        self.active_app = "home"
        self.last_action_time = time.time()
        return ActionResult(success=True, action="GO_HOME", details={"active_app": "home"})

    async def launch_app(self, package_or_name: str) -> ActionResult:
        self.active_app = package_or_name.lower()
        self.last_action_time = time.time()
        return ActionResult(
            success=True,
            action="LAUNCH_APP",
            details={"active_app": self.active_app}
        )

    async def get_screenshot(self) -> Dict[str, Any]:
        return {
            "success": True,
            "format": "virtual_buffer",
            "resolution": "1080x2400",
            "active_app": self.active_app,
            "timestamp": time.time()
        }

    async def get_ui_hierarchy(self) -> Dict[str, Any]:
        return {
            "success": True,
            "active_app": self.active_app,
            "source": "synapse_phone_dom",
            "nodes_count": 8
        }
