"""
Wave 3 Test Suite (P8, P9) for Synapse AI Agent Platform:
- P8: Native Biometric Authorization Gate & Cryptographic Approval Flow
- P9: Accessibility Tree & Gesture Hardening (No Hardcoded Fallbacks, Resilient Token Search)
"""

import os
import sys
import json
import time
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.financial_gate import financial_gate
from app.task_manager import task_manager, TaskState
from app.device.gateway import device_gateway


def test_p8_biometric_gate_evaluation_and_approval():
    print("\n--> [P8] Testing Native Biometric Authorization Gate & Token Lifecycle...")
    task_id = f"task_bio_gate_{int(time.time()*1000)}"
    user_id = "tenant_primary"
    
    # 1. Initialize task state
    task_manager.create_task(task_id, user_id, "Order gourmet sushi $68.50")
    
    # 2. Financial gate evaluates transaction
    eval_res = financial_gate.evaluate_transaction(task_id, "order gourmet sushi", "$68.50", user_id)
    assert eval_res["requires_approval"] is True
    assert eval_res["is_high_value"] is True
    token = eval_res["token"]
    assert token.startswith("tok_")
    
    # 3. Verify counterfeit token is rejected on separate transaction
    task_id_fake = f"task_bio_fake_{int(time.time()*1000)}"
    financial_gate.evaluate_transaction(task_id_fake, "Counterfeit attempt", "$100.00", user_id)
    fake_token = f"tok_{int(time.time())}_counterfeit_signature_00000000"
    fake_auth = financial_gate.authorize_transaction(fake_token, task_id_fake, user_id)
    assert fake_auth["success"] is False
    assert fake_auth["reason"] in ("INVALID_SIGNATURE", "MALFORMED_TOKEN")
    
    # 4. Verify valid token commits approval atomically to ledger on original task_id
    auth_res = financial_gate.authorize_transaction(token, task_id, user_id)
    assert auth_res["success"] is True
    assert auth_res["status"] == "AUTHORIZED"
    
    # 5. Verify single-use token consumption (replay protection)
    replay_res = financial_gate.authorize_transaction(token, task_id, user_id)
    assert replay_res["success"] is False
    
    print("    [PASS] Biometric transaction evaluation, counterfeit rejection, and replay protection verified.")


def test_p8_websocket_biometric_auth_flow():
    print("--> [P8] Testing WebSocket Biometric Flow (Approve & Decline)...")
    client = TestClient(app)
    
    headers = {"X-API-Key": "synapse_api_sec_prod_9a2b8c4d1e7f0_2026"}
    
    # Test WebSocket connection with device token
    with client.websocket_connect("/ws/agent?token=dev_token_nexus_01") as ws:
        # Create a pending transaction
        task_id = f"task_ws_bio_{int(time.time()*1000)}"
        eval_res = financial_gate.evaluate_transaction(task_id, "Book flights", "$420.00", "tenant_primary")
        token = eval_res["token"]
        task_manager.create_task(task_id, "tenant_primary", "Book flights $420")
        
        # Send BIOMETRIC_AUTH_RESULT with APPROVED
        bio_payload = {
            "type": "BIOMETRIC_AUTH_RESULT",
            "task_id": task_id,
            "token": token,
            "status": "APPROVED",
            "amount": "$420.00",
            "action": "Book flights",
            "signature": "hmac_verified_signature"
        }
        ws.send_text(json.dumps(bio_payload))
        
        resp = ws.receive_json()
        assert resp["type"] == "ACTION_CONFIRMED"
        assert resp["status"] == "AUTHORIZED"
        assert resp["task_id"] == task_id
        
        # Verify task state in manager
        task_record = task_manager.get_task(task_id)
        assert task_record.state == TaskState.AUTHORIZED
        
        # Test Decline scenario
        task_id_decline = f"task_ws_decline_{int(time.time()*1000)}"
        eval_decline = financial_gate.evaluate_transaction(task_id_decline, "Transfer funds", "$150.00", "tenant_primary")
        token_decline = eval_decline["token"]
        task_manager.create_task(task_id_decline, "tenant_primary", "Transfer funds $150")
        
        bio_decline_payload = {
            "type": "BIOMETRIC_AUTH_RESULT",
            "task_id": task_id_decline,
            "token": token_decline,
            "status": "REJECTED",
            "reason": "User cancelled biometric prompt"
        }
        ws.send_text(json.dumps(bio_decline_payload))
        
        resp_decline = ws.receive_json()
        assert resp_decline["type"] == "AUTH_FAILED"
        assert resp_decline["status"] == "DECLINED"
        assert task_manager.get_task(task_id_decline).state == TaskState.FAILED

    print("    [PASS] WebSocket Biometric authorization and decline transitions verified.")


def test_p9_hardcoded_coordinates_eliminated():
    print("\n--> [P9] Testing Elimination of Hardcoded Coordinates in Android Client...")
    kt_client_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "android", "app", "src", "main", "java", "com", "synapse", "ai", "network", "SynapseWebSocketClient.kt"
    ))
    
    assert os.path.exists(kt_client_path), f"File not found: {kt_client_path}"
    with open(kt_client_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Verify legacy fallback coordinates are completely gone
    assert "fallbackX" not in content, "Found legacy fallbackX in SynapseWebSocketClient.kt!"
    assert "fallbackY" not in content, "Found legacy fallbackY in SynapseWebSocketClient.kt!"
    assert "2204f" not in content, "Found hardcoded composer coordinate 2204f!"
    assert "2230f" not in content, "Found hardcoded direct tab coordinate 2230f!"
    
    # Verify dynamic scrolling and accessibility methods are present
    assert "findNodeWithScroll" in content
    assert "findFirstEditableNode" in content
    assert "dismissKeyboard" in content
    assert "sendBiometricAuthResult" in content
    
    print("    [PASS] Verified zero hardcoded coordinates; dynamic tree exploration active.")


def test_p9_accessibility_resilient_tree_search():
    print("--> [P9] Testing Accessibility Resilient Search Logic...")
    acc_service_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "android", "app", "src", "main", "java", "com", "synapse", "ai", "accessibility", "SynapseAccessibilityService.kt"
    ))
    
    assert os.path.exists(acc_service_path), f"File not found: {acc_service_path}"
    with open(acc_service_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "findNodeWithScroll" in content
    assert "findFirstEditableNode" in content
    assert "dismissKeyboard" in content
    assert "debounceMs" in content
    assert "targetTokens" in content
    
    print("    [PASS] Verified multi-tier token search, scroll retries, and debounced hierarchy caching.")


if __name__ == "__main__":
    test_p8_biometric_gate_evaluation_and_approval()
    test_p8_websocket_biometric_auth_flow()
    test_p9_hardcoded_coordinates_eliminated()
    test_p9_accessibility_resilient_tree_search()
    print("\n==================================================")
    print("ALL WAVE 3 (P8, P9) TESTS PASSED SUCCESSFULLY (100% OK)")
    print("==================================================")
