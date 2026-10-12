import time
from typing import Dict, Any, List

class TaskTracer:
    """
    Sub-millisecond latency tracer for distributed task execution.
    Tracks timings across all pipeline stages:
    receipt -> intent -> planning -> memory -> dispatch -> device_exec -> observe -> verify.
    """
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.start_time = time.perf_counter()
        self.timestamps: Dict[str, float] = {"receipt": self.start_time}
        self.durations_ms: Dict[str, float] = {}

    def mark(self, stage: str):
        now = time.perf_counter()
        self.timestamps[stage] = now
        # Calculate duration of the completed prior stage
        keys = list(self.timestamps.keys())
        if len(keys) >= 2:
            prev_stage = keys[-2]
            self.durations_ms[f"{prev_stage}_duration_ms"] = round((now - self.timestamps[prev_stage]) * 1000, 2)

    def finish(self) -> Dict[str, Any]:
        end_time = time.perf_counter()
        self.timestamps["finish"] = end_time
        total_ms = round((end_time - self.start_time) * 1000, 2)
        
        # Ensure last stage duration is recorded
        keys = list(self.timestamps.keys())
        if len(keys) >= 2:
            last_stage = keys[-2]
            self.durations_ms[f"{last_stage}_duration_ms"] = round((end_time - self.timestamps[last_stage]) * 1000, 2)

        return {
            "task_id": self.task_id,
            "total_latency_ms": total_ms,
            "stage_breakdown": self.durations_ms,
            "meets_fastpath_target": total_ms < 1500.0,
            "target_budget": "FASTPATH (<1.5s)" if total_ms < 1500.0 else "STANDARD (<6s)"
        }
