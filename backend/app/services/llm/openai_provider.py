"""OpenAI LLM provider implementation stub."""

from typing import List, Optional
from backend.app.core.errors import LLMProviderError
from backend.app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """Provider for OpenAI models (GPT-4o, GPT-3.5-Turbo)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o", **kwargs):
        super().__init__(api_key=api_key, model=model, **kwargs)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate_text(self, prompt: str, temperature: float = 0.2, max_tokens: int = 1024) -> LLMResponse:
        if not self.api_key:
            raise LLMProviderError("OPENAI_API_KEY is not configured in environment.")
        # Phase 1 integration hook
        raise NotImplementedError("OpenAI LLM generation will be implemented in Phase 1.")

    async def generate_chat(self, messages: List[LLMMessage], temperature: float = 0.2) -> LLMResponse:
        if not self.api_key:
            raise LLMProviderError("OPENAI_API_KEY is not configured in environment.")
        # Phase 1 integration hook
        raise NotImplementedError("OpenAI chat generation will be implemented in Phase 1.")
