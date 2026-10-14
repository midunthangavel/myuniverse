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
import uuid
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "synapse_memory.db")
SECRET_KEY_STR = os.getenv("SYNAPSE_GOVERNANCE_SECRET")
if not SECRET_KEY_STR or SECRET_KEY_STR == "synapse-hmac-secure-token-gate-key-2026":
    raise RuntimeError("CRITICAL SECURITY ERROR: SYNAPSE_GOVERNANCE_SECRET must be set for production governance!")
SECRET_KEY = SECRET_KEY_STR.encode()

class BiometricChallengeManager:
    """
    Manages server-issued cryptographic approval challenges.
    Binds challenge to (nonce, task_id, tenant_id, action, amount, expires_at).
    Enforces atomic single-use challenge consumption and signature verification.
    """
    def __init__(self, ttl_seconds: int = 120):
        self.ttl_seconds = ttl_seconds
        self.db_path = DB_PATH
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS biometric_challenges (
                challenge_nonce TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                action TEXT NOT NULL,
                amount TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                consumed INTEGER DEFAULT 0,
                consumed_at REAL
            )
        """)
        conn.commit()
        conn.close()

    def issue_challenge(self, task_id: str, action: str, amount: str, tenant_id: str) -> Dict[str, Any]:
        now = time.time()
        expires_at = now + self.ttl_seconds
        challenge_nonce = f"chn_{uuid.uuid4().hex}"

        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO biometric_challenges (challenge_nonce, task_id, tenant_id, action, amount, created_at, expires_at, consumed)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (challenge_nonce, task_id, tenant_id, action, amount, now, expires_at))
        conn.commit()
        conn.close()

        payload_to_sign = f"{challenge_nonce}:{task_id}:{tenant_id}:{action}:{amount}"

        return {
            "challenge_nonce": challenge_nonce,
            "task_id": task_id,
            "tenant_id": tenant_id,
            "action": action,
            "amount": amount,
            "payload_to_sign": payload_to_sign,
            "expires_at": expires_at,
            "ttl_seconds": self.ttl_seconds
        }

    def verify_and_consume(
        self,
        challenge_nonce: str,
        signature: str,
        task_id: str,
        tenant_id: str,
        device_secret: Optional[bytes] = None
    ) -> Dict[str, Any]:
        now = time.time()
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM biometric_challenges WHERE challenge_nonce = ?",
            (challenge_nonce,)
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            return {"valid": False, "reason": "CHALLENGE_NOT_FOUND"}

        if row["consumed"] == 1:
            conn.close()
            return {"valid": False, "reason": "CHALLENGE_ALREADY_USED"}

        if now > row["expires_at"]:
            conn.close()
            return {"valid": False, "reason": "CHALLENGE_EXPIRED"}

        if row["task_id"] != task_id or row["tenant_id"] != tenant_id:
            conn.close()
            return {"valid": False, "reason": "CHALLENGE_BINDING_MISMATCH"}

        payload = f"{challenge_nonce}:{row['task_id']}:{row['tenant_id']}:{row['action']}:{row['amount']}"
        key = device_secret or SECRET_KEY
        expected_sig = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            conn.close()
            return {"valid": False, "reason": "INVALID_SIGNATURE"}

        cur.execute("""
            UPDATE biometric_challenges
            SET consumed = 1, consumed_at = ?
            WHERE challenge_nonce = ? AND consumed = 0
        """, (now, challenge_nonce))
        updated = cur.rowcount > 0
        conn.commit()
        conn.close()

        if not updated:
            return {"valid": False, "reason": "CONCURRENT_CHALLENGE_CONSUMPTION"}

        return {
            "valid": True,
            "task_id": task_id,
            "tenant_id": tenant_id,
            "action": row["action"],
            "amount": row["amount"],
            "timestamp": now
        }

    @staticmethod
    def compute_signature(challenge_nonce: str, task_id: str, tenant_id: str, action: str, amount: str, secret: Optional[bytes] = None) -> str:
        key = secret or SECRET_KEY
        payload = f"{challenge_nonce}:{task_id}:{tenant_id}:{action}:{amount}"
        return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


class ApprovalTokenManager:
    """Generates and validates HMAC-signed one-time execution tokens with 120s TTL."""
    
    def __init__(self, ttl_seconds: int = 120):
        self.ttl_seconds = ttl_seconds
        self.db_path = DB_PATH
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS used_tokens (
                token TEXT PRIMARY KEY,
                consumed_at REAL
            )
        """)
        conn.commit()
        conn.close()

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

        # Atomic consume token
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO used_tokens (token, consumed_at) VALUES (?, ?)", (token_str, time.time()))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return {"valid": False, "reason": "TOKEN_ALREADY_USED"}
            
        conn.close()
        return {"valid": True, "task_id": expected_task_id, "timestamp": now}


