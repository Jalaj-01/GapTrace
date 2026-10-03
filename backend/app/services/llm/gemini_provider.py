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

    def __init__(
        self,
        api_key: Optional[str] = None,
        backup_api_key: Optional[str] = None,
        model: str = "gemini-3.8-flash",
        **kwargs: Any,
    ):
        super().__init__(api_key=api_key, model=model, **kwargs)
        self.backup_api_key = backup_api_key

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def available_keys(self) -> List[str]:
        keys = []
        if self.api_key:
            keys.append(self.api_key)
        if self.backup_api_key and self.backup_api_key not in keys:
            keys.append(self.backup_api_key)
        return keys

    async def _send_generate_content(
        self,
        payload: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Send content generation request with automatic backup key failover."""
        keys = self.available_keys
        if not keys:
            raise LLMProviderError("GEMINI_API_KEY is not configured in environment.")

        last_error: Optional[Exception] = None
        for idx, key in enumerate(keys):
            url = f"{self.BASE_URL}/{self.model}:generateContent?key={key}"
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, json=payload)

                if resp.status_code == 200:
                    return resp.json()

                error_body = resp.text
                if resp.status_code == 429:
                    err = LLMRateLimitError(f"Gemini rate limit exceeded (HTTP 429): {error_body}")
                elif resp.status_code == 403:
                    err = LLMProviderError(
                        f"Gemini API returned HTTP 403 (PERMISSION_DENIED): {error_body}. "
                        "Please verify that your Google Cloud / Google AI Studio project has enabled the Generative Language API "
                        "and that the account permissions are active."
                    )
                elif resp.status_code == 404:
                    err = LLMProviderError(f"Gemini model '{self.model}' not found (HTTP 404): {error_body}")
                else:
                    err = LLMProviderError(f"Gemini API returned error {resp.status_code}: {error_body}")

                if idx < len(keys) - 1:
                    logger.warning(
                        "Gemini key #%d failed with HTTP %d. Attempting backup key failover...",
                        idx + 1,
                        resp.status_code,
                    )
                    last_error = err
                    continue
                else:
                    raise err

            except httpx.TimeoutException as exc:
                err = LLMTimeoutError(f"Gemini API request timed out after {timeout}s: {str(exc)}")
                if idx < len(keys) - 1:
                    logger.warning("Gemini key #%d timed out. Attempting backup key...", idx + 1)
                    last_error = err
                    continue
                raise err
            except (LLMRateLimitError, LLMProviderError, LLMTimeoutError):
                raise
            except Exception as exc:
                err = LLMProviderError(f"Unexpected error communicating with Gemini API: {str(exc)}")
                if idx < len(keys) - 1:
                    logger.warning("Gemini key #%d encountered error: %s. Trying backup...", idx + 1, str(exc))
                    last_error = err
                    continue
                raise err

        if last_error:
            raise last_error
        raise LLMProviderError("Gemini request failed on all configured API keys.")

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> LLMResponse:
        """Generate text from a prompt using Gemini REST API."""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        data = await self._send_generate_content(payload=payload, timeout=timeout)
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
            model_name=self.model or "gemini-3.8-flash",
            provider=self.provider_name,
            usage={
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
            metadata={"candidates_count": len(candidates)},
        )

    async def generate_chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> LLMResponse:
        """Generate response from a list of chat messages."""
        gemini_contents = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else "user"
            gemini_contents.append({"role": role, "parts": [{"text": msg.content}]})

        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        data = await self._send_generate_content(payload=payload, timeout=timeout)
        candidates = data.get("candidates", [])
        if not candidates:
            raise LLMProviderError("Gemini response contained no candidates.")

        generated_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return LLMResponse(
            text=generated_text,
            model_name=self.model or "gemini-3.8-flash",
            provider=self.provider_name,
            usage=data.get("usageMetadata", {}),
        )
