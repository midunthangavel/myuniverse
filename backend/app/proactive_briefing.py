"""
Proactive Morning Briefing & Schedule Optimizer Engine for Synapse AI.
Provides ambient, autonomous intelligence over first-party SQLite state:
1. Dynamic Agenda & Timeline Synthesis from first_party_calendar_events.
2. Conflict & Buffer Detection (overlapping meetings, tight travel gaps).
3. Nutrition & Lunch Window Optimization (identifies free slots, suggests meal orders).
4. Task Triage & Focus Time Blocking (correlates pending tasks with schedule).
5. 1-Click Proactive Action Execution (native capability resolution without UI clicks).
6. Neural Voice Audio Synthesis (Edge-TTS conversational briefing).
"""

import time
import uuid
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .first_party_services import (
    calendar_service,
    tasks_service,
    food_service,
    messages_service,
    get_db_connection
)
from .tts import NeuralTTS


def _parse_time_minutes(time_str: str) -> Optional[int]:
    """Parses time strings like '14:00', '2:30 PM', '10:00 AM' into minutes since midnight."""
    clean = time_str.strip().upper()
    
    # Try 24-hour format HH:MM
    m24 = re.search(r"(\d{1,2}):(\d{2})", clean)
    if not m24:
        return None
        
    hours = int(m24.group(1))
    minutes = int(m24.group(2))
    
    if "PM" in clean and hours < 12:
        hours += 12
    elif "AM" in clean and hours == 12:
        hours = 0
        
    return hours * 60 + minutes


