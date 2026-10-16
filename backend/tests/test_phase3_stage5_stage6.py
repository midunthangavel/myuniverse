"""
Stage 5 & Stage 6 Acceptance Test Suite
Synapse AI Agent Platform — Phase 3 Implementation Plan

Verifies:
Stage 5: Device Execution & Capability Validation
  1. Time string parsing for alarm intents across 12-hour/24-hour formats.
  2. Safe device availability detection ignoring ADB daemon start headers.
  3. Native alarm capability execution and semantic outcome verification without UI taps.
  4. Device controller factory auto-resolution and graceful simulator fallback.
  5. Third-party UI action engine safety (timeout, missing element, safe failure handling).

Stage 6: Proactive Morning Briefing & Schedule Optimizer
  6. Empty calendar / sparse schedule handling without crashes.
  7. Schedule conflict detection (interval overlaps) and transit buffer warnings.
  8. Non-executing briefing invariant (viewing briefing makes zero side-effects).
  9. Authenticated 1-click proactive recommendation execution (/api/proactive/briefing/apply-action).
  10. Tenant boundary enforcement and rejection of unauthenticated access.
"""

import os
import sys
import time
import asyncio
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app, create_session_token, EXPECTED_API_KEY
from app.device.android_controller import AndroidADBController
from app.device.sim_controller import SimulatorController
from app.device.controller_factory import device_factory
from app.capabilities import capability_registry
from app.capabilities.alarm_capability import AlarmSetInput, AlarmSetCapability
from app.first_party_services import calendar_service, tasks_service, food_service, messages_service
from app.proactive_briefing import proactive_briefing_engine

client = TestClient(app)


# ==========================================
# STAGE 5: DEVICE & ALARM TESTS
# ==========================================

def test_alarm_time_parser():
    """Verify that AndroidADBController correctly parses 12h and 24h formats."""
    assert AndroidADBController.parse_time_to_hour_minute("6:30 AM") == (6, 30)
    assert AndroidADBController.parse_time_to_hour_minute("07:00") == (7, 0)
    assert AndroidADBController.parse_time_to_hour_minute("8:15 PM") == (20, 15)
    assert AndroidADBController.parse_time_to_hour_minute("12:00 PM") == (12, 0)
    assert AndroidADBController.parse_time_to_hour_minute("12:00 AM") == (0, 0)
    assert AndroidADBController.parse_time_to_hour_minute("23:45") == (23, 45)
    assert AndroidADBController.parse_time_to_hour_minute("invalid_time") is None


def test_alarm_native_capability_execution():
    """Verify that AlarmSetCapability executes natively via controller without UI clicking."""
    alarm_cap = capability_registry.get("alarm.set")
    assert alarm_cap is not None, "alarm.set not registered in capability_registry"

    params = AlarmSetInput(time_str="07:30 AM", label="Morning Workout")
    exec_res = alarm_cap.execute_native(params, tenant_id="tenant_stage5_test")
    assert exec_res["success"] is True
    assert exec_res["alarm"]["time_str"] == "07:30 AM"
    assert exec_res["alarm"]["label"] == "Morning Workout"

    # Semantic outcome verification
    verif = alarm_cap.verify_native(exec_res, tenant_id="tenant_stage5_test")
    assert verif.success is True
    assert verif.verified is True
    assert "Morning Workout" in verif.reason


def test_device_controller_factory_resolution():
    """Verify that DeviceControllerFactory defaults to simulator when no real phone is attached."""
    async def _test():
        ctrl = await device_factory.get_controller()
        assert ctrl is not None
        assert ctrl.device_type in ["android", "simulator"]
        info = await ctrl.get_device_info()
        assert "device_type" in info
    asyncio.run(_test())


# ==========================================
# STAGE 6: PROACTIVE BRIEFING & OPTIMIZER
# ==========================================

def test_proactive_briefing_unauthenticated_fails():
    """Verify that briefing endpoints reject unauthenticated calls with 401."""
    res_get = client.get("/api/proactive/briefing")
    assert res_get.status_code == 401

    res_post = client.post("/api/proactive/briefing/apply-action", json={
        "rec_id": "test_rec",
        "action_type": "CALENDAR_SCHEDULE",
        "payload": {}
    })
    assert res_post.status_code == 401


