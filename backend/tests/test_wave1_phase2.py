"""
Automated Verification Suite for Phase 2 - Wave 1 Upgrades:
- P0: Fail-Closed API Authentication & Secret Configuration
- P1: Tenant Isolation, Dynamic Device Provisioning & Session Lifecycle
- P2: Truthful Execution Verification & False-Positive Elimination
"""

import os
import asyncio
import hashlib
from fastapi.testclient import TestClient
from app.main import app, EXPECTED_API_KEY
from app.device.gateway import device_gateway, DeviceGateway
from app.device.verification_engine import task_verification_engine
from app.financial_gate import financial_gate

client = TestClient(app)

def test_p0_fail_closed_authentication():
    print("\n--> [P0] Testing Fail-Closed API Authentication...")
    
    # 1. Missing X-API-Key header -> 401 Unauthorized
    res_no_key = client.get("/api/llm/providers")
    assert res_no_key.status_code == 401, f"Expected 401, got {res_no_key.status_code}"
    assert "Unauthorized" in res_no_key.json()["detail"]
    print("    [PASS] Missing API key rejected with 401 Unauthorized.")

    # 2. Invalid X-API-Key header -> 403 Forbidden
    res_bad_key = client.get("/api/llm/providers", headers={"X-API-Key": "invalid_attacker_key"})
    assert res_bad_key.status_code == 403, f"Expected 403, got {res_bad_key.status_code}"
    assert "Forbidden" in res_bad_key.json()["detail"]
    print("    [PASS] Invalid API key rejected with 403 Forbidden.")

    # 3. Valid X-API-Key header -> 200 OK
    res_valid = client.get("/api/llm/providers", headers={"X-API-Key": EXPECTED_API_KEY})
    assert res_valid.status_code == 200, f"Expected 200, got {res_valid.status_code}"
    assert "providers" in res_valid.json()
    print("    [PASS] Valid API key authenticated successfully.")

    # 4. Public endpoint (/api/health) accessible without API key
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    print("    [PASS] Public health endpoint accessible without authentication.")


def test_p1_tenant_isolation_and_gateway():
    print("\n--> [P1] Testing Tenant Isolation and Device Gateway...")
    
    gw = DeviceGateway()
    
    # 1. Unregistered token fails closed
    assert gw.authenticate_device("unregistered_random_token") is None
    print("    [PASS] Unregistered device tokens fail closed.")

    # 2. Dynamic device registration bound to specific tenant
    tenant_alice = "tenant_alice_123"
    token_alice = gw.register_device(device_id="pixel_7_alice", tenant_id=tenant_alice)
    auth_alice = gw.authenticate_device(token_alice)
    assert auth_alice is not None
    assert auth_alice["device_id"] == "pixel_7_alice"
    assert auth_alice["tenant_id"] == tenant_alice
    print("    [PASS] Dynamic device registration succeeds with tenant binding.")

    # 3. Token revocation terminates authentication
    gw.revoke_device(token_alice)
    assert gw.authenticate_device(token_alice) is None
    print("    [PASS] Revoked device token is immediately invalidated.")

    # 4. Cross-tenant isolation
    token_bob = gw.register_device(device_id="galaxy_s24_bob", tenant_id="tenant_bob_456")
    # Simulate active session for Bob
    class DummyWS:
        async def accept(self): pass
        async def send_json(self, data): pass
        async def close(self, code=1000): pass

    async def run_session_test():
        session_bob = await gw.connect(DummyWS(), "galaxy_s24_bob", "tenant_bob_456")
        
        # Bob's active session is accessible to Bob
        active_bob = gw.get_active_session_for_tenant("tenant_bob_456")
        assert active_bob is not None
        assert active_bob.device_id == "galaxy_s24_bob"

        # Alice cannot access Bob's device session
        active_alice = gw.get_active_session_for_tenant("tenant_alice_123")
        assert active_alice is None, "Cross-tenant intrusion: Alice retrieved Bob's device session!"

        # In-flight command cancellation on disconnect
        cmd_task = asyncio.create_task(session_bob.send_command("task_1", {"type": "TAP"}, {}))
        await asyncio.sleep(0.05)
        gw.disconnect(session_bob.session_id, reason="TEST_DISCONNECT")
        cmd_res = await cmd_task
        assert cmd_res["status"] == "FAILED"
        assert cmd_res["reason"] == "TEST_DISCONNECT"
        print("    [PASS] In-flight commands cleanly terminated on session disconnect.")

    asyncio.run(run_session_test())
    print("    [PASS] Cross-tenant device isolation strictly enforced.")


