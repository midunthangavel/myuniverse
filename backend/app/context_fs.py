"""
OpenViking-Inspired Context Database & Virtual Filesystem (viking://)
Provides:
1. Hierarchical filesystem abstraction for agent memory, resources, and skills.
2. 3-Tier Progressive Retrieval (L0 Abstract, L1 Overview, L2 Full Detail) saving ~80% token costs.
3. Transparent inspection tools: viking_ls, viking_tree, viking_read, viking_write.
"""

from typing import Dict, Any, List, Optional
import json
import hashlib

class VikingNode:
    """
    A file or directory node in the viking:// virtual filesystem.
    Maintains 3 levels of progressive disclosure:
    - L0: Ultra-compact abstract (~15-30 tokens) for routing and exploration.
    - L1: Structural overview / schema (~100-250 tokens) for agent planning.
    - L2: Full raw document or JSON data for deep execution.
    """
    def __init__(self, uri: str, name: str, is_dir: bool = False, l0: str = "", l1: str = "", l2: Any = None):
        self.uri = uri
        self.name = name
        self.is_dir = is_dir
        self.l0 = l0
        self.l1 = l1
        self.l2 = l2
        self.children: Dict[str, "VikingNode"] = {}

    def to_dict(self, depth: int = 1) -> Dict[str, Any]:
        res = {
            "uri": self.uri,
            "name": self.name,
            "is_dir": self.is_dir,
            "l0_abstract": self.l0
        }
        if self.is_dir and depth > 0:
            res["children"] = [child.to_dict(depth - 1) for child in self.children.values()]
        return res


