"""OpenAI LLM provider implementation (Phase 9)."""

from typing import Any, Dict, List, Optional
import httpx

from backend.app.core.errors import LLMProviderError, LLMRateLimitError, LLMTimeoutError
from backend.app.core.logging import get_logger
from backend.app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = get_logger("app.llm.openai")


class OpenAIProvider(BaseLLMProvider):
    """Provider for OpenAI models (GPT-4o, GPT-3.5-Turbo, etc.) via OpenAI REST API."""

    ENDPOINT = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o", **kwargs: Any):
        super().__init__(api_key=api_key, model=model, **kwargs)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> LLMResponse:
        """Generate text from a prompt using OpenAI chat completions."""
        messages = [LLMMessage(role="user", content=prompt)]
        return await self.generate_chat(messages, temperature=temperature, max_tokens=max_tokens, timeout=timeout)

    async def generate_chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> LLMResponse:
        """Generate response from a list of chat messages."""
        if not self.api_key:
            raise LLMProviderError("OPENAI_API_KEY is not configured in environment.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model or "gpt-4o",
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(self.ENDPOINT, headers=headers, json=payload)

            if resp.status_code == 429:
                raise LLMRateLimitError(f"OpenAI rate limit exceeded (HTTP 429): {resp.text}")
            elif resp.status_code >= 400:
                raise LLMProviderError(f"OpenAI API returned error {resp.status_code}: {resp.text}")

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise LLMProviderError("OpenAI response contained no completion choices.")

            message_obj = choices[0].get("message", {})
            text = message_obj.get("content", "")
            usage = data.get("usage", {})

            return LLMResponse(
                text=text,
                model_name=self.model or "gpt-4o",
                provider=self.provider_name,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                metadata={"finish_reason": choices[0].get("finish_reason")},
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"OpenAI API request timed out after {timeout}s: {str(exc)}")
        except (LLMRateLimitError, LLMProviderError, LLMTimeoutError):
            raise
        except Exception as exc:
            raise LLMProviderError(f"Unexpected error communicating with OpenAI API: {str(exc)}")