class OTPInterceptor:
    """
    Extracts and manages transient One-Time Passwords with strict privacy masking,
    active TTL auto-purging, and single-use consumption.
    """

    def __init__(self, ttl_seconds: int = 180):
        self.ttl_seconds = ttl_seconds
        self.cached_otps: List[Dict[str, Any]] = []

    def _purge_expired(self):
        """Active in-memory garbage collection of expired verification codes."""
        now = time.time()
        self.cached_otps = [o for o in self.cached_otps if o["expires_at"] > now and not o.get("consumed", False)]

    def extract_otp(self, text: str, source: str = "notification") -> Optional[Dict[str, Any]]:
        self._purge_expired()
        
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
            # Mask the source text to prevent storing cleartext sensitive notification content
            masked_text = re.sub(r"\b" + re.escape(extracted_code) + r"\b", "****", text)
            record = {
                "otp_code": extracted_code,
                "source_masked": masked_text,
                "source": source,
                "extracted_at": time.time(),
                "expires_at": time.time() + self.ttl_seconds,
                "consumed": False
            }
            self.cached_otps.append(record)
            return {
                "detected": True,
                "source": source,
                "extracted_at": record["extracted_at"],
                "expires_in_seconds": self.ttl_seconds
            }
        return None

    def get_latest_valid_otp(self) -> Optional[Dict[str, Any]]:
        self._purge_expired()
        now = time.time()
        valid = [o for o in self.cached_otps if o["expires_at"] > now and not o.get("consumed", False)]
        return valid[-1] if valid else None

    def consume_otp(self, otp_code: str) -> bool:
        """Single-use OTP consumption: immediately burns the code to prevent replay attacks."""
        self._purge_expired()
        for o in self.cached_otps:
            if o["otp_code"] == otp_code and not o.get("consumed", False):
                o["consumed"] = True
                self._purge_expired()
                return True
        return False


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

    def log_approval(self, task_id: str, approved: bool, notes: str = "") -> bool:
        conn = self._get_connection()
        cur = conn.cursor()
        status = "AUTHORIZED" if approved else "DECLINED"
        
        # Check current status to guarantee atomic single transition
        cur.execute("""
            SELECT user_id, action, amount, token, status
            FROM financial_audit_ledger
            WHERE task_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (task_id,))
        row = cur.fetchone()
        
        if not row:
            conn.close()
            return False
            
        user_id, action, amount, token, current_status = row
        if current_status != "PENDING_APPROVAL":
            conn.close()
            return False
            
        cur.execute("""
            INSERT INTO financial_audit_ledger (timestamp, user_id, task_id, action, amount, status, token, approved_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (time.time(), user_id, task_id, action, amount, status, token, time.time(), notes))
            
        conn.commit()
        conn.close()
        return True

    def get_ledger(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, timestamp, user_id, task_id, action, amount, status, token, approved_at, notes
            FROM financial_audit_ledger
            ORDER BY timestamp DESC, id DESC
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
            ORDER BY timestamp DESC
            LIMIT 1
        """, (task_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {"user_id": row[0], "action": row[1], "amount": row[2], "status": row[3]}
        return None


class FinancialGate:
    """Master governance orchestrator for high-risk and payment actions."""

    def __init__(self):
        self.challenge_manager = BiometricChallengeManager(ttl_seconds=120)
        self.token_manager = ApprovalTokenManager(ttl_seconds=120)
        self.otp_interceptor = OTPInterceptor()
        self.ledger = FinancialAuditLedger()

    def evaluate_transaction(self, task_id: str, action: str, amount: str, user_id: str = "user_default") -> Dict[str, Any]:
        """Assesses transaction, issues cryptographic challenge nonce, signs token, and logs to ledger."""
        challenge_info = self.challenge_manager.issue_challenge(task_id, action, amount, user_id)
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
            "challenge_nonce": challenge_info["challenge_nonce"],
            "payload_to_sign": challenge_info["payload_to_sign"],
            "expires_in_seconds": 120,
            "governance_mode": "ASK",
            "message": f"Biometric authorization required to execute {amount} charge for {action}."
        }

    def authorize_transaction(
        self,
        token_str: Optional[str] = None,
        task_id: str = "",
        user_id: str = "user_default",
        challenge_nonce: Optional[str] = None,
        signature: Optional[str] = None,
        device_secret: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Validates cryptographic proof (server challenge signature or one-time token)
        and commits atomic authorization state transition.
        """
        req = self.ledger.get_request(task_id)
        if not req:
            return {"success": False, "reason": "TASK_NOT_FOUND"}
        if req["status"] != "PENDING_APPROVAL":
            return {"success": False, "reason": f"TASK_ALREADY_{req['status']}"}
        if req["user_id"] != user_id:
            return {"success": False, "reason": "USER_MISMATCH"}

        # 1. Primary path: Server challenge-response protocol with cryptographic device signature
        if challenge_nonce and signature:
            chal_res = self.challenge_manager.verify_and_consume(
                challenge_nonce=challenge_nonce,
                signature=signature,
                task_id=task_id,
                tenant_id=user_id,
                device_secret=device_secret
            )
            if not chal_res["valid"]:
                self.ledger.log_approval(task_id, approved=False, notes=f"Challenge signature rejected: {chal_res['reason']}")
                return {"success": False, "reason": chal_res["reason"]}

            self.ledger.log_approval(task_id, approved=True, notes="Cryptographically verified device challenge signature")
            return {
                "success": True,
                "task_id": task_id,
                "status": "AUTHORIZED",
                "authorized_at": time.time(),
                "auth_method": "BIOMETRIC_CHALLENGE_SIGNATURE",
                "message": "Payment authorization cryptographically verified and committed to ledger."
            }

        # 2. Token-based validation path (HMAC token)
        elif token_str:
            res = self.token_manager.verify_token(token_str, task_id, req["user_id"], req["action"], req["amount"])
            if not res["valid"]:
                self.ledger.log_approval(task_id, approved=False, notes=f"Authorization rejected: {res['reason']}")
                return {"success": False, "reason": res["reason"]}

            self.ledger.log_approval(task_id, approved=True, notes="Cryptographically verified one-time HMAC token")
            return {
                "success": True,
                "task_id": task_id,
                "status": "AUTHORIZED",
                "authorized_at": time.time(),
                "auth_method": "HMAC_TOKEN",
                "message": "Payment authorization successfully committed to ledger."
            }

        return {"success": False, "reason": "MISSING_AUTHORIZATION_CREDENTIALS"}

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
