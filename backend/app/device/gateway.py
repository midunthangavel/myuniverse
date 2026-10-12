import os
import json
import uuid
import time
import asyncio
from typing import Dict, Any, Optional
from fastapi import WebSocket

class DeviceSession:
    def __init__(self, websocket: WebSocket, device_id: str, tenant_id: str):
        self.websocket = websocket
        self.device_id = device_id
        self.tenant_id = tenant_id
        self.session_id = str(uuid.uuid4())
        self.sequence = 0
        self.pending_commands: Dict[str, asyncio.Future] = {}
        self.connected_at = time.time()
        self.is_active = True

    async def send_command(self, task_id: str, action: Dict[str, Any], expected: Dict[str, Any], expires_in_sec: int = 60) -> Dict[str, Any]:
        if not self.is_active:
            return {"status": "FAILED", "reason": "SESSION_INACTIVE", "task_id": task_id}
            
        self.sequence += 1
        command_id = str(uuid.uuid4())
        
        command = {
            "type": "COMMAND",
            "task_id": task_id,
            "command_id": command_id,
            "sequence": self.sequence,
            "action": action,
            "expected": expected,
            "expires_at": int(time.time()) + expires_in_sec
        }
        
        future = asyncio.get_event_loop().create_future()
        self.pending_commands[command_id] = future
        
        try:
            await self.websocket.send_json(command)
        except Exception as e:
            self.pending_commands.pop(command_id, None)
            return {"status": "FAILED", "reason": f"SEND_FAILED: {e}", "command_id": command_id, "task_id": task_id}
        
        try:
            # Wait for device to return COMMAND_RESULT
            result = await asyncio.wait_for(future, timeout=expires_in_sec)
            return result
        except asyncio.TimeoutError:
            self.pending_commands.pop(command_id, None)
            return {"status": "FAILED", "reason": "TIMEOUT", "command_id": command_id, "task_id": task_id}

    def handle_result(self, payload: Dict[str, Any]):
        command_id = payload.get("command_id")
        if command_id and command_id in self.pending_commands:
            future = self.pending_commands.pop(command_id)
            if not future.done():
                future.set_result(payload)

    def cancel_all_pending(self, reason: str = "SESSION_TERMINATED"):
        """Cancel and complete any pending command futures when session terminates."""
        self.is_active = False
        for cmd_id, future in list(self.pending_commands.items()):
            if not future.done():
                future.set_result({"status": "FAILED", "reason": reason, "command_id": cmd_id})
        self.pending_commands.clear()


class DeviceGateway:
    """
    Tenant-Isolated Device Gateway.
    Enforces dynamic enrollment, revocable credentials, fail-closed auth,
    and bounded session lifecycles.
    """
    def __init__(self):
        self.sessions: Dict[str, DeviceSession] = {}
        self.tenant_devices: Dict[str, set] = {}
        self.device_registry: Dict[str, Dict[str, Any]] = {}
        self._load_registry()

    def _load_registry(self):
        """Loads provisioned device tokens from environment without hardcoded credentials."""
        raw_tokens = os.getenv("SYNAPSE_DEVICE_TOKENS")
        if raw_tokens:
            try:
                parsed = json.loads(raw_tokens)
                if isinstance(parsed, dict):
                    self.device_registry.update(parsed)
            except Exception as e:
                print(f"[DeviceGateway Warning] Failed to parse SYNAPSE_DEVICE_TOKENS: {e}")

    def register_device(self, device_id: str, tenant_id: str, custom_token: Optional[str] = None) -> str:
        """Dynamically provisions a revocable enrollment credential bound to a tenant."""
        token = custom_token or f"syn_dev_{uuid.uuid4().hex}"
        self.device_registry[token] = {
            "device_id": device_id,
            "tenant_id": tenant_id,
            "created_at": time.time(),
            "is_revoked": False
        }
        return token

    def revoke_device(self, token: str) -> bool:
        """Revokes a device token and terminates any existing sessions immediately."""
        record = self.device_registry.get(token)
        if not record:
            return False
            
        record["is_revoked"] = True
        device_id = record.get("device_id")
        tenant_id = record.get("tenant_id")
        
        # Disconnect active sessions for this device
        active_sids = [sid for sid, s in self.sessions.items() if s.device_id == device_id and s.tenant_id == tenant_id]
        for sid in active_sids:
            self.disconnect(sid, reason="TOKEN_REVOKED")
            
        return True

    def authenticate_device(self, token: str) -> Optional[Dict[str, str]]:
        """Authenticates a device against the known registry. Fails closed if missing or invalid."""
        if not token:
            return None
        record = self.device_registry.get(token)
        if not record or record.get("is_revoked", False):
            return None
        return {
            "device_id": record["device_id"],
            "tenant_id": record["tenant_id"]
        }

    async def connect(self, websocket: WebSocket, device_id: str, tenant_id: str) -> DeviceSession:
        await websocket.accept()
        
        # Clean up any stale sessions for the same device and tenant
        stale_sids = [
            sid for sid, s in self.sessions.items() 
            if s.device_id == device_id and s.tenant_id == tenant_id
        ]
        for sid in stale_sids:
            self.disconnect(sid, reason="REPLACED_BY_NEW_CONNECTION")
            
        session = DeviceSession(websocket, device_id, tenant_id)
        self.sessions[session.session_id] = session
        
        if tenant_id not in self.tenant_devices:
            self.tenant_devices[tenant_id] = set()
        self.tenant_devices[tenant_id].add(session.session_id)
        
        print(f"[DeviceGateway] Device connected. Session: {session.session_id} | Device: {device_id} | Tenant: {tenant_id}")
        return session

    def disconnect(self, session_id: str, reason: str = "DEVICE_DISCONNECTED"):
        if session_id in self.sessions:
            session = self.sessions.pop(session_id)
            session.cancel_all_pending(reason=reason)
            if session.tenant_id in self.tenant_devices:
                self.tenant_devices[session.tenant_id].discard(session_id)
                if not self.tenant_devices[session.tenant_id]:
                    self.tenant_devices.pop(session.tenant_id, None)
            print(f"[DeviceGateway] Device disconnected. Session: {session_id} | Reason: {reason}")

    def get_session(self, session_id: str) -> Optional[DeviceSession]:
        return self.sessions.get(session_id)
        
    def get_active_session_for_tenant(self, tenant_id: str, device_id: Optional[str] = None) -> Optional[DeviceSession]:
        """Returns active session strictly belonging to tenant_id."""
        session_ids = self.tenant_devices.get(tenant_id, set())
        for sid in session_ids:
            session = self.sessions.get(sid)
            if session and session.is_active:
                if device_id is None or session.device_id == device_id:
                    return session
        return None

device_gateway = DeviceGateway()

