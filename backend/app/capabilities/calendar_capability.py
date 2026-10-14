from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .base import CapabilityContract, RiskLevel, PreconditionResult, CapabilityPlan, CapabilityOutcome, ExecutionStep

class CalendarCreateInput(BaseModel):
    title: str = Field(description="Event summary/title")
    start_time: str = Field(description="Start time of event, e.g., 'tomorrow 3 PM' or '2026-10-13 15:00'")
    duration_min: int = Field(default=30, description="Duration in minutes")
    attendees: List[str] = Field(default_factory=list, description="List of participant names/emails")

class CalendarCreateCapability(CapabilityContract):
    name = "calendar.create"
    description = "Schedules and confirms a new event in the user's calendar."
    risk_level = RiskLevel.MEDIUM
    input_schema = CalendarCreateInput

    def evaluate_preconditions(self, params: CalendarCreateInput, context: Dict[str, Any]) -> PreconditionResult:
        if not params.title or not params.title.strip():
            return PreconditionResult(passed=False, missing_requirements=["title"], reason="Event title is required.")
        if not params.start_time or not params.start_time.strip():
            return PreconditionResult(passed=False, missing_requirements=["start_time"], reason="Event start time is required.")
            
        return PreconditionResult(
            passed=True,
            resolved_context={"title": params.title.strip(), "time": params.start_time.strip()}
        )

    def generate_plan(self, params: CalendarCreateInput, context: Dict[str, Any]) -> CapabilityPlan:
        steps = [
            ExecutionStep(
                action="OPEN_APP",
                target="com.google.android.calendar",
                desc="Launch Google Calendar",
                expected_package="com.google.android.calendar"
            ),
            ExecutionStep(
                action="TAP",
                target="com.google.android.calendar:id/floating_action_button",
                desc="Tap create new event FAB",
                expected_element="Add title"
            ),
            ExecutionStep(
                action="TYPE",
                target="com.google.android.calendar:id/title_edit_text",
                value=params.title,
                desc=f"Enter event title: {params.title}",
                expected_element=params.title
            ),
            ExecutionStep(
                action="TAP",
                target="com.google.android.calendar:id/save_button",
                desc="Tap save event",
                expected_element=params.title  # Event now appears on schedule view
            )
        ]
        return CapabilityPlan(
            capability_name=self.name,
            risk_level=self.risk_level,
            steps=steps,
            requires_authorization=False,
            summary=f"Schedule '{params.title}' for {params.start_time}"
        )

    def verify_outcome(self, plan: CapabilityPlan, execution_results: List[Dict[str, Any]]) -> CapabilityOutcome:
        if not execution_results:
            return CapabilityOutcome(success=False, verified=False, reason="No execution steps recorded.")
            
        last_step = execution_results[-1]
        verified = last_step.get("status") == "VERIFIED" or last_step.get("success", False)
        
        return CapabilityOutcome(
            success=verified,
            verified=verified,
            reason="Calendar event confirmed on schedule view." if verified else last_step.get("reason", "Event creation unverified."),
            evidence={"last_observation": last_step.get("observation", {})}
        )

    def execute_native(self, params: CalendarCreateInput, tenant_id: str = "tenant_default", idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        from ..first_party_services import calendar_service
        dur = getattr(params, "duration_min", 30)
        loc = getattr(params, "location", "")
        return calendar_service.create_event(
            tenant_id=tenant_id,
            title=params.title,
            start_time=params.start_time,
            duration_minutes=dur,
            location=loc,
            attendees=params.attendees,
            idempotency_key=idempotency_key
        )

    def verify_native(self, native_result: Dict[str, Any], tenant_id: str = "tenant_default") -> CapabilityOutcome:
        if not native_result.get("success"):
            return CapabilityOutcome(
                success=False,
                verified=False,
                reason=native_result.get("error", "Calendar creation failed"),
                evidence=native_result
            )
        ev = native_result.get("event", {})
        ev_id = ev.get("id")
        from ..first_party_services import calendar_service
        verified_ev = calendar_service.get_event(tenant_id, ev_id)
        if verified_ev and verified_ev["title"] == ev.get("title"):
            return CapabilityOutcome(
                success=True,
                verified=True,
                reason=f"Event '{ev.get('title')}' verified in durable SQLite storage at {ev.get('start_time')}.",
                evidence={"event": verified_ev}
            )
        return CapabilityOutcome(
            success=False,
            verified=False,
            reason="Event not found in persistent database after creation.",
            evidence=native_result
        )
