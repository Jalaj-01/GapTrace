"""Large Language Model (LLM) abstraction, provider implementations, and synthesis services."""

from backend.app.services.llm.base import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
)
from backend.app.services.llm.citation_validator import (
    CitationValidator,
    get_citation_validator,
)
from backend.app.services.llm.factory import (
    get_llm_provider,
    set_global_mock_provider,
)
from backend.app.services.llm.gemini_provider import GeminiProvider
from backend.app.services.llm.local_provider import LocalLLMProvider
from backend.app.services.llm.mock_provider import MockLLMProvider
from backend.app.services.llm.openai_provider import OpenAIProvider
from backend.app.services.llm.synthesis_service import (
    GapRAGSynthesizer,
    get_gap_rag_synthesizer,
)

__all__ = [
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
    "GeminiProvider",
    "OpenAIProvider",
    "LocalLLMProvider",
    "MockLLMProvider",
    "get_llm_provider",
    "set_global_mock_provider",
    "CitationValidator",
    "get_citation_validator",
    "GapRAGSynthesizer",
    "get_gap_rag_synthesizer",
]
