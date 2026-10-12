"""
Wave 5 Test Suite (P13, P14, P15) for Synapse AI Agent Platform:
- P13: Full End-to-End Regression Test Matrix & Truthful Verification
- P14: Cloud Android Multi-Session Density Benchmark Harness
- P15: Production Packaging, Secrets & Environment Validation
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.device.gateway import device_gateway
from app.device.density_benchmark import DensityBenchmark
from app.device.verification_engine import task_verification_engine, ExpectedOutcome


def test_p13_end_to_end_truthful_pipeline():
    print("\n--> [P13] Testing Complete End-to-End Truthful Execution Pipeline...")
    client = TestClient(app)
    
    # 1. Reject unauthorized requests (Fail-Closed)
    bad_res = client.get("/api/capabilities", headers={"X-API-Key": "invalid_untrusted_token"})
    assert bad_res.status_code == 403
    
    # 2. Allow authenticated requests
    auth_headers = {"X-API-Key": "synapse_api_sec_prod_9a2b8c4d1e7f0_2026"}
    good_res = client.get("/api/capabilities", headers=auth_headers)
    assert good_res.status_code == 200
    
    # 3. Truthful verification engine rejects static screen with unchanged fingerprint
    import hashlib
    fp_pre = hashlib.sha256(b"Screen_Initial").hexdigest()
    fp_post_changed = hashlib.sha256(b"Screen_Changed").hexdigest()
    
    noop_result = {
        "status": "DISPATCHED",
        "action": {"type": "TAP"},
        "screen_fingerprint": fp_pre,
        "observation": {"foreground_package": "com.target.app", "visible_nodes": [{"id": "btn", "text": "Click Here"}]}
    }
    
    verif_noop = task_verification_engine.verify_wss_result(
        result=noop_result,
        expected={},
        pre_fingerprint=fp_pre
    )
    assert verif_noop.verified is False, "Violation: verifier accepted unchanged screen!"
    assert "identical" in verif_noop.reason or "No state transition" in verif_noop.reason
    
    # 4. Truthful verification engine approves genuine verified change
    changed_result = {
        "status": "DISPATCHED",
        "action": {"type": "TAP"},
        "screen_fingerprint": fp_post_changed,
        "observation": {"foreground_package": "com.target.app", "visible_nodes": [{"id": "txt_success", "text": "Success Screen: Order Confirmed"}]}
    }
    good_verif = task_verification_engine.verify_wss_result(
        result=changed_result,
        expected={"element_present": "Success Screen"},
        pre_fingerprint=fp_pre
    )
    assert good_verif.verified is True
    
    print("    [PASS] Strict fail-closed auth and truthful verification pipeline verified.")


def test_p14_density_benchmark():
    print("\n--> [P14] Running Cloud Android Multi-Session Density Benchmark...")
    benchmark = DensityBenchmark(device_gateway)
    
    result = asyncio.run(benchmark.run_density_test(concurrent_devices=20, commands_per_device=3))
    
    print(f"    Concurrent Devices : {result['concurrent_devices']}")
    print(f"    Total Commands     : {result['total_commands_executed']}")
    print(f"    Total Duration     : {result['total_duration_sec']}s")
    print(f"    Throughput         : {result['throughput_cmds_per_sec']} cmds/sec")
    print(f"    Latency p50        : {result['latency_p50_ms']}ms")
    print(f"    Latency p95        : {result['latency_p95_ms']}ms")
    print(f"    Latency p99        : {result['latency_p99_ms']}ms")
    print(f"    Crosstalk Detected : {result['crosstalk_detected']}")
    
    assert result["crosstalk_detected"] is False, "CRITICAL: Cross-session crosstalk detected!"
    assert result["latency_p99_ms"] < 50.0, f"p99 latency ({result['latency_p99_ms']}ms) exceeded 50ms target!"
    assert result["passed"] is True
    
    print("    [PASS] 20 concurrent device sessions scaled with 0 crosstalk and p99 < 50ms.")


def test_p15_environment_validation():
    print("\n--> [P15] Testing Production Environment Validation Script...")
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "validate_environment.py"))
    assert os.path.exists(script_path), f"File not found: {script_path}"
    
    # Run the validation script in a subprocess
    res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
        
    assert res.returncode == 0, f"Environment validation failed with exit code {res.returncode}"
    assert "STATUS: PASSED" in res.stdout
    
    print("    [PASS] Production packaging & security environment verified.")


if __name__ == "__main__":
    test_p13_end_to_end_truthful_pipeline()
    test_p14_density_benchmark()
    test_p15_environment_validation()
    print("\n==================================================")
    print("ALL WAVE 5 (P13, P14, P15) TESTS PASSED SUCCESSFULLY (100% OK)")
    print("==================================================")
