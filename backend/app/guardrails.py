"""
Trust & Permission Guardrails Engine for Synapse AI Agent
Evaluates action risk tiers (Low, Medium, High) and delegates financial operations
to the cryptographic Financial Governance Gate (Module 2.4).
"""

from typing import Dict, Any, Tuple
from .financial_gate import financial_gate

class GuardrailsEngine:
    """Combines rule-based risk classification with cryptographic financial governance."""

    def __init__(self):
        self.financial_gate = financial_gate

    @staticmethod
    def evaluate_risk(intent: str, domain: str, parameters: Dict[str, Any]) -> Tuple[str, str]:
        """
        Returns (risk_tier, risk_reason)
        risk_tier: 'low' | 'medium' | 'high'
        """
        # High Risk: Financial Transactions & Irreversible Changes
        if intent in ["book_movie", "order_food", "transfer_money", "make_payment", "book_ride"]:
            cost = parameters.get("cost", "$0.00")
            return (
                "high",
                f"Financial transaction with payment amount ({cost}) requires explicit cryptographic authorization."
            )

        if intent in ["delete_data", "wipe_cache", "revoke_permissions"]:
            return (
                "high",
                "Irreversible deletion or system security change requires explicit confirmation."
            )

        # Medium Risk: Data Modifications & External Communications
        if intent in ["schedule_meeting", "send_message", "update_contact"]:
            return (
                "medium",
                "Modifying user calendar or personal data requires 1-tap user confirmation."
            )

        # Low Risk: Read-only, Local System & Safe Queries
        return (
            "low",
            "Read-only information retrieval or local device automation allows autonomous execution."
        )

    def evaluate_and_sign(self, task_id: str, intent: str, domain: str, parameters: Dict[str, Any], user_id: str = "user_default") -> Dict[str, Any]:
        risk_tier, reason = self.evaluate_risk(intent, domain, parameters)
        cost = parameters.get("cost", "$0.00")
        
        result = {
            "risk_tier": risk_tier,
            "reason": reason,
            "intent": intent,
            "cost": cost
        }

        if risk_tier == "high" and cost != "$0.00":
            gate_eval = self.financial_gate.evaluate_transaction(
                task_id=task_id,
                action=intent,
                amount=cost,
                user_id=user_id
            )
            result["financial_gate"] = gate_eval
            result["token"] = gate_eval["token"]
            result["requires_token_approval"] = True
        else:
            result["requires_token_approval"] = False

        return result