def test_p2_truthful_verification():
    print("\n--> [P2] Testing Truthful Execution Verification...")
    
    fp_a = hashlib.sha256(b"ScreenA_Calculator").hexdigest()
    fp_b = hashlib.sha256(b"ScreenB_Result4").hexdigest()

    # 1. Device reports explicit failure
    failed_result = {
        "status": "FAILED",
        "reason": "Accessibility node not clickable",
        "screen_fingerprint": fp_a,
        "observation": {"foreground_package": "com.android.calculator2", "visible_nodes": []}
    }
    v1 = task_verification_engine.verify_wss_result(failed_result, expected={}, pre_fingerprint=fp_a)
    assert v1.verified is False
    assert "Device execution failed" in v1.reason or "Accessibility" in v1.reason
    print("    [PASS] Device execution failure correctly verified as FAILED.")

    # 2. Mutating action with identical pre and post fingerprint (UI unchanged)
    noop_result = {
        "status": "DISPATCHED",
        "action": {"type": "TAP"},
        "screen_fingerprint": fp_a,
        "observation": {"foreground_package": "com.android.calculator2", "visible_nodes": []}
    }
    v2 = task_verification_engine.verify_wss_result(noop_result, expected={}, pre_fingerprint=fp_a)
    assert v2.verified is False
    assert "identical" in v2.reason or "No state transition" in v2.reason
    print("    [PASS] State non-transition (identical fingerprint) correctly rejected.")

    # 3. False-Positive rejection: Expected element missing
    missing_elem_result = {
        "status": "DISPATCHED",
        "action": {"type": "TAP"},
        "screen_fingerprint": fp_b,
        "observation": {
            "foreground_package": "com.android.calculator2",
            "visible_nodes": [{"id": "btn_c", "text": "C", "desc": "Clear"}]
        }
    }
    v3 = task_verification_engine.verify_wss_result(
        missing_elem_result, 
        expected={"element_present": "Order Placed"}, 
        pre_fingerprint=fp_a
    )
    assert v3.verified is False
    assert "Order Placed" in v3.reason
    print("    [PASS] False-positive rejected when expected element is absent.")

    # 4. Successful semantic verification: Expected element is present
    success_result = {
        "status": "DISPATCHED",
        "action": {"type": "TAP"},
        "screen_fingerprint": fp_b,
        "observation": {
            "foreground_package": "com.android.calculator2",
            "visible_nodes": [{"id": "result", "text": "4", "desc": "Result 4"}]
        }
    }
    v4 = task_verification_engine.verify_wss_result(
        success_result, 
        expected={"element_present": "Result 4"}, 
        pre_fingerprint=fp_a
    )
    assert v4.verified is True
    print("    [PASS] Truthful match validated with verified=True.")


def test_p7_governance_otp_and_ledger():
    print("\n--> [P7] Testing Governance OTP Lifecycle and Ledger Immutability...")
    
    interceptor = financial_gate.otp_interceptor
    
    # 1. Extraction masks text and does not leak code via detection summary
    summary = interceptor.extract_otp("Your verification code is 849201 for banking login.", source="sms")
    assert summary is not None
    assert summary["detected"] is True
    assert "otp_code" not in summary  # Clean summary without raw code exposure
    
    # 2. Retrieval fetches latest valid OTP
    latest = interceptor.get_latest_valid_otp()
    assert latest is not None
    assert latest["otp_code"] == "849201"
    assert "****" in latest["source_masked"]
    
    # 3. Single-use consumption burns code
    consumed = interceptor.consume_otp("849201")
    assert consumed is True
    assert interceptor.get_latest_valid_otp() is None
    print("    [PASS] Single-use OTP successfully consumed and evicted.")

    import time
    tid = f"test_task_gov_{int(time.time() * 1000)}"
    financial_gate.ledger.log_request(tid, "CHARGE_CARD", "$45.00", "tok_test_123", "tenant_alice")
    
    # First approval succeeds
    ok1 = financial_gate.ledger.log_approval(tid, approved=True, notes="User biometric approval")
    assert ok1 is True
    
    # Second concurrent approval fails (prevent duplicate transition)
    ok2 = financial_gate.ledger.log_approval(tid, approved=True, notes="Duplicate attempt")
    assert ok2 is False
    print("    [PASS] Ledger atomic state transitions protect against replay/duplicate approvals.")


if __name__ == "__main__":
    test_p0_fail_closed_authentication()
    test_p1_tenant_isolation_and_gateway()
    test_p2_truthful_verification()
    test_p7_governance_otp_and_ledger()
    print("\n" + "=" * 50)
    print("ALL WAVE 1 (P0, P1, P2, P7) TESTS PASSED SUCCESSFULLY (100% OK)")
    print("=" * 50)
