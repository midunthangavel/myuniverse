from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .base import CapabilityContract, RiskLevel, PreconditionResult, CapabilityPlan, CapabilityOutcome, ExecutionStep

class AlarmSetInput(BaseModel):
    time_str: str = Field(description="Time to set alarm, e.g., '6:30 AM' or '07:00'")
    label: str = Field(default="Wake up", description="Label for alarm")

class AlarmSetCapability(CapabilityContract):
    name = "alarm.set"
    description = "Configures and enables an alarm on the device clock."
    risk_level = RiskLevel.LOW
    input_schema = AlarmSetInput

    def evaluate_preconditions(self, params: AlarmSetInput, context: Dict[str, Any]) -> PreconditionResult:
        if not params.time_str or not params.time_str.strip():
            return PreconditionResult(passed=False, missing_requirements=["time_str"], reason="Alarm time is required.")
        return PreconditionResult(passed=True, resolved_context={"time": params.time_str.strip()})

    def generate_plan(self, params: AlarmSetInput, context: Dict[str, Any]) -> CapabilityPlan:
        # FastPath native action
        steps = [
            ExecutionStep(
                action="NATIVE_INTENT",
                target="android.intent.action.SET_ALARM",
                value=params.time_str,
                desc=f"Set device alarm for {params.time_str}",
                expected_element="Alarm set"
            )
        ]
        return CapabilityPlan(
            capability_name=self.name,
            risk_level=self.risk_level,
            steps=steps,
            requires_authorization=False,
            summary=f"Set alarm for {params.time_str}"
        )

    def verify_outcome(self, plan: CapabilityPlan, execution_results: List[Dict[str, Any]]) -> CapabilityOutcome:
        if not execution_results:
            return CapabilityOutcome(success=False, verified=False, reason="No execution steps.")
        last_step = execution_results[-1]
        verified = last_step.get("status") == "VERIFIED" or last_step.get("success", False)
        return CapabilityOutcome(
            success=verified,
            verified=verified,
            reason=f"Alarm successfully scheduled for {plan.summary}." if verified else "Failed to verify alarm.",
            evidence={"result": last_step}
        )
