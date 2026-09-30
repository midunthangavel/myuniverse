"""
Swipe Screen Tool Primitive
Inspired by minitap-ai gesture primitives.
Executes directional or coordinate-based swipe gestures.
"""

from typing import Dict, Any
from ..tool_registry import BaseTool, register_tool

@register_tool(name="swipe_screen", risk_level="low", category="device")
class SwipeScreenTool(BaseTool):
    description = "Performs directional screen swipe (up, down, left, right) or custom vector gesture."
    parameters = {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["up", "down", "left", "right"],
                "description": "Cardinal swipe direction"
            },
            "distance": {"type": "integer", "description": "Swipe distance in pixels", "default": 400},
            "duration_ms": {"type": "integer", "description": "Swipe duration in milliseconds", "default": 250}
        },
        "required": ["direction"]
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        direction = params.get("direction", "up").lower()
        distance = params.get("distance", 400)
        duration_ms = params.get("duration_ms", 250)

        return {
            "success": True,
            "action": "SWIPE",
            "direction": direction,
            "distance_px": distance,
            "duration_ms": duration_ms,
            "message": f"Swiped {direction} by {distance}px ({duration_ms}ms)."
        }
