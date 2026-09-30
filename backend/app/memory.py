"""
Persistent SQLite Personal Memory Engine for Synapse Agent
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "synapse_memory.db")

class MemoryStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Explicit User Preferences
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS explicit_preferences (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                category TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. Learned Behavioral Habits
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_habits (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                text TEXT NOT NULL,
                observation_count INTEGER DEFAULT 1,
                confidence TEXT DEFAULT '85%',
                last_observed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 3. Entities & Graph Memory
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT,
                address TEXT,
                priority TEXT DEFAULT 'Standard',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 4. Routines & Schedule Rules
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS routines (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                schedule_rule TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
            """)

            # 5. Action Audit & Safety Log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                intent TEXT NOT NULL,
                action_type TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                confirmed_by_user INTEGER DEFAULT 0,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            conn.commit()

            # Seed default if empty
            cursor.execute("SELECT COUNT(*) as cnt FROM explicit_preferences")
            if cursor.fetchone()["cnt"] == 0:
                self.seed_defaults(conn)

    def seed_defaults(self, conn: sqlite3.Connection):
        cursor = conn.cursor()
        
        # Explicit
        defaults_explicit = [
            ("exp_1", "user_default", "Food", "Dietary: Strictly Vegetarian (avoids non-veg & gelatin)"),
            ("exp_2", "user_default", "Entertainment", "Movie Format: Prefers IMAX 70mm or Dolby Atmos"),
            ("exp_3", "user_default", "Entertainment", "Showtime Window: Evening slots between 7:30 PM – 9:30 PM"),
            ("exp_4", "user_default", "Schedule", "Meeting Constraint: Never schedule meetings before 10:00 AM"),
            ("exp_5", "user_default", "Preferences", "Seating: Prefers center-back rows (E-H) in theatres")
        ]
        cursor.executemany("INSERT INTO explicit_preferences (id, user_id, category, text) VALUES (?, ?, ?, ?)", defaults_explicit)

        # Learned
        defaults_learned = [
            ("lrn_1", "user_default", "cinema", "Cinema Venue: PVR Inox Palladium", 8, "94%"),
            ("lrn_2", "user_default", "food", "Friday Dinner: Frequently orders Biryani from Paradise Spice", 6, "89%"),
            ("lrn_3", "user_default", "commute", "Commute Preference: Takes Metro when city traffic > 30 min delay", 12, "84%")
        ]
        cursor.executemany("INSERT INTO learned_habits (id, user_id, domain, text, observation_count, confidence) VALUES (?, ?, ?, ?, ?, ?)", defaults_learned)

        # Entities
        defaults_entities = [
            ("ent_1", "user_default", "John Vance", "Colleague & Engineering Lead", None, "High"),
            ("ent_2", "user_default", "Mom", "Family (Immediate bypass for emergency calls)", None, "VIP"),
            ("ent_3", "user_default", "Home", "Residence", "402 Skyline Heights, Tech Corridor", "Standard"),
            ("ent_4", "user_default", "Office", "Workplace", "Apex Innovation Center, Block 4", "Standard")
        ]
        cursor.executemany("INSERT INTO entities (id, user_id, name, role, address, priority) VALUES (?, ?, ?, ?, ?, ?)", defaults_entities)

        # Routines
        defaults_routines = [
            ("rtn_1", "user_default", "Work Day Routine", "10:00 AM – 6:30 PM (Mon-Fri)"),
            ("rtn_2", "user_default", "Focus Time Window", "2:00 PM – 4:00 PM (Silent alerts)"),
            ("rtn_3", "user_default", "Quiet Hours", "11:00 PM – 7:30 AM")
        ]
        cursor.executemany("INSERT INTO routines (id, user_id, title, schedule_rule) VALUES (?, ?, ?, ?)", defaults_routines)

        conn.commit()

    def get_full_profile(self, user_id: str = "user_default") -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM explicit_preferences WHERE user_id = ?", (user_id,))
            explicit = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT * FROM learned_habits WHERE user_id = ?", (user_id,))
            learned = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT * FROM entities WHERE user_id = ?", (user_id,))
            entities = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT * FROM routines WHERE user_id = ? AND active = 1", (user_id,))
            routines = [dict(row) for row in cursor.fetchall()]

            return {
                "explicit": explicit,
                "learned": learned,
                "entities": entities,
                "routines": routines
            }

    def add_explicit(self, user_id: str, category: str, text: str) -> str:
        item_id = f"exp_{int(datetime.now().timestamp() * 1000)}"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO explicit_preferences (id, user_id, category, text) VALUES (?, ?, ?, ?)",
                           (item_id, user_id, category, text))
            conn.commit()
        return item_id

    def remove_item(self, table: str, item_id: str):
        allowed_tables = {"explicit_preferences", "learned_habits", "entities", "routines"}
        if table not in allowed_tables:
            raise ValueError(f"Invalid table name {table}")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
            conn.commit()

    def log_action_audit(self, user_id: str, intent: str, action_type: str, risk_level: str, confirmed: bool):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO action_audit_log (user_id, intent, action_type, risk_level, confirmed_by_user)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, intent, action_type, risk_level, 1 if confirmed else 0))
            conn.commit()

    def retrieve_context(self, user_id: str, intent: str, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        profile = self.get_full_profile(user_id)
        matches = []

        # Food & dining
        if any(w in q for w in ["food", "biryani", "dinner", "restaurant", "lunch"]) or intent == "order_food":
            for e in profile["explicit"]:
                if "vegetarian" in e["text"].lower() or "diet" in e["text"].lower():
                    matches.append({"type": "EXPLICIT_PREFERENCE", "text": e["text"]})
            for h in profile["learned"]:
                if "biryani" in h["text"].lower() or "dinner" in h["text"].lower():
                    matches.append({"type": "LEARNED_HABIT", "text": f"{h['text']} (Confidence: {h['confidence']})"})

        # Cinema & movies
        if any(w in q for w in ["movie", "cinema", "theatre", "ticket"]) or intent == "book_movie":
            for e in profile["explicit"]:
                if any(w in e["text"].lower() for w in ["movie", "showtime", "seating"]):
                    matches.append({"type": "EXPLICIT_RULE", "text": e["text"]})
            for h in profile["learned"]:
                if "cinema" in h["text"].lower():
                    matches.append({"type": "LEARNED_HABIT", "text": f"{h['text']} (Confidence: {h['confidence']})"})

        # Meeting & calendar
        if any(w in q for w in ["meeting", "schedule", "calendar", "john", "sync"]) or intent == "schedule_meeting":
            for e in profile["explicit"]:
                if "meeting" in e["text"].lower():
                    matches.append({"type": "EXPLICIT_RULE", "text": e["text"]})
            if "john" in q:
                for ent in profile["entities"]:
                    if "john" in ent["name"].lower():
                        matches.append({"type": "CONTACT_GRAPH", "text": f"{ent['name']}: {ent['role']}"})
            for r in profile["routines"]:
                if "focus" in r["title"].lower():
                    matches.append({"type": "SCHEDULE_CONSTRAINT", "text": f"{r['title']}: {r['schedule_rule']}"})

        # Fallback if no specific keyword matches
        if not matches:
            for e in profile["explicit"][:2]:
                matches.append({"type": "EXPLICIT_RULE", "text": e["text"]})

        return matches