class OpenVikingContextFS:
    """
    Virtual Context Filesystem Engine using viking:// protocol.
    Organizes user profile, learned habits, app schemas, and skills.
    """
    def __init__(self):
        self.root = VikingNode("viking://", "root", is_dir=True, l0="Root context space")
        self._init_default_hierarchy()

    def _init_default_hierarchy(self):
        """Initializes canonical OpenViking directories and seeds initial context."""
        self.mkdir("viking://user")
        self.mkdir("viking://resources")
        self.mkdir("viking://skills")
        self.mkdir("viking://sessions")

        # 1. User Profile
        self.write(
            "viking://user/profile.md",
            l0="Alex Rivera, Tech Lead & cinephile, prefers proactive assistance with security gates.",
            l1="Name: Alex Rivera | Role: Tech Lead | Location: Downtown Metro | Communication: Concise, proactive | Privacy Tier: High (biometric for financial/bookings)",
            l2={
                "name": "Alex Rivera",
                "handle": "@alex_rivera",
                "timezone": "America/New_York",
                "preferred_character": "Nova (Holo-AI)",
                "voice_speed": 1.05,
                "autonomous_level": "Supervised (Biometric for payments)",
                "notification_schedule": "Quiet hours after 10:30 PM except emergency"
            }
        )

        # 2. Cinema Habit
        self.write(
            "viking://user/habits/cinema.json",
            l0="IMAX 70mm, Dolby Atmos, center row seats (G-H), prefers 8-9 PM Friday/Saturday.",
            l1="Cinema Preferences:\n- Format: IMAX Laser / 70mm, Dolby Atmos\n- Seating: Center rows (Row G or H, seats 8-14)\n- Snacks: Salted Caramel Popcorn + Sparkling Water\n- Frequency: 2x/month | Confidence: 0.94",
            l2={
                "domain": "cinema",
                "favorite_theater": "Downtown IMAX Megaplex (Screen 1)",
                "preferred_formats": ["IMAX Laser 70mm", "Dolby Cinema"],
                "seat_preferences": {"preferred_rows": ["G", "H"], "avoid_rows": ["A", "B", "C"], "position": "Center"},
                "preferred_showtimes": ["20:15", "20:45", "21:00"],
                "learned_confidence": 0.94,
                "observations_count": 18
            }
        )

        # 3. Food Habit
        self.write(
            "viking://user/habits/food.json",
            l0="Biryani & Asian, medium-high spice, no cilantro, extra raita, under 35 mins.",
            l1="Food Preferences:\n- Cuisines: Hyderabadi Dum Biryani, Thai Basil, Dim Sum\n- Dietary: Strictly no raw cilantro; medium-spicy\n- Condiments: Extra raita, mirchi ka salan\n- Max delivery time: 40 mins | Confidence: 0.96",
            l2={
                "domain": "food",
                "favorite_dishes": ["Royal Mutton Dum Biryani", "Pad Thai Chicken", "Steamed Dumplings"],
                "dietary_exclusions": ["Cilantro (coriander leaves)", "Excessive sweet sauces"],
                "preferred_restaurants": ["Paradise Biryani Express", "Bangkok Street Deli"],
                "average_spend": "$24 - $38",
                "learned_confidence": 0.96,
                "observations_count": 24
            }
        )

        # 4. App Schemas (Resources)
        self.write(
            "viking://resources/cinepass/schema.json",
            l0="CinePass Movie App: Search movies, select showtime, choose seat (Row G/H), checkout.",
            l1="App: CinePass v4.2\nScreens:\n- /home: Trending movies & format pills\n- /movie_detail: Synopsis, ratings, showtime picker\n- /seat_map: Interactive grid (rows A-K)\n- /checkout: Card on file, Apple Pay, confirm button",
            l2={
                "package_name": "com.synapse.cinepass",
                "primary_screens": ["home", "detail", "seat_selection", "checkout"],
                "key_element_ids": {
                    "btn_book_now": "cinepass:id/btn_book_now",
                    "showtime_pill": "cinepass:id/pill_showtime_2015",
                    "seat_g12": "cinepass:id/seat_row_G_col_12",
                    "pay_button": "cinepass:id/btn_authorize_pay"
                },
                "coordinates": {"btn_book": [180, 520], "seat_center": [190, 360], "pay_cta": [190, 680]}
            }
        )

        self.write(
            "viking://resources/bitego/schema.json",
            l0="BiteGo Food Delivery: Search dish/restaurant, customize spice/addons, 1-tap checkout.",
            l1="App: BiteGo v3.8\nScreens:\n- /feed: Featured restaurants, categories (Biryani, Burger, Healthy)\n- /menu: Dishes, add-on checkboxes (extra raita, spice level)\n- /cart: Promo codes, delivery address, place order CTA",
            l2={
                "package_name": "com.synapse.bitego",
                "primary_screens": ["restaurants", "menu", "customization", "cart"],
                "key_element_ids": {
                    "dish_biryani": "bitego:id/card_royal_biryani",
                    "btn_add_to_cart": "bitego:id/btn_add_cart",
                    "opt_extra_raita": "bitego:id/check_raita",
                    "btn_place_order": "bitego:id/btn_place_order"
                },
                "coordinates": {"add_btn": [310, 310], "place_order_btn": [190, 710]}
            }
        )

        # 5. Skills
        self.write(
            "viking://skills/book_movie_imax.json",
            l0="Autonomous IMAX ticket booking with seat selection and high-risk payment approval gate.",
            l1="Skill: book_movie_imax\nSteps: 1. Launch CinePass -> 2. Select IMAX format -> 3. Choose 8:15 PM -> 4. Select Center Seat (G12) -> 5. Request Biometric Approval -> 6. Confirm Purchase",
            l2={
                "name": "book_movie_imax",
                "required_permissions": ["com.synapse.cinepass", "ACCESSIBILITY_TAP"],
                "risk_tier": "high",
                "governance_mode": "ASK",
                "steps": [
                    {"step": 1, "action": "LAUNCH_APP", "target": "cinepass"},
                    {"step": 2, "action": "FILTER_FORMAT", "format": "IMAX"},
                    {"step": 3, "action": "SELECT_SHOWTIME", "time": "20:15"},
                    {"step": 4, "action": "PICK_SEAT", "preferred_rows": ["G", "H"], "target_seat": "G12"},
                    {"step": 5, "action": "GOVERNANCE_GATE", "type": "BIOMETRIC_CONFIRM", "amount": "$24.50"},
                    {"step": 6, "action": "EXECUTE_PAYMENT", "after_verify": True}
                ]
            }
        )

    def _resolve_path(self, uri: str, tenant_id: str = "tenant_default") -> List[str]:
        cleaned = uri.replace("viking://", "").strip("/")
        return [tenant_id] + [p for p in cleaned.split("/") if p]

    def mkdir(self, uri: str, tenant_id: str = "tenant_default") -> VikingNode:
        parts = self._resolve_path(uri, tenant_id)
        current = self.root
        path_acc = "viking://"
        for part in parts:
            path_acc += f"/{part}"
            if part not in current.children:
                current.children[part] = VikingNode(path_acc, part, is_dir=True, l0=f"Directory: {part}")
            current = current.children[part]
        return current

    def write(self, uri: str, l0: str = "", l1: str = "", l2: Any = None, tenant_id: str = "tenant_default") -> VikingNode:
        parts = self._resolve_path(uri, tenant_id)
        dir_parts = parts[:-1]
        file_name = parts[-1]

        # Traverse or create parents
        current = self.root
        path_acc = "viking://"
        for part in dir_parts:
            path_acc += f"/{part}"
            if part not in current.children:
                current.children[part] = VikingNode(path_acc, part, is_dir=True, l0=f"Directory: {part}")
            current = current.children[part]

        file_uri = f"{path_acc}/{file_name}"
        node = VikingNode(file_uri, file_name, is_dir=False, l0=l0, l1=l1, l2=l2)
        current.children[file_name] = node
        return node

    def get_node(self, uri: str, tenant_id: str = "tenant_default") -> Optional[VikingNode]:
        if uri in ["viking://", "viking:/", "viking:"]:
            # Returns the tenant's root
            return self.get_node(f"viking://{tenant_id}", tenant_id="system") if tenant_id != "system" else self.root
            
        parts = self._resolve_path(uri, tenant_id)
        current = self.root
        for part in parts:
            if part not in current.children:
                return None
            current = current.children[part]
        return current

    def read(self, uri: str, tier: str = "L1", tenant_id: str = "tenant_default") -> Dict[str, Any]:
        """
        Reads a node at the specified progressive disclosure level (L0, L1, or L2).
        Returns metadata, tier requested, and the actual content.
        """
        node = self.get_node(uri, tenant_id)
        if not node:
            return {"error": f"URI '{uri}' not found in viking:// context database", "success": False}

        tier_upper = tier.upper()
        if tier_upper == "L0":
            content = node.l0
            token_est = len(str(content).split()) * 1.3
        elif tier_upper == "L1":
            content = node.l1 or node.l0
            token_est = len(str(content).split()) * 1.3
        else: # L2
            content = node.l2 or node.l1
            token_est = len(json.dumps(content) if isinstance(content, (dict, list)) else str(content)) / 4.0

        return {
            "uri": node.uri,
            "name": node.name,
            "tier": tier_upper,
            "estimated_tokens": int(token_est),
            "content": content,
            "success": True
        }

    def ls(self, uri: str = "viking://", tenant_id: str = "tenant_default") -> List[Dict[str, Any]]:
        """Lists directory entries with L0 abstracts."""
        node = self.get_node(uri, tenant_id)
        if not node:
            return []
        if not node.is_dir:
            return [{"uri": node.uri, "name": node.name, "is_dir": False, "l0": node.l0}]

        results = []
        for child in node.children.values():
            results.append({
                "uri": child.uri,
                "name": child.name,
                "is_dir": child.is_dir,
                "l0": child.l0
            })
        return sorted(results, key=lambda x: (not x["is_dir"], x["name"]))

    def tree(self, uri: str = "viking://", depth: int = 3, tenant_id: str = "tenant_default") -> Dict[str, Any]:
        """Returns visual tree structure of the context database."""
        node = self.get_node(uri, tenant_id)
        if not node:
            return {"error": f"URI '{uri}' not found"}
        return node.to_dict(depth=depth)

    def search_context(self, query: str) -> List[Dict[str, Any]]:
        """Rapid fuzzy search across all L0/L1 nodes without opening heavy L2 payloads."""
        q = query.lower()
        matches = []

        def _traverse(node: VikingNode):
            if not node.is_dir:
                score = 0
                if q in node.name.lower():
                    score += 0.5
                if q in node.l0.lower():
                    score += 0.4
                if q in node.l1.lower():
                    score += 0.3
                
                # Check keywords
                for word in q.split():
                    if word in node.l0.lower() or word in node.l1.lower():
                        score += 0.15

                if score >= 0.3:
                    matches.append({
                        "uri": node.uri,
                        "name": node.name,
                        "l0": node.l0,
                        "l1": node.l1,
                        "relevance_score": min(round(score, 2), 1.0)
                    })

            for child in node.children.values():
                _traverse(child)

        _traverse(self.root)
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matches
