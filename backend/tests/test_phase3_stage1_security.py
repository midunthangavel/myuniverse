"""
Stage 1 Acceptance Test Suite — Security & Tenant Boundary Hardening
Synapse AI Agent Platform — Phase 3 Implementation Plan

Verifies:
1. 401 Unauthorized on all protected routes when credentials are missing.
2. 403 Forbidden on invalid API keys; 401 on forged/expired Bearer session tokens.
3. Public ticket issuance (/api/auth/session) with short-lived HMAC-signed tokens.
4. Protection against cross-tenant impersonation (403 Forbidden on tenant tampering).
5. State-changing showcase is strictly POST and authenticated (GET returns 405).
6. Cryptographic single-use challenge-response biometric authorization with tamper detection.
7. Device token registration, authentication, and instantaneous revocation.
8. Automated scanning of frontend source and production bundle for zero hardcoded secrets.
"""

import os
import sys
import time
import glob
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app, create_session_token, verify_session_token, EXPECTED_API_KEY
from app.financial_gate import financial_gate, BiometricChallengeManager
from app.device.gateway import device_gateway

client = TestClient(app)


def test_missing_credentials_rejected_on_protected_routes():
    """Verify that all non-public endpoints strictly reject requests lacking auth credentials."""
    protected_endpoints = [
        ("GET", "/api/services/food/restaurants"),
        ("GET", "/api/services/calendar/events"),
        ("GET", "/api/services/tasks"),
        ("GET", "/api/showcase/steps"),
        ("POST", "/api/showcase/run"),
        ("GET", "/api/proactive/briefing"),
        ("POST", "/api/agent/orchestrate"),
        ("POST", "/api/governance/evaluate"),
        ("GET", "/api/device/status")
    ]

    for method, path in protected_endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json={})
        assert res.status_code == 401, f"Expected 401 for unauthenticated {method} {path}, got {res.status_code}"
        assert "Unauthorized" in res.json().get("detail", "")


def test_invalid_credentials_rejected():
    """Verify that forged API keys and forged session tokens fail closed."""
    # Invalid API key -> 403
    res_bad_key = client.get("/api/services/food/restaurants", headers={"X-API-Key": "completely_fake_key_12345"})
    assert res_bad_key.status_code == 403

    # Forged Bearer session token -> 401
    res_forged_token = client.get("/api/services/food/restaurants", headers={"Authorization": "Bearer st.fake_payload.bad_signature"})
    assert res_forged_token.status_code == 401

    # Expired session token -> 401
    expired_token = create_session_token(tenant_id="tenant_primary", ttl_seconds=-10)
    res_expired = client.get("/api/services/food/restaurants", headers={"Authorization": f"Bearer {expired_token}"})
    assert res_expired.status_code == 401


def test_public_session_ticket_issuance_and_access():
    """Verify that clients can exchange tenant identity for a valid scoped session ticket with authentication."""
    # Unauthenticated request must be rejected (Security Hardening P0)
    res_unauth = client.post("/api/auth/session", json={"tenant_id": "tenant_alice"})
    assert res_unauth.status_code in (401, 403)

    # Authenticated admin request succeeds
    res = client.post("/api/auth/session", json={"tenant_id": "tenant_alice"}, headers={"X-API-Key": EXPECTED_API_KEY})
    assert res.status_code == 200
    data = res.json()
    assert "session_token" in data
    assert data["token_type"] == "Bearer"
    assert data["tenant_id"] == "tenant_alice"

    token = data["session_token"]
    assert token.startswith("st.")

    # Access protected route with Bearer session token
    res_authed = client.get("/api/services/food/restaurants", headers={"Authorization": f"Bearer {token}"})
    assert res_authed.status_code == 200
    assert len(res_authed.json()) >= 3


def test_cross_tenant_access_rejection():
    """
    Verify that an authenticated user bound to tenant_alice CANNOT spoof X-Tenant-ID
    or body tenant_id to access or mutate tenant_bob data.
    """
    alice_token = create_session_token(tenant_id="tenant_alice", principal="user_alice")
    headers = {"Authorization": f"Bearer {alice_token}"}

    # 1. Attempt reading tasks with header spoofing
    res_read = client.get("/api/services/tasks", headers={**headers, "X-Tenant-ID": "tenant_bob"})
    assert res_read.status_code == 403
    assert "Cross-tenant access violation" in res_read.json()["detail"]

    # 2. Attempt creating calendar event with body spoofing
    res_write = client.post(
        "/api/services/calendar/events",
        headers=headers,
        json={
            "tenant_id": "tenant_bob",
            "title": "Malicious Spoofed Meeting",
            "start_time": "2026-10-15T10:00:00"
        }
    )
    assert res_write.status_code == 403
    assert "Cross-tenant access violation" in res_write.json()["detail"]

    # 3. Legitimate request using alice's bound tenant succeeds
    res_ok = client.get("/api/services/tasks", headers=headers)
    assert res_ok.status_code == 200


def test_showcase_strictly_post():
    """Verify that /api/showcase/run is strictly POST and rejects GET requests."""
    admin_headers = {"X-API-Key": EXPECTED_API_KEY}
    res_get = client.get("/api/showcase/run", headers=admin_headers)
    assert res_get.status_code == 405  # Method Not Allowed


