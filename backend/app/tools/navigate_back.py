"""
Navigate Back Tool Primitive
Triggers back navigation in the current app hierarchy or browser history.
"""

from typing import Dict, Any
from ..tool_registry import BaseTool, register_tool

@register_tool(name="navigate_back", risk_level="low", category="device")
class NavigateBackTool(BaseTool):
    description = "Navigates back to the preceding screen or triggers device back button."
    parameters = {
        "type": "object",
        "properties": {
            "steps": {"type": "integer", "description": "Number of back steps to take", "default": 1}
        }
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        steps = params.get("steps", 1)
        return {
            "success": True,
            "action": "NAVIGATE_BACK",
            "steps": steps,
            "message": f"Navigated back {steps} screen(s)."
        }
