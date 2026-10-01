"""Local LLM provider (Ollama / vLLM / HuggingFace local server) (Phase 9)."""

from typing import Any, Dict, List, Optional
import httpx

from backend.app.core.errors import LLMProviderError, LLMRateLimitError, LLMTimeoutError
from backend.app.core.logging import get_logger
from backend.app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = get_logger("app.llm.local")


class LocalLLMProvider(BaseLLMProvider):
    """Provider for self-hosted or local LLM instances (Ollama, vLLM, llama.cpp, LocalAI)."""

    def __init__(self, base_url: str = "http://localhost:11434/v1", model: str = "llama3", **kwargs: Any):
        super().__init__(model=model, **kwargs)
        self.base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "local"

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> LLMResponse:
        """Generate text from a prompt using local OpenAI-compatible endpoint."""
        messages = [LLMMessage(role="user", content=prompt)]
        return await self.generate_chat(messages, temperature=temperature, max_tokens=max_tokens, timeout=timeout)

    async def generate_chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> LLMResponse:
        """Generate response from a list of chat messages using local server."""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model or "llama3",
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)

            if resp.status_code == 429:
                raise LLMRateLimitError(f"Local LLM rate limit: {resp.text}")
            elif resp.status_code >= 400:
                raise LLMProviderError(f"Local LLM returned status {resp.status_code}: {resp.text}")

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise LLMProviderError("Local LLM response contained no choices.")

            text = choices[0].get("message", {}).get("content", "")
            return LLMResponse(
                text=text,
                model_name=self.model or "llama3",
                provider=self.provider_name,
                usage=data.get("usage", {}),
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Local LLM request timed out after {timeout}s: {str(exc)}")
        except (LLMRateLimitError, LLMProviderError, LLMTimeoutError):
            raise
        except httpx.ConnectError as exc:
            raise LLMProviderError(f"Failed to connect to local LLM server at {self.base_url}: {str(exc)}")
        except Exception as exc:
            raise LLMProviderError(f"Local LLM generation failed: {str(exc)}")
