from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from .base import CapabilityContract, RiskLevel, PreconditionResult, CapabilityPlan, CapabilityOutcome, ExecutionStep

class FoodOrderInput(BaseModel):
    item: str = Field(description="Name of food item (e.g., 'Boneless Chicken Biryani')")
    restaurant: Optional[str] = Field(default=None, description="Preferred restaurant name")
    quantity: int = Field(default=1, description="Number of portions")
    max_price: Optional[float] = Field(default=None, description="Max allowed price in currency units")
    delivery_address: Optional[str] = Field(default=None, description="Delivery location override")

class FoodOrderCapability(CapabilityContract):
    name = "food.order"
    description = "Prepares and executes a food delivery order requiring user biometric confirmation."
    risk_level = RiskLevel.HIGH_FINANCIAL
    input_schema = FoodOrderInput

    def evaluate_preconditions(self, params: FoodOrderInput, context: Dict[str, Any]) -> PreconditionResult:
        if not params.item or not params.item.strip():
            return PreconditionResult(passed=False, missing_requirements=["item"], reason="Food item is required.")
            
        return PreconditionResult(
            passed=True,
            resolved_context={
                "item": params.item.strip(),
                "restaurant": params.restaurant or "Meghana Foods (Usual)",
                "quantity": params.quantity,
                "estimated_price": "₹450.00"
            }
        )

    def generate_plan(self, params: FoodOrderInput, context: Dict[str, Any]) -> CapabilityPlan:
        rest = params.restaurant or "Meghana Foods"
        steps = [
            ExecutionStep(
                action="OPEN_APP",
                target="in.swiggy.android",
                desc=f"Launch food delivery app for {rest}",
                expected_package="in.swiggy.android"
            ),
            ExecutionStep(
                action="TAP",
                target="search_bar",
                desc=f"Search for '{rest}'",
                expected_element=rest
            ),
            ExecutionStep(
                action="TAP",
                target="add_item_btn",
                desc=f"Add {params.quantity}x {params.item} to cart",
                expected_element="Cart"
            ),
            ExecutionStep(
                action="TAP",
                target="view_cart_btn",
                desc="Proceed to checkout cart",
                expected_element="Proceed to Pay"
            ),
            ExecutionStep(
                action="TAP",
                target="confirm_order_btn",
                desc="Authorize and commit order",
                expected_element="Order Placed"
            )
        ]
        return CapabilityPlan(
            capability_name=self.name,
            risk_level=self.risk_level,
            steps=steps,
            requires_authorization=True,
            authorization_amount="₹450.00",
            summary=f"Order {params.quantity}x {params.item} from {rest} (Total: ₹450.00)"
        )

    def verify_outcome(self, plan: CapabilityPlan, execution_results: List[Dict[str, Any]]) -> CapabilityOutcome:
        if not execution_results:
            return CapabilityOutcome(success=False, verified=False, reason="No execution steps recorded.")
            
        last_step = execution_results[-1]
        verified = last_step.get("status") == "VERIFIED" or last_step.get("success", False)
        
        return CapabilityOutcome(
            success=verified,
            verified=verified,
            reason="Order successfully placed and verified on confirmation screen." if verified else last_step.get("reason", "Order placement could not be verified."),
            evidence={"last_observation": last_step.get("observation", {})}
        )

    def execute_native(self, params: FoodOrderInput, tenant_id: str = "tenant_default", idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        from ..first_party_services import food_service
        food_service.clear_cart(tenant_id)
        food_service.add_to_cart(tenant_id, params.item, params.quantity)
        rest_name = params.restaurant or "Sushi Zen"
        return food_service.checkout(
            tenant_id=tenant_id,
            address=params.delivery_address or "742 Evergreen Terrace",
            restaurant_name=rest_name,
            idempotency_key=idempotency_key
        )

    def verify_native(self, native_result: Dict[str, Any], tenant_id: str = "tenant_default") -> CapabilityOutcome:
        if not native_result.get("success"):
            return CapabilityOutcome(
                success=False,
                verified=False,
                reason=native_result.get("error", "Food order failed"),
                evidence=native_result
            )
        order = native_result.get("order", {})
        ord_id = order.get("order_id")
        from ..first_party_services import food_service
        orders = food_service.list_orders(tenant_id)
        matched = next((o for o in orders if o["order_id"] == ord_id), None)
        if matched and matched["status"] == "CONFIRMED":
            return CapabilityOutcome(
                success=True,
                verified=True,
                reason=f"Order '{ord_id}' confirmed in durable SQLite storage for {matched.get('restaurant_name')} (Total: ${matched.get('total')}).",
                evidence={"order": matched}
            )
        return CapabilityOutcome(
            success=False,
            verified=False,
            reason="Order not found in persistent database after checkout.",
            evidence=native_result
        )
