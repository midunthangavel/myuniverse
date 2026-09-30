"""
Proactive Ambient Intelligence Engine for Synapse AI.
Enables the phone agent to autonomously listen for background device events
(e.g., calendar conflicts, traffic delays, flight alerts, price drops)
and proactively alert the user without waiting for manual prompts.
"""

import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class AmbientEvent(BaseModel):
    event_id: str
    event_type: str  # TRAFFIC_ALERT | FLIGHT_DELAY | CALENDAR_CONFLICT | SEAT_OPENING
    source_app: str  # mail | calendar | maps | cinepass
    priority: str    # low | medium | high | urgent
    title: str
    description: str
    data: Dict[str, Any]
    timestamp: float = 0.0

class ProactiveIntelligenceEngine:
    def __init__(self, viking_fs, system1_classifier):
        self.viking_fs = viking_fs
        self.system1 = system1_classifier
        self.event_queue: List[AmbientEvent] = []
        self._init_scenario_templates()

    def _init_scenario_templates(self):
        """Pre-defined scenario templates for ambient real-world mobile events."""
        self.templates = {
            "traffic_conflict": {
                "event_type": "TRAFFIC_ALERT",
                "source_app": "maps",
                "priority": "urgent",
                "title": "Severe Traffic on Commute to Tech Summit",
                "description": "Accident on I-95 North adds 35 mins. Meeting with John Vance starts in 25 mins.",
                "data": {
                    "destination": "Downtown Convention Center",
                    "scheduled_time": "15:00",
                    "delay_minutes": 35,
                    "target_contact": "John Vance",
                    "suggested_actions": ["Reroute via express transit", "Message John to delay by 15 mins"]
                }
            },
            "flight_delay": {
                "event_type": "FLIGHT_DELAY",
                "source_app": "mail",
                "priority": "high",
                "title": "Delta Flight DL-482 Delayed by 2 Hours",
                "description": "Inbound aircraft delayed. New arrival: 8:45 PM. Airport pickup & dinner reservation conflict.",
                "data": {
                    "flight_number": "DL-482",
                    "original_arrival": "18:45",
                    "new_arrival": "20:45",
                    "conflicts": ["Hotel Check-in", "Dinner at Bangkok Street Deli"],
                    "suggested_actions": ["Reschedule dinner to 21:15", "Notify airport taxi"]
                }
            },
            "imax_seat_alert": {
                "event_type": "SEAT_OPENING",
                "source_app": "cinepass",
                "priority": "medium",
                "title": "Prime Center Seat G12 Just Released for Dune 70mm",
                "description": "Cancellation detected at Downtown IMAX for 8:15 PM showing. Matches your top seating habit.",
                "data": {
                    "theater": "Downtown IMAX Megaplex",
                    "format": "70mm IMAX Laser",
                    "showtime": "20:15",
                    "seat": "Row G, Seat 12 (Prime Center)",
                    "price": "$24.50",
                    "suggested_actions": ["Hold seat with 1-tap biometric confirmation"]
                }
            }
        }

    def trigger_ambient_event(self, template_key: str) -> Dict[str, Any]:
        """Triggers and evaluates an ambient device event."""
        template = self.templates.get(template_key)
        if not template:
            return {"error": f"Unknown template '{template_key}'"}

        event = AmbientEvent(
            event_id=f"evt_{int(time.time() * 1000)}",
            event_type=template["event_type"],
            source_app=template["source_app"],
            priority=template["priority"],
            title=template["title"],
            description=template["description"],
            data=template["data"],
            timestamp=time.time()
        )
        self.event_queue.append(event)

        # Formulate proactive resolution plan
        plan = self._formulate_proactive_plan(event)

        return {
            "event": event.dict(),
            "proactive_plan": plan
        }

    def _formulate_proactive_plan(self, event: AmbientEvent) -> Dict[str, Any]:
        """Synthesizes proactive cross-app action plan based on user habits."""
        if event.event_type == "TRAFFIC_ALERT":
            return {
                "character_state": "WAITING_CONFIRM",
                "speech_prompt": "Alex, an accident on I-95 will make you 15 minutes late for John. Shall I send him a quick update and hail an express ride?",
                "risk_tier": "medium",
                "steps": [
                    {"step": 1, "app": "spark_mail", "action": "DRAFT_MESSAGE", "to": "John Vance", "msg": "Running 15 mins late due to traffic."},
                    {"step": 2, "app": "maps", "action": "REROUTE_TRANSIT", "mode": "EXPRESS_LINE"}
                ],
                "governance_mode": "ASK"
            }
        elif event.event_type == "FLIGHT_DELAY":
            return {
                "character_state": "WAITING_CONFIRM",
                "speech_prompt": "Delta flight DL-482 was delayed by 2 hours. Would you like me to push your dinner reservation to 9:15 PM and notify your pickup?",
                "risk_tier": "medium",
                "steps": [
                    {"step": 1, "app": "bitego", "action": "RESCHEDULE_RESERVATION", "time": "21:15"},
                    {"step": 2, "app": "spark_mail", "action": "UPDATE_TAXI_PICKUP", "flight": "DL-482"}
                ],
                "governance_mode": "ASK"
            }
        else: # SEAT_OPENING
            return {
                "character_state": "WAITING_CONFIRM",
                "speech_prompt": "Prime Center Seat G12 just opened up for Dune 70mm IMAX tonight! Shall I reserve it for you?",
                "risk_tier": "high",
                "steps": [
                    {"step": 1, "app": "cinepass", "action": "SELECT_SEAT", "seat": "G12"},
                    {"step": 2, "app": "cinepass", "action": "AUTHORIZE_BOOKING", "cost": "$24.50"}
                ],
                "governance_mode": "ASK"
            }
