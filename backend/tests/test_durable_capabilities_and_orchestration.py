"""
Comprehensive Verification Suite: Native Capabilities, Durable Persistence & Multi-Tool Agent Execution
Covers:
1. Durability & Persistence across SQLite connection resets
2. Multi-Tenant Isolation & Zero Cross-Tenant Leakage
3. Idempotency Keys & Duplicate Action Prevention
4. Closed-Loop Truthful SQLite State Verification
5. Multi-Capability Compound Orchestrator (Decomposition, Financial Gate, Authorization)
6. REST API Security (Fail-Closed Auth & Scoped Tenants)
"""

import os
import sys
import time
import asyncio
import sqlite3
import json
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.first_party_services import (
    food_service,
    messages_service,
    calendar_service,
    tasks_service,
    get_db_connection,
    DB_PATH
)
from app.capabilities import capability_registry
from app.capabilities.calendar_capability import CalendarCreateInput
from app.capabilities.task_capability import TaskCreateInput
from app.capabilities.message_capability import MessageSendInput
from app.capabilities.food_capability import FoodOrderInput
from app.financial_gate import financial_gate
from app.multi_capability_orchestrator import multi_capability_orchestrator

API_KEY = "synapse_api_sec_prod_9a2b8c4d1e7f0_2026"
AUTH_HEADERS = {"X-API-Key": API_KEY}


def test_1_durability_across_connection_resets():
    print("\n--> [Test 1] Testing Durability Across SQLite Connection Resets...")
    tenant = f"tenant_persist_{int(time.time()*1000)}"

    # 1. Insert via services
    ev = calendar_service.create_event(tenant, "Board Strategy Dinner", "2026-10-30T19:00:00", 90, "Zen Garden")
    assert ev["success"] is True
    ev_id = ev["event"]["id"]

    tsk = tasks_service.create_task(tenant, "Prepare Financial Deck", priority="HIGH")
    assert tsk["success"] is True
    tsk_id = tsk["task"]["id"]

    msg = messages_service.send_message(tenant, "Investor Group", "Q4 Strategy materials ready.")
    assert msg["success"] is True
    msg_id = msg["message"]["id"]

    food_service.add_to_cart(tenant, "sushi_omakase", quantity=2)
    ord_res = food_service.checkout(tenant, address="100 Silicon Way", restaurant_name="Sushi Zen")
    assert ord_res["success"] is True
    ord_id = ord_res["order"]["order_id"]

    # 2. Reopen raw connection directly from disk
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM first_party_calendar_events WHERE id = ?", (ev_id,))
    row_ev = cur.fetchone()
    assert row_ev is not None, "Calendar event lost on disk!"
    assert row_ev["title"] == "Board Strategy Dinner"

    cur.execute("SELECT * FROM first_party_tasks WHERE id = ?", (tsk_id,))
    row_tsk = cur.fetchone()
    assert row_tsk is not None, "Task lost on disk!"
    assert row_tsk["priority"] == "HIGH"

    cur.execute("SELECT * FROM first_party_messages WHERE id = ?", (msg_id,))
    row_msg = cur.fetchone()
    assert row_msg is not None, "Message lost on disk!"
    assert row_msg["recipient"] == "Investor Group"

    cur.execute("SELECT * FROM first_party_food_orders WHERE order_id = ?", (ord_id,))
    row_ord = cur.fetchone()
    assert row_ord is not None, "Food order lost on disk!"
    assert row_ord["total"] > 0

    conn.close()
    print("    [PASS] 100% of state survived connection reset and persists in synapse_memory.db.")


