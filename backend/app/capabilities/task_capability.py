from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .base import CapabilityContract, RiskLevel, PreconditionResult, CapabilityPlan, CapabilityOutcome, ExecutionStep

class TaskCreateInput(BaseModel):
    title: str = Field(description="Task description or title")
    priority: str = Field(default="medium", description="Priority level: low, medium, high")
    due_date: Optional[str] = Field(default=None, description="Due date or reminder time")

class TaskCreateCapability(CapabilityContract):
    name = "task.create"
    description = "Records and tracks a personal task or reminder item."
    risk_level = RiskLevel.MEDIUM
    input_schema = TaskCreateInput

    def evaluate_preconditions(self, params: TaskCreateInput, context: Dict[str, Any]) -> PreconditionResult:
        if not params.title or not params.title.strip():
            return PreconditionResult(passed=False, missing_requirements=["title"], reason="Task title cannot be empty.")
        return PreconditionResult(passed=True, resolved_context={"title": params.title.strip()})

    def generate_plan(self, params: TaskCreateInput, context: Dict[str, Any]) -> CapabilityPlan:
        steps = [
            ExecutionStep(
                action="OPEN_APP",
                target="com.google.android.apps.tasks",
                desc="Launch Google Tasks",
                expected_package="com.google.android.apps.tasks"
            ),
            ExecutionStep(
                action="TAP",
                target="add_task_fab",
                desc="Tap new task button",
                expected_element="New task"
            ),
            ExecutionStep(
                action="TYPE",
                target="task_title_input",
                value=params.title,
                desc=f"Type task title: '{params.title}'",
                expected_element=params.title
            ),
            ExecutionStep(
                action="TAP",
                target="save_task_btn",
                desc="Save task item",
                expected_element=params.title
            )
        ]
        return CapabilityPlan(
            capability_name=self.name,
            risk_level=self.risk_level,
            steps=steps,
            requires_authorization=False,
            summary=f"Create task '{params.title}'"
        )

    def verify_outcome(self, plan: CapabilityPlan, execution_results: List[Dict[str, Any]]) -> CapabilityOutcome:
        if not execution_results:
            return CapabilityOutcome(success=False, verified=False, reason="No execution steps.")
        last_step = execution_results[-1]
        verified = last_step.get("status") == "VERIFIED" or last_step.get("success", False)
        return CapabilityOutcome(
            success=verified,
            verified=verified,
            reason="Task verified in personal tasks list." if verified else "Failed to verify task entry.",
            evidence={"result": last_step}
        )

    def execute_native(self, params: TaskCreateInput, tenant_id: str = "tenant_default") -> Dict[str, Any]:
        from ..first_party_services import tasks_service
        return tasks_service.create_task(
            tenant_id=tenant_id,
            title=params.title,
            due_date=params.due_date or "",
            priority=params.priority
        )
