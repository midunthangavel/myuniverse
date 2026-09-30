"""
Analyze Screen Tool
Evaluates accessibility nodes, interactive elements, and visible semantics.
"""

from typing import Dict, Any, List
from ..tool_registry import BaseTool, register_tool

@register_tool(name="analyze_screen", risk_level="low", category="intelligence")
class AnalyzeScreenTool(BaseTool):
    description = "Analyzes visible UI elements, accessibility tree, and interactive nodes."
    parameters = {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "description": "List of screen nodes with text, tag, and clickable flags",
                "items": {"type": "object"}
            },
            "active_app": {"type": "string", "description": "Current active application name"}
        },
        "required": ["active_app"]
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        nodes: List[Dict[str, Any]] = params.get("nodes", [])
        active_app = params.get("active_app", "unknown")

        interactive_count = sum(1 for n in nodes if n.get("clickable", True))
        extracted_text = " ".join([n.get("text", "") for n in nodes if n.get("text")])

        keywords = []
        for kw in ["IMAX", "Showtime", "Review", "John", "Biryani", "Premier", "Ride", "Confirm"]:
            if kw.lower() in extracted_text.lower():
                keywords.append(kw)

        return {
            "success": True,
            "active_app": active_app,
            "total_elements": len(nodes),
            "clickable_elements": interactive_count,
            "detected_keywords": keywords or ["UI Navigation", "Items"],
            "summary": f"Detected {len(nodes)} UI nodes in {active_app}. Extracted {len(keywords)} contextual keywords."
        }
