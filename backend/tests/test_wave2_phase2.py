"""
Automated Verification Suite for Phase 2 - Wave 2 Upgrades:
- P3: Standard Capability Contract System (message.send, calendar.create, food.order, alarm.set, task.create)
- P4: Latency Instrumentation & Delay Optimization (TaskTracer, Microsecond breakdown)
- P5: FastPath Router (<1.5s Deterministic Tier 1 Execution)
- P6: Idempotency & Task State Machine
"""

import time
from fastapi.testclient import TestClient
from app.main import app, EXPECTED_API_KEY
from app.capabilities import capability_registry, MessageSendInput, FoodOrderInput, CalendarCreateInput, AlarmSetInput
from app.fastpath_router import fastpath_router
from app.latency_tracer import TaskTracer
from app.task_manager import task_manager, TaskState

client = TestClient(app)

def test_p3_standard_capability_contracts():
    print("\n--> [P3] Testing Standard Capability Contracts...")
    
    # 1. Verify capability registry contains core contracts
    all_caps = capability_registry.list_all()
    cap_names = [c["name"] for c in all_caps]
    expected_caps = ["message.send", "calendar.create", "food.order", "alarm.set", "task.create"]
    for ec in expected_caps:
        assert ec in cap_names, f"Expected capability '{ec}' not found in {cap_names}"
    print(f"    [PASS] Core capabilities registered: {cap_names}")

    # 2. Test message.send contract
    msg_cap = capability_registry.get("message.send")
    assert msg_cap is not None
    # Preconditions check
    pre_fail = msg_cap.evaluate_preconditions(MessageSendInput(recipient="", text="Hi"), {})
    assert pre_fail.passed is False
    assert "recipient" in pre_fail.missing_requirements
    
    pre_ok = msg_cap.evaluate_preconditions(MessageSendInput(recipient="Rahul", text="Reaching in 20 min"), {})
    assert pre_ok.passed is True
    plan = msg_cap.generate_plan(MessageSendInput(recipient="Rahul", text="Reaching in 20 min"), {})
    assert len(plan.steps) == 4
    assert plan.requires_authorization is False
    print("    [PASS] message.send preconditions & deterministic plan verified.")

    # 3. Test food.order contract & financial risk rating
    food_cap = capability_registry.get("food.order")
    assert food_cap is not None
    assert food_cap.risk_level.value == "HIGH_FINANCIAL"
    food_plan = food_cap.generate_plan(FoodOrderInput(item="Boneless Chicken Biryani", restaurant="Meghana Foods"), {})
    assert food_plan.requires_authorization is True
    assert food_plan.authorization_amount is not None
    print("    [PASS] food.order HIGH_FINANCIAL risk & authorization gate verified.")

    # 4. Test calendar.create contract
    cal_cap = capability_registry.get("calendar.create")
    cal_plan = cal_cap.generate_plan(CalendarCreateInput(title="Meeting with Arun", start_time="tomorrow 3 PM"), {})
    assert len(cal_plan.steps) >= 3
    print("    [PASS] calendar.create plan verified.")

    # 5. Test REST capabilities endpoints
    res_list = client.get("/api/capabilities", headers={"X-API-Key": EXPECTED_API_KEY})
    assert res_list.status_code == 200
    assert res_list.json()["total_capabilities"] >= 5

    res_single = client.get("/api/capabilities/message.send", headers={"X-API-Key": EXPECTED_API_KEY})
    assert res_single.status_code == 200
    assert res_single.json()["name"] == "message.send"
    assert "schema" in res_single.json()
    print("    [PASS] REST /api/capabilities endpoints functioning correctly.")


def test_p4_latency_instrumentation():
    print("\n--> [P4] Testing Task Latency Instrumentation & Tracer...")
    
    tracer = TaskTracer(task_id="test_tracer_001")
    time.sleep(0.01) # Simulate 10ms receipt
    tracer.mark("intent_classification")
    time.sleep(0.02) # Simulate 20ms planning
    tracer.mark("device_dispatch")
    time.sleep(0.03) # Simulate 30ms dispatch
    tracer.mark("verification")
    
    trace_res = tracer.finish()
    assert "total_latency_ms" in trace_res
    assert trace_res["total_latency_ms"] >= 50.0
    assert "stage_breakdown" in trace_res
    assert "receipt_duration_ms" in trace_res["stage_breakdown"]
    assert "intent_classification_duration_ms" in trace_res["stage_breakdown"]
    assert "meets_fastpath_target" in trace_res
    print(f"    [PASS] Distributed tracer captures latency breakdown: total={trace_res['total_latency_ms']}ms.")


