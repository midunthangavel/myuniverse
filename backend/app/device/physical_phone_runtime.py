import asyncio
import uuid
from typing import Dict, Any, Optional
from .gateway import device_gateway
from .verification_engine import task_verification_engine

class PhysicalPhoneRuntime:
    """
    Phase 1 & D Implementation: Physical Phone Service Runtime.
    Exposes core capabilities via the secure WSS command protocol.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._last_fingerprint = None

    async def _execute_remote(self, action: Dict[str, Any], expected: Dict[str, Any] = None, task_id: str = None) -> Dict[str, Any]:
        """Dispatches commands via the WSS protocol to the authenticated device."""
        session = device_gateway.get_active_session_for_tenant(self.tenant_id)
        if not session:
            return {"success": False, "status": "FAILED", "reason": "No authenticated physical device connected for this tenant."}
            
        if not task_id:
            task_id = str(uuid.uuid4())
            
        expected = expected or {}
        
        result = await session.send_command(
            task_id=task_id,
            action=action,
            expected=expected
        )
        
        # Phase G: Closed-loop semantic verification
        verification = task_verification_engine.verify_wss_result(
            result=result,
            expected=expected,
            pre_fingerprint=self._last_fingerprint
        )
        
        # Update last known state for next fast-path check
        self._last_fingerprint = result.get("screen_fingerprint")
        
        # Fallback to checking if action entirely failed on device
        if result.get("status") == "FAILED":
            verification.verified = False
            verification.reason = result.get("reason", "Device execution failed.")

        return {
            "success": verification.verified,
            "status": "VERIFIED" if verification.verified else "FAILED",
            "reason": verification.reason,
            "observation": result.get("observation", {}),
            "screen_fingerprint": result.get("screen_fingerprint"),
            "raw_result": result
        }

    # Core Action Primitives
    
    async def tap(self, resource_id: str, expected: Dict[str, Any] = None) -> Dict[str, Any]:
        action = {
            "type": "TAP",
            "target": {"resource_id": resource_id}
        }
        return await self._execute_remote(action, expected)
        
    async def type(self, resource_id: str, text: str, expected: Dict[str, Any] = None) -> Dict[str, Any]:
        action = {
            "type": "TYPE",
            "target": {"resource_id": resource_id},
            "value": text
        }
        return await self._execute_remote(action, expected)

    async def swipe(self, direction: str, expected: Dict[str, Any] = None) -> Dict[str, Any]:
        action = {
            "type": "SWIPE",
            "direction": direction
        }
        return await self._execute_remote(action, expected)

    async def global_action(self, action_name: str, expected: Dict[str, Any] = None) -> Dict[str, Any]:
        """e.g., BACK, HOME, RECENTS"""
        action = {
            "type": "GLOBAL_ACTION",
            "name": action_name
        }
        return await self._execute_remote(action, expected)

    # Core Observation Primitives

    async def observe(self) -> Dict[str, Any]:
        """Trigger an observation round trip without performing an action."""
        action = {"type": "OBSERVE_ONLY"}
        return await self._execute_remote(action)
