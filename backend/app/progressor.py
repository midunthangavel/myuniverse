"""
Task Progressor & Execution Tracker for Synapse AI Agent
Inspired by MadeAgents/mobile-use Progressor pattern.
Monitors multi-step workflows, calculates completion percentage,
detects cyclic action loops, and decides whether to advance, retry, or replan.
"""

from typing import Dict, Any, List, Optional
import time

class TaskProgressor:
    """Tracks task lifecycle, step execution, and loop prevention."""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def start_task(
        self,
        task_id: str,
        goal: str,
        steps: List[Dict[str, Any]],
        app_name: str = "general"
    ) -> Dict[str, Any]:
        task_record = {
            "task_id": task_id,
            "goal": goal,
            "app_name": app_name,
            "total_steps": len(steps),
            "planned_steps": steps,
            "completed_steps": [],
            "current_step_index": 0,
            "progress_percent": 0.0,
            "status": "RUNNING",  # RUNNING, COMPLETED, FAILED, STALLED
            "consecutive_failures": 0,
            "action_history": [],
            "start_time": time.time(),
            "updated_time": time.time()
        }
        self.tasks[task_id] = task_record
        return task_record

    def update_step(
        self,
        task_id: str,
        step_index: int,
        action_name: str,
        reflection: Dict[str, Any]
    ) -> Dict[str, Any]:
        task = self.tasks.get(task_id)
        if not task:
            task = self.start_task(task_id, goal=f"Task {task_id}", steps=[{"action": action_name}])

        status = reflection.get("status", "SUCCESS")
        strategy = reflection.get("strategy", "PROCEED")
        
        task["action_history"].append({
            "step_index": step_index,
            "action": action_name,
            "reflection": reflection,
            "timestamp": time.time()
        })

        # Loop detection: check if last 3 actions targeted identical action with NOOP/FAILED
        recent_failures = [
            h for h in task["action_history"][-3:]
            if h["reflection"].get("status") in ["NOOP", "FAILED"]
        ]
        loop_detected = len(recent_failures) >= 3

        if status == "SUCCESS":
            task["completed_steps"].append(step_index)
            task["consecutive_failures"] = 0
            task["current_step_index"] = step_index + 1
        else:
            task["consecutive_failures"] += 1

        total = max(1, task["total_steps"])
        completed_count = len(task["completed_steps"])
        task["progress_percent"] = round((completed_count / total) * 100.0, 1)

        is_complete = task["current_step_index"] >= total
        if is_complete:
            task["status"] = "COMPLETED"
        elif loop_detected:
            task["status"] = "STALLED"
        elif task["consecutive_failures"] >= 4:
            task["status"] = "FAILED"

        task["updated_time"] = time.time()

        return {
            "task_id": task_id,
            "progress_percent": task["progress_percent"],
            "current_step_index": task["current_step_index"],
            "is_complete": is_complete,
            "loop_detected": loop_detected,
            "strategy": "REPLAN" if loop_detected else strategy,
            "status": task["status"],
            "consecutive_failures": task["consecutive_failures"]
        }

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)


# Global progressor singleton
task_progressor = TaskProgressor()
