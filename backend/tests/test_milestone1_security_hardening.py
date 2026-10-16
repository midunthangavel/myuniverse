"""
Milestone 1 — Security Hardening Regression Tests
Tests cover:
  P0: Session impersonation prevention (Critical Issue 1)
  P1: Biometric challenge-response binding (Critical Issue 2)
  P2: Briefing read-only invariant (Milestone 2)
  P3: Food order financial gate enforcement (Milestone 2)
"""

import os
import sys
import time
import json
import hmac
import hashlib
import asyncio
import unittest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Set required environment variables before importing app modules
os.environ.setdefault("SYNAPSE_API_KEY", "test-master-api-key-2026")
os.environ.setdefault("SYNAPSE_GOVERNANCE_SECRET", "test-governance-secret-key-2026-hardened")
os.environ.setdefault("SYNAPSE_DEVICE_TOKENS", json.dumps({
    "dev_token_nexus_01": {"device_id": "test_device", "tenant_id": "tenant_primary"}
}))


class TestSessionImpersonation(unittest.TestCase):
    """P0: Verify session issuance cannot be used for tenant impersonation."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        cls.client = TestClient(app)
        cls.api_key = os.environ["SYNAPSE_API_KEY"]

    def test_p0_01_unauthenticated_session_request_rejected(self):
        """Session endpoint must reject requests without authentication."""
        resp = self.client.post("/api/auth/session", json={"tenant_id": "tenant_primary"})
        self.assertIn(resp.status_code, [401, 403],
                      f"Unauthenticated session request should be 401/403, got {resp.status_code}")

    def test_p0_02_unauthenticated_no_body_rejected(self):
        """Session endpoint with no body and no auth must also fail."""
        resp = self.client.post("/api/auth/session")
        self.assertIn(resp.status_code, [401, 403])

    def test_p0_03_admin_can_issue_session_for_own_tenant(self):
        """Admin API key holder can issue a session for the default tenant."""
        resp = self.client.post(
            "/api/auth/session",
            json={"tenant_id": "tenant_primary"},
            headers={"X-API-Key": self.api_key}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("session_token", data)
        self.assertEqual(data["tenant_id"], "tenant_primary")

    def test_p0_04_admin_can_issue_cross_tenant_session(self):
        """Admin API key holder CAN specify a target tenant for testing."""
        resp = self.client.post(
            "/api/auth/session",
            json={"tenant_id": "tenant_test_isolation"},
            headers={"X-API-Key": self.api_key}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["tenant_id"], "tenant_test_isolation")

    def test_p0_05_session_user_cannot_escalate_tenant(self):
        """A session-authenticated user CANNOT request a session for a different tenant."""
        # First get a valid session for tenant_primary
        resp1 = self.client.post(
            "/api/auth/session",
            headers={"X-API-Key": self.api_key}
        )
        token = resp1.json()["session_token"]

        # Now try to use that session to issue a session for a different tenant
        resp2 = self.client.post(
            "/api/auth/session",
            json={"tenant_id": "tenant_attacker_controlled"},
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(resp2.status_code, 403,
                         f"Session user must not escalate to another tenant, got {resp2.status_code}")

    def test_p0_06_issued_session_token_is_valid_for_api(self):
        """An admin-issued session token should work for subsequent API calls."""
        resp1 = self.client.post(
            "/api/auth/session",
            headers={"X-API-Key": self.api_key}
        )
        token = resp1.json()["session_token"]

        resp2 = self.client.get(
            "/api/services/food/restaurants",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(resp2.status_code, 200)


class TestBiometricChallengeBinding(unittest.TestCase):
    """P1: Verify biometric challenge-response protocol binds signature to server nonce."""

    @classmethod
    def setUpClass(cls):
        from backend.app.financial_gate import BiometricChallengeManager, FinancialGate
        cls.challenge_mgr = BiometricChallengeManager(ttl_seconds=120)
        cls.financial_gate = FinancialGate()
        cls.gov_secret = os.environ["SYNAPSE_GOVERNANCE_SECRET"].encode()

    def test_p1_01_challenge_includes_nonce_and_payload(self):
        """Server-issued challenge must include challenge_nonce and payload_to_sign."""
        challenge = self.challenge_mgr.issue_challenge(
            task_id="test_task_01", action="food.checkout",
            amount="$45.00", tenant_id="tenant_primary"
        )
        self.assertIn("challenge_nonce", challenge)
        self.assertIn("payload_to_sign", challenge)
        self.assertTrue(challenge["challenge_nonce"].startswith("chn_"))
        self.assertIn("test_task_01", challenge["payload_to_sign"])

    def test_p1_02_correct_signature_verifies(self):
        """A correctly signed challenge must pass verification."""
        challenge = self.challenge_mgr.issue_challenge(
            task_id="test_task_02", action="food.checkout",
            amount="$30.00", tenant_id="tenant_primary"
        )
        payload = challenge["payload_to_sign"]
        sig = hmac.new(self.gov_secret, payload.encode(), hashlib.sha256).hexdigest()

        result = self.challenge_mgr.verify_and_consume(
            challenge_nonce=challenge["challenge_nonce"],
            signature=sig,
            task_id="test_task_02",
            tenant_id="tenant_primary"
        )
        self.assertTrue(result["valid"], f"Valid signature should verify, got: {result}")

    def test_p1_03_wrong_key_signature_rejected(self):
        """Signature made with wrong key (e.g., approval token as key) must be rejected."""
        challenge = self.challenge_mgr.issue_challenge(
            task_id="test_task_03", action="food.checkout",
            amount="$50.00", tenant_id="tenant_primary"
        )
        payload = challenge["payload_to_sign"]
        # Sign with approval token as key (the old broken behavior)
        wrong_key = b"tok_1234567890_abc123"
        bad_sig = hmac.new(wrong_key, payload.encode(), hashlib.sha256).hexdigest()

        result = self.challenge_mgr.verify_and_consume(
            challenge_nonce=challenge["challenge_nonce"],
            signature=bad_sig,
            task_id="test_task_03",
            tenant_id="tenant_primary"
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "INVALID_SIGNATURE")

    def test_p1_04_replay_rejected(self):
        """A consumed challenge cannot be replayed."""
        challenge = self.challenge_mgr.issue_challenge(
            task_id="test_task_04", action="payment",
            amount="$25.00", tenant_id="tenant_primary"
        )
        payload = challenge["payload_to_sign"]
        sig = hmac.new(self.gov_secret, payload.encode(), hashlib.sha256).hexdigest()

        # First use: should pass
        r1 = self.challenge_mgr.verify_and_consume(
            challenge_nonce=challenge["challenge_nonce"],
            signature=sig, task_id="test_task_04", tenant_id="tenant_primary"
        )
        self.assertTrue(r1["valid"])

        # Replay: should fail
        r2 = self.challenge_mgr.verify_and_consume(
            challenge_nonce=challenge["challenge_nonce"],
            signature=sig, task_id="test_task_04", tenant_id="tenant_primary"
        )
        self.assertFalse(r2["valid"])
        self.assertEqual(r2["reason"], "CHALLENGE_ALREADY_USED")

    def test_p1_05_wrong_payload_message_rejected(self):
        """Signature over the wrong message (old format without nonce) must be rejected."""
        challenge = self.challenge_mgr.issue_challenge(
            task_id="test_task_05", action="food.checkout",
            amount="$60.00", tenant_id="tenant_primary"
        )
        # Old broken Android format: taskId:amount:scope:timestamp
        old_message = "test_task_05:$60.00:FINANCIAL_PAYMENT:1234567890"
        bad_sig = hmac.new(self.gov_secret, old_message.encode(), hashlib.sha256).hexdigest()

        result = self.challenge_mgr.verify_and_consume(
            challenge_nonce=challenge["challenge_nonce"],
            signature=bad_sig,
            task_id="test_task_05",
            tenant_id="tenant_primary"
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "INVALID_SIGNATURE")

    def test_p1_06_cross_tenant_challenge_rejected(self):
        """Challenge issued for tenant_A cannot be consumed by tenant_B."""
        challenge = self.challenge_mgr.issue_challenge(
            task_id="test_task_06", action="payment",
            amount="$100.00", tenant_id="tenant_A"
        )
        payload = challenge["payload_to_sign"]
        sig = hmac.new(self.gov_secret, payload.encode(), hashlib.sha256).hexdigest()

        result = self.challenge_mgr.verify_and_consume(
            challenge_nonce=challenge["challenge_nonce"],
            signature=sig,
            task_id="test_task_06",
            tenant_id="tenant_B"  # Different tenant
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "CHALLENGE_BINDING_MISMATCH")

    def test_p1_07_expired_challenge_rejected(self):
        """Expired challenges must be rejected."""
        from backend.app.financial_gate import BiometricChallengeManager
        mgr = BiometricChallengeManager(ttl_seconds=-1)  # Already expired
        challenge = mgr.issue_challenge(
            task_id="test_task_07", action="payment",
            amount="$10.00", tenant_id="tenant_primary"
        )
        payload = challenge["payload_to_sign"]
        sig = hmac.new(self.gov_secret, payload.encode(), hashlib.sha256).hexdigest()

        time.sleep(0.1)  # Ensure it's past expiry
        result = mgr.verify_and_consume(
            challenge_nonce=challenge["challenge_nonce"],
            signature=sig,
            task_id="test_task_07",
            tenant_id="tenant_primary"
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "CHALLENGE_EXPIRED")

    def test_p1_08_token_only_approval_insufficient_for_high_value(self):
        """Financial gate should require challenge-response, not just token, for authorization.
        Token-based path should still work as fallback but challenge path is preferred."""
        eval_result = self.financial_gate.evaluate_transaction(
            task_id="test_task_08", action="food.checkout",
            amount="$75.00", user_id="tenant_primary"
        )
        self.assertIn("challenge_nonce", eval_result)
        self.assertIn("payload_to_sign", eval_result)
        self.assertTrue(eval_result["requires_approval"])


class TestBriefingReadOnlyInvariant(unittest.TestCase):
    """P2: Verify that reading the briefing never creates or modifies data."""

    @classmethod
    def setUpClass(cls):
        from backend.app.proactive_briefing import ProactiveBriefingEngine
        from backend.app.first_party_services import calendar_service
        cls.engine = ProactiveBriefingEngine()
        cls.calendar = calendar_service

    def test_p2_01_analyze_schedule_does_not_seed_data(self):
        """analyze_schedule must NOT call seed_demo_schedule_if_empty."""
        unique_tenant = f"readonly_test_{int(time.time() * 1000)}"
        
        # Before: no events
        events_before = self.calendar.list_events(unique_tenant)
        self.assertEqual(len(events_before), 0, "Fresh tenant should have no events")

        # Analyze: should NOT create any events
        analysis = self.engine.analyze_schedule(unique_tenant)

        # After: still no events
        events_after = self.calendar.list_events(unique_tenant)
        self.assertEqual(len(events_after), 0,
                         f"analyze_schedule must not create events, but found {len(events_after)}")

    def test_p2_02_generate_briefing_does_not_seed_data(self):
        """generate_briefing must NOT create any events."""
        unique_tenant = f"readonly_brief_{int(time.time() * 1000)}"

        events_before = self.calendar.list_events(unique_tenant)
        self.assertEqual(len(events_before), 0)

        # Generate briefing
        asyncio.run(self.engine.generate_briefing(unique_tenant, include_audio=False))

        events_after = self.calendar.list_events(unique_tenant)
        self.assertEqual(len(events_after), 0,
                         "generate_briefing must not create events")

    def test_p2_03_seed_demo_data_is_explicit(self):
        """seed_demo_data should be callable explicitly and actually create data."""
        unique_tenant = f"seed_test_{int(time.time() * 1000)}"
        
        self.engine.seed_demo_data(unique_tenant)
        events = self.calendar.list_events(unique_tenant)
        self.assertGreater(len(events), 0, "Explicit seed should create events")


class TestFoodOrderFinancialGate(unittest.TestCase):
    """P3: Verify food order actions in briefing require financial authorization."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        cls.client = TestClient(app)
        cls.api_key = os.environ["SYNAPSE_API_KEY"]

    def test_p3_01_food_order_without_token_returns_challenge(self):
        """FOOD_ORDER action without approval_token must return governance challenge, not execute."""
        resp = self.client.post(
            "/api/proactive/briefing/apply-action",
            json={
                "rec_id": "rec_lunch_preorder",
                "action_type": "FOOD_ORDER",
                "payload": {
                    "restaurant_name": "Sushi Zen",
                    "items": [{"item_id": "sushi_omakase", "name": "Omakase", "price": 45.0, "quantity": 1}]
                }
            },
            headers={"X-API-Key": self.api_key}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["success"], "Food order should not execute without approval")
        self.assertTrue(data["requires_approval"])
        self.assertIn("governance", data)
        self.assertIn("challenge_nonce", data["governance"])

    def test_p3_02_food_order_with_invalid_token_rejected(self):
        """FOOD_ORDER with an invalid approval token must be rejected."""
        resp = self.client.post(
            "/api/proactive/briefing/apply-action",
            json={
                "rec_id": "rec_lunch_test",
                "action_type": "FOOD_ORDER",
                "payload": {
                    "restaurant_name": "Sushi Zen",
                    "items": [{"item_id": "sushi_omakase", "price": 45.0, "quantity": 1}]
                },
                "approval_token": "tok_fake_invalid"
            },
            headers={"X-API-Key": self.api_key}
        )
        data = resp.json()
        self.assertFalse(data["success"])
        self.assertIn("reason", data)

    def test_p3_03_calendar_action_does_not_require_financial_gate(self):
        """Non-financial actions like CALENDAR_SCHEDULE should proceed without approval token."""
        test_tenant = f"tenant_cal_test_{int(time.time())}"
        resp = self.client.post(
            "/api/proactive/briefing/apply-action",
            json={
                "rec_id": "rec_focus_test",
                "action_type": "CALENDAR_SCHEDULE",
                "tenant_id": test_tenant,
                "payload": {
                    "title": "Focus Time",
                    "start_time": "04:00 PM",
                    "duration_minutes": 45,
                    "location": "Office"
                }
            },
            headers={"X-API-Key": self.api_key}
        )
        data = resp.json()
        self.assertTrue(data.get("success", False),
                        f"Calendar action should succeed without financial gate: {data}")


