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

    async def send_command(self, task_id: str, action: Dict[str, Any], expected: Dict[str, Any], expires_in_sec: int = 60) -> Dict[str, Any]:
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
        
        await self.websocket.send_json(command)
        
        try:
            # Wait for device to return COMMAND_RESULT
            result = await asyncio.wait_for(future, timeout=expires_in_sec)
            return result
        except asyncio.TimeoutError:
            self.pending_commands.pop(command_id, None)
            return {"status": "FAILED", "reason": "TIMEOUT"}

    def handle_result(self, payload: Dict[str, Any]):
        command_id = payload.get("command_id")
        if command_id and command_id in self.pending_commands:
            future = self.pending_commands.pop(command_id)
            if not future.done():
                future.set_result(payload)


class DeviceGateway:
    def __init__(self):
        self.sessions: Dict[str, DeviceSession] = {}
        self.tenant_devices: Dict[str, set] = {}

    def authenticate_device(self, token: str) -> Optional[Dict[str, str]]:
        # In a real system, verify cryptographic enrollment token.
        # For now, we simulate finding the device & tenant identity.
        if not token or len(token) < 10:
            return None
            
        # Mock derivation of identity from secure token
        return {
            "device_id": f"dev_{token[:8]}",
            "tenant_id": f"tenant_{token[-8:]}"
        }

    async def connect(self, websocket: WebSocket, device_id: str, tenant_id: str) -> DeviceSession:
        await websocket.accept()
        session = DeviceSession(websocket, device_id, tenant_id)
        self.sessions[session.session_id] = session
        
        if tenant_id not in self.tenant_devices:
            self.tenant_devices[tenant_id] = set()
        self.tenant_devices[tenant_id].add(session.session_id)
        
        print(f"Device connected. Session: {session.session_id} | Tenant: {tenant_id}")
        return session

    def disconnect(self, session_id: str):
        if session_id in self.sessions:
            session = self.sessions.pop(session_id)
            if session.tenant_id in self.tenant_devices:
                self.tenant_devices[session.tenant_id].discard(session_id)
            print(f"Device disconnected. Session: {session_id}")

    def get_session(self, session_id: str) -> Optional[DeviceSession]:
        return self.sessions.get(session_id)
        
    def get_active_session_for_tenant(self, tenant_id: str) -> Optional[DeviceSession]:
        session_ids = self.tenant_devices.get(tenant_id, set())
        for sid in session_ids:
            return self.sessions[sid]
        return None

device_gateway = DeviceGateway()
