import time
import uuid
from enum import Enum
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

class TaskState(str, Enum):
    CREATED = "CREATED"
    ROUTED = "ROUTED"
    AUTHORIZED = "AUTHORIZED"
    DISPATCHED = "DISPATCHED"
    OBSERVED = "OBSERVED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"

class TaskRecord(BaseModel):
    task_id: str
    idempotency_key: str
    tenant_id: str
    prompt: str
    state: TaskState = TaskState.CREATED
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    result_cache: Optional[Dict[str, Any]] = None
    reason: str = ""

class TaskManager:
    """
    Manages task lifecycle states, idempotency caching, and bounded timeouts.
    Guarantees that re-delivery of identical idempotency keys returns cached outcomes
    without re-executing state-altering device gestures or transactions.
    """
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.tasks_by_id: Dict[str, TaskRecord] = {}
        self.tasks_by_idempotency: Dict[str, str] = {} # idempotency_key -> task_id

    def _purge_stale(self):
        now = time.time()
        stale_ids = [tid for tid, t in self.tasks_by_id.items() if now - t.created_at > self.ttl_seconds]
        for tid in stale_ids:
            rec = self.tasks_by_id.pop(tid, None)
            if rec and rec.idempotency_key in self.tasks_by_idempotency:
                self.tasks_by_idempotency.pop(rec.idempotency_key, None)

    def create_or_get_task(self, tenant_id: str, prompt: str, idempotency_key: Optional[str] = None) -> Tuple[TaskRecord, bool]:
        self._purge_stale()
        key = idempotency_key or f"idem_{uuid.uuid4().hex}"
        
        # Check if task already exists for this tenant and idempotency key
        scoped_key = f"{tenant_id}:{key}"
        if scoped_key in self.tasks_by_idempotency:
            existing_id = self.tasks_by_idempotency[scoped_key]
            existing_task = self.tasks_by_id.get(existing_id)
            if existing_task:
                return existing_task, True

        # Create new task
        new_id = f"task_{uuid.uuid4().hex[:12]}"
        record = TaskRecord(
            task_id=new_id,
            idempotency_key=key,
            tenant_id=tenant_id,
            prompt=prompt,
            state=TaskState.CREATED
        )
        self.tasks_by_id[new_id] = record
        self.tasks_by_idempotency[scoped_key] = new_id
        return record, False

    def transition_state(self, task_id: str, new_state: TaskState, reason: str = "", result_cache: Optional[Dict[str, Any]] = None) -> Optional[TaskRecord]:
        record = self.tasks_by_id.get(task_id)
        if not record:
            return None
        record.state = new_state
        record.updated_at = time.time()
        if reason:
            record.reason = reason
        if result_cache:
            record.result_cache = result_cache
        return record

    def create_task(self, task_id: str, tenant_id: str, prompt: str) -> TaskRecord:
        record = TaskRecord(
            task_id=task_id,
            idempotency_key=f"idem_{task_id}",
            tenant_id=tenant_id,
            prompt=prompt,
            state=TaskState.CREATED
        )
        self.tasks_by_id[task_id] = record
        self.tasks_by_idempotency[f"{tenant_id}:idem_{task_id}"] = task_id
        return record

    def update_task_state(self, task_id: str, new_state: TaskState, extra: Optional[Dict[str, Any]] = None) -> Optional[TaskRecord]:
        return self.transition_state(task_id, new_state, result_cache=extra)

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self.tasks_by_id.get(task_id)

task_manager = TaskManager()