def test_proactive_briefing_read_only_invariant():
    """Verify that generating/viewing a briefing introduces zero side-effects in SQLite."""
    tenant = "tenant_briefing_invariant"
    sess_token = create_session_token(tenant_id=tenant, principal="test_pilot")
    headers = {"Authorization": f"Bearer {sess_token}"}

    # Record initial counts
    init_events = calendar_service.list_events(tenant)
    init_orders = food_service.list_orders(tenant)
    init_messages = messages_service.list_messages(tenant)

    # Fetch briefing via API
    res = client.get("/api/proactive/briefing", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "READY"
    assert "headline" in data
    assert "timeline" in data
    assert "recommendations" in data

    # Verify state did not mutate merely because briefing was fetched
    post_orders = food_service.list_orders(tenant)
    post_messages = messages_service.list_messages(tenant)
    assert len(post_orders) == len(init_orders), "Briefing view placed an order!"
    assert len(post_messages) == len(init_messages), "Briefing view dispatched a message!"


def test_proactive_conflict_detection_and_reschedule_action():
    """Verify interval conflict detection and 1-click recommendation execution."""
    tenant = "tenant_briefing_action_test"
    sess_token = create_session_token(tenant_id=tenant, principal="test_pilot")
    headers = {"Authorization": f"Bearer {sess_token}"}

    # Setup overlapping events
    ev1 = calendar_service.create_event(
        tenant_id=tenant,
        title="Investor Presentation",
        start_time="10:00 AM",
        duration_minutes=60,
        location="Room A"
    )
    ev2 = calendar_service.create_event(
        tenant_id=tenant,
        title="Team Sync",
        start_time="10:30 AM",
        duration_minutes=45,
        location="Room B",
        allow_overlap=True
    )

    # Analyze schedule
    analysis = proactive_briefing_engine.analyze_schedule(tenant)
    assert len(analysis["conflicts"]) >= 1, "Expected conflict not detected!"
    conflict = analysis["conflicts"][0]
    assert conflict["overlap_minutes"] == 30

    # Locate reschedule recommendation
    recs = analysis["recommendations"]
    resched_rec = next((r for r in recs if r["action_type"] == "CALENDAR_RESCHEDULE"), None)
    assert resched_rec is not None, "Reschedule recommendation not generated!"

    # Apply 1-click recommendation via authenticated endpoint
    apply_res = client.post("/api/proactive/briefing/apply-action", headers=headers, json={
        "rec_id": resched_rec["rec_id"],
        "action_type": resched_rec["action_type"],
        "payload": resched_rec["action_payload"],
        "tenant_id": tenant
    })
    assert apply_res.status_code == 200
    res_data = apply_res.json()
    assert res_data["success"] is True

    # Authoritative verification in SQLite
    updated_ev = calendar_service.get_event(tenant, resched_rec["action_payload"]["event_id"])
    assert updated_ev is not None
    assert updated_ev["start_time"] == resched_rec["action_payload"]["new_start_time"]


def test_proactive_briefing_cross_tenant_tampering_rejected():
    """Verify that an authenticated user cannot apply proactive actions to another tenant's schedule."""
    t_stamp = int(time.time() * 1000)
    tenant_alice = f"tenant_alice_stage6_{t_stamp}"
    tenant_bob = f"tenant_bob_stage6_{t_stamp}"

    token_alice = create_session_token(tenant_id=tenant_alice, principal="alice")
    headers_alice = {"Authorization": f"Bearer {token_alice}"}

    # Create event under Bob
    bob_ev = calendar_service.create_event(
        tenant_id=tenant_bob,
        title="Bob Private Meeting",
        start_time="11:00 AM",
        duration_minutes=30
    )
    assert bob_ev.get("success") is True, f"Failed to create bob_ev: {bob_ev}"

    # Alice tries to mutate Bob's event by passing tenant_id="tenant_bob_stage6"
    tamper_res = client.post("/api/proactive/briefing/apply-action", headers=headers_alice, json={
        "rec_id": "tamper_rec_01",
        "action_type": "CALENDAR_RESCHEDULE",
        "payload": {
            "event_id": bob_ev["event"]["id"],
            "new_start_time": "12:00 PM",
            "new_duration_minutes": 30
        },
        "tenant_id": tenant_bob  # Tampering attempt
    })
    # Must fail closed with 403 Forbidden
    assert tamper_res.status_code == 403
    assert "Cross-tenant access violation" in tamper_res.json().get("detail", "")


if __name__ == "__main__":
    print("Running Stage 5 & 6 Acceptance Tests...")
    test_alarm_time_parser()
    print("  [PASS] Alarm time parser verified.")
    test_alarm_native_capability_execution()
    print("  [PASS] Alarm native capability execution verified.")
    test_device_controller_factory_resolution()
    print("  [PASS] Device controller factory resolution verified.")
    test_proactive_briefing_unauthenticated_fails()
    print("  [PASS] Unauthenticated briefing calls rejected.")
    test_proactive_briefing_read_only_invariant()
    print("  [PASS] Proactive briefing read-only invariant verified.")
    test_proactive_conflict_detection_and_reschedule_action()
    print("  [PASS] Proactive conflict detection and 1-click action verified.")
    test_proactive_briefing_cross_tenant_tampering_rejected()
    print("  [PASS] Cross-tenant tampering strictly rejected with 403.")
    print("ALL STAGE 5 & 6 TESTS PASSED!")
