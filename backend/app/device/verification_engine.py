"""
Synapse AI — Task Verification & Recovery Engine
Implements closed-loop: PLAN ➔ ACT ➔ OBSERVE ➔ VERIFY ➔ RECOVER.
Detects temporal screen transitions (T-1 vs T0) and triggers deterministic
recovery pipelines (Wait, Scroll, Re-ground, Fallback) before reprompting LLMs.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from .state_engine import AndroidScreenState, AndroidUIElement

class ExpectedOutcome:
    """Defines what should occur following an action."""
    def __init__(
        self,
        screen_change: bool = True,
        target_appears: Optional[List[str]] = None,
        target_disappears: Optional[List[str]] = None,
        expected_screen_type: Optional[str] = None,
        expected_package: Optional[str] = None
    ):
        self.screen_change = screen_change
        self.target_appears = target_appears or []
        self.target_disappears = target_disappears or []
        self.expected_screen_type = expected_screen_type
        self.expected_package = expected_package

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_change": self.screen_change,
            "target_appears": self.target_appears,
            "target_disappears": self.target_disappears,
            "expected_screen_type": self.expected_screen_type,
            "expected_package": self.expected_package
        }


class VerificationResult:
    """Outcome of action verification."""
    def __init__(
        self,
        verified: bool,
        confidence: float,
        reason: str,
        screen_transition_detected: bool,
        recovery_applied: bool = False,
        recovery_method: Optional[str] = None
    ):
        self.verified = verified
        self.confidence = confidence
        self.reason = reason
        self.screen_transition_detected = screen_transition_detected
        self.recovery_applied = recovery_applied
        self.recovery_method = recovery_method

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified": self.verified,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "screen_transition_detected": self.screen_transition_detected,
            "recovery_applied": self.recovery_applied,
            "recovery_method": self.recovery_method
        }


class TaskVerificationEngine:
    """Verifies that an executed Android action caused the expected system transition."""

    @staticmethod
    def calculate_state_diff(pre_state: AndroidScreenState, post_state: AndroidScreenState) -> Dict[str, Any]:
        """Calculates temporal structural changes between pre-action (T-1) and post-action (T0)."""
        pre_labels = set(e.label.lower() for e in pre_state.elements if e.label)
        post_labels = set(e.label.lower() for e in post_state.elements if e.label)

        appeared = list(post_labels - pre_labels)
        disappeared = list(pre_labels - post_labels)
        package_changed = pre_state.app_package != post_state.app_package
        activity_changed = pre_state.activity_name != post_state.activity_name
        screen_type_changed = pre_state.screen_type != post_state.screen_type

        # Structural Jaccard Similarity (1.0 = identical screen, 0.0 = completely different)
        union = pre_labels.union(post_labels)
        similarity = len(pre_labels.intersection(post_labels)) / len(union) if union else 1.0

        transition_detected = (
            package_changed or 
            activity_changed or 
            screen_type_changed or 
            similarity < 0.85 or 
            len(appeared) > 0 or 
            len(disappeared) > 0
        )

        return {
            "transition_detected": transition_detected,
            "structural_similarity": round(similarity, 3),
            "package_changed": package_changed,
            "activity_changed": activity_changed,
            "screen_type_changed": screen_type_changed,
            "appeared_elements": appeared[:5],
            "disappeared_elements": disappeared[:5]
        }

    def verify_action(
        self,
        pre_state: AndroidScreenState,
        post_state: AndroidScreenState,
        expected: ExpectedOutcome
    ) -> VerificationResult:
        """Evaluates whether post_state matches expected outcomes."""
        diff = self.calculate_state_diff(pre_state, post_state)
        post_corpus = " ".join(e.label.lower() for e in post_state.elements)

        # 1. Package verification
        if expected.expected_package and expected.expected_package.lower() not in post_state.app_package.lower():
            return VerificationResult(
                verified=False,
                confidence=0.25,
                reason=f"Target package '{expected.expected_package}' not in foreground (got '{post_state.app_package}').",
                screen_transition_detected=diff["transition_detected"]
            )

        # 2. Check elements that MUST appear
        for target in expected.target_appears:
            if target.lower() not in post_corpus:
                return VerificationResult(
                    verified=False,
                    confidence=0.45,
                    reason=f"Expected element '{target}' did not appear on screen after action.",
                    screen_transition_detected=diff["transition_detected"]
                )

        # 3. Check elements that MUST disappear (e.g. dialog dismissed)
        for target in expected.target_disappears:
            if target.lower() in post_corpus:
                return VerificationResult(
                    verified=False,
                    confidence=0.40,
                    reason=f"Element '{target}' was expected to disappear but is still visible.",
                    screen_transition_detected=diff["transition_detected"]
                )

        # 4. Check screen transition expectation
        if expected.screen_change and not diff["transition_detected"]:
            return VerificationResult(
                verified=False,
                confidence=0.35,
                reason="Expected screen transition, but UI hierarchy remained identical (no change detected).",
                screen_transition_detected=False
            )

        # All conditions satisfied
        conf = 0.95 if diff["transition_detected"] else 0.85
        return VerificationResult(
            verified=True,
            confidence=conf,
            reason="Action successfully verified. Expected UI state matched.",
            screen_transition_detected=diff["transition_detected"]
        )

    async def execute_recovery(
        self,
        device_controller,
        failed_verification: VerificationResult,
        attempt: int = 1
    ) -> Tuple[bool, str]:
        """
        Executes deterministic recovery attempts before escalating to LLM re-planning:
        Attempt 1: Settle & wait (for network / animations)
        Attempt 2: Dismiss possible popup / press Back
        Attempt 3: Swipe / scroll to reveal occluded element
        """
        if attempt == 1:
            # Wait for animation or slow network loading
            await asyncio.sleep(1.5)
            return True, "SETTLE_WAIT"

        if attempt == 2:
            # Tap near top to dismiss toast, or press Back if stuck in dialog
            if hasattr(device_controller, "press_back"):
                await device_controller.press_back()
                await asyncio.sleep(1.0)
                return True, "DISMISS_KEYGUARD_OR_POPUP"

        if attempt == 3:
            # Scroll down to reveal elements below viewport
            if hasattr(device_controller, "swipe"):
                await device_controller.swipe(540, 1600, 540, 800, 300)
                await asyncio.sleep(1.0)
                return True, "SCROLL_TO_REVEAL"

        return False, "EXHAUSTED_RECOVERY"

task_verification_engine = TaskVerificationEngine()
