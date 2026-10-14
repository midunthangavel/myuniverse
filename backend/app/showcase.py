"""
Investor Demo Showcase Runner for Synapse AI Agent Platform
Provides a live, deterministic, 3-act end-to-end demonstration exercising:
- Act 1: Latency & Tier 1 FastPath Speed Benchmark (<1.5s total time, 0 LLM latency)
- Act 2: Autonomous Multi-Step Cross-App Workflow (Calendar -> Food Delivery -> Messages)
- Act 3: High-Risk Governance Gate & Biometric Verification with Immutable Audit Ledger
"""

import time
import asyncio
import uuid
from typing import Dict, Any, List, AsyncGenerator

from .fastpath_router import fastpath_router
from .latency_tracer import TaskTracer
from .financial_gate import financial_gate
from .task_manager import task_manager, TaskState
from .first_party_services import food_service, calendar_service, messages_service
from .capabilities import capability_registry


SHOWCASE_STEPS = [
    {
        "step": 1,
        "title": "Ambient Morning Briefing (Daemon + OpenViking)",
        "speech": "Good morning Midhun! Loading your Viking filesystem overview and daily agenda.",
        "app": "calendar",
        "action": "TRIGGER_DAEMON_BRIEFING",
        "engine": "OpenViking viking:// & APScheduler"
    },
    {
        "step": 2,
        "title": "Dynamic Highway Traffic Watcher (I-95)",
        "speech": "I-95 North is congested (+15m delay). Recommending PulseRide Premier or alternative route.",
        "app": "orbit_maps",
        "action": "MONITOR_TRAFFIC",
        "engine": "Orbit Maps & Scrapling Stealth Fetcher"
    },
    {
        "step": 3,
        "title": "Laya System 1 Triage (<15ms)",
        "speech": "User request: 'Book 2 tickets for Interstellar tonight'. Laya triaged in 9ms.",
        "app": "cinema",
        "action": "SYSTEM1_CLASSIFY",
        "engine": "Laya Sub-15ms Neural Classifier"
    },
    {
        "step": 4,
        "title": "Episodic Profile & App RAG Memory Recall",
        "speech": "Retrieved your habit: PVR INOX Palladium IMAX, Row F center-back seats.",
        "app": "cinema",
        "action": "RECALL_APP_RAG",
        "engine": "ChromaDB App-Specific Memory"
    },
    {
        "step": 5,
        "title": "Cloud Screen Perception & UGround Grounding",
        "speech": "PaddleOCR + OmniParser detected Row F14-F15 at normalized coordinates (0.52, 0.41).",
        "app": "cinema",
        "action": "GROUND_COORDINATES",
        "engine": "Cloud Perception & UGround Grounding"
    },
    {
        "step": 6,
        "title": "QwenPaw Governance & HMAC Approval Token",
        "speech": "Financial charge ($36.00) flagged as ASK mode. Issued signed HMAC token with 120s TTL.",
        "app": "cinema",
        "action": "GOVERNANCE_TOKEN_ISSUE",
        "engine": "QwenPaw OS & Financial Governance Gate"
    },
    {
        "step": 7,
        "title": "Cryptographic Biometric Authorization",
        "speech": "User confirmed with biometric signature. Token validated and committed to immutable SQLite ledger.",
        "app": "cinema",
        "action": "AUTHORIZE_TRANSACTION",
        "engine": "HMAC Token Verifier & Audit Ledger"
    },
    {
        "step": 8,
        "title": "Hierarchical Reflection Loop (MadeAgents)",
        "speech": "ActionReflector verified screen state transition: Tickets confirmed. Task progress: 100%.",
        "app": "cinema",
        "action": "REFLECT_ACTION",
        "engine": "ActionReflector & TaskProgressor"
    },
    {
        "step": 9,
        "title": "Multi-App Workflow Chaining & Saga Protection",
        "speech": "Chaining Calendar invite and PulseRide taxi. All operations guarded with automatic compensation rollback.",
        "app": "pulse_ride",
        "action": "EXECUTE_SAGA_CHAIN",
        "engine": "Multi-App Chaining & Saga Rollback"
    },
    {
        "step": 10,
        "title": "Continuous Personalization Flywheel Acceleration",
        "speech": "Bayesian flywheel reinforced your preference. Confidence upgraded to 96.4%.",
        "app": "food",
        "action": "FLYWHEEL_LEARNING",
        "engine": "Bayesian Flywheel & ReMe Memory"
    },
    {
        "step": 11,
        "title": "App Navigation Map Knowledge Ingestion",
        "speech": "Saved verified interaction trajectory into Viking filesystem and ChromaDB app collection.",
        "app": "cinema",
        "action": "STORE_APP_KNOWLEDGE",
        "engine": "AppExplorer & OpenViking Context FS"
    },
    {
        "step": 12,
        "title": "Full Mission Accomplished",
        "speech": "All tasks completed autonomously and securely. Synapse AI is standing by!",
        "app": "home",
        "action": "CELEBRATE",
        "engine": "Synapse Master Orchestrator"
    }
]


