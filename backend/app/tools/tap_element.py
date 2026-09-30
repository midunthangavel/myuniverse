"""
Tap Element Tool Primitive
Inspired by minitap-ai touch primitives.
Simulates or dispatches tap events on specified elements or screen coordinates.
"""

from typing import Dict, Any
from ..tool_registry import BaseTool, register_tool

@register_tool(name="tap_element", risk_level="low", category="device")
class TapElementTool(BaseTool):
    description = "Taps a targeted UI element by selector, resource ID, text label, or (x, y) coordinates."
    parameters = {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Element text, resource ID, or CSS selector"},
            "x": {"type": "number", "description": "Optional X screen coordinate (0.0 to 1.0 or pixel value)"},
            "y": {"type": "number", "description": "Optional Y screen coordinate (0.0 to 1.0 or pixel value)"},
            "wait_after_ms": {"type": "integer", "description": "Wait time in ms after tap", "default": 200}
        },
        "required": ["target"]
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get("target", "")
        x = params.get("x")
        y = params.get("y")
        wait_ms = params.get("wait_after_ms", 200)

        coord_str = f" at ({x}, {y})" if x is not None and y is not None else ""
        return {
            "success": True,
            "action": "TAP",
            "target": target,
            "coordinates": {"x": x, "y": y} if x is not None else None,
            "wait_ms": wait_ms,
            "message": f"Successfully tapped '{target}'{coord_str}."
        }
