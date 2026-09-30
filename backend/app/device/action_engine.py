"""
Synapse AI — Unified Android Action Engine
Unifies execution across:
1. Native Android Intents (ACTION_VIEW, geo:, web search, tel:)
2. Semantic Target Actions (Grounding Engine resolves natural language targets)
3. Physical Input & Gestures (ADB, UIAutomator, Fast Text Typing)
4. Closed-Loop Verification & Deterministic Recovery
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from .state_engine import android_state_engine, AndroidScreenState
from .grounding_engine import android_grounding_engine, GroundingResult
from .verification_engine import task_verification_engine, ExpectedOutcome, VerificationResult
from .controller_factory import device_factory

class ActionExecutionResult:
    def __init__(
        self,
        success: bool,
        action: str,
        target: Optional[str] = None,
        coordinates: Optional[Tuple[int, int]] = None,
        verification: Optional[VerificationResult] = None,
        method: str = "coordinate_tap",
        error: Optional[str] = None
    ):
        self.success = success
        self.action = action
        self.target = target
        self.coordinates = coordinates
        self.verification = verification
        self.method = method
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "target": self.target,
            "coordinates": list(self.coordinates) if self.coordinates else None,
            "method": self.method,
            "verification": self.verification.to_dict() if self.verification else None,
            "error": self.error
        }


class AndroidActionEngine:
    """The central unified action execution layer for Synapse Android Agent."""

    def __init__(self):
        self.state_engine = android_state_engine
        self.grounding_engine = android_grounding_engine
        self.verifier = task_verification_engine

    async def get_active_controller(self):
        return await device_factory.get_controller()

    async def launch_intent(
        self,
        action: str,
        uri: Optional[str] = None,
        package: Optional[str] = None,
        extras: Optional[Dict[str, str]] = None
    ) -> ActionExecutionResult:
        """Dispatches native Android Intent via Activity Manager."""
        ctrl = await self.get_active_controller()
        if not hasattr(ctrl, "_run_adb"):
            return ActionExecutionResult(success=True, action="INTENT", method="simulated_intent")

        cmd = ["shell", "am", "start", "-a", action]
        if uri:
            cmd.extend(["-d", uri])
        if package:
            cmd.extend(["-p", package])
        if extras:
            for k, v in extras.items():
                cmd.extend(["--es", k, str(v)])

        code, out, err = await ctrl._run_adb(cmd)
        success = (code == 0)
        return ActionExecutionResult(
            success=success,
            action="LAUNCH_INTENT",
            target=uri or action,
            method="native_android_intent",
            error=err if not success else None
        )

    async def open_app(self, package_or_name: str) -> ActionExecutionResult:
        """Launches target Android app."""
        ctrl = await self.get_active_controller()
        res = await ctrl.launch_app(package_or_name)
        return ActionExecutionResult(
            success=res.success,
            action="OPEN_APP",
            target=package_or_name,
            method="adb_launch_app",
            error=res.error
        )

    async def execute_semantic_action(
        self,
        action: str,  # 'tap' | 'type' | 'scroll'
        target: str,
        value: Optional[str] = None,
        expected_outcome: Optional[ExpectedOutcome] = None
    ) -> ActionExecutionResult:
        """
        Executes action using closed-loop:
        1. Perceive screen state T-1
        2. Ground semantic target to coordinates
        3. Execute action
        4. Perceive screen state T0
        5. Verify state transition and run recovery if needed
        """
        ctrl = await self.get_active_controller()
        action_clean = action.lower().strip()

        # Step 1: Perceive pre-action state (T-1)
        pre_state = await self.state_engine.perceive(ctrl)

        # Step 2: Ground target query to physical coordinates
        ground_res: GroundingResult = self.grounding_engine.ground_target(pre_state, target)
        if not ground_res.success:
            return ActionExecutionResult(
                success=False,
                action=action,
                target=target,
                method="grounding_failed",
                error=f"Could not ground semantic target '{target}' on current screen."
            )

        coords = ground_res.target_coordinates
        method_used = "semantic_grounded_tap"

        # Step 3: Execute Action
        if action_clean == "tap":
            await ctrl.tap(coords[0], coords[1])
        elif action_clean in ["type", "input"]:
            # Tap element first to gain focus
            await ctrl.tap(coords[0], coords[1])
            await asyncio.sleep(0.4)
            if value:
                await ctrl.input_text(value)
                method_used = "semantic_grounded_input"
        elif action_clean == "scroll":
            await ctrl.swipe(540, 1600, 540, 800, 300)
            method_used = "swipe_gesture"

        # Wait brief interval for UI rendering
        await asyncio.sleep(1.0)

        # Step 4: Perceive post-action state (T0)
        post_state = await self.state_engine.perceive(ctrl)

        # Step 5: Verify expected outcome
        expected = expected_outcome or ExpectedOutcome(screen_change=True)
        verification: VerificationResult = self.verifier.verify_action(pre_state, post_state, expected)

        # Step 6: Recovery loop if unverified
        if not verification.verified:
            for attempt in [1, 2]:
                rec_ok, rec_method = await self.verifier.execute_recovery(ctrl, verification, attempt=attempt)
                if rec_ok:
                    recovery_state = await self.state_engine.perceive(ctrl)
                    v_retry = self.verifier.verify_action(pre_state, recovery_state, expected)
                    if v_retry.verified:
                        v_retry.recovery_applied = True
                        v_retry.recovery_method = rec_method
                        verification = v_retry
                        break

        return ActionExecutionResult(
            success=verification.verified,
            action=action,
            target=target,
            coordinates=coords,
            verification=verification,
            method=method_used
        )

    async def press_back(self) -> ActionExecutionResult:
        ctrl = await self.get_active_controller()
        res = await ctrl.press_back()
        return ActionExecutionResult(success=res.success, action="PRESS_BACK", method="hardware_key")

    async def press_home(self) -> ActionExecutionResult:
        ctrl = await self.get_active_controller()
        res = await ctrl.press_home()
        return ActionExecutionResult(success=res.success, action="PRESS_HOME", method="hardware_key")

    async def wake_device(self) -> ActionExecutionResult:
        ctrl = await self.get_active_controller()
        if hasattr(ctrl, "_run_adb"):
            await ctrl._run_adb(["shell", "input", "keyevent", "224"])
            await ctrl._run_adb(["shell", "wm", "dismiss-keyguard"])
        return ActionExecutionResult(success=True, action="WAKE_DEVICE", method="hardware_key")

android_action_engine = AndroidActionEngine()
