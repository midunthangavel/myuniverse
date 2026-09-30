"""
Automated Verification Test Suite for Wave 3 Production & Real-World:
- Module 3.1: Real Device Bridge (DeviceFactory, SimulatorController, UIAutomatorParser)
- Module 3.2: Headless Browser Automation (BrowserAutomationEngine)
- Module 3.3: Local VLM Perception (LocalVLMPerceptionEngine)
- Module 3.4: Autonomous Scheduler Daemon (AutonomousSchedulerDaemon)
- Module 3.5: Saga Rollback Engine (SagaOrchestrator)
- Module 3.6: Day-in-the-Life Showcase (ShowcaseRunner)
- Wave 3 REST Endpoints
"""

import asyncio
from app.device import device_factory, UIAutomatorParser, SimulatorController
from app.browser_agent import browser_engine
from app.vlm_perception import vlm_engine
from app.scheduler import scheduler_daemon
from app.saga import saga_engine
from app.showcase import showcase_runner
from app.main import app

def test_device_bridge():
    print("--> Testing Module 3.1: Real Device Bridge...")
    status = asyncio.run(device_factory.get_status())
    assert "active_device_type" in status
    assert status["available_drivers"]["web_simulator"] is True

    # Test simulator controller actions
    sim = SimulatorController()
    tap_res = asyncio.run(sim.tap(100, 200))
    assert tap_res.success is True

    swipe_res = asyncio.run(sim.swipe(100, 500, 100, 100))
    assert swipe_res.success is True
    assert swipe_res.details["direction"] == "up"

    app_res = asyncio.run(sim.launch_app("cinema"))
    assert app_res.success is True
    assert sim.active_app == "cinema"

    # Test UIAutomator XML Parser
    bounds = UIAutomatorParser.parse_bounds("[120,340][480,560]")
    assert bounds["x1"] == 120 and bounds["y2"] == 560
    assert bounds["center_x"] == 300 and bounds["center_y"] == 450

    print("    [PASS] Real Device Bridge verified.")

def test_browser_automation():
    print("--> Testing Module 3.2: Headless Browser Automation...")
    st = browser_engine.get_status()
    assert "active_mode" in st

    # Test flow execution
    flow_res = asyncio.run(browser_engine.execute_flow("https://example.com", [
        {"action": "TAP", "target": "Login Button"},
        {"action": "INPUT_TEXT", "target": "Email Field"}
    ]))
    assert flow_res["steps_executed"] == 2
    assert flow_res["final_status"] == "SUCCESS"

    print("    [PASS] Headless Browser Automation verified.")

def test_vlm_perception():
    print("--> Testing Module 3.3: Local VLM Perception...")
    st = asyncio.run(vlm_engine.get_status())
    assert "vlm_available" in st

    analysis = asyncio.run(vlm_engine.analyze_screenshot("dGVzdF9pbWFnZQ=="))
    assert analysis["success"] is True

    elements = asyncio.run(vlm_engine.detect_elements("dGVzdF9pbWFnZQ=="))
    assert elements["detected_count"] > 0

    ground = asyncio.run(vlm_engine.ground_target("dGVzdF9pbWFnZQ==", "Confirm payment"))
    assert ground["success"] is True
    assert ground["coordinates"]["y"] > 2000

    print("    [PASS] Local VLM Perception verified.")

def test_scheduler_daemon():
    print("--> Testing Module 3.4: Autonomous Scheduler Daemon...")
    rules = scheduler_daemon.list_rules()
    assert len(rules) >= 4

    # Trigger morning briefing
    trig = scheduler_daemon.trigger_rule("rule_morning_briefing")
    assert trig["success"] is True
    assert "Briefing" in trig["dispatched_notification"]["title"]

    # Drain notifications
    notifs = scheduler_daemon.drain_notifications()
    assert len(notifs) >= 1
    assert notifs[0]["category"] == "briefing"

    # Queue should be empty now
    assert len(scheduler_daemon.drain_notifications()) == 0

    print("    [PASS] Autonomous Scheduler Daemon verified.")

