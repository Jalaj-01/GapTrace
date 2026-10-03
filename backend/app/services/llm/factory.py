"""Factory for instantiating the configured LLM provider."""

from typing import Any, Optional
from backend.app.core.config import settings
from backend.app.core.errors import LLMProviderError
from backend.app.services.llm.base import BaseLLMProvider
from backend.app.services.llm.gemini_provider import GeminiProvider
from backend.app.services.llm.local_provider import LocalLLMProvider
from backend.app.services.llm.mock_provider import MockLLMProvider
from backend.app.services.llm.openai_provider import OpenAIProvider

_global_mock_provider: Optional[MockLLMProvider] = None


def set_global_mock_provider(mock_provider: Optional[MockLLMProvider]) -> None:
    """Set or clear a global mock provider for test suites."""
    global _global_mock_provider
    _global_mock_provider = mock_provider


def get_llm_provider(
    provider_type: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> BaseLLMProvider:
    """Returns an initialized LLM provider instance based on settings or override."""
    global _global_mock_provider
    if _global_mock_provider is not None and (provider_type is None or provider_type.lower() == "mock"):
        return _global_mock_provider

    target_provider = (provider_type or settings.LLM_PROVIDER or "gemini").lower()

    if target_provider == "mock":
        if _global_mock_provider is not None:
            return _global_mock_provider
        return MockLLMProvider(model=model or "mock-model-v1", **kwargs)

    elif target_provider == "gemini":
        return GeminiProvider(
            api_key=api_key or settings.GEMINI_API_KEY,
            backup_api_key=kwargs.pop("backup_api_key", None) or settings.GEMINI_API_KEY_BACKUP,
            model=model or settings.DEFAULT_LLM_MODEL or "gemini-3.8-flash",
            **kwargs,
        )
    elif target_provider == "openai":
        return OpenAIProvider(
            api_key=api_key or settings.OPENAI_API_KEY,
            model=model or settings.DEFAULT_LLM_MODEL or "gpt-4o",
            **kwargs,
        )
    elif target_provider == "local":
        base_url = kwargs.pop("base_url", None) or settings.LOCAL_LLM_BASE_URL
        return LocalLLMProvider(
            base_url=base_url,
            model=model or settings.DEFAULT_LLM_MODEL or "llama3",
            **kwargs,
        )
    else:
        raise LLMProviderError(f"Unsupported LLM provider: {target_provider}")
