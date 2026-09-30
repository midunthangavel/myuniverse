"""
Device Controller Factory
Inspired by minitap-ai controller_factory.py.
Dynamically resolves device driver: Android (ADB) -> iOS (WDA) -> Web Simulator.
"""

from typing import Dict, Any, Optional
from .base_controller import BaseDeviceController, ActionResult
from .android_controller import AndroidADBController
from .ios_controller import IOSWDAController
from .sim_controller import SimulatorController

class DeviceControllerFactory:
    """Factory creating and managing device automation controllers."""

    def __init__(self):
        self.android = AndroidADBController()
        self.ios = IOSWDAController()
        self.simulator = SimulatorController()
        self._active_mode = "auto"
        self._active_controller: Optional[BaseDeviceController] = None

    async def get_controller(self, mode: str = "auto") -> BaseDeviceController:
        mode = mode.lower()
        if mode == "android":
            self._active_controller = self.android
            return self.android
        if mode == "ios":
            self._active_controller = self.ios
            return self.ios
        if mode == "simulator":
            self._active_controller = self.simulator
            return self.simulator

        # Auto detection
        if await self.android.is_available():
            self._active_controller = self.android
            return self.android
        if await self.ios.is_available():
            self._active_controller = self.ios
            return self.ios

        self._active_controller = self.simulator
        return self.simulator

    async def get_status(self) -> Dict[str, Any]:
        ctrl = await self.get_controller(self._active_mode)
        info = await ctrl.get_device_info()
        return {
            "active_mode": self._active_mode,
            "active_device_type": ctrl.device_type,
            "device_info": info,
            "available_drivers": {
                "android_adb": await self.android.is_available(),
                "ios_wda": await self.ios.is_available(),
                "web_simulator": True
            }
        }

    def set_mode(self, mode: str):
        self._active_mode = mode.lower()


# Singleton device factory
device_factory = DeviceControllerFactory()
