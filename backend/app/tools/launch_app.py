"""
Launch App Tool Primitive
Opens simulated or native target applications.
"""

from typing import Dict, Any
from ..tool_registry import BaseTool, register_tool

@register_tool(name="launch_app", risk_level="low", category="device")
class LaunchAppTool(BaseTool):
    description = "Launches an application by name or package identifier (e.g., cinema, food, pulse_ride, orbit_maps, calendar, spark_mail)."
    parameters = {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "App identifier (cinema, food, pulse_ride, orbit_maps, calendar, spark_mail, or package name)"
            },
            "reset_state": {"type": "boolean", "description": "Reset app to home view", "default": False}
        },
        "required": ["app_name"]
    }

    APP_MAP = {
        "cinema": "CinePass IMAX Experience",
        "cinepass": "CinePass IMAX Experience",
        "movie": "CinePass IMAX Experience",
        "food": "BiteGo Delivery Express",
        "bitego": "BiteGo Delivery Express",
        "pulse_ride": "PulseRide Premier Mobility",
        "ride": "PulseRide Premier Mobility",
        "uber": "PulseRide Premier Mobility",
        "orbit_maps": "Orbit Maps Live Nav",
        "maps": "Orbit Maps Live Nav",
        "navigation": "Orbit Maps Live Nav",
        "calendar": "Synapse Smart Schedule",
        "spark_mail": "SparkMail Priority Inbox",
        "mail": "SparkMail Priority Inbox"
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        app_key = params.get("app_name", "").lower()
        formal_name = self.APP_MAP.get(app_key, app_key.title())
        reset_state = params.get("reset_state", False)

        return {
            "success": True,
            "action": "LAUNCH_APP",
            "app_key": app_key,
            "app_name": formal_name,
            "reset_state": reset_state,
            "message": f"Foreground application switched to {formal_name}."
        }
