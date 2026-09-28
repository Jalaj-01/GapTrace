"""Local LLM provider (Ollama / vLLM / HuggingFace local server)."""

from typing import List, Optional
from backend.app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


class LocalLLMProvider(BaseLLMProvider):
    """Provider for self-hosted or local LLM instances (e.g. Ollama, llama.cpp, vLLM)."""

    def __init__(self, base_url: str = "http://localhost:11434/v1", model: str = "llama3", **kwargs):
        super().__init__(model=model, **kwargs)
        self.base_url = base_url

    @property
    def provider_name(self) -> str:
        return "local"

    async def generate_text(self, prompt: str, temperature: float = 0.2, max_tokens: int = 1024) -> LLMResponse:
        raise NotImplementedError("Local LLM text generation will be implemented in Phase 1.")

    async def generate_chat(self, messages: List[LLMMessage], temperature: float = 0.2) -> LLMResponse:
        raise NotImplementedError("Local LLM chat generation will be implemented in Phase 1.")
