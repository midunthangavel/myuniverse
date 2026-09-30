"""
Continuous Personalization & Flywheel Engine (Synapse Learner)
Analyzes user interactions, infers behavioral patterns, updates confidence weights,
and promotes high-confidence habits into the ChromaDB vector store.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import math
from .app_memory import app_specific_memory

class PersonalizationFlywheel:
    def __init__(self, memory_store, vector_memory):
        self.memory_store = memory_store
        self.vector_memory = vector_memory
        self.app_memory = app_specific_memory
        self.alpha = 0.25  # Learning rate / exponential smoothing factor
        self.min_confidence_threshold = 0.85  # Threshold to promote habit to primary vector index

    def record_interaction(
        self,
        user_id: str,
        domain: str,
        selection: str,
        feedback_type: str = "CONFIRMED_SELECTION",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Records an interaction and updates habit confidence weights in real-time.
        feedback_type: 'CONFIRMED_SELECTION' | 'USER_OVERRIDE' | 'REPEATED_CHOICE' | 'USER_DENIED'
        """
        profile = self.memory_store.get_full_profile(user_id)
        learned_habits = profile.get("learned", [])

        # Find matching habit in domain
        matched_habit = None
        for habit in learned_habits:
            if habit.get("domain") == domain or selection.lower() in habit.get("text", "").lower():
                matched_habit = habit
                break

        # Calculate updated metrics
        if matched_habit:
            current_count = matched_habit.get("observation_count", 1)
            raw_conf_str = matched_habit.get("confidence", "80%").replace("%", "")
            current_conf = float(raw_conf_str) / 100.0

            if feedback_type in ["CONFIRMED_SELECTION", "REPEATED_CHOICE"]:
                new_count = current_count + 1
                # Asymptotic confidence gain towards 99%
                new_conf = current_conf + (1.0 - current_conf) * self.alpha
            elif feedback_type == "USER_OVERRIDE":
                new_count = current_count
                new_conf = max(0.4, current_conf - 0.15)
            else:  # USER_DENIED
                new_count = current_count
                new_conf = max(0.3, current_conf - 0.20)

            formatted_conf = f"{round(new_conf * 100)}%"
            habit_id = matched_habit["id"]

            # Update SQLite
            with self.memory_store.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                UPDATE learned_habits
                SET observation_count = ?, confidence = ?, last_observed = CURRENT_TIMESTAMP
                WHERE id = ?
                """, (new_count, formatted_conf, habit_id))
                conn.commit()

            # Update ChromaDB Vector Store
            self.vector_memory.add_memory(
                doc_id=habit_id,
                text=f"Learned Habit: {matched_habit['text']}",
                metadata={"category": "LEARNED", "confidence": formatted_conf, "observations": new_count}
            )

            return {
                "status": "UPDATED",
                "habit_id": habit_id,
                "text": matched_habit["text"],
                "previous_confidence": f"{round(current_conf * 100)}%",
                "new_confidence": formatted_conf,
                "observations": new_count,
                "promoted": new_conf >= self.min_confidence_threshold
            }
        else:
            # Create new candidate habit
            habit_id = f"lrn_{int(datetime.now().timestamp() * 1000)}"
            initial_conf = "75%" if feedback_type == "CONFIRMED_SELECTION" else "60%"
            habit_text = f"{domain.capitalize()} Preference: Frequently selects {selection}"

            with self.memory_store.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO learned_habits (id, user_id, domain, text, observation_count, confidence)
                VALUES (?, ?, ?, ?, 1, ?)
                """, (habit_id, user_id, domain, habit_text, initial_conf))
                conn.commit()

            # Add to Vector Memory
            self.vector_memory.add_memory(
                doc_id=habit_id,
                text=f"Learned Habit: {habit_text}",
                metadata={"category": "LEARNED", "confidence": initial_conf, "observations": 1}
            )

            return {
                "status": "DISCOVERED_NEW_HABIT",
                "habit_id": habit_id,
                "text": habit_text,
                "new_confidence": initial_conf,
                "observations": 1,
                "promoted": False
            }

    def get_learning_insights(self, user_id: str = "user_default") -> Dict[str, Any]:
        """Returns statistical overview of user habits, weights, and flywheel momentum."""
        profile = self.memory_store.get_full_profile(user_id)
        learned = profile.get("learned", [])

        total_observations = sum(h.get("observation_count", 0) for h in learned)
        high_confidence_count = sum(1 for h in learned if int(h.get("confidence", "0%").replace("%", "")) >= 85)

        return {
            "flywheel_status": "ACCELERATING" if total_observations > 15 else "TRAINING",
            "total_observed_interactions": total_observations,
            "active_learned_habits": len(learned),
            "high_confidence_habits": high_confidence_count,
            "habits_list": learned,
            "flywheel_efficiency": f"{round(min(98.5, 60.0 + total_observations * 1.5), 1)}%"
        }