def _format_minutes_time(total_minutes: int) -> str:
    """Formats minutes since midnight into '1:30 PM' string."""
    hours = (total_minutes // 60) % 24
    minutes = total_minutes % 60
    period = "AM" if hours < 12 else "PM"
    display_hour = hours if 1 <= hours <= 12 else (12 if hours == 0 else hours - 12)
    return f"{display_hour}:{minutes:02d} {period}"


class ProactiveBriefingEngine:
    def __init__(self):
        self.tts = NeuralTTS()

    def seed_demo_schedule_if_empty(self, tenant_id: str):
        """Ensures the demo environment has an illustrative schedule to analyze."""
        events = calendar_service.list_events(tenant_id)
        if not events:
            # Seed 3 realistic events with an intentional overlap conflict and tight buffer
            calendar_service.create_event(
                tenant_id=tenant_id,
                title="Q4 Product Strategy Review",
                start_time="10:00 AM",
                duration_minutes=60,
                location="Main Boardroom",
                attendees=["sarah@company.com", "david@company.com"]
            )
            calendar_service.create_event(
                tenant_id=tenant_id,
                title="Executive Sync & Budget Approval",
                start_time="01:30 PM",
                duration_minutes=60,
                location="Downtown HQ",
                attendees=["vp_finance@company.com"]
            )
            # Intentional overlap conflict
            calendar_service.create_event(
                tenant_id=tenant_id,
                title="Engineering Architecture Retro",
                start_time="02:00 PM",
                duration_minutes=60,
                location="Online (Google Meet)",
                attendees=["lead_dev@company.com", "alex@company.com"],
                allow_overlap=True
            )

        tasks = tasks_service.list_tasks(tenant_id, completed=False)
        if not tasks:
            tasks_service.create_task(
                tenant_id=tenant_id,
                title="Finalize Q4 Investor Slide Deck",
                due_date="Today 5:00 PM",
                priority="HIGH"
            )
            tasks_service.create_task(
                tenant_id=tenant_id,
                title="Review API Security Audit Findings",
                due_date="Tomorrow",
                priority="NORMAL"
            )

    def seed_demo_data(self, tenant_id: str):
        """Explicitly seeds demo data. Call from /api/demo/seed, NEVER from read paths."""
        self.seed_demo_schedule_if_empty(tenant_id)

    def analyze_schedule(self, tenant_id: str, target_date: Optional[str] = None) -> Dict[str, Any]:
        """Performs deep schedule, conflict, nutrition, and task analysis.
        Pure read-only — never mutates state. Filters events to target_date (defaults to today)."""
        events = calendar_service.list_events(tenant_id)
        tasks = tasks_service.list_tasks(tenant_id, completed=False)
        recent_orders = food_service.list_orders(tenant_id)

        # Filter events to the target date (defaults to today)
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")

        filtered_events = []
        for ev in events:
            ev_date = ev.get("date", "")
            # Include events that match today, have no date (legacy), or are explicitly today
            if not ev_date or ev_date == target_date:
                filtered_events.append(ev)

        # 1. Parse and sort events chronologically — skip unparseable times with warning
        timeline = []
        for ev in filtered_events:
            mins = _parse_time_minutes(ev["start_time"])
            if mins is None:
                logging.warning(f"[ProactiveBriefing] Skipping event '{ev.get('title', 'unknown')}' — unparseable start_time: '{ev['start_time']}'")
                continue
            duration = ev.get("duration_minutes", 60)
            timeline.append({
                **ev,
                "start_minutes": mins,
                "end_minutes": mins + duration,
                "end_time_str": _format_minutes_time(mins + duration),
                "has_conflict": False,
                "conflict_details": None,
                "tight_buffer": False
            })

        timeline.sort(key=lambda x: x["start_minutes"])

        # 2. Conflict & Travel Buffer Detection
        conflicts = []
        recommendations = []

        for i in range(len(timeline)):
            for j in range(i + 1, len(timeline)):
                ev1 = timeline[i]
                ev2 = timeline[j]

                # Check overlap: start2 < end1
                if ev2["start_minutes"] < ev1["end_minutes"]:
                    overlap_mins = ev1["end_minutes"] - ev2["start_minutes"]
                    ev1["has_conflict"] = True
                    ev2["has_conflict"] = True
                    ev1["conflict_details"] = f"Collides with '{ev2['title']}' by {overlap_mins}m"
                    ev2["conflict_details"] = f"Collides with '{ev1['title']}' by {overlap_mins}m"

                    conf_desc = (
                        f"Overlap detected: '{ev1['title']}' ({ev1['start_time']} - {ev1['end_time_str']}) "
                        f"collides with '{ev2['title']}' ({ev2['start_time']} - {ev2['end_time_str']}) by {overlap_mins} minutes."
                    )
                    conflicts.append({
                        "event_1": ev1["title"],
                        "event_2": ev2["title"],
                        "overlap_minutes": overlap_mins,
                        "description": conf_desc
                    })

                    # Suggest moving ev2 to after ev1
                    suggested_start_mins = ev1["end_minutes"] + 15
                    suggested_start_str = _format_minutes_time(suggested_start_mins)
                    recommendations.append({
                        "rec_id": f"rec_shift_{ev2['id']}",
                        "title": f"Shift '{ev2['title']}' to {suggested_start_str}",
                        "category": "CONFLICT_RESOLUTION",
                        "impact": f"Eliminates {overlap_mins}-minute collision with '{ev1['title']}' and adds a 15m buffer.",
                        "action_type": "CALENDAR_RESCHEDULE",
                        "risk_tier": "LOW",
                        "action_payload": {
                            "event_id": ev2["id"],
                            "new_start_time": suggested_start_str,
                            "new_duration_minutes": ev2["duration_minutes"]
                        }
                    })

                # Check tight travel buffer if different physical locations
                elif (
                    ev2["start_minutes"] - ev1["end_minutes"] < 15
                    and ev1.get("location")
                    and ev2.get("location")
                    and ev1["location"] != ev2["location"]
                    and "Online" not in ev1["location"]
                    and "Online" not in ev2["location"]
                ):
                    gap = ev2["start_minutes"] - ev1["end_minutes"]
                    ev1["tight_buffer"] = True
                    ev2["tight_buffer"] = True
                    recommendations.append({
                        "rec_id": f"rec_buffer_{ev2['id']}",
                        "title": f"Add 20m Transit Buffer between '{ev1['title']}' and '{ev2['title']}'",
                        "category": "BUFFER_OPTIMIZATION",
                        "impact": f"Allows transit from {ev1['location']} to {ev2['location']} without arriving late.",
                        "action_type": "CALENDAR_RESCHEDULE",
                        "risk_tier": "LOW",
                        "action_payload": {
                            "event_id": ev2["id"],
                            "new_start_time": _format_minutes_time(ev1["end_minutes"] + 20),
                            "new_duration_minutes": ev2["duration_minutes"]
                        }
                    })

        # 3. Lunch & Nutrition Optimization Window
        # Scan midday period: 11:30 AM (690m) to 2:00 PM (840m)
        lunch_window_start = 690
        lunch_window_end = 840
        has_lunch_break = True
        available_lunch_slot = None

        # Check if any event covers the entire lunch window
        busy_spans = []
        for ev in timeline:
            if ev["end_minutes"] > lunch_window_start and ev["start_minutes"] < lunch_window_end:
                busy_spans.append((max(lunch_window_start, ev["start_minutes"]), min(lunch_window_end, ev["end_minutes"])))

        busy_spans.sort()
        curr = lunch_window_start
        for b_start, b_end in busy_spans:
            if b_start - curr >= 45:
                available_lunch_slot = (curr, b_start)
                break
            curr = max(curr, b_end)

        if not available_lunch_slot and (lunch_window_end - curr >= 45):
            available_lunch_slot = (curr, lunch_window_end)

        if available_lunch_slot:
            slot_start_str = _format_minutes_time(available_lunch_slot[0])
            slot_end_str = _format_minutes_time(available_lunch_slot[1])
            duration = available_lunch_slot[1] - available_lunch_slot[0]

            recommendations.append({
                "rec_id": "rec_lunch_preorder",
                "title": f"Pre-order Lunch for {slot_start_str} Window",
                "category": "LUNCH_OPTIMIZATION",
                "impact": f"You have a {duration}-minute opening ({slot_start_str} - {slot_end_str}). Pre-orders avoid delivery rush.",
                "action_type": "FOOD_ORDER",
                "risk_tier": "MEDIUM",
                "action_payload": {
                    "restaurant_name": "Sushi Zen",
                    "items": [
                        {"item_id": "sushi_omakase", "name": "Omakase Platter", "price": 45.0, "quantity": 1}
                    ],
                    "target_time": slot_start_str
                }
            })
        elif not busy_spans:
            recommendations.append({
                "rec_id": "rec_lunch_default",
                "title": "Schedule Lunch Break at 12:30 PM",
                "category": "LUNCH_OPTIMIZATION",
                "impact": "Midday is completely open. Block 45 minutes for lunch and focus.",
                "action_type": "CALENDAR_SCHEDULE",
                "risk_tier": "LOW",
                "action_payload": {
                    "title": "Lunch Break & Recharge",
                    "start_time": "12:30 PM",
                    "duration_minutes": 45,
                    "location": "Local"
                }
            })

        # 4. Task Triage & Focus Time Blocks
        high_priority_tasks = [t for t in tasks if t.get("priority") in ("HIGH", "URGENT")]
        if high_priority_tasks:
            top_task = high_priority_tasks[0]
            recommendations.append({
                "rec_id": f"rec_focus_{top_task['id']}",
                "title": f"Block 45m Focus Time: '{top_task['title']}'",
                "category": "FOCUS_BLOCK",
                "impact": f"Guarantees dedicated execution window before the deadline ({top_task.get('due_date', 'today')}).",
                "action_type": "CALENDAR_SCHEDULE",
                "risk_tier": "LOW",
                "action_payload": {
                    "title": f"Focus Time: {top_task['title']}",
                    "start_time": "04:00 PM",
                    "duration_minutes": 45,
                    "location": "Quiet Workspace"
                }
            })

        return {
            "timeline": timeline,
            "conflicts": conflicts,
            "recommendations": recommendations,
            "total_events": len(timeline),
            "total_tasks": len(tasks),
            "high_priority_tasks": high_priority_tasks
        }

    async def generate_briefing(self, tenant_id: str, include_audio: bool = False) -> Dict[str, Any]:
        """Generates a complete synthesized Morning Briefing with conversational speech text and optional audio."""
        analysis = self.analyze_schedule(tenant_id)

        ev_count = analysis["total_events"]
        conf_count = len(analysis["conflicts"])
        task_count = analysis["total_tasks"]
        recs = analysis["recommendations"]

        speech_parts = [
            f"Good morning! Here is your Synapse briefing.",
            f"You have {ev_count} event{'s' if ev_count != 1 else ''} scheduled today and {task_count} pending task{'s' if task_count != 1 else ''}."
        ]

        if conf_count > 0:
            speech_parts.append(f"Attention: I detected {conf_count} scheduling conflict that needs resolution.")
        else:
            speech_parts.append("Your schedule is in great shape with clear transition buffers.")

        if recs:
            top_rec = recs[0]
            speech_parts.append(f"My top recommendation: {top_rec['title']}. Would you like me to apply it?")

        speech_text = " ".join(speech_parts)

        audio_data_uri = None
        if include_audio:
            try:
                audio_data_uri = await self.tts.generate_audio_base64(speech_text)
            except Exception as e:
                print(f"[ProactiveBriefing Warning] TTS synthesis failed: {e}")

        headline = f"☀️ Good Morning! {ev_count} Events • {conf_count} Conflict{'s' if conf_count != 1 else ''} • {task_count} Tasks"

        return {
            "status": "READY",
            "timestamp": time.time(),
            "headline": headline,
            "speech_text": speech_text,
            "audio_data_uri": audio_data_uri,
            "timeline": analysis["timeline"],
            "conflicts": analysis["conflicts"],
            "recommendations": recs,
            "summary_stats": {
                "events_count": ev_count,
                "conflicts_count": conf_count,
                "pending_tasks_count": task_count,
                "recommendations_count": len(recs)
            }
        }

    def apply_recommendation(
        self,
        tenant_id: str,
        rec_id: str,
        action_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Applies a proactive recommendation natively via SQLite backend capabilities."""
        now = time.time()
        
        if action_type == "CALENDAR_RESCHEDULE":
            event_id = payload.get("event_id")
            new_time = payload.get("new_start_time")
            new_dur = payload.get("new_duration_minutes")
            res = calendar_service.reschedule_event(
                tenant_id=tenant_id,
                event_id=event_id,
                new_start_time=new_time,
                new_duration_minutes=new_dur
            )
            return {
                "success": res.get("success", False),
                "action": "CALENDAR_RESCHEDULE",
                "message": f"Successfully rescheduled event to {new_time}.",
                "details": res
            }

        elif action_type == "CALENDAR_SCHEDULE":
            res = calendar_service.create_event(
                tenant_id=tenant_id,
                title=payload.get("title", "Focus Session"),
                start_time=payload.get("start_time", "03:30 PM"),
                duration_minutes=payload.get("duration_minutes", 45),
                location=payload.get("location", ""),
                idempotency_key=f"proactive_cal_{rec_id}_{int(now)}"
            )
            return {
                "success": res.get("success", False),
                "action": "CALENDAR_SCHEDULE",
                "message": f"Added '{payload.get('title')}' at {payload.get('start_time')}.",
                "details": res
            }

        elif action_type == "FOOD_ORDER":
            rest = payload.get("restaurant_name", "Sushi Zen")
            items = payload.get("items", [{"item_id": "sushi_omakase", "quantity": 1}])
            for it in items:
                item_id = it.get("item_id") or "sushi_omakase"
                qty = it.get("quantity", 1)
                food_service.add_to_cart(tenant_id, item_id, qty)

            order_res = food_service.checkout(
                tenant_id=tenant_id,
                address="Office Suite 400",
                restaurant_name=rest,
                idempotency_key=f"proactive_order_{rec_id}_{int(now)}"
            )
            return {
                "success": order_res.get("success", False),
                "action": "FOOD_ORDER",
                "message": f"Successfully scheduled food order from {rest}.",
                "details": order_res
            }

        elif action_type == "MESSAGE_NOTIFY":
            res = messages_service.send_message(
                tenant_id=tenant_id,
                recipient=payload.get("recipient", "Team Channel"),
                body=payload.get("body", "Schedule update"),
                idempotency_key=f"proactive_msg_{rec_id}_{int(now)}"
            )
            return {
                "success": res.get("success", False),
                "action": "MESSAGE_NOTIFY",
                "message": f"Sent update to {payload.get('recipient')}.",
                "details": res
            }

        return {"success": False, "error": f"Unsupported proactive action_type '{action_type}'"}


# Global Proactive Briefing Engine Singleton
proactive_briefing_engine = ProactiveBriefingEngine()
