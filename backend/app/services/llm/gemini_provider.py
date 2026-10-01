"""Google Gemini LLM provider implementation (Phase 9)."""

from typing import Any, Dict, List, Optional
import httpx

from backend.app.core.errors import LLMProviderError, LLMRateLimitError, LLMTimeoutError
from backend.app.core.logging import get_logger
from backend.app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = get_logger("app.llm.gemini")


class GeminiProvider(BaseLLMProvider):
    """Provider for Google Gemini models via REST API or GenAI protocol."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash", **kwargs: Any):
        super().__init__(api_key=api_key, model=model, **kwargs)

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> LLMResponse:
        """Generate text from a prompt using Gemini REST API."""
        if not self.api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured in environment.")

        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)

            if resp.status_code == 429:
                raise LLMRateLimitError(f"Gemini rate limit exceeded (HTTP 429): {resp.text}")
            elif resp.status_code >= 400:
                raise LLMProviderError(f"Gemini API returned error {resp.status_code}: {resp.text}")

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMProviderError("Gemini response contained no candidates.")

            content_parts = candidates[0].get("content", {}).get("parts", [])
            if not content_parts or "text" not in content_parts[0]:
                raise LLMProviderError("Malformed content parts in Gemini response.")

            generated_text = content_parts[0]["text"]
            usage = data.get("usageMetadata", {})

            return LLMResponse(
                text=generated_text,
                model_name=self.model or "gemini-2.5-flash",
                provider=self.provider_name,
                usage={
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0),
                },
                metadata={"candidates_count": len(candidates)},
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Gemini API request timed out after {timeout}s: {str(exc)}")
        except (LLMRateLimitError, LLMProviderError, LLMTimeoutError):
            raise
        except Exception as exc:
            raise LLMProviderError(f"Unexpected error communicating with Gemini API: {str(exc)}")

    async def generate_chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> LLMResponse:
        """Generate response from a list of chat messages."""
        if not self.api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured in environment.")

        # Map LLMMessage roles to Gemini format
        gemini_contents = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else "user"
            gemini_contents.append({"role": role, "parts": [{"text": msg.content}]})

        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)

            if resp.status_code == 429:
                raise LLMRateLimitError(f"Gemini rate limit exceeded: {resp.text}")
            elif resp.status_code >= 400:
                raise LLMProviderError(f"Gemini API error {resp.status_code}: {resp.text}")

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMProviderError("Gemini response contained no candidates.")

            generated_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return LLMResponse(
                text=generated_text,
                model_name=self.model or "gemini-2.5-flash",
                provider=self.provider_name,
                usage=data.get("usageMetadata", {}),
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Gemini request timed out: {str(exc)}")
        except (LLMRateLimitError, LLMProviderError, LLMTimeoutError):
            raise
        except Exception as exc:
            raise LLMProviderError(f"Gemini chat generation failed: {str(exc)}")
