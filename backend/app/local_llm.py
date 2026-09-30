"""
Local LLM Engine for Synapse Personal AI Agent.
Delegates to the Universal LLM Factory (Module 1.1) while maintaining
100% backward compatibility for all existing callers.
"""

from typing import Dict, Any, List, Optional
from .llm_factory import llm_factory, get_llm, BaseLLMProvider

class LocalLLMClient:
    """Compatibility wrapper that routes calls to the Universal LLM Factory."""

    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", local_ai_url: str = "http://127.0.0.1:1234/v1"):
        self.ollama_url = ollama_url
        self.local_ai_url = local_ai_url
        self.default_model = "llama3"
        self.factory = llm_factory

    async def detect_provider(self) -> Dict[str, Any]:
        """Checks which local LLM runtime is available via the factory."""
        provider = await self.factory.get_best_available_provider()
        return await provider.health_check()

    async def plan_task(
        self,
        prompt: str,
        memories: List[Dict[str, Any]],
        screen_context: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Plans a task using the active factory provider."""
        provider = await self.factory.get_best_available_provider()
        return await provider.plan_task(prompt, memories, screen_context)
