"""
Synapse AI — Android Grounding Engine
Decouples LLM semantic planning from physical Android coordinates.
Translates high-level intent (e.g. target="Search" or "Clear") into ranked UI candidate elements
using multi-factor scoring (Text Match, Semantic Overlap, Role Ontology, Clickability, Confidence).
The LLM handles reasoning; the Grounding Engine handles physical coordinate resolution.
"""

from typing import Dict, Any, List, Optional, Tuple
from .state_engine import AndroidScreenState, AndroidUIElement

class GroundingCandidate:
    def __init__(self, element: AndroidUIElement, total_score: float, breakdown: Dict[str, float]):
        self.element = element
        self.total_score = total_score
        self.breakdown = breakdown

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.element.node_id,
            "label": self.element.label,
            "role": self.element.role,
            "center": list(self.element.center),
            "bounds": self.element.bounds,
            "total_score": round(self.total_score, 3),
            "score_breakdown": {k: round(v, 2) for k, v in self.breakdown.items()}
        }

class GroundingResult:
    def __init__(
        self,
        query: str,
        best_candidate: Optional[GroundingCandidate],
        all_candidates: List[GroundingCandidate]
    ):
        self.query = query
        self.best_candidate = best_candidate
        self.all_candidates = all_candidates

    @property
    def success(self) -> bool:
        return self.best_candidate is not None and self.best_candidate.total_score >= 0.40

    @property
    def target_coordinates(self) -> Tuple[int, int]:
        if self.best_candidate:
            return self.best_candidate.element.center
        return (540, 1200)

    @property
    def confidence(self) -> float:
        return self.best_candidate.total_score if self.best_candidate else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "success": self.success,
            "confidence": round(self.confidence, 3),
            "target_coordinates": list(self.target_coordinates),
            "matched_element": self.best_candidate.to_dict() if self.best_candidate else None,
            "top_candidates": [c.to_dict() for c in self.all_candidates[:3]]
        }


class AndroidGroundingEngine:
    """Evaluates and ranks candidate UI elements for any natural language target."""

    SYNONYM_MAP = {
        "+": ["add", "addition", "plus", "sum"],
        "-": ["subtract", "subtraction", "minus", "difference"],
        "×": ["multiply", "multiplication", "times", "product", "*"],
        "÷": ["divide", "division", "slash", "by", "/"],
        "=": ["equal", "equals", "calculate", "result", "solve", "evaluate"],
        "c": ["clear", "reset", "all clear", "ac"],
        "⌫": ["backspace", "delete", "del", "remove"],
        "search": ["find", "lookup", "query", "explore"],
        "voice search": ["mic", "microphone", "speak", "voice"],
        "images": ["photos", "pictures", "gallery", "image"],
        "wi-fi": ["wifi", "wireless", "internet", "network", "ssid"],
        "display": ["brightness", "dark mode", "light mode", "screen", "theme"],
        "about phone": ["specs", "model", "storage", "device info"]
    }

    @classmethod
    def _text_match_score(cls, query: str, text: str, content_desc: str, res_id: str) -> float:
        q = query.lower().strip()
        t = text.lower().strip()
        c = content_desc.lower().strip()
        r = res_id.lower().split("/")[-1] if res_id else ""

        # Exact match
        if q == t or q == c:
            return 1.0

        # Concept Alias / Synonym matching
        for key, syns in cls.SYNONYM_MAP.items():
            if t == key or c == key or r == key:
                if any(syn in q for syn in syns):
                    return 0.95
            if q == key and any(syn in (t + " " + c) for syn in syns):
                return 0.95

        # Clean label match (e.g. "+" or "search")
        if (len(q) > 1 and q in t) or (len(q) > 1 and q in c) or (len(q) > 1 and q in r):
            return 0.85
        if t in q and len(t) > 1:
            return 0.75
        
        # Word overlap Jaccard
        q_words = set(q.split())
        target_words = set((t + " " + c + " " + r).split())
        if not target_words or not q_words:
            return 0.0
        overlap = q_words.intersection(target_words)
        return len(overlap) / len(q_words.union(target_words))

    @staticmethod
    def _role_match_score(query: str, role: str) -> float:
        q = query.lower()
        role = role.upper()
        if "button" in q and "BUTTON" in role:
            return 0.25
        if ("search" in q or "find" in q) and role == "SEARCH":
            return 0.30
        if ("tab" in q or "switch" in q) and role == "TAB":
            return 0.25
        if ("type" in q or "input" in q or "text" in q) and role == "TEXT_FIELD":
            return 0.30
        if ("clear" in q or "cancel" in q) and role == "CANCEL":
            return 0.30
        if ("confirm" in q or "equal" in q or "=" in q) and role == "CONFIRM":
            return 0.30
        return 0.0

    def ground_target(
        self,
        screen_state: AndroidScreenState,
        target_query: str,
        expected_role: Optional[str] = None
    ) -> GroundingResult:
        """
        Ranks all elements on screen against target_query.
        Returns the top-scoring candidate with physical touch coordinates.
        """
        scored_candidates: List[GroundingCandidate] = []

        for elem in screen_state.elements:
            text_score = self._text_match_score(target_query, elem.text, elem.content_desc, elem.resource_id)
            role_score = self._role_match_score(target_query, elem.role)
            clickable_boost = 0.15 if elem.clickable else 0.0
            confidence_weight = elem.confidence * 0.10

            # Compute combined multi-factor score (Normalized to ~1.0)
            total = (text_score * 0.60) + role_score + clickable_boost + confidence_weight
            
            # Additional penalty if expected role specified and mismatched
            if expected_role and elem.role.upper() != expected_role.upper():
                total *= 0.6

            breakdown = {
                "text_match": text_score * 0.60,
                "role_match": role_score,
                "clickable_boost": clickable_boost,
                "confidence_weight": confidence_weight
            }

            candidate = GroundingCandidate(elem, min(1.0, total), breakdown)
            scored_candidates.append(candidate)

        # Sort descending by total score
        scored_candidates.sort(key=lambda c: c.total_score, reverse=True)

        best = scored_candidates[0] if scored_candidates and scored_candidates[0].total_score >= 0.25 else None

        return GroundingResult(
            query=target_query,
            best_candidate=best,
            all_candidates=scored_candidates
        )

android_grounding_engine = AndroidGroundingEngine()
