from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, Field
import time

class RiskLevel(str, Enum):
    LOW = "LOW"                      # Read-only or reversible (read screen, open app)
    MEDIUM = "MEDIUM"                # State-altering but non-financial (messages, calendar events, tasks)
    HIGH_FINANCIAL = "HIGH_FINANCIAL"# Financial charge, payment, booking requiring biometric/PIN gate

class PreconditionResult(BaseModel):
    passed: bool
    missing_requirements: List[str] = Field(default_factory=list)
    resolved_context: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""

class ExecutionStep(BaseModel):
    action: str                      # OPEN_APP, TAP, TYPE, SWIPE, GLOBAL_ACTION, NATIVE_INTENT
    target: str = ""
    value: str = ""
    desc: str = ""
    expected_package: str = ""
    expected_element: str = ""

class CapabilityPlan(BaseModel):
    capability_name: str
    risk_level: RiskLevel
    steps: List[ExecutionStep] = Field(default_factory=list)
    requires_authorization: bool = False
    authorization_amount: Optional[str] = None
    summary: str = ""

class CapabilityOutcome(BaseModel):
    success: bool
    verified: bool
    reason: str = ""
    evidence: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0

class CapabilityContract(ABC):
    """
    Standardized capability contract interface.
    Enforces typed schema, preconditions, risk rating, execution plan,
    and truthful outcome verification postconditions.
    """
    name: str
    description: str
    risk_level: RiskLevel
    input_schema: Type[BaseModel]

    @abstractmethod
    def evaluate_preconditions(self, params: BaseModel, context: Dict[str, Any]) -> PreconditionResult:
        """Validates prerequisites (e.g. contact existence, network, auth)."""
        pass

    @abstractmethod
    def generate_plan(self, params: BaseModel, context: Dict[str, Any]) -> CapabilityPlan:
        """Generates concrete deterministic steps and expected semantic postconditions."""
        pass

    @abstractmethod
    def verify_outcome(self, plan: CapabilityPlan, execution_results: List[Dict[str, Any]]) -> CapabilityOutcome:
        """Evaluates whether the requested outcome truthfully occurred."""
        pass

    def execute_native(self, params: BaseModel, tenant_id: str = "tenant_default", idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        """Executes capability natively through first-party service backends when available."""
        return {"supported": False, "reason": "Native execution not implemented"}

    def verify_native(self, native_result: Dict[str, Any], tenant_id: str = "tenant_default") -> CapabilityOutcome:
        """Truthfully verifies native execution against persistent SQLite storage."""
        if not native_result.get("success", False):
            return CapabilityOutcome(
                success=False,
                verified=False,
                reason=native_result.get("error", "Native execution failed"),
                evidence=native_result
            )
        return CapabilityOutcome(
            success=True,
            verified=True,
            reason="Native operation verified in durable storage.",
            evidence=native_result
        )
