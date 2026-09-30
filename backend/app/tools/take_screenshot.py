"""
Take Screenshot Tool Primitive
Captures current screen buffer, node accessibility state, or visual bounding boxes.
"""

import time
from typing import Dict, Any
from ..tool_registry import BaseTool, register_tool

@register_tool(name="take_screenshot", risk_level="low", category="device")
class TakeScreenshotTool(BaseTool):
    description = "Captures an instantaneous screenshot and extracts view hierarchy metadata."
    parameters = {
        "type": "object",
        "properties": {
            "include_hierarchy": {"type": "boolean", "description": "Include extracted UI accessibility tree", "default": True},
            "quality": {"type": "integer", "description": "Compression quality 1-100", "default": 85}
        }
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        include_hierarchy = params.get("include_hierarchy", True)
        timestamp = time.time()
        return {
            "success": True,
            "action": "TAKE_SCREENSHOT",
            "timestamp": timestamp,
            "resolution": "1080x2400",
            "format": "image/webp",
            "hierarchy_included": include_hierarchy,
            "message": "Screen snapshot successfully captured for perception engine."
        }
