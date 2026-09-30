"""
Day-in-the-Life Showcase Driver for Synapse AI Agent
Provides a choreographed 12-step end-to-end automated demonstration
exercising all 7 integrated repositories and Phase 3 architectures.
"""

from typing import Dict, Any, List
import time

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
    """Manages playback of the 12-step showcase sequence."""

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


# Global showcase runner singleton
showcase_runner = ShowcaseRunner()
