"""
Base Device Controller for Synapse Agent
Inspired by minitap-ai/mobile-use device controller abstractions.
Defines unified interface for real Android (ADB), iOS (WebDriverAgent), and Simulator devices.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class ActionResult:
    """Standardized action response across all device platforms."""
    def __init__(self, success: bool, action: str, details: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.success = success
        self.action = action
        self.details = details or {}
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "details": self.details,
            "error": self.error
        }


class BaseDeviceController(ABC):
    """Abstract controller interface covering phone touch, keyboard, screen perception, and navigation."""

    device_type: str = "unknown"

    @abstractmethod
    async def get_device_info(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def tap(self, x: int, y: int) -> ActionResult:
        pass

    @abstractmethod
    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 250) -> ActionResult:
        pass

    @abstractmethod
    async def input_text(self, text: str) -> ActionResult:
        pass

    @abstractmethod
    async def press_back(self) -> ActionResult:
        pass

    @abstractmethod
    async def press_home(self) -> ActionResult:
        pass

    @abstractmethod
    async def launch_app(self, package_or_name: str) -> ActionResult:
        pass

    @abstractmethod
    async def get_screenshot(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_ui_hierarchy(self) -> Dict[str, Any]:
        pass
