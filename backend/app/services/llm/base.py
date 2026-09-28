"""Abstract Base Class for provider-independent Large Language Model interfaces."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """Normalized chat message."""
    role: str = Field(..., description="Role of the author: system, user, assistant")
    content: str = Field(..., description="Text content of the message")


class LLMResponse(BaseModel):
    """Normalized LLM generation response."""
    text: str
    model_name: str
    provider: str
    usage: Dict[str, int] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract interface guaranteeing provider-agnostic behavior (Gemini, OpenAI, Local)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, **kwargs: Any):
        self.api_key = api_key
        self.model = model
        self.extra_config = kwargs

    @abstractmethod
    async def generate_text(self, prompt: str, temperature: float = 0.2, max_tokens: int = 1024) -> LLMResponse:
        """Generate a response from a simple prompt string."""
        pass

    @abstractmethod
    async def generate_chat(self, messages: List[LLMMessage], temperature: float = 0.2) -> LLMResponse:
        """Generate a response from a series of chat messages."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier for the provider."""
        pass
