"""
Laya-Inspired System 1 Fast Decision Engine for Synapse AI.
Provides:
1. Non-autoregressive rapid single-pass intent classification (<15ms).
2. The 3 Laya Decision Primitives:
   - `choice`: Discrete domain/capability classification.
   - `score`: Calibrated confidence score (0.0 - 1.0).
   - `noul`: Out-of-distribution, injection, and safety filter.
3. Instant character micro-reaction & viking:// context pre-fetching suggestions.
"""

import time
import re
from typing import Dict, Any, List, Optional
import numpy as np

class LayaSystem1Classifier:
    """
    Sub-15ms System 1 Decision Engine inspired by receptron/laya.
    Bypasses heavy generative LLM token sampling for instant routing, risk scoring,
    and immediate character mood triggering.
    """
    def __init__(self):
        # Intent category archetypes with semantic token weights
        self.intent_archetypes = {
            "CINEMA_BOOKING": {
                "keywords": ["movie", "cinema", "ticket", "imax", "showtime", "seat", "theater", "dune", "oppenheimer", "film"],
                "target_app": "cinepass",
                "default_risk": "high", # financial booking
                "suggested_character_state": "WORKING",
                "viking_preload": [
                    "viking://user/habits/cinema.json",
                    "viking://resources/cinepass/schema.json",
                    "viking://skills/book_movie_imax.json"
                ]
            },
            "FOOD_ORDERING": {
                "keywords": ["food", "biryani", "order", "delivery", "dinner", "lunch", "eat", "restaurant", "burger", "pizza", "spice"],
                "target_app": "bitego",
                "default_risk": "high", # payment transaction
                "suggested_character_state": "WORKING",
                "viking_preload": [
                    "viking://user/habits/food.json",
                    "viking://resources/bitego/schema.json"
                ]
            },
            "SCREEN_INTERPRETATION": {
                "keywords": ["screen", "look", "see", "what is this", "read", "inspect", "app", "view", "window", "page", "active"],
                "target_app": "current",
                "default_risk": "low", # read-only
                "suggested_character_state": "SEARCHING",
                "viking_preload": [
                    "viking://user/profile.md"
                ]
            },
            "WEB_RESEARCH": {
                "keywords": ["search", "google", "web", "find out", "check price", "weather", "news", "reviews", "rating", "online"],
                "target_app": "browser",
                "default_risk": "low",
                "suggested_character_state": "SEARCHING",
                "viking_preload": [
                    "viking://user/profile.md"
                ]
            },
            "EMAIL_TRIAGE": {
                "keywords": ["email", "mail", "inbox", "spark", "unread", "reply", "draft", "meeting", "colleague", "boss"],
                "target_app": "mail",
                "default_risk": "medium",
                "suggested_character_state": "THINKING",
                "viking_preload": [
                    "viking://user/profile.md",
                    "viking://user/habits/commute.json"
                ]
            },
            "CASUAL_CHAT": {
                "keywords": ["hello", "hi", "hey", "who are you", "what can you do", "help", "thanks", "good morning", "synapse"],
                "target_app": "home",
                "default_risk": "low",
                "suggested_character_state": "SPEAKING",
                "viking_preload": [
                    "viking://user/profile.md"
                ]
            }
        }

        # Prompt injection & hazard patterns for Laya 'noul' gate
        self.injection_patterns = [
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"system\s*override",
            r"dump\s+database",
            r"format\s+drive",
            r"rm\s+-rf",
            r"transfer\s+all\s+funds",
            r"delete\s+all\s+contacts",
            r"export\s+private\s+keys"
        ]

    def classify_system1(self, user_prompt: str, active_app: str = "home") -> Dict[str, Any]:
        """
        Executes single-pass System 1 judgment in <15ms.
        Returns Laya primitives: `choice`, `score`, and `noul`.
        """
        start_time = time.perf_counter()
        p = user_prompt.lower().strip()

        # 1. Evaluate 'noul' primitive: Safety, Prompt Injection, Outlier detection
        noul_passed = True
        hazard_reason = None
        for pattern in self.injection_patterns:
            if re.search(pattern, p):
                noul_passed = False
                hazard_reason = f"Security hazard detected: matches pattern '{pattern}'"
                break

        # If noul fails, immediate safety clamp
        if not noul_passed:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "engine": "Laya System 1",
                "choice": "SECURITY_REJECTION",
                "score": 0.99,
                "noul": {
                    "is_safe": False,
                    "anomaly_flag": True,
                    "hazard_reason": hazard_reason,
                    "risk_tier": "critical"
                },
                "latency_ms": elapsed_ms,
                "action": "DENY",
                "suggested_character_state": "ERROR",
                "viking_preload": []
            }

        # 2. Score candidate intent archetypes
        scores = {}
        for intent_name, data in self.intent_archetypes.items():
            base_score = 0.05
            for kw in data["keywords"]:
                if kw in p:
                    base_score += 0.28
                elif any(word in kw for word in p.split()):
                    base_score += 0.12

            # Boost if currently active app aligns with intent
            if data["target_app"] == active_app:
                base_score += 0.15

            scores[intent_name] = min(base_score, 0.98)

        # Softmax normalization simulation
        raw_vals = np.array(list(scores.values()))
        exp_vals = np.exp(raw_vals * 3.0) # temperature scale
        probs = exp_vals / np.sum(exp_vals)

        sorted_indices = np.argsort(probs)[::-1]
        best_idx = sorted_indices[0]
        intent_names = list(scores.keys())
        top_choice = intent_names[best_idx]
        confidence_score = float(probs[best_idx])

        # If highest confidence is low, fallback to CASUAL_CHAT or WEB_RESEARCH
        if confidence_score < 0.28 and len(p.split()) > 3:
            top_choice = "WEB_RESEARCH"
            confidence_score = 0.55

        archetype = self.intent_archetypes.get(top_choice, self.intent_archetypes["CASUAL_CHAT"])

        # 3. Governance mapping (QwenPaw alignment)
        risk_tier = archetype["default_risk"]
        governance_action = "ALLOW"
        if risk_tier == "high":
            governance_action = "ASK"
        elif risk_tier == "medium":
            governance_action = "ASK"

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "engine": "Laya System 1 (Non-Autoregressive)",
            "choice": top_choice,
            "score": round(confidence_score, 3),
            "noul": {
                "is_safe": True,
                "anomaly_flag": False,
                "hazard_reason": None,
                "risk_tier": risk_tier
            },
            "governance_action": governance_action,
            "target_app": archetype["target_app"],
            "suggested_character_state": archetype["suggested_character_state"],
            "viking_preload": archetype["viking_preload"],
            "latency_ms": elapsed_ms
        }