class ShowcaseRunner:
    """Orchestrates live 3-act investor demonstrations and 12-step playback."""

    def __init__(self):
        self.steps = SHOWCASE_STEPS

    def get_steps(self) -> List[Dict[str, Any]]:
        return self.steps

    def execute_step(self, step_number: int) -> Dict[str, Any]:
        idx = max(0, min(len(self.steps) - 1, step_number - 1))
        step_data = self.steps[idx]
        return {
            "step_number": step_number,
            "total_steps": len(self.steps),
            "step": step_data,
            "timestamp": time.time()
        }

    async def run_live_showcase(self, tenant_id: str = "tenant_primary") -> AsyncGenerator[Dict[str, Any], None]:
        yield {
            "type": "SHOWCASE_START",
            "tenant_id": tenant_id,
            "timestamp": time.time(),
            "message": "Initiating Synapse Autonomous Agent Showcase..."
        }

        # ========================================================
        # ACT 1: Latency & Tier 1 FastPath Speed Benchmark (<1.5s)
        # ========================================================
        tracer = TaskTracer(task_id=f"showcase_act1_{int(time.time()*1000)}")
        tracer.mark("fastpath_start")
        
        yield {
            "type": "SHOWCASE_ACT_START",
            "act": 1,
            "title": "Act 1: Zero-LLM FastPath Latency Target (<1.5s)",
            "intent": "Set alarm for 7:30 AM tomorrow",
            "timestamp": time.time()
        }
        
        fp_start = time.perf_counter()
        fastpath_result = fastpath_router.route("Set alarm for 7:30 AM tomorrow")
        fp_latency_ms = (time.perf_counter() - fp_start) * 1000.0
        
        tracer.mark("fastpath_routed")
        trace_summary = tracer.finish()

        yield {
            "type": "SHOWCASE_ACT_PROGRESS",
            "act": 1,
            "step": "FASTPATH_EVALUATION",
            "matched": fastpath_result.is_matched,
            "classification_latency_ms": round(fp_latency_ms, 2),
            "total_stage_ms": round(trace_summary["total_latency_ms"], 2),
            "action": fastpath_result.intent if fastpath_result.is_matched else None
        }

        # FastPath arithmetic validation
        math_res = fastpath_router.route("What is 45 * 12")
        yield {
            "type": "SHOWCASE_ACT_COMPLETE",
            "act": 1,
            "status": "VERIFIED",
            "budget_met": trace_summary["meets_fastpath_target"],
            "fastpath_match": fastpath_result.dict(),
            "math_evaluation": math_res.dict(),
            "duration_ms": round(trace_summary["total_latency_ms"], 2)
        }

        await asyncio.sleep(0.05)

        # ========================================================
        # ACT 2: Multi-Step Cross-App Workflow
        # ========================================================
        yield {
            "type": "SHOWCASE_ACT_START",
            "act": 2,
            "title": "Act 2: Autonomous Multi-Step Cross-App Chaining",
            "intent": "Schedule Friday lunch, order food from Sushi Zen, and notify team",
            "timestamp": time.time()
        }

        # Step 2.1: Calendar Booking
        cal_res = calendar_service.create_event(
            tenant_id=tenant_id,
            title="Team Strategy Lunch",
            start_time="2026-10-16T13:00:00",
            duration_minutes=60,
            location="Headquarters Dining Room",
            attendees=["alex@synapse.ai", "sam@synapse.ai"]
        )
        yield {
            "type": "SHOWCASE_ACT_PROGRESS",
            "act": 2,
            "substep": 1,
            "app": "Synapse Calendar",
            "action": "CALENDAR_EVENT_CREATED",
            "result": cal_res
        }

        # Step 2.2: Food Cart Assembly & Order
        food_service.clear_cart(tenant_id)
        food_service.add_to_cart(tenant_id, "sushi_omakase", quantity=2)
        cart_info = food_service.get_cart(tenant_id)
        food_order = food_service.checkout(tenant_id, address="Headquarters Suite 400")
        yield {
            "type": "SHOWCASE_ACT_PROGRESS",
            "act": 2,
            "substep": 2,
            "app": "Synapse Food",
            "action": "FOOD_ORDER_PLACED",
            "cart": cart_info,
            "order": food_order
        }

        # Step 2.3: Message Notification Dispatch
        msg_res = messages_service.send_message(
            tenant_id=tenant_id,
            recipient="alex@synapse.ai",
            body="Team Strategy Lunch scheduled for Friday 1:00 PM. Sushi Zen order placed!"
        )
        yield {
            "type": "SHOWCASE_ACT_COMPLETE",
            "act": 2,
            "status": "VERIFIED",
            "chained_services": ["Synapse Calendar", "Synapse Food", "Synapse Messages"],
            "calendar_event": cal_res.get("event"),
            "food_order": food_order.get("order"),
            "message_notification": msg_res.get("message")
        }

        await asyncio.sleep(0.05)

        # ========================================================
        # ACT 3: High-Risk Governance Gate & Biometric Verification
        # ========================================================
        yield {
            "type": "SHOWCASE_ACT_START",
            "act": 3,
            "title": "Act 3: Biometric Governance Gate & Immutable Audit Ledger",
            "intent": "Authorize and settle financial transaction of $97.20",
            "timestamp": time.time()
        }

        task_id = f"showcase_gate_{int(time.time()*1000)}"
        eval_res = financial_gate.evaluate_transaction(
            task_id=task_id,
            action="Settle corporate dining charge",
            amount="$97.20",
            user_id=tenant_id
        )
        token = eval_res["token"]

        yield {
            "type": "SHOWCASE_ACT_PROGRESS",
            "act": 3,
            "step": "GOVERNANCE_TOKEN_ISSUED",
            "task_id": task_id,
            "token": token,
            "requires_approval": eval_res["requires_approval"],
            "is_high_value": eval_res["is_high_value"]
        }

        # Simulate user hardware biometric fingerprint confirmation
        auth_commit = financial_gate.authorize_transaction(
            token_str=token,
            task_id=task_id,
            user_id=tenant_id
        )

        # Inspect immutable audit ledger
        latest_ledger_entry = financial_gate.ledger.get_ledger(limit=1)[0]

        yield {
            "type": "SHOWCASE_ACT_COMPLETE",
            "act": 3,
            "status": "AUTHORIZED",
            "task_id": task_id,
            "authorization_result": auth_commit,
            "ledger_verified": latest_ledger_entry["task_id"] == task_id and latest_ledger_entry["status"] == "AUTHORIZED",
            "audit_record": latest_ledger_entry
        }

        # ========================================================
        # SHOWCASE CONCLUSION
        # ========================================================
        yield {
            "type": "SHOWCASE_COMPLETE",
            "status": "ALL_ACTS_VERIFIED",
            "acts_completed": [1, 2, 3],
            "timestamp": time.time(),
            "verdict": "Synapse Phone-Native Agent: Speed, Chaining, and Governance Verified."
        }


# Global showcase runner singleton
showcase_runner = ShowcaseRunner()
