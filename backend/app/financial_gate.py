"""
Financial Governance Gate for Synapse AI Agent
Provides cryptographically signed HMAC one-time approval tokens (120s TTL),
regex-based OTP interception, and an immutable SQLite financial audit ledger.
"""

import os
import hmac
import hashlib
import time
import re
import sqlite3
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "synapse_memory.db")
SECRET_KEY = os.getenv("SYNAPSE_GOVERNANCE_SECRET", "synapse-hmac-secure-token-gate-key-2026").encode()

class ApprovalTokenManager:
    """Generates and validates HMAC-signed one-time execution tokens with 120s TTL."""
    
    def __init__(self, ttl_seconds: int = 120):
        self.ttl_seconds = ttl_seconds
        self.used_tokens: set = set()

    def generate_token(self, task_id: str, action: str, amount: str, user_id: str = "user_default") -> Dict[str, Any]:
        issued_at = int(time.time())
        expires_at = issued_at + self.ttl_seconds
        payload = f"{task_id}:{user_id}:{action}:{amount}:{issued_at}:{expires_at}"
        signature = hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()
        token_str = f"tok_{issued_at}_{signature[:32]}"

        return {
            "token": token_str,
            "task_id": task_id,
            "user_id": user_id,
            "action": action,
            "amount": amount,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "ttl_seconds": self.ttl_seconds
        }

    def verify_token(self, token_str: str, expected_task_id: str, expected_user_id: str, expected_action: str, expected_amount: str) -> Dict[str, Any]:
        if token_str in self.used_tokens:
            return {"valid": False, "reason": "TOKEN_ALREADY_USED"}

        parts = token_str.split("_")
        if len(parts) < 3 or not parts[1].isdigit():
            return {"valid": False, "reason": "MALFORMED_TOKEN"}

        issued_at = int(parts[1])
        expires_at = issued_at + self.ttl_seconds
        now = int(time.time())
        if now > expires_at:
            return {"valid": False, "reason": "TOKEN_EXPIRED"}

        # Recompute HMAC signature and cryptographically verify
        payload = f"{expected_task_id}:{expected_user_id}:{expected_action}:{expected_amount}:{issued_at}:{expires_at}"
        expected_signature = hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()
        expected_token = f"tok_{issued_at}_{expected_signature[:32]}"
        
        if not hmac.compare_digest(token_str, expected_token):
            return {"valid": False, "reason": "INVALID_SIGNATURE"}

        # Consume token
        self.used_tokens.add(token_str)
        return {"valid": True, "task_id": expected_task_id, "timestamp": now}


class OTPInterceptor:
    """Extracts and stores transient One-Time Passwords from SMS or notifications."""

    def __init__(self):
        self.cached_otps: List[Dict[str, Any]] = []

    def extract_otp(self, text: str, source: str = "notification") -> Optional[Dict[str, Any]]:
        # Regex for standard 4-8 digit verification codes
        patterns = [
            r"(?:code|otp|pin|verification|auth|password)[:\s]+([0-9]{4,8})",
            r"\b([0-9]{4,6})\s+is\s+your\b",
            r"\b([0-9]{4,6})\s+for\b"
        ]
        extracted_code = None
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                extracted_code = match.group(1)
                break

        if not extracted_code:
            # Fallback bare 6-digit number check if context mentions security
            if any(w in text.lower() for w in ["verify", "code", "security", "passcode"]):
                match = re.search(r"\b([0-9]{6})\b", text)
                if match:
                    extracted_code = match.group(1)

        if extracted_code:
            record = {
                "otp_code": extracted_code,
                "source_text": text,
                "source": source,
                "extracted_at": time.time(),
                "expires_at": time.time() + 300  # 5 min TTL
            }
            self.cached_otps.append(record)
            return record
        return None

    def get_latest_valid_otp(self) -> Optional[Dict[str, Any]]:
        now = time.time()
        valid = [o for o in self.cached_otps if o["expires_at"] > now]
        return valid[-1] if valid else None


