"""
Input Text Tool Primitive
Focuses a target input element and enters textual data.
"""

from typing import Dict, Any
from ..tool_registry import BaseTool, register_tool

@register_tool(name="input_text", risk_level="low", category="device")
class InputTextTool(BaseTool):
    description = "Inputs text into a focused field or specific UI target."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to type into the field"},
            "target": {"type": "string", "description": "Optional target input element name or selector"},
            "clear_first": {"type": "boolean", "description": "Whether to clear existing text before typing", "default": False}
        },
        "required": ["text"]
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        text = params.get("text", "")
        target = params.get("target", "active_input")
        clear_first = params.get("clear_first", False)

        return {
            "success": True,
            "action": "INPUT_TEXT",
            "target": target,
            "text_length": len(text),
            "cleared_previous": clear_first,
            "message": f"Entered '{text}' into {target}."
        }