def test_saga_rollback():
    print("--> Testing Module 3.5: Saga Rollback Engine...")
    
    # 1. Committed forward saga
    steps = [
        {"action": "SELECT_SEATS", "params": {"seat": "F14"}},
        {"action": "CHARGE_PAYMENT", "params": {"amount": "$36.00"}},
        {"action": "DRAFT_CALENDAR", "params": {"title": "Interstellar"}}
    ]
    saga_ok = saga_engine.execute_saga("Book Movie Saga", steps)
    assert saga_ok["status"] == "COMMITTED"
    assert len(saga_ok["compensations"]) == 0

    # 2. Failed saga with reverse compensation rollback
    saga_fail = saga_engine.execute_saga("Failed Movie Saga", steps, simulate_failure_at=2)
    assert saga_fail["status"] == "ROLLED_BACK"
    assert saga_fail["steps_completed_before_failure"] == 2
    assert len(saga_fail["compensations"]) == 2
    # Compensations executed in reverse order: CHARGE_PAYMENT (step 1) then SELECT_SEATS (step 0)
    assert saga_fail["compensations"][0]["compensated_action"] == "REFUND_PAYMENT"
    assert saga_fail["compensations"][1]["compensated_action"] == "DESELECT_SEATS"

    print("    [PASS] Saga Rollback Engine verified.")

def test_showcase_runner():
    print("--> Testing Module 3.6: Day-in-the-Life Showcase...")
    steps = showcase_runner.get_steps()
    assert len(steps) == 12

    s1 = showcase_runner.execute_step(1)
    assert s1["step"]["step"] == 1
    assert "Morning" in s1["step"]["title"]

    s12 = showcase_runner.execute_step(12)
    assert s12["step"]["step"] == 12
    assert "Accomplished" in s12["step"]["title"]

    print("    [PASS] Day-in-the-Life Showcase verified.")

def test_wave3_rest_endpoints():
    print("--> Testing Wave 3 REST Endpoints...")
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # Device Status
    res = client.get("/api/device/status")
    assert res.status_code == 200
    assert "active_device_type" in res.json()

    # Device Tap
    res = client.post("/api/device/tap", json={"x": 540, "y": 960})
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Browser execute flow
    res = client.post("/api/browser/execute-flow", json={
        "url": "https://synapse.local",
        "steps": [{"action": "TAP", "target": "Explore"}]
    })
    assert res.status_code == 200

    # VLM status
    res = client.get("/api/vlm/status")
    assert res.status_code == 200

    # Scheduler rules & trigger
    res = client.get("/api/daemon/rules")
    assert res.status_code == 200
    res = client.post("/api/daemon/trigger/rule_traffic_monitor")
    assert res.status_code == 200
    res = client.get("/api/daemon/notifications")
    assert res.status_code == 200
    assert res.json()["count"] >= 1

    # Saga execute
    res = client.post("/api/saga/execute", json={
        "saga_name": "Test Chain",
        "steps": [{"action": "ADD_TO_CART"}, {"action": "CHARGE_PAYMENT"}],
        "simulate_failure_at": 1
    })
    assert res.status_code == 200
    assert res.json()["status"] == "ROLLED_BACK"

    # Showcase steps
    res = client.get("/api/showcase/steps")
    assert res.status_code == 200
    assert res.json()["total_steps"] == 12

    print("    [PASS] Wave 3 REST Endpoints verified successfully.")

if __name__ == "__main__":
    test_device_bridge()
    test_browser_automation()
    test_vlm_perception()
    test_scheduler_daemon()
    test_saga_rollback()
    test_showcase_runner()
    test_wave3_rest_endpoints()
    print("\n==============================================")
    print("ALL WAVE 3 PRODUCTION TESTS PASSED (100% OK)")
    print("==============================================")
