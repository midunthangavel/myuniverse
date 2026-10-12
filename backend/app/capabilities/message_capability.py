from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .base import CapabilityContract, RiskLevel, PreconditionResult, CapabilityPlan, CapabilityOutcome, ExecutionStep

class MessageSendInput(BaseModel):
    recipient: str = Field(description="Name or phone number of recipient")
    text: str = Field(description="Body of message to deliver")
    app_target: str = Field(default="com.whatsapp", description="Target messaging app package")

class MessageSendCapability(CapabilityContract):
    name = "message.send"
    description = "Composes, dispatches, and verifies delivery of a message to a recipient."
    risk_level = RiskLevel.MEDIUM
    input_schema = MessageSendInput

    def evaluate_preconditions(self, params: MessageSendInput, context: Dict[str, Any]) -> PreconditionResult:
        if not params.recipient or not params.recipient.strip():
            return PreconditionResult(passed=False, missing_requirements=["recipient"], reason="Recipient cannot be empty.")
        if not params.text or not params.text.strip():
            return PreconditionResult(passed=False, missing_requirements=["text"], reason="Message text cannot be empty.")
            
        return PreconditionResult(
            passed=True,
            resolved_context={"recipient": params.recipient.strip(), "text": params.text.strip(), "app": params.app_target}
        )

    def generate_plan(self, params: MessageSendInput, context: Dict[str, Any]) -> CapabilityPlan:
        steps = [
            ExecutionStep(
                action="OPEN_APP",
                target=params.app_target,
                desc=f"Open messaging app {params.app_target}",
                expected_package=params.app_target
            ),
            ExecutionStep(
                action="TAP",
                target="com.whatsapp:id/search",
                desc=f"Tap search to find {params.recipient}",
                expected_element=params.recipient
            ),
            ExecutionStep(
                action="TYPE",
                target="com.whatsapp:id/entry",
                value=params.text,
                desc=f"Type message: '{params.text}'",
                expected_element=params.text
            ),
            ExecutionStep(
                action="TAP",
                target="com.whatsapp:id/send",
                desc="Tap send button",
                expected_element=params.text  # Verified by message bubble presence
            )
        ]
        return CapabilityPlan(
            capability_name=self.name,
            risk_level=self.risk_level,
            steps=steps,
            requires_authorization=False,
            summary=f"Send message to {params.recipient}: '{params.text}'"
        )

    def verify_outcome(self, plan: CapabilityPlan, execution_results: List[Dict[str, Any]]) -> CapabilityOutcome:
        if not execution_results:
            return CapabilityOutcome(success=False, verified=False, reason="No execution steps recorded.")
            
        last_step = execution_results[-1]
        verified = last_step.get("status") == "VERIFIED" or last_step.get("success", False)
        
        return CapabilityOutcome(
            success=verified,
            verified=verified,
            reason="Message bubble verified on active chat screen." if verified else last_step.get("reason", "Failed to verify message send."),
            evidence={"last_observation": last_step.get("observation", {})}
        )

    def execute_native(self, params: MessageSendInput, tenant_id: str = "tenant_default") -> Dict[str, Any]:
        from ..first_party_services import messages_service
        return messages_service.send_message(tenant_id, params.recipient, params.text)
