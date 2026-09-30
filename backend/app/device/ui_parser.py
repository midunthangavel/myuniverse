"""
UIAutomator & View Hierarchy XML Parser for Device Bridge
Inspired by minitap-ai UIAutomator XML parsing pattern.
Converts Android accessibility node hierarchy dumps into structured UI node elements.
"""

import xml.etree.ElementTree as ET
import re
from typing import Dict, Any, List, Optional

class UIAutomatorParser:
    """Parses Android uiautomator dump XML into structured elements."""

    @staticmethod
    def parse_bounds(bounds_str: str) -> Dict[str, int]:
        """Parses '[x1,y1][x2,y2]' bounds into {x1, y1, x2, y2, width, height, center_x, center_y}."""
        pattern = r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]"
        m = re.match(pattern, bounds_str or "")
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            return {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "width": x2 - x1,
                "height": y2 - y1,
                "center_x": (x1 + x2) // 2,
                "center_y": (y1 + y2) // 2
            }
        return {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "width": 0, "height": 0, "center_x": 0, "center_y": 0}

    @classmethod
    def parse_xml(cls, xml_content: str) -> List[Dict[str, Any]]:
        """Parses UIAutomator XML dump string into clean list of UI nodes."""
        nodes: List[Dict[str, Any]] = []
        if not xml_content or not xml_content.strip():
            return nodes

        try:
            root = ET.fromstring(xml_content.strip())
            for elem in root.iter("node"):
                text = elem.attrib.get("text", "")
                content_desc = elem.attrib.get("content-desc", "")
                resource_id = elem.attrib.get("resource-id", "")
                class_name = elem.attrib.get("class", "")
                clickable = elem.attrib.get("clickable", "false") == "true"
                bounds_str = elem.attrib.get("bounds", "")

                label = text or content_desc or resource_id.split("/")[-1] if resource_id else ""
                if label or clickable:
                    bounds = cls.parse_bounds(bounds_str)
                    nodes.append({
                        "text": label,
                        "resource_id": resource_id,
                        "class_name": class_name,
                        "clickable": clickable,
                        "bounds": bounds,
                        "center": (bounds["center_x"], bounds["center_y"])
                    })
        except Exception as e:
            print(f"UIAutomator XML parsing warning: {e}")

        return nodes

    @staticmethod
    def filter_interactive_elements(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters nodes to only actionable interactive elements."""
        return [n for n in nodes if n.get("clickable") or len(n.get("text", "").strip()) > 0]
