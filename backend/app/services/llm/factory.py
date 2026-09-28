"""Factory for instantiating the configured LLM provider."""

from typing import Optional
from backend.app.core.config import settings
from backend.app.core.errors import LLMProviderError
from backend.app.services.llm.base import BaseLLMProvider
from backend.app.services.llm.gemini_provider import GeminiProvider
from backend.app.services.llm.local_provider import LocalLLMProvider
from backend.app.services.llm.openai_provider import OpenAIProvider


def get_llm_provider(provider_type: Optional[str] = None) -> BaseLLMProvider:
    """Returns an initialized LLM provider instance based on settings or override."""
    target_provider = (provider_type or settings.LLM_PROVIDER).lower()

    if target_provider == "gemini":
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.DEFAULT_LLM_MODEL or "gemini-2.5-flash",
        )
    elif target_provider == "openai":
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.DEFAULT_LLM_MODEL or "gpt-4o",
        )
    elif target_provider == "local":
        return LocalLLMProvider(
            base_url=settings.LOCAL_LLM_BASE_URL,
            model=settings.DEFAULT_LLM_MODEL or "llama3",
        )
    else:
        raise LLMProviderError(f"Unsupported LLM provider: {target_provider}")