def test_2_multi_tenant_isolation():
    print("\n--> [Test 2] Testing Multi-Tenant Isolation & Zero Cross-Tenant Leakage...")
    tenant_a = f"tenant_alpha_{int(time.time()*1000)}"
    tenant_b = f"tenant_beta_{int(time.time()*1000)}"

    # Populate Tenant A
    calendar_service.create_event(tenant_a, "Alpha Secret Meeting", "2026-10-25T11:00:00")
    tasks_service.create_task(tenant_a, "Alpha Secret Task", priority="URGENT")
    messages_service.send_message(tenant_a, "Confidential Contact", "Classified message")
    food_service.add_to_cart(tenant_a, "sushi_spicy_tuna", 1)
    food_service.checkout(tenant_a)

    # Query Tenant B -> Must return ZERO of Tenant A's data
    events_b = calendar_service.list_events(tenant_b)
    assert len(events_b) == 0, f"Tenant B leaked Tenant A events: {events_b}"

    tasks_b = tasks_service.list_tasks(tenant_b)
    assert len(tasks_b) == 0, f"Tenant B leaked Tenant A tasks: {tasks_b}"

    threads_b = messages_service.get_threads(tenant_b)
    assert len(threads_b) == 0, f"Tenant B leaked Tenant A messages: {threads_b}"

    orders_b = food_service.list_orders(tenant_b)
    assert len(orders_b) == 0, f"Tenant B leaked Tenant A orders: {orders_b}"

    cart_b = food_service.get_cart(tenant_b)
    assert len(cart_b["items"]) == 0, f"Tenant B leaked Tenant A cart: {cart_b}"

    print("    [PASS] Strict multi-tenant isolation verified with zero cross-tenant crosstalk.")


def test_3_idempotency_protection():
    print("\n--> [Test 3] Testing Idempotency Keys & Duplicate Action Prevention...")
    tenant = f"tenant_idemp_{int(time.time()*1000)}"
    idemp_key = f"idemp_{uuid.uuid4().hex[:12]}"

    # Submit first request
    res1 = calendar_service.create_event(tenant, "Standup", "2026-10-22T09:00:00", idempotency_key=idemp_key)
    assert res1["success"] is True

    # Re-submit duplicate request with identical idempotency key
    res2 = calendar_service.create_event(tenant, "Standup", "2026-10-22T09:00:00", idempotency_key=idemp_key)
    assert res2["success"] is True
    assert res2.get("cached") is True
    assert res2["event"]["id"] == res1["event"]["id"], "Idempotency returned duplicate ID!"

    # Verify database has exactly 1 record
    all_events = calendar_service.list_events(tenant)
    assert len(all_events) == 1, f"Expected 1 record in SQLite, found {len(all_events)}"

    print("    [PASS] Idempotent repeat requests intercepted with cached result and 0 duplicate rows.")


def test_4_closed_loop_db_verification():
    print("\n--> [Test 4] Testing Closed-Loop Truthful SQLite State Verification...")
    tenant = f"tenant_verif_{int(time.time()*1000)}"

    cap_cal = capability_registry.get("calendar.create")
    res_cal = cap_cal.execute_native(CalendarCreateInput(title="Sprint Demo", start_time="2026-10-24T16:00:00"), tenant_id=tenant)
    verif = cap_cal.verify_native(res_cal, tenant_id=tenant)
    assert verif.verified is True
    assert "Sprint Demo" in verif.reason

    # Fake outcome check: verifier MUST reject nonexistent entities
    fake_res = {"success": True, "event": {"id": "cal_nonexistent_fake", "title": "Ghost Event"}}
    verif_fake = cap_cal.verify_native(fake_res, tenant_id=tenant)
    assert verif_fake.verified is False
    assert "not found" in verif_fake.reason.lower()

    print("    [PASS] Closed-loop DB verifier confirmed genuine rows and rejected synthetic/fake state.")


