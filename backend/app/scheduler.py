"""
Autonomous Scheduler Daemon for Synapse AI Agent
Manages ambient cron triggers, background traffic monitors, meeting prep notifications,
and habit flywheel recalibration sweeps.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional

class AutonomousSchedulerDaemon:
    """Coordinates ambient background schedules and drains alert notifications."""

    DEFAULT_RULES = [
        {
            "rule_id": "rule_morning_briefing",
            "title": "Daily Morning Ambient Briefing",
            "schedule": "08:00 AM Daily",
            "description": "Synthesizes agenda, morning commute traffic, flight updates, and tailored recommendations.",
            "category": "proactive",
            "enabled": True,
            "last_run": None
        },
        {
            "rule_id": "rule_traffic_monitor",
            "title": "Dynamic Commute Traffic Watcher",
            "schedule": "Every 30 mins (Commute Windows 07:30-09:30, 16:30-18:30)",
            "description": "Monitors highway I-95 congestion and suggests alternative transit or pulse ride.",
            "category": "mobility",
            "enabled": True,
            "last_run": None
        },
        {
            "rule_id": "rule_meeting_prep",
            "title": "Pre-Meeting Context Dossier",
            "schedule": "15 mins before Calendar Events",
            "description": "Pre-loads attendee email threads and Viking context notes into working memory.",
            "category": "productivity",
            "enabled": True,
            "last_run": None
        },
        {
            "rule_id": "rule_flywheel_decay",
            "title": "Bayesian Habit Decay & Confidence Sweep",
            "schedule": "Every Sunday at 00:00",
            "description": "Recalibrates decayed preferences and promotes verified routines to ChromaDB.",
            "category": "learning",
            "enabled": True,
            "last_run": None
        }
    ]

    def __init__(self):
        self.rules: Dict[str, Dict[str, Any]] = {r["rule_id"]: dict(r) for r in self.DEFAULT_RULES}
        self.notification_queue: List[Dict[str, Any]] = []
        self._running = False

    def list_rules(self) -> List[Dict[str, Any]]:
        return list(self.rules.values())

    def trigger_rule(self, rule_id: str) -> Dict[str, Any]:
        """Manually triggers a rule for demonstration and testing."""
        rule = self.rules.get(rule_id)
        if not rule:
            return {"success": False, "error": f"Rule '{rule_id}' not found"}

        now = time.time()
        rule["last_run"] = now

        # Formulate contextual notification
        if rule_id == "rule_morning_briefing":
            notification = {
                "id": f"notif_{int(now * 1000)}",
                "title": "☀️ Good Morning! Your Synapse Briefing",
                "body": "2 meetings scheduled today. ⚠️ +15m heavy traffic on I-95 North. CinePass Interstellar tonight at 8:30 PM.",
                "category": "briefing",
                "timestamp": now,
                "priority": "high",
                "actions": ["View Route", "Open CinePass"]
            }
        elif rule_id == "rule_traffic_monitor":
            notification = {
                "id": f"notif_{int(now * 1000)}",
                "title": "🚗 Commute Alert: Heavy Congestion",
                "body": "I-95 North slow from Exit 22. Consider departing 10m earlier or booking PulseRide Premier.",
                "category": "traffic",
                "timestamp": now,
                "priority": "normal",
                "actions": ["Book PulseRide", "Orbit Maps"]
            }
        elif rule_id == "rule_meeting_prep":
            notification = {
                "id": f"notif_{int(now * 1000)}",
                "title": "📅 Meeting in 15m: John Vance Sync",
                "body": "Loaded recent notes and action items from OpenViking filesystem.",
                "category": "meeting",
                "timestamp": now,
                "priority": "high",
                "actions": ["Review Notes"]
            }
        else:
            notification = {
                "id": f"notif_{int(now * 1000)}",
                "title": "🧠 Personalization Flywheel Calibrated",
                "body": "Confidence scores updated for 4 active habits. All weights synchronized with ChromaDB.",
                "category": "flywheel",
                "timestamp": now,
                "priority": "low"
            }

        self.notification_queue.append(notification)
        return {
            "success": True,
            "rule_id": rule_id,
            "dispatched_notification": notification
        }

    def drain_notifications(self) -> List[Dict[str, Any]]:
        """Drains pending notifications queue for frontend delivery."""
        pending = list(self.notification_queue)
        self.notification_queue.clear()
        return pending

    def add_custom_rule(self, rule_id: str, title: str, schedule: str, description: str) -> Dict[str, Any]:
        rule = {
            "rule_id": rule_id,
            "title": title,
            "schedule": schedule,
            "description": description,
            "category": "custom",
            "enabled": True,
            "last_run": None
        }
        self.rules[rule_id] = rule
        return rule


# Global scheduler daemon singleton
scheduler_daemon = AutonomousSchedulerDaemon()
