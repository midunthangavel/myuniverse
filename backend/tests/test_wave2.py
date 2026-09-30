"""
Automated Verification Test Suite for Wave 2 Intelligence Layer:
- Module 2.1: Hierarchical Reflection Engine (ActionReflector, TaskProgressor, TrajectoryReflector)
- Module 2.2: Proactive App Exploration Engine (AppExplorer, Knowledge Maps)
- Module 2.3: App-Specific RAG Memory (AppSpecificMemory, ChromaDB collections)
- Module 2.4: Financial Governance Gate (HMAC Tokens, OTP Extraction, SQLite Ledger)
- Wave 2 REST API Endpoints
"""

import time
from app.reflector import action_reflector, trajectory_reflector, ReflectionStatus, NextActionStrategy
from app.progressor import task_progressor
from app.explorer import app_explorer
from app.app_memory import app_specific_memory
from app.financial_gate import financial_gate
from app.main import app

def test_reflection_engine():
    print("--> Testing Module 2.1: Hierarchical Reflection Engine...")
    
    # 1. Successful state change
    before_st = {"title": "CinePass IMAX Experience", "nodes": [{"text": "Select Seats"}]}
    after_st = {"title": "Select Seats - Interstellar", "nodes": [{"text": "Row F14"}, {"text": "Row F15"}]}
    res = action_reflector.reflect(before_st, after_st, {"action": "TAP", "target": "Select Seats"}, "cinema")
    assert res["status"] == ReflectionStatus.SUCCESS.value
    assert res["strategy"] == NextActionStrategy.PROCEED.value
    assert len(res["detected_changes"]) > 0

    # 2. NOOP / Unchanged state (retry adjusted)
    res_noop = action_reflector.reflect(before_st, before_st, {"action": "TAP", "target": "Select Seats"}, "cinema")
    assert res_noop["status"] == ReflectionStatus.NOOP.value
    assert res_noop["strategy"] == NextActionStrategy.RETRY_ADJUSTED.value
    assert res_noop["retry_params"] is not None

    # 3. Error modal state
    error_st = {"title": "Error Dialog", "nodes": [{"text": "Payment failed: Card unavailable"}]}
    res_err = action_reflector.reflect(before_st, error_st, {"action": "TAP", "target": "Authorize Payment"}, "cinema")
    assert res_err["status"] == ReflectionStatus.FAILED.value
    assert res_err["strategy"] == NextActionStrategy.ESCALATE_TO_USER.value

    # 4. Task Progressor tracking
    tid = f"test_task_{int(time.time()*1000)}"
    task_progressor.start_task(tid, "Book CinePass Ticket", [{"action": "TAP"}, {"action": "SELECT"}], "cinema")
    prog = task_progressor.update_step(tid, 0, "TAP", res)
    assert prog["progress_percent"] == 50.0
    assert prog["is_complete"] is False

    # 5. Trajectory Reflector
    learn = trajectory_reflector.extract_learnings(
        user_goal="Book 2 tickets for Interstellar",
        trajectory_steps=[{"action": "TAP", "target": "Interstellar"}, {"action": "SELECT", "target": "Row F"}],
        final_state=after_st,
        app_name="cinema"
    )
    assert "cinema" in learn["lesson"]
    assert learn["total_steps"] == 2

    print("    [PASS] Hierarchical Reflection Engine verified.")

def test_app_explorer():
    print("--> Testing Module 2.2: Proactive App Exploration Engine...")
    apps = ["cinema", "food", "pulse_ride", "orbit_maps", "calendar", "spark_mail"]
    for app_name in apps:
        k = app_explorer.get_knowledge(app_name)
        assert k is not None, f"Knowledge map for {app_name} not found"
        assert "screens" in k and len(k["screens"]) > 0
        assert "transitions" in k and len(k["transitions"]) > 0

    path = app_explorer.get_navigation_path("cinema", "seat_selection")
    assert len(path) > 0
    assert path[0]["action"] == "TAP"

    print("    [PASS] Proactive App Exploration Engine verified.")

def test_app_memory():
    print("--> Testing Module 2.3: App-Specific RAG Memory...")
    shortcuts = app_specific_memory.get_app_shortcuts("food")
    assert len(shortcuts) > 0
    assert "Paradise" in shortcuts[0]["task"]

    # Record trajectory
    doc_id = app_specific_memory.record_successful_trajectory(
        app="pulse_ride",
        task="Book Premier Ride to Airport",
        steps=[{"action": "LAUNCH_APP", "target": "pulse_ride"}, {"action": "TAP", "target": "Airport"}]
    )
    assert doc_id.startswith("traj_pulse_ride_")

    similar = app_specific_memory.retrieve_similar_task("pulse_ride", "Airport")
    assert len(similar) > 0

    print("    [PASS] App-Specific RAG Memory verified.")

def test_financial_gate():
    print("--> Testing Module 2.4: Financial Governance Gate...")
    tid = f"fin_task_{int(time.time()*1000)}"
    eval_res = financial_gate.evaluate_transaction(tid, "book_movie", "$36.00")
    assert eval_res["requires_approval"] is True
    assert eval_res["token"].startswith("tok_")

    # Authorize with valid token
    auth_res = financial_gate.authorize_transaction(eval_res["token"], tid)
    assert auth_res["success"] is True
    assert auth_res["status"] == "AUTHORIZED"

    # Reject re-used token
    reuse_res = financial_gate.authorize_transaction(eval_res["token"], tid)
    assert reuse_res["success"] is False

    # OTP extraction
    otp_sample = "Your Synapse verification code is 849201. Do not share this code."
    otp = financial_gate.otp_interceptor.extract_otp(otp_sample)
    assert otp is not None
    assert otp["otp_code"] == "849201"

    # Immutable ledger check
    ledger = financial_gate.ledger.get_ledger(limit=10)
    assert len(ledger) > 0
    assert ledger[0]["task_id"] == tid

    print("    [PASS] Financial Governance Gate verified.")

def test_wave2_rest_endpoints():
    print("--> Testing Wave 2 REST Endpoints...")
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # 1. Reflector evaluate endpoint
    res = client.post("/api/reflector/evaluate", json={
        "before_state": {"title": "Home", "nodes": []},
        "after_state": {"title": "Menu", "nodes": [{"text": "Biryani"}]},
        "intended_action": {"action": "TAP", "target": "Order"},
        "active_app": "food"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"

    # 2. Explorer endpoint
    res = client.get("/api/explorer/knowledge/cinema")
    assert res.status_code == 200
    assert "screens" in res.json()

    # 3. App memory shortcuts endpoint
    res = client.get("/api/app-memory/cinema/shortcuts")
    assert res.status_code == 200
    assert len(res.json()["shortcuts"]) > 0

    # 4. Financial Gate Ledger endpoint
    res = client.get("/api/governance/ledger")
    assert res.status_code == 200
    assert "ledger" in res.json()

    # 5. OTP Intercept endpoint
    res = client.post("/api/governance/intercept-otp", json={
        "text": "Your banking OTP code: 492810 for $36.00 payment.",
        "source": "sms"
    })
    assert res.status_code == 200
    assert res.json()["detected"] is True
    assert res.json()["otp"]["otp_code"] == "492810"

    print("    [PASS] Wave 2 REST Endpoints verified successfully.")

if __name__ == "__main__":
    test_reflection_engine()
    test_app_explorer()
    test_app_memory()
    test_financial_gate()
    test_wave2_rest_endpoints()
    print("\n==============================================")
    print("ALL WAVE 2 INTELLIGENCE TESTS PASSED (100% OK)")
    print("==============================================")
