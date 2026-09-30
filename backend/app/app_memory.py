"""
App-Specific RAG Memory Engine for Synapse AI Agent
Inspired by MadeAgents color_mobile/memory.py and rag/main.py.
Maintains isolated, high-resolution vector collections per mobile application
storing successful action trajectories, navigation shortcuts, and UI element grounding caches.
"""

import time
import json
from typing import Dict, Any, List, Optional
from .vector_memory import VectorMemoryStore

class AppSpecificMemory:
    """Manages dedicated per-app semantic trajectory memory in ChromaDB."""

    BASELINE_SHORTCUTS = {
        "cinema": [
            {
                "shortcut_id": "cine_book_imax_f14",
                "task": "Book Interstellar 70mm IMAX center seats",
                "steps": [
                    {"action": "LAUNCH_APP", "target": "cinema"},
                    {"action": "TAP", "target": "Interstellar 70mm IMAX"},
                    {"action": "TAP", "target": "Row F14-F15"},
                    {"action": "TAP", "target": "Confirm Booking"}
                ],
                "confidence": 0.98,
                "usage_count": 8
            }
        ],
        "food": [
            {
                "shortcut_id": "bitego_veg_biryani_reorder",
                "task": "Order Special Veg Dum Biryani from Paradise",
                "steps": [
                    {"action": "LAUNCH_APP", "target": "food"},
                    {"action": "TAP", "target": "Paradise Dum Biryani"},
                    {"action": "TAP", "target": "Special Veg Dum Biryani"},
                    {"action": "TAP", "target": "Add to Cart"},
                    {"action": "TAP", "target": "Place Order"}
                ],
                "confidence": 0.96,
                "usage_count": 12
            }
        ],
        "pulse_ride": [
            {
                "shortcut_id": "pulse_ride_commute_work",
                "task": "Book Premier Ride to Tech Hub HQ",
                "steps": [
                    {"action": "LAUNCH_APP", "target": "pulse_ride"},
                    {"action": "TAP", "target": "Tech Hub HQ"},
                    {"action": "TAP", "target": "Premier"},
                    {"action": "TAP", "target": "Confirm PulseRide"}
                ],
                "confidence": 0.97,
                "usage_count": 15
            }
        ],
        "orbit_maps": [
            {
                "shortcut_id": "maps_morning_commute",
                "task": "Start GPS navigation to Office",
                "steps": [
                    {"action": "LAUNCH_APP", "target": "orbit_maps"},
                    {"action": "TAP", "target": "Commute to Office"}
                ],
                "confidence": 0.99,
                "usage_count": 22
            }
        ],
        "calendar": [
            {
                "shortcut_id": "cal_draft_sync",
                "task": "Draft meeting with John Vance",
                "steps": [
                    {"action": "LAUNCH_APP", "target": "calendar"},
                    {"action": "TAP", "target": "+ New Event"},
                    {"action": "INPUT_TEXT", "target": "Title", "text": "Sync with John Vance"},
                    {"action": "TAP", "target": "Save Event"}
                ],
                "confidence": 0.94,
                "usage_count": 6
            }
        ],
        "spark_mail": [
            {
                "shortcut_id": "mail_open_flight_itinerary",
                "task": "Check United Airlines flight UA 442 status",
                "steps": [
                    {"action": "LAUNCH_APP", "target": "spark_mail"},
                    {"action": "TAP", "target": "Flight Itinerary: UA 442"}
                ],
                "confidence": 0.98,
                "usage_count": 9
            }
        ]
    }

    def __init__(self, vector_store: Optional[VectorMemoryStore] = None):
        self.vector_store = vector_store or VectorMemoryStore()
        self.shortcuts: Dict[str, List[Dict[str, Any]]] = dict(self.BASELINE_SHORTCUTS)
        self._seed_baseline_trajectories()

    def _seed_baseline_trajectories(self):
        """Seeds baseline shortcuts into ChromaDB app collections."""
        try:
            for app, sc_list in self.shortcuts.items():
                for sc in sc_list:
                    steps_str = " -> ".join([f"{s['action']}({s.get('target', '')})" for s in sc["steps"]])
                    doc_text = f"Task: {sc['task']} | Workflow: {steps_str}"
                    self.vector_store.add_app_memory(
                        app_name=app,
                        doc_id=sc["shortcut_id"],
                        text=doc_text,
                        metadata={
                            "task": sc["task"],
                            "confidence": sc["confidence"],
                            "type": "shortcut",
                            "steps_json": json.dumps(sc["steps"])
                        }
                    )
        except Exception as e:
            print(f"App memory seeding notice: {e}")

    def record_successful_trajectory(
        self,
        app: str,
        task: str,
        steps: List[Dict[str, Any]],
        confidence: float = 0.95
    ) -> str:
        """Stores verified successful execution trajectory for future RAG recall."""
        app_key = app.lower().replace("-", "_").replace(" ", "_")
        doc_id = f"traj_{app_key}_{int(time.time())}"
        steps_str = " -> ".join([f"{s.get('action', 'ACT')}({s.get('target', '')})" for s in steps])
        doc_text = f"Task: {task} | Flow: {steps_str}"

        # 1. Update in-memory shortcuts
        if app_key not in self.shortcuts:
            self.shortcuts[app_key] = []
        
        self.shortcuts[app_key].append({
            "shortcut_id": doc_id,
            "task": task,
            "steps": steps,
            "confidence": confidence,
            "usage_count": 1
        })

        # 2. Add to ChromaDB App Collection
        self.vector_store.add_app_memory(
            app_name=app_key,
            doc_id=doc_id,
            text=doc_text,
            metadata={
                "task": task,
                "confidence": confidence,
                "type": "recorded_trajectory",
                "steps_json": json.dumps(steps)
            }
        )
        return doc_id

    def retrieve_similar_task(self, app: str, task_description: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Vector similarity search against past successful executions in this specific app."""
        app_key = app.lower().replace("-", "_").replace(" ", "_")
        matches = self.vector_store.search_app_memory(app_key, task_description, n_results=n_results)
        
        # Fallback to local shortcut list if vector search returns empty
        if not matches and app_key in self.shortcuts:
            for sc in self.shortcuts[app_key]:
                if any(w in sc["task"].lower() for w in task_description.lower().split()):
                    matches.append({
                        "text": f"Task: {sc['task']}",
                        "metadata": {"task": sc["task"], "steps_json": json.dumps(sc["steps"])},
                        "similarity": "95.0%",
                        "app": app_key
                    })
        return matches

    def get_app_shortcuts(self, app: str) -> List[Dict[str, Any]]:
        """Retrieves verified shortcuts for given application."""
        app_key = app.lower().replace("-", "_").replace(" ", "_")
        return self.shortcuts.get(app_key, [])

    def list_supported_apps(self) -> List[str]:
        return sorted(list(self.shortcuts.keys()))


# Global app memory singleton
app_specific_memory = AppSpecificMemory()
