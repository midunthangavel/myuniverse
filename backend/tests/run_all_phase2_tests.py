"""
Master Phase 2 (P0-P15) Comprehensive Regression Runner
Executes all 5 Waves sequentially to verify end-to-end stability and truthful execution.
"""

import os
import sys
import subprocess
import time

WAVES = [
    ("Wave 1 (P0, P1, P2, P7): Security, Gateway, Verifier & Financial Gate", "tests/test_wave1_phase2.py"),
    ("Wave 2 (P3, P4, P5, P6): Capabilities, Tracer, FastPath & State Machine", "tests/test_wave2_phase2.py"),
    ("Wave 3 (P8, P9): Biometric Gate & Accessibility Hardening", "tests/test_wave3_phase2.py"),
    ("Wave 4 (P10, P11, P12): Native Services, Isolated Memory & Investor Showcase", "tests/test_wave4_phase2.py"),
    ("Wave 5 (P13, P14, P15): Regression Matrix, Density Benchmark & Packaging", "tests/test_wave5_phase2.py"),
]

def run_all():
    print("\n" + "="*70, flush=True)
    print("  SYNAPSE AI: MASTER PHASE 2 (P0 - P15) VERIFICATION RUNNER", flush=True)
    print("="*70, flush=True)
    
    overall_start = time.time()
    results = []
    
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["PYTHONUNBUFFERED"] = "1"
    
    for title, test_script in WAVES:
        print(f"\n>>> Running {title}...", flush=True)
        script_path = os.path.join(backend_dir, test_script)
        t0 = time.time()
        res = subprocess.run([sys.executable, "-u", script_path], cwd=backend_dir, env=env)
        dur = round(time.time() - t0, 2)
        
        if res.returncode == 0:
            print(f"    --> [PASSED] in {dur}s", flush=True)
            results.append((title, True, dur))
        else:
            print(f"    --> [FAILED] in {dur}s", flush=True)
            results.append((title, False, dur))

    total_time = round(time.time() - overall_start, 2)
    print("\n" + "="*70, flush=True)
    print("  PHASE 2 SUMMARY MATRIX", flush=True)
    print("="*70, flush=True)
    all_passed = True
    for title, passed, dur in results:
        status_str = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"  {status_str} {title:<60} ({dur}s)", flush=True)

    print("-" * 70, flush=True)
    print(f"Total Execution Time: {total_time}s", flush=True)
    if all_passed:
        print("\nALL PHASE 2 PRIORITY TIERS (P0 TO P15) ARE 100% VERIFIED & PRODUCTION READY!", flush=True)
        print("="*70 + "\n", flush=True)
        return 0
    else:
        print("\nSOME TESTS FAILED.", flush=True)
        print("="*70 + "\n", flush=True)
        return 1

if __name__ == "__main__":
    sys.exit(run_all())
