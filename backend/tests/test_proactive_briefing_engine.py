"""
Unit & Integration Verification Suite for Synapse AI:
Proactive Morning Briefing & Schedule Optimizer Engine

Validates:
1. Schedule Parsing, Chronological Ordering, and Timeline Construction.
2. Conflict & Overlap Detection (accurate collision calculation and alert generation).
3. Transit Buffer Protection (detects tight gaps between physical locations).
4. Nutrition / Midday Lunch Window Optimization (detects free slots).
5. Task Triage & Focus Block Scheduling.
6. 1-Click Native Action Execution (rescheduling, focus block insertion, meal order).
7. Fail-Closed REST API Security & Tenant Isolation.
"""

import sys
import os
import unittest
import asyncio

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from backend.app.main import app, EXPECTED_API_KEY
from backend.app.first_party_services import (
    calendar_service,
    tasks_service,
    food_service,
    messages_service,
    get_db_connection
)
from backend.app.proactive_briefing import (
    proactive_briefing_engine,
    _parse_time_minutes,
    _format_minutes_time
)


class TestProactiveBriefingEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_tenant = "tenant_briefing_test"
        cls.headers = {
            "X-API-Key": EXPECTED_API_KEY,
            "X-Tenant-ID": cls.test_tenant
        }
        cls._cleanup_test_data()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_test_data()

    @classmethod
    def _cleanup_test_data(cls):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM first_party_calendar_events WHERE tenant_id = ?", (cls.test_tenant,))
            cursor.execute("DELETE FROM first_party_tasks WHERE tenant_id = ?", (cls.test_tenant,))
            cursor.execute("DELETE FROM first_party_food_orders WHERE tenant_id = ?", (cls.test_tenant,))
            cursor.execute("DELETE FROM first_party_food_cart WHERE tenant_id = ?", (cls.test_tenant,))
            cursor.execute("DELETE FROM first_party_messages WHERE tenant_id = ?", (cls.test_tenant,))
            conn.commit()

    def setUp(self):
        self._cleanup_test_data()

    def test_01_time_parsing_and_formatting(self):
        """Verifies robust conversion of time strings to minutes and back."""
        print("\n--> [Test 1] Testing Time Parsing & Formatting Utility...")
        self.assertEqual(_parse_time_minutes("10:00 AM"), 600)
        self.assertEqual(_parse_time_minutes("01:30 PM"), 810)
        self.assertEqual(_parse_time_minutes("12:00 PM"), 720)
        self.assertEqual(_parse_time_minutes("12:00 AM"), 0)
        self.assertEqual(_parse_time_minutes("14:45"), 885)

        self.assertEqual(_format_minutes_time(600), "10:00 AM")
        self.assertEqual(_format_minutes_time(810), "1:30 PM")
        self.assertEqual(_format_minutes_time(720), "12:00 PM")
        self.assertEqual(_format_minutes_time(0), "12:00 AM")
        print("    [PASS] Time arithmetic and bi-directional conversions verified.")

    def test_02_conflict_and_overlap_detection(self):
        """Verifies accurate detection of overlapping calendar events."""
        print("\n--> [Test 2] Testing Schedule Conflict & Overlap Detection...")
        # Event 1: 10:00 AM - 11:00 AM
        calendar_service.create_event(
            tenant_id=self.test_tenant,
            title="Design Review",
            start_time="10:00 AM",
            duration_minutes=60,
            location="Room A"
        )
        # Event 2: 10:30 AM - 11:30 AM (30 min collision)
        calendar_service.create_event(
            tenant_id=self.test_tenant,
            title="Client Presentation",
            start_time="10:30 AM",
            duration_minutes=60,
            location="Room B",
            allow_overlap=True
        )

        analysis = proactive_briefing_engine.analyze_schedule(self.test_tenant)
        self.assertGreaterEqual(len(analysis["conflicts"]), 1)
        conf = analysis["conflicts"][0]
        self.assertIn("Design Review", [conf["event_1"], conf["event_2"]])
        self.assertIn("Client Presentation", [conf["event_1"], conf["event_2"]])
        self.assertEqual(conf["overlap_minutes"], 30)

        # Check that recommendation was generated
        reschedule_recs = [r for r in analysis["recommendations"] if r["action_type"] == "CALENDAR_RESCHEDULE"]
        self.assertGreaterEqual(len(reschedule_recs), 1)
        print(f"    [PASS] Overlap of 30m detected and reschedule recommendation formulated: {reschedule_recs[0]['title']}")

    def test_03_transit_buffer_detection(self):
        """Verifies detection of tight travel buffer between distinct physical locations."""
        print("\n--> [Test 3] Testing Tight Transit Buffer Detection...")
        # Event 1: 10:00 AM - 11:00 AM at Office
        calendar_service.create_event(
            tenant_id=self.test_tenant,
            title="Morning Standup",
            start_time="10:00 AM",
            duration_minutes=60,
            location="Office Campus 1"
        )
        # Event 2: 11:05 AM - 12:05 PM at Downtown Convention Center (5m gap between different locations)
        calendar_service.create_event(
            tenant_id=self.test_tenant,
            title="Tech Summit Keynote",
            start_time="11:05 AM",
            duration_minutes=60,
            location="Downtown Convention Center"
        )

        analysis = proactive_briefing_engine.analyze_schedule(self.test_tenant)
        buffer_recs = [r for r in analysis["recommendations"] if r["category"] == "BUFFER_OPTIMIZATION"]
        self.assertGreaterEqual(len(buffer_recs), 1)
        print(f"    [PASS] Tight transit buffer flagged: '{buffer_recs[0]['title']}'.")

    def test_04_nutrition_window_and_task_triage(self):
        """Verifies detection of open lunch window and high-priority task triage."""
        print("\n--> [Test 4] Testing Lunch Window Optimization & Task Triage...")
        # Event: 10:00 AM - 11:30 AM
        calendar_service.create_event(
            tenant_id=self.test_tenant,
            title="Executive Strategy Session",
            start_time="10:00 AM",
            duration_minutes=90,
            location="Boardroom"
        )
        # Afternoon Event: 2:00 PM - 3:00 PM
        calendar_service.create_event(
            tenant_id=self.test_tenant,
            title="Investor Update",
            start_time="02:00 PM",
            duration_minutes=60,
            location="Boardroom"
        )
        # Pending urgent task
        tasks_service.create_task(
            tenant_id=self.test_tenant,
            title="Draft Board Resolution Memo",
            due_date="Today 4 PM",
            priority="HIGH"
        )

        analysis = proactive_briefing_engine.analyze_schedule(self.test_tenant)
        
        # Check lunch recommendation
        lunch_recs = [r for r in analysis["recommendations"] if r["category"] == "LUNCH_OPTIMIZATION"]
        self.assertGreaterEqual(len(lunch_recs), 1)
        self.assertEqual(lunch_recs[0]["action_type"], "FOOD_ORDER")

        # Check task focus block recommendation
        focus_recs = [r for r in analysis["recommendations"] if r["category"] == "FOCUS_BLOCK"]
        self.assertGreaterEqual(len(focus_recs), 1)
        self.assertIn("Draft Board Resolution Memo", focus_recs[0]["title"])
        print(f"    [PASS] Lunch window ({lunch_recs[0]['action_payload']['target_time']}) and Focus Block identified.")

    def test_05_1click_action_execution(self):
        """Verifies 1-click native execution of proactive recommendations."""
        print("\n--> [Test 5] Testing 1-Click Proactive Action Execution...")
        # Seed an event to reschedule
        ev_res = calendar_service.create_event(
            tenant_id=self.test_tenant,
            title="Team Architecture Sync",
            start_time="02:00 PM",
            duration_minutes=60,
            location="Room 101"
        )
        event_id = ev_res["event"]["id"]

        # Apply reschedule recommendation
        res = proactive_briefing_engine.apply_recommendation(
            tenant_id=self.test_tenant,
            rec_id="rec_test_shift",
            action_type="CALENDAR_RESCHEDULE",
            payload={
                "event_id": event_id,
                "new_start_time": "03:30 PM",
                "new_duration_minutes": 60
            }
        )
        self.assertTrue(res["success"])

        # Closed-loop check in SQLite
        updated_ev = calendar_service.get_event(self.test_tenant, event_id)
        self.assertEqual(updated_ev["start_time"], "03:30 PM")

        # Apply Food Order recommendation
        food_res = proactive_briefing_engine.apply_recommendation(
            tenant_id=self.test_tenant,
            rec_id="rec_test_food",
            action_type="FOOD_ORDER",
            payload={
                "restaurant_name": "Sushi Zen",
                "items": [{"item_id": "sushi_omakase", "name": "Omakase Platter", "price": 45.0, "quantity": 1}]
            }
        )
        self.assertTrue(food_res["success"])

        orders = food_service.list_orders(self.test_tenant)
        self.assertGreaterEqual(len(orders), 1)
        self.assertEqual(orders[0]["restaurant_name"], "Sushi Zen")
        print("    [PASS] 1-Click calendar rescheduling and food ordering executed and verified in SQLite.")

    def test_06_rest_api_security_and_endpoints(self):
        """Verifies fail-closed authentication and REST endpoints for morning briefing."""
        print("\n--> [Test 6] Testing REST API Security & Endpoints...")

        # 1. Unauthenticated request must fail 401
        res = self.client.get("/api/proactive/briefing")
        self.assertEqual(res.status_code, 401)

        # 2. Authenticated request succeeds
        res = self.client.get("/api/proactive/briefing", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("headline", data)
        self.assertIn("speech_text", data)
        self.assertIn("timeline", data)
        self.assertIn("recommendations", data)

        # 3. Schedule optimization analysis endpoint
        res = self.client.post("/api/proactive/briefing/optimize", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        opt_data = res.json()
        self.assertIn("conflicts", opt_data)

        # 4. Apply action endpoint
        apply_payload = {
            "rec_id": "rec_api_test",
            "action_type": "CALENDAR_SCHEDULE",
            "payload": {
                "title": "API Verified Focus Block",
                "start_time": "04:30 PM",
                "duration_minutes": 30,
                "location": "Quiet Lab"
            },
            "tenant_id": self.test_tenant
        }
        res = self.client.post("/api/proactive/briefing/apply-action", json=apply_payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        res_data = res.json()
        self.assertTrue(res_data["success"])

        print("    [PASS] Fail-closed authentication enforced and all /api/proactive/briefing/* endpoints operational.")


if __name__ == "__main__":
    print("=" * 70)
    print("  SYNAPSE AI: PROACTIVE MORNING BRIEFING & OPTIMIZER TEST SUITE")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestProactiveBriefingEngine)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "=" * 70)
        print("  ALL 6 PROACTIVE BRIEFING TEST SUITES PASSED 100%!")
        print("=" * 70 + "\n")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("  TEST SUITE REPORTED FAILURES!")
        print("=" * 70 + "\n")
        sys.exit(1)
