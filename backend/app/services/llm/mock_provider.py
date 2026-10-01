"""Mock LLM Provider for unit and integration testing (Phase 9).

Supports simulating all normal and failure scenarios:
- Grounded citation generation
- Hallucinated citations ([E99])
- Unsupported / contradicted claims
- Insufficient evidence flags
- Malformed JSON responses
- Provider timeouts
- Provider rate limits
- Generic provider failures
"""

import json
import re
from typing import Any, Dict, List, Optional

from backend.app.core.errors import LLMProviderError, LLMRateLimitError, LLMTimeoutError
from backend.app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse


class MockLLMProvider(BaseLLMProvider):
    """Programmable mock provider for deterministic offline testing."""

    def __init__(
        self,
        mode: str = "grounded",
        custom_response: Optional[str] = None,
        model: str = "mock-model-v1",
        **kwargs: Any,
    ):
        super().__init__(model=model, **kwargs)
        self.mode = mode
        self.custom_response = custom_response
        self.call_count = 0
        self.last_prompt: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "mock"

    def set_mode(self, mode: str, custom_response: Optional[str] = None) -> None:
        """Dynamically reconfigure mock behavior between test steps."""
        self.mode = mode
        if custom_response is not None:
            self.custom_response = custom_response

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_prompt = prompt

        # 1. Error simulation modes
        if self.mode == "timeout":
            raise LLMTimeoutError(f"Mocked LLM timeout after {timeout} seconds")
        elif self.mode == "rate_limit":
            raise LLMRateLimitError("Mocked LLM rate limit (HTTP 429) exceeded")
        elif self.mode == "provider_failure":
            raise LLMProviderError("Mocked LLM upstream provider failure (HTTP 502)")
        elif self.mode == "malformed_json":
            return LLMResponse(
                text="<<<ERROR: Malformed Non-JSON Output from Model>>>",
                model_name=self.model,
                provider=self.provider_name,
            )

        # 2. Custom string response
        if self.custom_response is not None:
            return LLMResponse(
                text=self.custom_response,
                model_name=self.model,
                provider=self.provider_name,
            )

        # 3. Hallucination mode (citing non-existent [E99])
        if self.mode == "hallucination":
            payload = {
                "gap_explanation": "Quadratic memory scaling is solved using imaginary tensor compression [E99].",
                "why_it_matters": "Context expansion fails without phantom datasets [E100].",
                "supporting_evidence_summary": "Prior work proved memory is negligible [E99].",
                "counter_evidence_summary": "No counter evidence exists anywhere [E99].",
                "current_status": "Completely resolved according to unverified sources [E99].",
                "potential_research_questions": ["How to utilize non-existent tensors?"],
                "potential_future_directions": ["Test on invented benchmark ABC-1000."],
                "evidence_limitations": "None acknowledged.",
                "insufficient_evidence": False,
            }
            return LLMResponse(
                text=json.dumps(payload),
                model_name=self.model,
                provider=self.provider_name,
            )

        # 4. Unsupported claim mode (cites [E1] but makes claim contrary to evidence)
        if self.mode == "unsupported":
            payload = {
                "gap_explanation": "Attention mechanisms execute in constant O(1) time without any memory overhead [E1].",
                "why_it_matters": "All hardware can handle infinite context length effortlessly [E1].",
                "supporting_evidence_summary": "Transformers have zero computational complexity [E1].",
                "counter_evidence_summary": "No papers ever reported memory issues [E1].",
                "current_status": "The issue is entirely trivial and solved [E1].",
                "potential_research_questions": ["Why do models need memory at all?"],
                "potential_future_directions": ["Deploy on devices with 0 RAM."],
                "evidence_limitations": "Evidence is complete and flawless.",
                "insufficient_evidence": False,
            }
            return LLMResponse(
                text=json.dumps(payload),
                model_name=self.model,
                provider=self.provider_name,
            )

        # 5. Insufficient evidence mode
        if self.mode == "insufficient_evidence":
            payload = {
                "gap_explanation": "The literature contains sparse and preliminary observations regarding this candidate gap [E1].",
                "why_it_matters": "Understanding this domain is blocked by an absence of empirical evaluations [E1].",
                "supporting_evidence_summary": "Only one preliminary note addresses this challenge [E1].",
                "counter_evidence_summary": "No counter-evidence or attempted solutions are present in the indexed literature.",
                "current_status": "Uncertain due to severe lack of multi-paper corroboration.",
                "potential_research_questions": ["What benchmark can systematically quantify this gap?"],
                "potential_future_directions": ["Conduct multi-dataset ablation studies."],
                "evidence_limitations": "Severe limitation: only a solitary study mentions the symptom with no reproducible metrics.",
                "insufficient_evidence": True,
            }
            return LLMResponse(
                text=json.dumps(payload),
                model_name=self.model,
                provider=self.provider_name,
            )

        # 6. Default grounded response
        evidence_snippets = re.findall(r"\[(E\d+)\]\s*\([^\)]*\):\s*\"(.*?)\"(?=\n|$)", prompt)
        if not evidence_snippets:
            evidence_snippets = re.findall(r"\[(E\d+)\][^\"]*\"([^\"]+)\"", prompt)

        snippet_map = {tag: text.strip() for tag, text in evidence_snippets}
        available_tags = list(snippet_map.keys())

        t1 = available_tags[0] if available_tags else "E1"
        s1 = snippet_map.get(t1, "Quadratic memory complexity in self-attention remains a significant scaling bottleneck.")

        if len(available_tags) > 1:
            t2 = available_tags[1]
            s2 = snippet_map.get(t2, "Recent sparse attention formulations provide partial mitigation.")
            counter_summary = f"Mitigations are documented in literature: {s2} [{t2}]."
            status_summary = f"Current literature confirms that {s1} [{t1}], while mitigations report {s2} [{t2}]."
        else:
            counter_summary = "No empirical counter-evidence or mitigations were identified in the indexed literature."
            status_summary = f"Empirical findings confirm this limitation persists as an open bottleneck: {s1} [{t1}]."

        payload = {
            "gap_explanation": f"The verified research gap is grounded in empirical evidence: {s1} [{t1}].",
            "why_it_matters": "Theoretical and practical significance: Attention memory bounds limit scaling to long scientific context windows.",
            "supporting_evidence_summary": f"Corroborating evidence confirms the bottleneck: {s1} [{t1}].",
            "counter_evidence_summary": counter_summary,
            "current_status": status_summary,
            "potential_research_questions": [
                "Can sub-quadratic attention preserve exact token recall on needle-in-haystack evaluations?",
                "How do recurrent-memory hybrids perform on multi-hop scientific question answering?",
            ],
            "potential_future_directions": [
                "Investigate linear attention architectures with state-space recurrence mechanisms.",
                "Develop adaptive block-sparse algorithms with dynamic routing.",
            ],
            "evidence_limitations": "Evaluations are primarily centered on standard benchmark datasets; cross-domain evaluations remain limited.",
            "insufficient_evidence": False,
        }
        return LLMResponse(
            text=json.dumps(payload),
            model_name=self.model,
            provider=self.provider_name,
            usage={"prompt_tokens": 120, "completion_tokens": 180, "total_tokens": 300},
        )

    async def generate_chat(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ) -> LLMResponse:
        prompt = "\n".join([f"{m.role}: {m.content}" for m in messages])
        return await self.generate_text(prompt, temperature=temperature, max_tokens=max_tokens, timeout=timeout)
