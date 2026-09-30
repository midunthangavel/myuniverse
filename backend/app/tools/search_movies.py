"""
Search Movies Tool
Queries CinePass movie catalog and seat availability.
"""

from typing import Dict, Any
from ..tool_registry import BaseTool, register_tool

@register_tool(name="search_movies", risk_level="low", category="service")
class SearchMoviesTool(BaseTool):
    description = "Searches CinePass movie showtimes, venues, and seat availability."
    parameters = {
        "type": "object",
        "properties": {
            "movie_name": {"type": "string", "description": "Title of the movie"},
            "preferred_theater": {"type": "string", "description": "User preferred theater chain or branch"},
            "preferred_slot": {"type": "string", "description": "Preferred time slot (e.g. 8:30 PM)"}
        },
        "required": ["movie_name"]
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        movie = params.get("movie_name", "Interstellar 70mm IMAX")
        theater = params.get("preferred_theater") or "PVR INOX Palladium IMAX"
        slot = params.get("preferred_slot") or "8:30 PM"

        return {
            "success": True,
            "movie": movie,
            "venue": theater,
            "matched_slot": slot,
            "available_seats": ["F14", "F15", "F16"],
            "unit_price": "$18.00",
            "total_price": "$36.00 (2 tickets)"
        }
