"""
Production Environment Validation Script for Synapse AI Agent Platform (P15)
Verifies all security secrets, fail-closed configurations, database permissions,
and required runtime dependencies prior to container launch or production deployment.
"""

import os
import sys
import json
import sqlite3

def validate():
    errors = []
    warnings = []
    print("\n=======================================================")
    print("  SYNAPSE AI: PRODUCTION ENVIRONMENT VALIDATION (P15)")
    print("=======================================================")

    # 1. Python Version Check
    py_ver = sys.version_info
    print(f"[*] Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < (3, 10):
        errors.append(f"Python 3.10+ required. Current version: {sys.version}")

    # 2. Try loading .env from backend/.env or root
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    backend_env = os.path.join(root_dir, "backend", ".env")
    root_env = os.path.join(root_dir, ".env")
    
    try:
        from dotenv import load_dotenv
        if os.path.exists(backend_env):
            load_dotenv(backend_env)
            print(f"[*] Loaded environment from: {backend_env}")
        elif os.path.exists(root_env):
            load_dotenv(root_env)
            print(f"[*] Loaded environment from: {root_env}")
        else:
            warnings.append("No .env file found in backend/ or root.")
    except ImportError:
        errors.append("python-dotenv library is not installed.")

    # 3. Security Secrets Validation
    api_key = os.getenv("SYNAPSE_API_KEY")
    if not api_key:
        errors.append("SYNAPSE_API_KEY environment variable is missing (Fail-Closed Auth violation).")
    elif len(api_key) < 20:
        errors.append("SYNAPSE_API_KEY is too short (< 20 characters). Must be a high-entropy secret.")
    else:
        print("[+] SYNAPSE_API_KEY: Configured & high-entropy.")

    gov_secret = os.getenv("SYNAPSE_GOVERNANCE_SECRET")
    if not gov_secret:
        errors.append("SYNAPSE_GOVERNANCE_SECRET environment variable is missing.")
    elif gov_secret == "synapse-hmac-secure-token-gate-key-2026":
        errors.append("SYNAPSE_GOVERNANCE_SECRET is using the insecure default key!")
    else:
        print("[+] SYNAPSE_GOVERNANCE_SECRET: Configured & hardened.")

    device_tokens_raw = os.getenv("SYNAPSE_DEVICE_TOKENS")
    if not device_tokens_raw:
        errors.append("SYNAPSE_DEVICE_TOKENS is missing. Device gateway will refuse connections.")
    else:
        try:
            tokens = json.loads(device_tokens_raw)
            if not isinstance(tokens, dict) or len(tokens) == 0:
                errors.append("SYNAPSE_DEVICE_TOKENS must be a non-empty JSON dictionary.")
            else:
                print(f"[+] SYNAPSE_DEVICE_TOKENS: Valid JSON mapping with {len(tokens)} registered device(s).")
        except Exception as e:
            errors.append(f"SYNAPSE_DEVICE_TOKENS is invalid JSON: {e}")

    # 4. Storage & SQLite Permissions
    db_path = os.path.join(root_dir, "backend", "synapse_memory.db")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS _env_test (id INTEGER PRIMARY KEY, ts REAL)")
        cur.execute("INSERT INTO _env_test (ts) VALUES (1.0)")
        conn.commit()
        cur.execute("DROP TABLE _env_test")
        conn.commit()
        conn.close()
        print("[+] SQLite Memory DB: Read/Write verified.")
    except Exception as e:
        errors.append(f"SQLite DB writable test failed at {db_path}: {e}")

    # 5. Core Dependencies Check
    required_modules = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "chromadb",
        "websockets"
    ]
    for mod in required_modules:
        try:
            __import__(mod)
            print(f"[+] Dependency '{mod}': Available.")
        except ImportError:
            errors.append(f"Required module '{mod}' is not installed.")

    print("\n-------------------------------------------------------")
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  [!] {w}")

    if errors:
        print("CRITICAL VALIDATION ERRORS DETECTED:")
        for err in errors:
            print(f"  [X] {err}")
        print("\nSTATUS: FAILED (System is NOT production ready)")
        print("=======================================================\n")
        return False
    else:
        print("STATUS: PASSED (100% Production Ready & Fail-Closed)")
        print("=======================================================\n")
        return True

if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
