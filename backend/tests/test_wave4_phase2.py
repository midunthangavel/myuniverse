"""
Wave 4 Test Suite (P10, P11, P12) for Synapse AI Agent Platform:
- P10: First-Party Native Services Engine (Food, Messages, Calendar, Tasks) & Native Capability Bindings
- P11: Vector Memory Tenant Namespacing & Cold-Start Isolation (Zero Cross-Tenant Leakage)
- P12: Investor Demo Showcase Runner (3-Act Streaming Demonstration)
"""

import os
import sys
import json
import time
import asyncio
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.first_party_services import food_service, messages_service, calendar_service, tasks_service
from app.capabilities import capability_registry
from app.capabilities.food_capability import FoodOrderInput
from app.capabilities.message_capability import MessageSendInput
from app.capabilities.calendar_capability import CalendarCreateInput
from app.capabilities.task_capability import TaskCreateInput
from app.vector_memory import vector_memory
from app.showcase import showcase_runner


def test_p10_first_party_services_and_native_capabilities():
    print("\n--> [P10] Testing First-Party Native Services Engine & Capability Bindings...")
    tenant = f"tenant_test_{int(time.time()*1000)}"
    
    # 1. Food Service & Native Capability
    rests = food_service.list_restaurants()
    assert len(rests) >= 3, "Expected at least 3 seeded restaurants"
    
    cap_food = capability_registry.get("food.order")
    order_params = FoodOrderInput(item="Omakase Platter", restaurant="Sushi Zen", quantity=2)
    native_food_res = cap_food.execute_native(order_params, tenant_id=tenant)
    assert native_food_res["success"] is True
    assert native_food_res["order"]["total"] > 0
    assert len(native_food_res["order"]["items"]) == 1
    
    # 2. Messages Service & Native Capability
    cap_msg = capability_registry.get("message.send")
    msg_params = MessageSendInput(recipient="charlie@synapse.ai", text="Sync at 4 PM?")
    native_msg_res = cap_msg.execute_native(msg_params, tenant_id=tenant)
    assert native_msg_res["success"] is True
    assert native_msg_res["message"]["status"] == "DELIVERED"
    threads = messages_service.get_threads(tenant)
    assert len(threads) == 1
    assert threads[0]["recipient"] == "charlie@synapse.ai"
    
    # 3. Calendar Service & Native Capability
    cap_cal = capability_registry.get("calendar.create")
    cal_params = CalendarCreateInput(title="Sprint Retro", start_time="2026-10-20T15:00:00", duration_min=45)
    native_cal_res = cap_cal.execute_native(cal_params, tenant_id=tenant)
    assert native_cal_res["success"] is True
    assert native_cal_res["event"]["title"] == "Sprint Retro"
    
    # Test Calendar conflict detection
    conflict_res = cap_cal.execute_native(cal_params, tenant_id=tenant)
    assert conflict_res["success"] is False
    assert conflict_res["conflict"] is True
    
    # 4. Tasks Service & Native Capability
    cap_task = capability_registry.get("task.create")
    task_params = TaskCreateInput(title="Deploy Phase 2 Containers", priority="HIGH")
    native_task_res = cap_task.execute_native(task_params, tenant_id=tenant)
    assert native_task_res["success"] is True
    task_id = native_task_res["task"]["id"]
    
    # Complete task
    complete_res = tasks_service.complete_task(tenant, task_id)
    assert complete_res["success"] is True
    assert complete_res["task"]["completed"] is True
    
    print("    [PASS] All 4 first-party services and native capability executions verified.")


def test_p10_rest_endpoints():
    print("--> [P10] Testing First-Party REST API Endpoints...")
    client = TestClient(app)
    headers = {"X-API-Key": "synapse_api_sec_prod_9a2b8c4d1e7f0_2026"}
    
    # Test food restaurants
    r = client.get("/api/services/food/restaurants", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) >= 3
    
    # Test calendar events
    r = client.get("/api/services/calendar/events?tenant_id=tenant_primary", headers=headers)
    assert r.status_code == 200
    
    # Test tasks endpoint
    r = client.get("/api/services/tasks?tenant_id=tenant_primary", headers=headers)
    assert r.status_code == 200
    
    print("    [PASS] REST endpoints for first-party services operational.")


