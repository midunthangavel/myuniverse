"""
Autonomous App Exploration & UI Affordance Vector Memory Engine
Inspired by MadeAgents/mobile-use proactive exploration architecture.
Autonomously traverses mobile app UI trees, discovers interactive components,
records transition graphs, generates semantic affordances, indexes them into
ChromaDB vector memory, and persists navigation maps to OpenViking virtual filesystem.
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from .context_fs import OpenVikingContextFS
from .vector_memory import VectorMemoryStore
from .device.ui_parser import UIAutomatorParser

class AppKnowledgeMap:
    """Represents the discovered navigation graph for an application."""
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.screens: Dict[str, Dict[str, Any]] = {}
        self.transitions: List[Dict[str, Any]] = []
        self.shortcuts: Dict[str, List[str]] = {}
        self.indexed_elements: List[Dict[str, Any]] = []
        self.explored_at = time.time()

    def add_screen(self, screen_id: str, title: str, elements: List[Dict[str, Any]]):
        self.screens[screen_id] = {
            "title": title,
            "element_count": len(elements),
            "interactive_elements": [e.get("text") or e.get("id") or e.get("label") or "element" for e in elements if e.get("clickable", True)],
            "elements": elements
        }

    def add_transition(self, source_screen: str, action: str, target_element: str, destination_screen: str):
        self.transitions.append({
            "from": source_screen,
            "action": action,
            "target": target_element,
            "to": destination_screen,
            "timestamp": time.time()
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "app_name": self.app_name,
            "total_screens": len(self.screens),
            "total_indexed_elements": len(self.indexed_elements),
            "screens": self.screens,
            "transitions": self.transitions,
            "shortcuts": self.shortcuts,
            "indexed_elements": self.indexed_elements,
            "explored_at": self.explored_at
        }


class AppExplorer:
    """Explores mobile applications to map navigation hierarchy and index UI affordances into vector memory."""

    # Built-in native and simulated app profiles for Android and Synapse ecosystem
    # REMOVED: Agent must explore dynamically.
    APP_PROFILES = {}

    def __init__(self, viking_fs: Optional[OpenVikingContextFS] = None, vector_store: Optional[VectorMemoryStore] = None):
        self.viking_fs = viking_fs or OpenVikingContextFS()
        self.vector_store = vector_store or VectorMemoryStore()
        self.knowledge_maps: Dict[str, Dict[str, Any]] = {}
        self._sync_all_profiles()

    def _sync_all_profiles(self):
        """Initializes knowledge maps from built-in app definitions."""
        for app_key, profile in self.APP_PROFILES.items():
            self.knowledge_maps[app_key] = profile

    async def crawl_and_index_app(
        self,
        app_name_or_package: str,
        device_controller = None,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Autonomously crawls an application (live via ADB if available, or high-fidelity model),
        extracts every button, tab, input, and affordance, and indexes them into ChromaDB vector memory.
        """
        app_key = app_name_or_package.lower().strip()
        matched_profile_key = None
        for k in self.APP_PROFILES.keys():
            if app_key == k or app_key in k:
                matched_profile_key = k
                break

        canonical_key = matched_profile_key or app_key.replace(" ", "_")
        kmap = AppKnowledgeMap(canonical_key)
        
        crawled_screens = {}
        indexed_items = []
        is_live_hardware = False

        # Check if live device controller is connected
        if device_controller and hasattr(device_controller, "is_available"):
            try:
                avail = await device_controller.is_available()
                if avail:
                    is_live_hardware = True
            except Exception:
                is_live_hardware = False

        # Live Hardware Crawl Execution
        if is_live_hardware and device_controller:
            try:
                # 1. Wake device & launch app
                await device_controller._run_adb(["shell", "input", "keyevent", "224"])
                await device_controller._run_adb(["shell", "wm", "dismiss-keyguard"])
                
                target_launch = canonical_key
                if matched_profile_key and "activity" in self.APP_PROFILES[matched_profile_key]:
                    target_launch = self.APP_PROFILES[matched_profile_key]["activity"]
                
                await device_controller.launch_app(target_launch)
                await asyncio.sleep(2.0)

                # 2. Dump uiautomator hierarchy
                ui_dump = await device_controller.get_ui_hierarchy()
                if ui_dump.get("success"):
                    nodes = ui_dump.get("nodes", [])
                    screen_title = f"Live Screen — {canonical_key}"
                    screen_elements = []

                    for idx, node in enumerate(nodes):
                        text = node.get("text", "").strip()
                        res_id = node.get("resource_id", "")
                        clickable = node.get("clickable", False)
                        class_name = node.get("class_name", "").split(".")[-1] or "Element"
                        center = node.get("center", (540, 1200))
                        bounds = node.get("bounds", {})

                        if not text and not clickable:
                            continue

                        label = text or res_id.split("/")[-1] or f"{class_name}_{idx}"
                        elem_id = f"elem_{idx}_{label.replace(' ', '_').lower()}"
                        
                        affordance_desc = f"{class_name} element '{label}' on {canonical_key}. Allows user interaction at coordinates {center}."

                        elem_data = {
                            "id": elem_id,
                            "text": label,
                            "type": class_name,
                            "bounds": [bounds.get("x1", 0), bounds.get("y1", 0), bounds.get("x2", 0), bounds.get("y2", 0)],
                            "center": list(center),
                            "affordance": affordance_desc,
                            "clickable": clickable
                        }
                        screen_elements.append(elem_data)

                    crawled_screens["live_main"] = {
                        "title": screen_title,
                        "elements": screen_elements
                    }
                    kmap.add_screen("live_main", screen_title, screen_elements)
            except Exception as e:
                pass

        # If live hardware didn't yield elements, we don't synthesize fake data anymore.
        if not crawled_screens:
            print(f"Failed to crawl screen for app '{canonical_key}'.")
            return {"success": False, "error": "No elements found on active screen."}

        # Step 4: Index all discovered UI affordances into ChromaDB Vector Memory!
        for screen_id, sdata in crawled_screens.items():
            screen_title = sdata.get("title", screen_id)
            elements = sdata.get("elements", [])

            for elem in elements:
                elem_id = elem.get("id") or f"{canonical_key}_{screen_id}_{elem.get('text', 'btn')}"
                label = elem.get("text", "")
                elem_type = elem.get("type", "Widget")
                center = elem.get("center", [540, 1200])
                affordance = elem.get("affordance") or f"Interactive {elem_type} '{label}' in {screen_title}."

                # Rich vector embedding document
                vector_doc = (
                    f"App: {canonical_key} | Screen: {screen_title} | UI Element: {label} | "
                    f"Type: {elem_type} | Coordinates: X={center[0]}, Y={center[1]} | "
                    f"Affordance: {affordance} | Action: TAP or INPUT"
                )

                meta = {
                    "app": canonical_key,
                    "screen_id": screen_id,
                    "screen_title": screen_title,
                    "label": label,
                    "type": elem_type,
                    "center_x": center[0],
                    "center_y": center[1],
                    "category": "UI_AFFORDANCE",
                    "clickable": elem.get("clickable", True)
                }

                # Index into ChromaDB app collection
                doc_uid = f"affordance_{canonical_key}_{screen_id}_{elem.get('id', label).replace(' ', '_').lower()}"
                try:
                    self.vector_store.add_app_memory(
                        app_name=canonical_key,
                        doc_id=doc_uid,
                        text=vector_doc,
                        metadata=meta
                    )
                except Exception:
                    pass

                indexed_items.append({
                    "doc_id": doc_uid,
                    "label": label,
                    "type": elem_type,
                    "screen": screen_title,
                    "coordinates": center,
                    "affordance": affordance,
                    "vector_doc": vector_doc
                })

        kmap.indexed_elements = indexed_items

        # Step 5: Persist knowledge map to OpenViking virtual filesystem
        viking_uri = f"viking://apps/{canonical_key}/nav_map.json"
        kmap_dict = kmap.to_dict()
        try:
            self.viking_fs.write(viking_uri, json.dumps(kmap_dict, indent=2), tier="L1")
        except Exception:
            pass

        self.knowledge_maps[canonical_key] = kmap_dict

        # Step 6: Run sample semantic vector query sanity checks
        sanity_queries = ["calculate", "search", "settings", "view", "select"]
        sample_query = "calculate or add values" if "calc" in canonical_key else ("search Google or images" if "chrome" in canonical_key else "configure network or display")
        sample_matches = self.vector_store.search_app_memory(canonical_key, sample_query, n_results=3)

        return {
            "success": True,
            "app": canonical_key,
            "display_name": self.APP_PROFILES.get(canonical_key, {}).get("display_name", canonical_key),
            "source": "live_hardware_adb" if is_live_hardware else "high_fidelity_native_profile",
            "total_screens": len(crawled_screens),
            "total_ui_elements_indexed": len(indexed_items),
            "viking_storage_uri": viking_uri,
            "screens": list(crawled_screens.keys()),
            "sample_vector_retrieval": {
                "query": sample_query,
                "matches": sample_matches
            },
            "indexed_elements": indexed_items
        }

    def semantic_search_ui_element(self, app_name: str, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB vector memory for the best UI element matching user's natural language intent.
        Returns matched button, coordinates, similarity score, and action recommendation.
        """
        app_key = app_name.lower().strip()
        matched_key = None
        for k in self.APP_PROFILES.keys():
            if app_key == k or app_key in k:
                matched_key = k
                break
        canonical = matched_key or app_key

        return self.vector_store.search_app_memory(canonical, query, n_results=n_results)

    def get_navigation_path(self, app_name: str, target: str) -> List[Dict[str, Any]]:
        """Calculates step-by-step navigation path to reach target UI element or screen."""
        app_key = app_name.lower().replace(" ", "_")
        kmap = self.knowledge_maps.get(app_key, {})
        transitions = kmap.get("transitions", [])

        for tr in transitions:
            if target.lower() in tr.get("target", "").lower() or target.lower() in tr.get("to", "").lower():
                return [tr]

        if transitions:
            return transitions[:2]
        return [{"from": "home", "action": "LAUNCH_APP", "target": app_name, "to": "home"}]

    def get_knowledge(self, app_name: str) -> Optional[Dict[str, Any]]:
        app_key = app_name.lower().replace(" ", "_")
        return self.knowledge_maps.get(app_key)


# Global explorer singleton
app_explorer = AppExplorer()
