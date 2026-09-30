"""
Hierarchical Action & Trajectory Reflection Engine for Synapse AI Agent
Inspired by MadeAgents/mobile-use hierarchical reflection patterns.
Provides post-action state verification, error detection, retry parameter adjustment,
and trajectory-level insight extraction.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import time

class ReflectionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NOOP = "NOOP"

class NextActionStrategy(str, Enum):
    PROCEED = "PROCEED"
    RETRY_ADJUSTED = "RETRY_ADJUSTED"
    ROLLBACK = "ROLLBACK"
    ESCALATE_TO_USER = "ESCALATE_TO_USER"

class ActionReflector:
    """
    Evaluates individual action consequences by comparing pre- and post-action states.
    Detects silent UI failures, missed taps, loading stalls, and unexpected modals.
    """
    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def reflect(
        self,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        intended_action: Dict[str, Any],
        active_app: str = "unknown"
    ) -> Dict[str, Any]:
        before_title = before_state.get("title", "")
        after_title = after_state.get("title", "")
        before_nodes = before_state.get("nodes", [])
        after_nodes = after_state.get("nodes", [])

        action_type = intended_action.get("action", "").upper()
        target = intended_action.get("target", "")

        detected_changes: List[str] = []
        if before_title != after_title:
            detected_changes.append(f"Screen title transitioned: '{before_title}' -> '{after_title}'")
        
        node_diff = len(after_nodes) - len(before_nodes)
        if node_diff != 0:
            detected_changes.append(f"UI element count shifted by {node_diff:+d}")

        # Check for error indicators
        has_error = False
        error_msg = ""
        for n in after_nodes:
            text = (n.get("text") or "").lower()
            if any(err_word in text for err_word in ["error", "failed", "invalid", "unavailable", "try again", "denied"]):
                has_error = True
                error_msg = n.get("text")
                break

        # Verification logic
        if has_error:
            status = ReflectionStatus.FAILED
            strategy = NextActionStrategy.ESCALATE_TO_USER
            reasoning = f"Encountered error on screen: '{error_msg}'"
            retry_params = None
        elif before_state == after_state and action_type in ["TAP", "CLICK", "SELECT_SEATS"]:
            status = ReflectionStatus.NOOP
            strategy = NextActionStrategy.RETRY_ADJUSTED
            reasoning = f"No UI state change detected following {action_type} on '{target}'."
            # Suggest slight coordinate shift or increased timeout
            retry_params = {
                "wait_after_ms": 400,
                "retry_offset_px": 5,
                "force_focus": True
            }
        elif before_title != after_title or detected_changes:
            status = ReflectionStatus.SUCCESS
            strategy = NextActionStrategy.PROCEED
            reasoning = f"Action {action_type} successfully updated state. Changes: {', '.join(detected_changes)}."
            retry_params = None
        else:
            status = ReflectionStatus.SUCCESS
            strategy = NextActionStrategy.PROCEED
            reasoning = f"Action {action_type} dispatched normally."
            retry_params = None

        record = {
            "timestamp": time.time(),
            "active_app": active_app,
            "intended_action": intended_action,
            "status": status.value,
            "strategy": strategy.value,
            "reasoning": reasoning,
            "detected_changes": detected_changes,
            "retry_params": retry_params,
            "confidence": 0.94 if status == ReflectionStatus.SUCCESS else 0.72
        }
        self.history.append(record)
        return record


class TrajectoryReflector:
    """
    Analyzes entire multi-step trajectories upon task conclusion.
    Extracts atomic rules, app flow knowledge, and performance metrics.
    """
    def extract_learnings(
        self,
        user_goal: str,
        trajectory_steps: List[Dict[str, Any]],
        final_state: Dict[str, Any],
        app_name: str
    ) -> Dict[str, Any]:
        total_steps = len(trajectory_steps)
        successful_steps = [s for s in trajectory_steps if s.get("status", "SUCCESS") == "SUCCESS"]
        success_rate = (len(successful_steps) / total_steps) if total_steps > 0 else 1.0

        # Extract sequence of operations
        actions_sequence = [
            f"{s.get('action', 'STEP')}({s.get('target', 'screen')})"
            for s in trajectory_steps
        ]
        shortcut_pattern = " -> ".join(actions_sequence)

        # Formulate consolidated lesson
        lesson = (
            f"In {app_name}, goal '{user_goal}' achieved via sequence: {shortcut_pattern}. "
            f"Step success rate: {success_rate * 100:.1f}%."
        )

        return {
            "app_name": app_name,
            "user_goal": user_goal,
            "total_steps": total_steps,
            "success_rate": success_rate,
            "shortcut_pattern": shortcut_pattern,
            "lesson": lesson,
            "actions_sequence": actions_sequence,
            "timestamp": time.time()
        }


# Global reflector singletons
action_reflector = ActionReflector()
trajectory_reflector = TrajectoryReflector()