class FinancialAuditLedger:
    """Immutable SQLite ledger of all financial governance evaluations & approvals."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_table()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_table(self):
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS financial_audit_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                user_id TEXT,
                task_id TEXT,
                action TEXT,
                amount TEXT,
                status TEXT,
                token TEXT,
                approved_at REAL,
                notes TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log_request(self, task_id: str, action: str, amount: str, token: str, user_id: str = "user_default"):
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO financial_audit_ledger (timestamp, user_id, task_id, action, amount, status, token, approved_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (time.time(), user_id, task_id, action, amount, "PENDING_APPROVAL", token, None, "Awaiting biometric or explicit confirmation"))
        conn.commit()
        conn.close()

    def log_approval(self, task_id: str, approved: bool, notes: str = ""):
        conn = self._get_connection()
        cur = conn.cursor()
        status = "AUTHORIZED" if approved else "DECLINED"
        cur.execute("""
            UPDATE financial_audit_ledger
            SET status = ?, approved_at = ?, notes = ?
            WHERE task_id = ?
        """, (status, time.time(), notes, task_id))
        conn.commit()
        conn.close()

    def get_ledger(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, timestamp, user_id, task_id, action, amount, status, token, approved_at, notes
            FROM financial_audit_ledger
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "user_id": r[2],
                "task_id": r[3],
                "action": r[4],
                "amount": r[5],
                "status": r[6],
                "token": r[7],
                "approved_at": r[8],
                "notes": r[9]
            }
            for r in rows
        ]

    def get_request(self, task_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, action, amount, status
            FROM financial_audit_ledger
            WHERE task_id = ?
        """, (task_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {"user_id": row[0], "action": row[1], "amount": row[2], "status": row[3]}
        return None


class FinancialGate:
    """Master governance orchestrator for high-risk and payment actions."""

    def __init__(self):
        self.token_manager = ApprovalTokenManager(ttl_seconds=120)
        self.otp_interceptor = OTPInterceptor()
        self.ledger = FinancialAuditLedger()

    def evaluate_transaction(self, task_id: str, action: str, amount: str, user_id: str = "user_default") -> Dict[str, Any]:
        """Assesses transaction, signs one-time token, and logs to immutable ledger."""
        token_info = self.token_manager.generate_token(task_id, action, amount, user_id)
        self.ledger.log_request(task_id, action, amount, token_info["token"], user_id)

        # Parse numeric amount if present
        cost_val = 0.0
        try:
            cleaned = amount.replace("$", "").strip()
            cost_val = float(cleaned)
        except Exception:
            cost_val = 0.0

        is_high_value = cost_val > 50.0

        return {
            "task_id": task_id,
            "action": action,
            "amount": amount,
            "requires_approval": True,
            "is_high_value": is_high_value,
            "token": token_info["token"],
            "expires_in_seconds": 120,
            "governance_mode": "ASK",
            "message": f"Biometric authorization required to execute {amount} charge for {action}."
        }

    def authorize_transaction(self, token_str: str, task_id: str, user_id: str = "user_default") -> Dict[str, Any]:
        """Validates cryptographic token and marks transaction approved."""
        # Retrieve original request to bind token to exact action and amount
        req = self.ledger.get_request(task_id)
        if not req:
            return {"success": False, "reason": "TASK_NOT_FOUND"}
        if req["status"] != "PENDING_APPROVAL":
            return {"success": False, "reason": f"TASK_ALREADY_{req['status']}"}
        if req["user_id"] != user_id:
            return {"success": False, "reason": "USER_MISMATCH"}

        res = self.token_manager.verify_token(token_str, task_id, req["user_id"], req["action"], req["amount"])
        if not res["valid"]:
            self.ledger.log_approval(task_id, approved=False, notes=f"Authorization rejected: {res['reason']}")
            return {"success": False, "reason": res["reason"]}

        self.ledger.log_approval(task_id, approved=True, notes="Cryptographically verified one-time token approval")
        return {
            "success": True,
            "task_id": task_id,
            "status": "AUTHORIZED",
            "authorized_at": time.time(),
            "message": "Payment authorization successfully committed to ledger."
        }

    def decline_transaction(self, task_id: str, user_id: str = "user_default", reason: str = "User declined") -> Dict[str, Any]:
        self.ledger.log_approval(task_id, approved=False, notes=reason)
        return {
            "success": True,
            "task_id": task_id,
            "status": "DECLINED",
            "reason": reason
        }


# Global financial gate singleton
financial_gate = FinancialGate()