def test_biometric_cryptographic_challenge_protocol():
    """
    Verifies cryptographic challenge-response protocol:
    1. Issue challenge bound to (task_id, tenant_id, action, amount).
    2. Single-use atomic consumption: second attempt fails.
    3. Replay attack rejection.
    4. Tampered payload / signature rejection.
    """
    # 1. Valid authorization commit and atomic single-use nonce consumption
    task_id_1 = f"test_gate_valid_{int(time.time()*1000)}"
    tenant = "tenant_crypto_test"
    action = "Transfer funds"
    amount = "$150.00"

    eval_1 = financial_gate.evaluate_transaction(task_id_1, action, amount, user_id=tenant)
    assert eval_1["requires_approval"] is True
    nonce_1 = eval_1["challenge_nonce"]
    assert nonce_1 is not None

    valid_sig_1 = BiometricChallengeManager.compute_signature(nonce_1, task_id_1, tenant, action, amount)

    ok_auth = financial_gate.authorize_transaction(
        task_id=task_id_1,
        user_id=tenant,
        challenge_nonce=nonce_1,
        signature=valid_sig_1
    )
    assert ok_auth["success"] is True
    assert ok_auth["status"] == "AUTHORIZED"
    assert ok_auth["auth_method"] == "BIOMETRIC_CHALLENGE_SIGNATURE"

    # 2. Replay attack rejection (atomic single-use consumption)
    replay_auth = financial_gate.authorize_transaction(
        task_id=task_id_1,
        user_id=tenant,
        challenge_nonce=nonce_1,
        signature=valid_sig_1
    )
    assert replay_auth["success"] is False
    assert replay_auth["reason"] in ("CHALLENGE_ALREADY_USED", "TASK_ALREADY_AUTHORIZED")

    # 3. Invalid signature rejection (tested on fresh task)
    task_id_2 = f"test_gate_bad_{int(time.time()*1000)}"
    eval_2 = financial_gate.evaluate_transaction(task_id_2, action, amount, user_id=tenant)
    nonce_2 = eval_2["challenge_nonce"]

    bad_auth = financial_gate.authorize_transaction(
        task_id=task_id_2,
        user_id=tenant,
        challenge_nonce=nonce_2,
        signature="invalid_signature_hex"
    )
    assert bad_auth["success"] is False
    assert bad_auth["reason"] == "INVALID_SIGNATURE"

    # 4. Cross-task binding mismatch rejection
    task_id_3 = f"test_gate_mismatch_{int(time.time()*1000)}"
    eval_3 = financial_gate.evaluate_transaction(task_id_3, action, amount, user_id=tenant)
    nonce_3 = eval_3["challenge_nonce"]

    mismatch_auth = financial_gate.authorize_transaction(
        task_id=task_id_3,
        user_id="different_tenant",
        challenge_nonce=nonce_3,
        signature=valid_sig_1
    )
    assert mismatch_auth["success"] is False


def test_device_enrollment_and_revocation():
    """Verify dynamic device registration, authentication, and instantaneous revocation."""
    device_id = f"phone_{int(time.time()*1000)}"
    tenant_id = "tenant_fleet_1"

    token = device_gateway.register_device(device_id=device_id, tenant_id=tenant_id)
    assert token.startswith("syn_dev_")

    # Authenticate device
    identity = device_gateway.authenticate_device(token)
    assert identity is not None
    assert identity["device_id"] == device_id
    assert identity["tenant_id"] == tenant_id

    # Revoke device
    revoked = device_gateway.revoke_device(token)
    assert revoked is True

    # Confirm subsequent auth fails closed
    assert device_gateway.authenticate_device(token) is None


def test_no_hardcoded_backend_secrets_in_frontend():
    """Scans all client source files and production build outputs to ensure no backend master secrets exist."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src_dir = os.path.join(project_root, "src")
    dist_dir = os.path.join(project_root, "dist")

    forbidden_patterns = [
        EXPECTED_API_KEY,
        "synapse_api_sec"
    ]

    files_to_check = []
    for ext in ("*.js", "*.html", "*.css", "*.ts"):
        files_to_check.extend(glob.glob(os.path.join(src_dir, "**", ext), recursive=True))
        if os.path.exists(dist_dir):
            files_to_check.extend(glob.glob(os.path.join(dist_dir, "**", ext), recursive=True))

    assert len(files_to_check) > 0, "No frontend files found to scan"

    for file_path in files_to_check:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            for pattern in forbidden_patterns:
                assert pattern not in content, f"SECURITY VIOLATION: Hardcoded secret pattern '{pattern}' detected in {file_path}"


if __name__ == "__main__":
    test_missing_credentials_rejected_on_protected_routes()
    test_invalid_credentials_rejected()
    test_public_session_ticket_issuance_and_access()
    test_cross_tenant_access_rejection()
    test_showcase_strictly_post()
    test_biometric_cryptographic_challenge_protocol()
    test_device_enrollment_and_revocation()
    test_no_hardcoded_backend_secrets_in_frontend()
    print("\n========================================================")
    print("ALL PHASE 3 STAGE 1 SECURITY ACCEPTANCE TESTS PASSED (100% OK)")
    print("========================================================")
