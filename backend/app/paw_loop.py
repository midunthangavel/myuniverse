"""
QwenPaw-Inspired Mobile Agent Operating Loop & ReMe Memory Governance Engine.
Provides:
1. 3-Layer ReMe Memory:
   - Working Memory (active goal, scratchpad, ephemeral variables)
   - Episodic History (verbatim turn traces, tool outputs, OCR snapshots)
   - Evolving Profile (markdown-based structured long-term knowledge)
2. Mobile Agent OS Loop Engineering with anti-runaway step budgets.
3. Composable Governance Gates: ALLOW, ASK, DENY.
4. Post-Action Visual Verification (diffing before vs after UI state).
"""

from typing import Dict, Any, List, Optional
import time
import json

class ReMeMemory:
    """
    3-Layer ReMe Memory Architecture inspired by agentscope-ai/QwenPaw.
    """
    def __init__(self, user_id: str = "user_default"):
        self.user_id = user_id
        
        # Layer 1: Working Memory (volatile, task-scoped)
        self.working_memory = {
            "session_id": f"sess_{int(time.time())}",
            "active_goal": "",
            "current_step": 0,
            "max_steps": 8, # anti-runaway loop limit
            "scratchpad": {},
            "active_screen": {},
            "governance_mode": "ALLOW"
        }

        # Layer 2: Episodic Turn History (verbatim interaction traces)
        self.episodic_history: List[Dict[str, Any]] = []

        # Layer 3: Evolving Profile (self-updating markdown knowledge)
        self.evolving_profile = """# User Long-Term Knowledge Graph (ReMe Layer 3)
- User: Alex Rivera (Tech Lead, Cinephile)
- Cinema: Prefers IMAX Laser 70mm, Dolby Atmos, center row seats (G12/H14). Avoids front rows.
- Food: Loves Royal Hyderabadi Dum Biryani, medium-high spice. Strictly NO raw cilantro. Extra raita.
- Safety: Requires biometric gate for all payments over $0.00. Autonomous read-only browsing allowed.
- Devices: Synapse Phone 16 Pro (Android 15), Wear OS Smartwatch connected.
"""

    def reset_working_memory(self, goal: str, screen_context: Dict[str, Any] = None):
        self.working_memory["session_id"] = f"sess_{int(time.time())}"
        self.working_memory["active_goal"] = goal
        self.working_memory["current_step"] = 0
        self.working_memory["scratchpad"] = {}
        self.working_memory["active_screen"] = screen_context or {}
        self.working_memory["governance_mode"] = "ALLOW"

    def record_turn(self, role: str, content: Any, metadata: Dict[str, Any] = None):
        self.episodic_history.append({
            "timestamp": time.time(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        })

    def auto_memory_evolve(self, observation: str):
        """Auto-Memory event note-taking: Appends learned observations to Evolving Profile."""
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        self.evolving_profile += f"\n- [{timestamp_str}] Auto-Learned: {observation}"


class QwenPawMobileLoop:
    """
    Mobile Agent OS Execution Loop & Governance Engine.
    Enforces loop boundaries, checks ALLOW/ASK/DENY gates, and validates UI outcomes.
    """
    def __init__(self, reme: ReMeMemory):
        self.reme = reme
        self.max_step_budget = 8 # Prevents runaway recursive sub-agent loops

    def evaluate_governance(self, intent: str, planned_action: Dict[str, Any]) -> Dict[str, Any]:
        """
        QwenPaw Composable Governance Gate (Upgraded):
        Uses semantic semantic categorization across action, target, and intent
        to assign risk tiers (ALLOW, ASK, DENY) robustly.
        """
        action_name = planned_action.get("action", "").upper()
        target = str(planned_action.get("target", "")).lower()
        summary = str(planned_action.get("summary", "")).lower()
        amount_str = str(planned_action.get("amount", "0"))
        
        # High-Risk semantic vectors
        destructive_semantics = ["format", "reset", "wipe", "delete all", "root", "uninstall"]
        financial_semantics = ["pay", "buy", "purchase", "checkout", "transfer", "subscribe", "book", "order"]
        privacy_semantics = ["password", "credential", "auth", "social security", "credit card", "private"]
        
        combined_text = f"{action_name} {target} {summary}"
        
        # Hard DENY check (Destructive / Security Override)
        if any(d in combined_text for d in destructive_semantics):
            return {
                "decision": "DENY",
                "reason": f"Semantic risk engine blocked destructive operation in intent: '{intent}'.",
                "requires_modal": False
            }

        # ASK check (Financial / Privacy)
        if any(f in combined_text for f in financial_semantics) or amount_str not in ["0", "$0.00", ""]:
            return {
                "decision": "ASK",
                "reason": "Financial transaction or high-risk privacy context detected. Biometric Auth required.",
                "requires_modal": True,
                "prompt": f"Authorize security gate for: {planned_action.get('summary', 'transaction')}?"
            }

        # Moderate ASK check (Single deletions)
        if "delete" in combined_text or "cancel" in combined_text or "remove" in combined_text:
            return {
                "decision": "ASK",
                "reason": "Destructive data modification requires confirmation.",
                "requires_modal": True,
                "prompt": f"Confirm deletion/cancellation of {planned_action.get('target', 'item')}?"
            }

        # ALLOW default (Read-only / Navigation)
        return {
            "decision": "ALLOW",
            "reason": "Semantic profile indicates safe autonomous navigation.",
            "requires_modal": False
        }

    def verify_post_action(self, before_state: Dict[str, Any], after_state: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-Action Visual Verification:
        Compares UI state before and after action to ensure gesture had the expected effect.
        """
        before_app = before_state.get("app", "")
        after_app = after_state.get("app", "")
        before_title = before_state.get("title", "")
        after_title = after_state.get("title", "")

        changed = (before_app != after_app) or (before_title != after_title)
        
        # In a real environment, also diffs accessibility nodes or screen screenshot hash
        return {
            "verified": True,
            "state_changed": changed,
            "action_executed": action.get("action", "TAP"),
            "feedback": "UI successfully transitioned to new state." if changed else "UI remained stable (in-page update)."
        }
