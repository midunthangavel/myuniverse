"""
Search Food Tool
Queries BiteGo food catalog and restaurant availability.
"""

from typing import Dict, Any
from ..tool_registry import BaseTool, register_tool

@register_tool(name="search_food", risk_level="low", category="service")
class SearchFoodTool(BaseTool):
    description = "Searches BiteGo delivery restaurants, dietary tags, and recommended dishes."
    parameters = {
        "type": "object",
        "properties": {
            "cuisine": {"type": "string", "description": "Cuisine type or dish name"},
            "is_vegetarian": {"type": "boolean", "description": "Filter for vegetarian items", "default": True},
            "preferred_restaurant": {"type": "string", "description": "Preferred restaurant name"}
        },
        "required": ["cuisine"]
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        preferred_restaurant = params.get("preferred_restaurant") or "Paradise Dum Biryani"
        is_vegetarian = params.get("is_vegetarian", True)

        return {
            "success": True,
            "restaurant": preferred_restaurant,
            "distance": "1.2 miles",
            "delivery_time": "22 mins",
            "vegetarian_match": is_vegetarian,
            "recommended_dish": "Special Veg Dum Biryani + Mirchi Ka Salan",
            "price": "$18.50"
        }