def test_5_multi_capability_orchestrator():
    print("\n--> [Test 5] Testing Multi-Capability Compound Intent Orchestrator...")
    prompt = "Schedule lunch for Friday, order sushi for two people, notify my team, and add a follow-up task"
    tenant = f"tenant_orch_{int(time.time()*1000)}"

    # 1. Decomposition
    plan = multi_capability_orchestrator.decompose_prompt(prompt, tenant_id=tenant)
    assert len(plan.steps) == 4
    assert [s.capability_name for s in plan.steps] == ["calendar.create", "food.order", "message.send", "task.create"]
    assert plan.requires_approval is True
    assert plan.total_cost > 0

    # 2. Unapproved Execution (must halt at food.order with APPROVAL_REQUIRED)
    res_unapproved = asyncio.run(multi_capability_orchestrator.execute_orchestration(prompt, tenant_id=tenant))
    appr_events = [e for e in res_unapproved["all_events"] if e.get("type") == "APPROVAL_REQUIRED"]
    assert len(appr_events) == 1, "Expected APPROVAL_REQUIRED event for food order"
    appr = appr_events[0]
    assert appr["action"] == "food.order"
    assert appr["restaurant"] == "Sushi Zen"
    assert "financial_token" in appr

    # 3. Approved Execution with HMAC Token
    tenant_appr = f"tenant_orch_appr_{int(time.time()*1000)}"
    gate_eval = financial_gate.evaluate_transaction("gate_orch_test", "Order 2x Sushi", f"${plan.total_cost:.2f}", user_id=tenant_appr)
    token = gate_eval["token"]

    res_approved = asyncio.run(multi_capability_orchestrator.execute_orchestration(
        prompt=prompt,
        tenant_id=tenant_appr,
        authorization_token=token
    ))
    assert res_approved["success"] is True
    final_evt = res_approved["final_event"]
    assert final_evt["status"] == "ALL_VERIFIED"
    assert "calendar_event" in final_evt["created_resources"]
    assert "food_order" in final_evt["created_resources"]
    assert "message" in final_evt["created_resources"]
    assert "task" in final_evt["created_resources"]

    print("    [PASS] Multi-capability orchestrator decomposed, gated, and executed all 4 tools cleanly.")


def test_6_rest_api_security_and_orchestrate_endpoint():
    print("\n--> [Test 6] Testing Fail-Closed REST API Security & /api/agent/orchestrate...")
    client = TestClient(app)

    # 1. Unauthenticated request must be rejected (Fail-Closed)
    bad_res = client.get("/api/services/calendar/events")
    assert bad_res.status_code in [401, 403], f"Expected 401/403, got {bad_res.status_code}"

    # 2. Authenticated request succeeds
    good_res = client.get("/api/services/calendar/events", headers=AUTH_HEADERS)
    assert good_res.status_code == 200

    # 3. Test /api/agent/orchestrate
    tenant = f"tenant_rest_orch_{int(time.time()*1000)}"
    orch_res = client.post(
        "/api/agent/orchestrate",
        headers={**AUTH_HEADERS, "X-Tenant-Id": tenant},
        json={"prompt": "Schedule meeting with John Vance tomorrow at 3 PM and add follow-up task"}
    )
    assert orch_res.status_code == 200
    data = orch_res.json()
    assert data["success"] is True
    assert "calendar_event" in data["final_event"]["created_resources"]
    assert "task" in data["final_event"]["created_resources"]

    print("    [PASS] Fail-closed authentication enforced and /api/agent/orchestrate endpoint operational.")


def run_all_tests():
    print("=" * 70)
    print("  SYNAPSE AI: CAPABILITY & DURABLE STORAGE VERIFICATION SUITE")
    print("=" * 70)
    t0 = time.time()

    test_1_durability_across_connection_resets()
    test_2_multi_tenant_isolation()
    test_3_idempotency_protection()
    test_4_closed_loop_db_verification()
    test_5_multi_capability_orchestrator()
    test_6_rest_api_security_and_orchestrate_endpoint()

    dur = round(time.time() - t0, 2)
    print("\n" + "=" * 70)
    print(f"  ALL 6 VERIFICATION SUITES PASSED 100% IN {dur}s!")
    print("=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    import uuid
    sys.exit(run_all_tests())
