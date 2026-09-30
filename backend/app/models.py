"""
Pydantic Schemas for Synapse Personal AI Agent Platform
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CharacterState(BaseModel):
    state: str = Field(..., description="IDLE | LISTENING | THINKING | SEARCHING | WORKING | SPEAKING | WAITING_CONFIRM | SUCCESS | ERROR")
    speech_text: Optional[str] = None
    action_label: Optional[str] = None

class ScreenNode(BaseModel):
    id: str = "node"
    role: Optional[str] = "element"
    text: Optional[str] = None
    desc: Optional[str] = None
    clickable: bool = True
    bounds: Optional[Any] = None

class ScreenContext(BaseModel):
    app: str
    title: str
    visible_nodes: List[ScreenNode] = []

class TaskRequest(BaseModel):
    user_id: str = "user_default"
    prompt: str
    screen_context: Optional[ScreenContext] = None

class ActionStep(BaseModel):
    action: str
    target: Optional[str] = None
    desc: str
    status: str = "pending"

class TaskPlan(BaseModel):
    intent: str
    domain: str
    summary: str
    risk_tier: str  # low | medium | high
    risk_reason: str
    cost: Optional[str] = None
    steps: List[ActionStep]
    retrieved_memories: List[Dict[str, Any]] = []

class TaskResponse(BaseModel):
    success: bool
    plan: TaskPlan
    character_response: CharacterState
    result_data: Optional[Dict[str, Any]] = None

class AddMemoryRequest(BaseModel):
    user_id: str = "user_default"
    category: str
    text: str

class MemoryItem(BaseModel):
    id: str
    category: str
    text: str
    confidence: Optional[str] = None
    created_at: Optional[str] = None