def test_p11_vector_memory_tenant_isolation():
    print("\n--> [P11] Testing Vector Memory Tenant Isolation & Cold-Start...")
    tenant_a = f"tenant_alpha_{int(time.time()*1000)}"
    tenant_b = f"tenant_beta_{int(time.time()*1000)}"
    
    # Store secret in Tenant A
    vector_memory.add_memory(
        doc_id="sec_a",
        text="Tenant Alpha secret dietary restriction: Strict Vegan with Peanut Allergy",
        user_id=tenant_a,
        metadata={"category": "DIET"}
    )
    
    # Store preference in Tenant B
    vector_memory.add_memory(
        doc_id="pref_b",
        text="Tenant Beta preference: Carnivore diet with prime ribeye steak",
        user_id=tenant_b,
        metadata={"category": "DIET"}
    )
    
    # Query Tenant A: must NEVER see Tenant B's data
    results_a = vector_memory.semantic_search("diet preferences steak", user_id=tenant_a, n_results=5)
    for res in results_a:
        assert "Carnivore" not in res["text"], "CRITICAL LEAK: Tenant Alpha saw Tenant Beta's preferences!"
        assert "ribeye" not in res["text"]
    
    # Query Tenant B: must NEVER see Tenant A's data
    results_b = vector_memory.semantic_search("diet peanut allergy vegan", user_id=tenant_b, n_results=5)
    for res in results_b:
        assert "Vegan" not in res["text"], "CRITICAL LEAK: Tenant Beta saw Tenant Alpha's allergy!"
        
    # Cold-Start Bootstrap Test
    tenant_new = f"tenant_cold_{int(time.time()*1000)}"
    seeded_count = vector_memory.bootstrap_cold_start_profile(tenant_new)
    assert seeded_count > 0, "Expected non-zero bootstrap preferences"
    cold_results = vector_memory.semantic_search("notifications delivery", user_id=tenant_new, n_results=2)
    assert len(cold_results) > 0
    assert cold_results[0]["metadata"].get("category") == "COLD_START_BOOTSTRAP"
    
    print("    [PASS] Strict vector memory tenant namespacing and cold-start isolation verified.")


def test_p12_investor_showcase_runner():
    print("\n--> [P12] Testing Investor Showcase Runner (3-Act Live Orchestration)...")
    
    async def run_acts():
        events = []
        async for ev in showcase_runner.run_live_showcase("tenant_investor_demo"):
            events.append(ev)
            
        # Verify Act 1
        act1_complete = next((e for e in events if e.get("type") == "SHOWCASE_ACT_COMPLETE" and e.get("act") == 1), None)
        assert act1_complete is not None, "Act 1 completion event missing"
        assert act1_complete["status"] == "VERIFIED"
        assert act1_complete["budget_met"] is True
        assert act1_complete["duration_ms"] < 1500.0
        
        # Verify Act 2
        act2_complete = next((e for e in events if e.get("type") == "SHOWCASE_ACT_COMPLETE" and e.get("act") == 2), None)
        assert act2_complete is not None, "Act 2 completion event missing"
        assert act2_complete["status"] == "VERIFIED"
        assert len(act2_complete["chained_services"]) == 3
        
        # Verify Act 3
        act3_complete = next((e for e in events if e.get("type") == "SHOWCASE_ACT_COMPLETE" and e.get("act") == 3), None)
        assert act3_complete is not None, "Act 3 completion event missing"
        assert act3_complete["status"] == "AUTHORIZED"
        assert act3_complete["ledger_verified"] is True
        
        # Verify Overall Completion
        overall = next((e for e in events if e.get("type") == "SHOWCASE_COMPLETE"), None)
        assert overall is not None, "Showcase overall completion event missing"
        assert overall["status"] == "ALL_ACTS_VERIFIED"
        assert overall["acts_completed"] == [1, 2, 3]

    asyncio.run(run_acts())
    
    # Test REST API trigger
    client = TestClient(app)
    headers = {"X-API-Key": "synapse_api_sec_prod_9a2b8c4d1e7f0_2026"}
    res = client.post("/api/showcase/run", json={"tenant_id": "tenant_api_showcase"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert len(res.json()["events"]) >= 7
    
    print("    [PASS] 3-act investor showcase runner executed and verified end-to-end.")


if __name__ == "__main__":
    test_p10_first_party_services_and_native_capabilities()
    test_p10_rest_endpoints()
    test_p11_vector_memory_tenant_isolation()
    test_p12_investor_showcase_runner()
    print("\n==================================================")
    print("ALL WAVE 4 (P10, P11, P12) TESTS PASSED SUCCESSFULLY (100% OK)")
    print("==================================================")
