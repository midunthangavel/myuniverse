"""
Send Notification Tool
Dispatches push notifications and banners to simulated or native device.
"""

from typing import Dict, Any
from ..tool_registry import BaseTool, register_tool

@register_tool(name="send_notification", risk_level="low", category="device")
class SendNotificationTool(BaseTool):
    description = "Pushes a system notification or alert banner to the device status tray."
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Notification title"},
            "body": {"type": "string", "description": "Notification body content"},
            "priority": {"type": "string", "enum": ["low", "normal", "high"], "default": "normal"},
            "action_url": {"type": "string", "description": "Optional deep link or route"}
        },
        "required": ["title", "body"]
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        title = params.get("title", "Synapse Alert")
        body = params.get("body", "")
        priority = params.get("priority", "normal")

        return {
            "success": True,
            "action": "SEND_NOTIFICATION",
            "title": title,
            "body": body,
            "priority": priority,
            "delivered": True,
            "message": f"Notification '{title}' delivered to device."
        }
