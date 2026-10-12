import re
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class FastPathResult(BaseModel):
    is_matched: bool
    tier: str = "TIER_1_FASTPATH"
    intent: str = ""
    direct_speech: Optional[str] = None
    direct_plan: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0

class FastPathRouter:
    """
    Tier 1 Deterministic FastPath Router.
    Bypasses general-purpose generative LLM inference for obvious deterministic actions:
    - Native alarms & clocks (<1.5s target)
    - Hardware gestures (BACK, HOME, RECENTS)
    - Direct app launches (Calculator, Chrome, WhatsApp, Maps)
    - Safe mathematical arithmetic calculations
    """
    def __init__(self):
        # Known common package maps
        self.app_package_map = {
            "calculator": "com.google.android.calculator",
            "chrome": "com.android.chrome",
            "browser": "com.android.chrome",
            "maps": "com.google.android.apps.maps",
            "whatsapp": "com.whatsapp",
            "messages": "com.google.android.apps.messaging",
            "calendar": "com.google.android.calendar",
            "settings": "com.android.settings",
            "youtube": "com.google.android.youtube",
            "camera": "com.google.android.GoogleCamera",
            "clock": "com.google.android.deskclock"
        }

    def route(self, prompt: str) -> FastPathResult:
        t0 = time.perf_counter()
        p = prompt.strip()
        p_lower = p.lower()

        # 1. Global Hardware Gestures
        if p_lower in ["back", "go back", "press back", "previous"]:
            lat = round((time.perf_counter() - t0) * 1000, 2)
            return FastPathResult(
                is_matched=True,
                intent="GLOBAL_BACK",
                direct_speech="Going back.",
                direct_plan={
                    "intent": "global_back",
                    "summary": "Navigate back",
                    "steps": [{"action": "GLOBAL_ACTION", "target": "BACK", "desc": "Navigate Back"}]
                },
                latency_ms=lat
            )

        if p_lower in ["home", "go home", "press home", "desktop"]:
            lat = round((time.perf_counter() - t0) * 1000, 2)
            return FastPathResult(
                is_matched=True,
                intent="GLOBAL_HOME",
                direct_speech="Returning to home screen.",
                direct_plan={
                    "intent": "global_home",
                    "summary": "Navigate home",
                    "steps": [{"action": "GLOBAL_ACTION", "target": "HOME", "desc": "Press Home button"}]
                },
                latency_ms=lat
            )

        # 2. Simple Arithmetic / Calculation
        calc_match = re.search(r"^(?:calculate|what is|compute)\s+([0-9\s\+\-\*\/\.\(\)]+)$", p_lower)
        if calc_match:
            expr = calc_match.group(1).strip()
            try:
                # Safe eval of numbers and standard operators only
                if re.match(r"^[0-9\s\+\-\*\/\.\(\)]+$", expr):
                    result_val = eval(expr, {"__builtins__": {}}, {})
                    lat = round((time.perf_counter() - t0) * 1000, 2)
                    return FastPathResult(
                        is_matched=True,
                        intent="CALCULATE",
                        direct_speech=f"The answer is {result_val}.",
                        direct_plan={
                            "intent": "calculate",
                            "summary": f"Calculate {expr} = {result_val}",
                            "steps": [{"action": "EXPLAIN_RESULT", "target": str(result_val), "desc": f"Result: {result_val}"}]
                        },
                        latency_ms=lat
                    )
            except Exception:
                pass

        # 3. Direct App Launch (Open / Launch X)
        open_match = re.search(r"^(?:open|launch|start)\s+([a-zA-Z0-9\s]+)$", p_lower)
        if open_match:
            app_name = open_match.group(1).strip()
            pkg = self.app_package_map.get(app_name) or self.app_package_map.get(app_name.replace(" ", ""))
            if pkg:
                lat = round((time.perf_counter() - t0) * 1000, 2)
                return FastPathResult(
                    is_matched=True,
                    intent="OPEN_APP",
                    direct_speech=f"Opening {app_name}.",
                    direct_plan={
                        "intent": "open_app",
                        "summary": f"Open {app_name}",
                        "steps": [{
                            "action": "OPEN_APP",
                            "target": pkg,
                            "desc": f"Launch {app_name}",
                            "expected_package": pkg
                        }]
                    },
                    latency_ms=lat
                )

        # 4. Deterministic Alarm Setter
        alarm_match = re.search(r"(?:set\s+(?:an\s+)?alarm\s+(?:for\s+)?|wake\s+me\s+up\s+at\s+)([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?)", p_lower)
        if alarm_match:
            time_str = alarm_match.group(1).strip()
            lat = round((time.perf_counter() - t0) * 1000, 2)
            return FastPathResult(
                is_matched=True,
                intent="SET_ALARM",
                direct_speech=f"Alarm scheduled for {time_str}.",
                direct_plan={
                    "intent": "set_alarm",
                    "summary": f"Set alarm for {time_str}",
                    "steps": [{
                        "action": "OPEN_APP",
                        "target": "com.google.android.deskclock",
                        "desc": f"Set clock alarm for {time_str}",
                        "expected_package": "com.google.android.deskclock"
                    }]
                },
                latency_ms=lat
            )

        # No deterministic FastPath match -> Fall through to Standard Tier 2
        lat = round((time.perf_counter() - t0) * 1000, 2)
        return FastPathResult(is_matched=False, latency_ms=lat)

fastpath_router = FastPathRouter()
