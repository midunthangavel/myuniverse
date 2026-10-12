import re
from typing import Dict, Any, List, Optional
from .base import CapabilityContract
from .message_capability import MessageSendCapability
from .calendar_capability import CalendarCreateCapability
from .food_capability import FoodOrderCapability
from .alarm_capability import AlarmSetCapability
from .task_capability import TaskCreateCapability

class CapabilityRegistry:
    """
    Registry for standard Synapse capabilities.
    Resolves intents to validated execution contracts with pre- and postconditions.
    """
    def __init__(self):
        self._capabilities: Dict[str, CapabilityContract] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(MessageSendCapability())
        self.register(CalendarCreateCapability())
        self.register(FoodOrderCapability())
        self.register(AlarmSetCapability())
        self.register(TaskCreateCapability())

    def register(self, capability: CapabilityContract):
        self._capabilities[capability.name] = capability

    def get(self, name: str) -> Optional[CapabilityContract]:
        return self._capabilities.get(name)

    def list_all(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": cap.name,
                "description": cap.description,
                "risk_level": cap.risk_level.value,
                "schema": cap.input_schema.model_json_schema()
            }
            for cap in self._capabilities.values()
        ]

    def match_by_intent(self, intent: str, prompt: str = "") -> Optional[CapabilityContract]:
        intent_lower = intent.lower()
        if "message" in intent_lower or "whatsapp" in intent_lower or "text" in intent_lower:
            return self.get("message.send")
        if "calendar" in intent_lower or "meeting" in intent_lower or "schedule" in intent_lower:
            return self.get("calendar.create")
        if "food" in intent_lower or "biryani" in intent_lower or "order" in intent_lower:
            return self.get("food.order")
        if "alarm" in intent_lower or "wake" in intent_lower:
            return self.get("alarm.set")
        if "task" in intent_lower or "todo" in intent_lower or "reminder" in intent_lower:
            return self.get("task.create")
            
        # Fallback keyword regex on prompt
        prompt_lower = prompt.lower()
        if re.search(r"\b(message|whatsapp|send a message|text)\b", prompt_lower):
            return self.get("message.send")
        if re.search(r"\b(schedule|meeting|calendar|appointment)\b", prompt_lower):
            return self.get("calendar.create")
        if re.search(r"\b(food|biryani|order|dinner|lunch)\b", prompt_lower):
            return self.get("food.order")
        if re.search(r"\b(alarm|wake me)\b", prompt_lower):
            return self.get("alarm.set")
        if re.search(r"\b(task|todo|remind me to)\b", prompt_lower):
            return self.get("task.create")

        return None

capability_registry = CapabilityRegistry()