class TestDemoSeedEndpoint(unittest.TestCase):
    """P4: Verify /api/demo/seed requires admin and works explicitly."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from backend.app.main import app
        cls.client = TestClient(app)
        cls.api_key = os.environ["SYNAPSE_API_KEY"]

    def test_p4_01_demo_seed_requires_admin(self):
        """Non-admin session users cannot seed demo data."""
        # Get a session token first
        resp1 = self.client.post(
            "/api/auth/session",
            headers={"X-API-Key": self.api_key}
        )
        token = resp1.json()["session_token"]

        resp2 = self.client.post(
            "/api/demo/seed",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(resp2.status_code, 403)

    def test_p4_02_demo_seed_works_with_admin_key(self):
        """Admin API key holder can seed demo data."""
        resp = self.client.post(
            "/api/demo/seed",
            headers={"X-API-Key": self.api_key}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])


if __name__ == "__main__":
    print("=" * 72)
    print("Milestone 1 — Security Hardening Regression Tests")
    print("=" * 72)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestSessionImpersonation,
        TestBiometricChallengeBinding,
        TestBriefingReadOnlyInvariant,
        TestFoodOrderFinancialGate,
        TestDemoSeedEndpoint,
    ]

    for tc in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(tc))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 72)
    total = result.testsRun
    failures = len(result.failures) + len(result.errors)
    passed = total - failures
    print(f"TOTAL: {total} | PASSED: {passed} | FAILED: {failures}")
    print("=" * 72)

    sys.exit(0 if failures == 0 else 1)