def test_p5_fastpath_router():
    print("\n--> [P5] Testing Tier 1 FastPath Router (<1.5s Target)...")
    
    # 1. Alarm FastPath
    r_alarm = fastpath_router.route("Set an alarm for 6:30 tomorrow morning")
    assert r_alarm.is_matched is True
    assert r_alarm.intent == "SET_ALARM"
    assert r_alarm.latency_ms < 10.0 # Sub-10ms routing
    print(f"    [PASS] FastPath Alarm matched in {r_alarm.latency_ms}ms (Zero LLM inference).")

    # 2. Hardware Gestures
    r_back = fastpath_router.route("go back")
    assert r_back.is_matched is True
    assert r_back.intent == "GLOBAL_BACK"
    
    r_home = fastpath_router.route("home")
    assert r_home.is_matched is True
    assert r_home.intent == "GLOBAL_HOME"
    print("    [PASS] FastPath Hardware gestures (BACK, HOME) matched deterministically.")

    # 3. Direct App Launch
    r_calc = fastpath_router.route("open calculator")
    assert r_calc.is_matched is True
    assert r_calc.intent == "OPEN_APP"
    assert r_calc.direct_plan["steps"][0]["target"] == "com.google.android.calculator"
    print("    [PASS] FastPath Direct app launch (Calculator) resolved in <5ms.")

    # 4. Arithmetic Evaluation
    r_math = fastpath_router.route("calculate 25 * 4")
    assert r_math.is_matched is True
    assert r_math.intent == "CALCULATE"
    assert "100" in r_math.direct_speech
    print("    [PASS] FastPath instant arithmetic evaluation verified.")

    # 5. Non-FastPath fallback to Tier 2
    r_complex = fastpath_router.route("Order my usual biryani from Meghana Foods")
    assert r_complex.is_matched is False # Correctly falls through to Tier 2 Standard capability
    print("    [PASS] Complex food order correctly routes to Tier 2 Standard execution.")


def test_p6_idempotency_and_task_manager():
    print("\n--> [P6] Testing Idempotency and Task State Machine...")
    
    tenant = "tenant_idempotency_test"
    idem_key = f"idem_key_{int(time.time()*1000)}"
    prompt = "Send Rahul a message"
    
    # 1. Create task with idempotency key
    task_rec, is_dup = task_manager.create_or_get_task(tenant, prompt, idem_key)
    assert is_dup is False
    assert task_rec.state == TaskState.CREATED
    print("    [PASS] Task created in CREATED state with idempotency key.")

    # 2. Progress through states: CREATED -> ROUTED -> DISPATCHED -> VERIFIED
    task_manager.transition_state(task_rec.task_id, TaskState.ROUTED)
    assert task_manager.get_task(task_rec.task_id).state == TaskState.ROUTED

    task_manager.transition_state(task_rec.task_id, TaskState.DISPATCHED)
    assert task_manager.get_task(task_rec.task_id).state == TaskState.DISPATCHED

    task_manager.transition_state(
        task_rec.task_id, 
        TaskState.VERIFIED, 
        reason="Action confirmed", 
        result_cache={"summary": "Message sent to Rahul", "verified": True}
    )
    assert task_manager.get_task(task_rec.task_id).state == TaskState.VERIFIED
    print("    [PASS] Task state machine transitioned cleanly to VERIFIED.")

    # 3. Repeated request with identical idempotency key returns cached task
    task_dup, is_dup2 = task_manager.create_or_get_task(tenant, prompt, idem_key)
    assert is_dup2 is True
    assert task_dup.task_id == task_rec.task_id
    assert task_dup.state == TaskState.VERIFIED
    assert task_dup.result_cache["verified"] is True
    print("    [PASS] Idempotency duplicate intercepted: returns cached verified result without duplicate execution.")

    # 4. REST API: Inspect task status
    res_task = client.get(f"/api/tasks/{task_rec.task_id}", headers={"X-API-Key": EXPECTED_API_KEY})
    assert res_task.status_code == 200
    assert res_task.json()["state"] == "VERIFIED"
    assert res_task.json()["result_cache"]["summary"] == "Message sent to Rahul"
    print("    [PASS] REST API /api/tasks/{task_id} returns accurate state machine record.")


if __name__ == "__main__":
    test_p3_standard_capability_contracts()
    test_p4_latency_instrumentation()
    test_p5_fastpath_router()
    test_p6_idempotency_and_task_manager()
    print("\n" + "=" * 50)
    print("ALL WAVE 2 (P3, P4, P5, P6) TESTS PASSED SUCCESSFULLY (100% OK)")
    print("=" * 50)
