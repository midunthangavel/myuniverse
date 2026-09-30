"""
Synapse Granular Agent Tool Primitives.
Auto-registers tools with the ToolRegistryEngine upon package import.
Also provides backward-compatible ToolRegistry facade.
"""

from ..tool_registry import (
    tool_registry,
    register_tool,
    get_tool,
    list_registered_tools,
    execute_tool,
    BaseTool
)

from .tap_element import TapElementTool
from .swipe_screen import SwipeScreenTool
from .input_text import InputTextTool
from .launch_app import LaunchAppTool
from .navigate_back import NavigateBackTool
from .take_screenshot import TakeScreenshotTool
from .schedule_meeting import ScheduleMeetingTool
from .analyze_screen import AnalyzeScreenTool
from .web_search import WebSearchTool
from .send_notification import SendNotificationTool
from .search_movies import SearchMoviesTool
from .search_food import SearchFoodTool

class ToolRegistry:
    """Legacy compatibility facade mapping to the new Decorator Tool Registry."""

    @staticmethod
    def search_movies(movie_name: str, preferred_theater: str = None, preferred_slot: str = None):
        return execute_tool("search_movies", {
            "movie_name": movie_name,
            "preferred_theater": preferred_theater,
            "preferred_slot": preferred_slot
        })

    @staticmethod
    def search_food(cuisine: str, is_vegetarian: bool = True, preferred_restaurant: str = None):
        return execute_tool("search_food", {
            "cuisine": cuisine,
            "is_vegetarian": is_vegetarian,
            "preferred_restaurant": preferred_restaurant
        })

    @staticmethod
    def analyze_screen_nodes(nodes, active_app: str):
        return execute_tool("analyze_screen", {
            "nodes": nodes,
            "active_app": active_app
        })

    @staticmethod
    def schedule_meeting(attendee: str, time_slot: str, conflict_check: bool = True):
        return execute_tool("schedule_meeting", {
            "attendee": attendee,
            "time_slot": time_slot,
            "conflict_check": conflict_check
        })

__all__ = [
    "ToolRegistry",
    "tool_registry",
    "register_tool",
    "get_tool",
    "list_registered_tools",
    "execute_tool",
    "BaseTool",
    "TapElementTool",
    "SwipeScreenTool",
    "InputTextTool",
    "LaunchAppTool",
    "NavigateBackTool",
    "TakeScreenshotTool",
    "ScheduleMeetingTool",
    "AnalyzeScreenTool",
    "WebSearchTool",
    "SendNotificationTool",
    "SearchMoviesTool",
    "SearchFoodTool",
]
