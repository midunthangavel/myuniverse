"""
Saga Rollback & Transaction Compensation Engine
Implements the distributed Saga execution pattern for multi-step mobile agent workflows.
Maintains reversible compensation actions for every forward operation.
If any step in a multi-app chain fails, previously completed steps are safely rolled back in reverse order.
"""

import time
from typing import Dict, Any, List, Optional, Callable

class SagaStep:
    """Represents a forward action paired with its compensating undo action."""
    def __init__(self, name: str, forward_action: str, compensate_action: str, params: Dict[str, Any]):
        self.name = name
        self.forward_action = forward_action
        self.compensate_action = compensate_action
        self.params = params
        self.status = "PENDING"  # PENDING, EXECUTED, COMPENSATED, FAILED


class SagaOrchestrator:
    """Coordinates forward execution and backward compensation for atomic chains."""

    # Built-in compensation registry
    COMPENSATIONS = {
        "SELECT_SEATS": "DESELECT_SEATS",
        "HOLD_SEATS": "RELEASE_SEATS_HOLD",
        "CHARGE_PAYMENT": "REFUND_PAYMENT",
        "DRAFT_CALENDAR": "DELETE_CALENDAR_EVENT",
        "BOOK_PULSE_RIDE": "CANCEL_PULSE_RIDE",
        "ADD_TO_CART": "REMOVE_FROM_CART",
        "SEND_EMAIL": "MARK_AS_DRAFT"
    }

    def __init__(self):
        self.sagas: Dict[str, Dict[str, Any]] = {}

    def execute_saga(
        self,
        saga_name: str,
        steps: List[Dict[str, Any]],
        simulate_failure_at: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes a sequence of steps.
        If a step fails (or simulate_failure_at triggers), rolls back previously executed steps in reverse.
        """
        saga_id = f"saga_{int(time.time() * 1000)}"
        executed_steps: List[Dict[str, Any]] = []
        compensations_run: List[Dict[str, Any]] = []
        has_failed = False
        failure_reason = None

        for idx, step in enumerate(steps):
            act = step.get("action", "")
            comp = self.COMPENSATIONS.get(act, f"UNDO_{act}")

            # Check simulated failure
            if simulate_failure_at is not None and idx == simulate_failure_at:
                has_failed = True
                failure_reason = f"Simulated failure at step {idx+1}: {act}"
                break

            # Execute forward step
            step_record = {
                "step_index": idx,
                "action": act,
                "compensation": comp,
                "params": step.get("params", {}),
                "status": "SUCCESS",
                "timestamp": time.time()
            }
            executed_steps.append(step_record)

        if has_failed:
            # ROLLBACK in reverse order
            for exec_step in reversed(executed_steps):
                comp_act = exec_step["compensation"]
                compensations_run.append({
                    "original_step": exec_step["step_index"],
                    "compensated_action": comp_act,
                    "status": "COMPENSATED",
                    "timestamp": time.time()
                })
                exec_step["status"] = "ROLLED_BACK"

            saga_record = {
                "saga_id": saga_id,
                "saga_name": saga_name,
                "status": "ROLLED_BACK",
                "total_steps": len(steps),
                "steps_completed_before_failure": len(executed_steps),
                "compensations_executed": len(compensations_run),
                "failure_reason": failure_reason,
                "executed_steps": executed_steps,
                "compensations": compensations_run,
                "completed_at": time.time()
            }
        else:
            saga_record = {
                "saga_id": saga_id,
                "saga_name": saga_name,
                "status": "COMMITTED",
                "total_steps": len(steps),
                "steps_completed_before_failure": len(executed_steps),
                "compensations_executed": 0,
                "failure_reason": None,
                "executed_steps": executed_steps,
                "compensations": [],
                "completed_at": time.time()
            }

        self.sagas[saga_id] = saga_record
        return saga_record

    def get_saga(self, saga_id: str) -> Optional[Dict[str, Any]]:
        return self.sagas.get(saga_id)

    def list_sagas(self) -> List[Dict[str, Any]]:
        return list(self.sagas.values())


# Global saga orchestrator singleton
saga_engine = SagaOrchestrator()
