"""Unit Tests for Phase 9: Evidence-Grounded RAG and LLM Synthesis.

Validates:
- Provider abstraction: Gemini, OpenAI, Local, Mock providers.
- Provider failure handling: timeouts, rate limits, provider failures, malformed JSON.
- Automated Citation Validator:
  * Supported claims (entailment & semantic overlap)
  * Contradicted claims (NLI contradiction)
  * Unsupported claims (weak lexical/semantic alignment)
  * Hallucinated citations ([E99])
  * Missing evidence / uncited claims
  * Evidence Support Rate (ESR) calculation
- RAG evidence retrieval and citation map assembly.
- Grounded prompt safety invariants (no invented citations, papers, or datasets).
- End-to-end synthesizer with Mock LLM provider.
"""

from datetime import datetime, timezone
import json
import pytest

from backend.app.core.errors import (
    CitationValidationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from backend.app.models.paper import (
    CategorizedEvidenceItem,
    CitationSource,
    CitationValidationReport,
    ClaimValidationStatus,
    EvidenceType,
    GapEvidenceDates,
    GapEvidenceItem,
    GapGenealogyResponse,
    GapLifecycleDetailResponse,
    GapLifecycleStatus,
    GapSynthesisResponse,
    GapSynthesizeRequest,
    GapVerificationFinalStatus,
    GapVerificationResponse,
    ResearchGapCandidateResponse,
)
from backend.app.services.gaps.candidate_generator import (
    ResearchGapCandidateGenerator,
    get_gap_candidate_generator,
)
from backend.app.services.gaps.lifecycle_service import GapLifecycleTracker
from backend.app.services.gaps.verification_service import GapVerificationEngine
from backend.app.services.graph.research_graph import ResearchKnowledgeGraph
from backend.app.services.llm.base import BaseLLMProvider, LLMMessage, LLMResponse
from backend.app.services.llm.citation_validator import CitationValidator, get_citation_validator
from backend.app.services.llm.factory import get_llm_provider
from backend.app.services.llm.gemini_provider import GeminiProvider
from backend.app.services.llm.local_provider import LocalLLMProvider
from backend.app.services.llm.mock_provider import MockLLMProvider
from backend.app.services.llm.openai_provider import OpenAIProvider
from backend.app.services.llm.synthesis_service import GapRAGSynthesizer
from backend.app.services.retrieval.semantic_search import SemanticSearchService


# ==============================================================================
# 1. Provider Abstraction Tests
# ==============================================================================

class TestProviderAbstractionUnit:
    """Tests LLM provider interface abstraction and factory instantiation."""

    def test_gemini_provider_instantiation(self):
        prov = GeminiProvider(api_key="test-gemini-key", model="gemini-2.5-flash")
        assert prov.provider_name == "gemini"
        assert prov.model == "gemini-2.5-flash"
        assert prov.api_key == "test-gemini-key"

    def test_gemini_provider_missing_key_error(self):
        prov = GeminiProvider(api_key=None)
        with pytest.raises(LLMProviderError, match="GEMINI_API_KEY is not configured"):
            prov.generate_text_sync("Hello")

    def test_openai_provider_instantiation(self):
        prov = OpenAIProvider(api_key="test-openai-key", model="gpt-4o")
        assert prov.provider_name == "openai"
        assert prov.model == "gpt-4o"
        assert prov.api_key == "test-openai-key"

    def test_openai_provider_missing_key_error(self):
        prov = OpenAIProvider(api_key=None)
        with pytest.raises(LLMProviderError, match="OPENAI_API_KEY is not configured"):
            prov.generate_text_sync("Hello")

    def test_local_provider_instantiation(self):
        prov = LocalLLMProvider(base_url="http://localhost:11434/v1", model="llama3")
        assert prov.provider_name == "local"
        assert prov.model == "llama3"
        assert prov.base_url == "http://localhost:11434/v1"

    def test_mock_provider_modes_and_counters(self):
        prov = MockLLMProvider(mode="grounded", model="mock-test")
        assert prov.provider_name == "mock"
        assert prov.call_count == 0

        resp = prov.generate_text_sync("Test prompt")
        assert prov.call_count == 1
        assert "quadratic memory complexity" in resp.text.lower()

        # Switch mode to custom
        prov.set_mode("custom", custom_response="Custom output")
        resp2 = prov.generate_text_sync("Prompt 2")
        assert resp2.text == "Custom output"
        assert prov.call_count == 2

    def test_factory_provider_resolution(self):
        mock_p = get_llm_provider("mock", model="custom-mock")
        assert isinstance(mock_p, MockLLMProvider)
        assert mock_p.model == "custom-mock"

        gemini_p = get_llm_provider("gemini", api_key="k1")
        assert isinstance(gemini_p, GeminiProvider)

        openai_p = get_llm_provider("openai", api_key="k2")
        assert isinstance(openai_p, OpenAIProvider)

        local_p = get_llm_provider("local", base_url="http://127.0.0.1:8000/v1")
        assert isinstance(local_p, LocalLLMProvider)

        with pytest.raises(LLMProviderError, match="Unsupported LLM provider"):
            get_llm_provider("unsupported_engine")


# ==============================================================================
# 2. Provider Failure & Resilience Tests
# ==============================================================================

class TestProviderFailureAndResilienceUnit:
    """Tests provider failure handling: timeouts, rate limits, upstream errors, malformed JSON."""

    def test_timeout_handling(self):
        prov = MockLLMProvider(mode="timeout")
        with pytest.raises(LLMTimeoutError, match="Mocked LLM timeout"):
            prov.generate_text_sync("Any prompt", timeout=5.0)

    def test_rate_limit_handling(self):
        prov = MockLLMProvider(mode="rate_limit")
        with pytest.raises(LLMRateLimitError, match="rate limit"):
            prov.generate_text_sync("Any prompt")

    def test_provider_upstream_failure(self):
        prov = MockLLMProvider(mode="provider_failure")
        with pytest.raises(LLMProviderError, match="upstream provider failure"):
            prov.generate_text_sync("Any prompt")

    def test_malformed_json_response_parsing(self):
        synthesizer = GapRAGSynthesizer()
        with pytest.raises(LLMProviderError, match="Failed to parse valid JSON"):
            synthesizer._parse_llm_json("<<<Non-JSON Garbage Output>>>")

    @pytest.mark.asyncio
    async def test_gemini_backup_key_failover(self, monkeypatch):
        prov = GeminiProvider(api_key="primary-key", backup_api_key="backup-key")
        assert prov.available_keys == ["primary-key", "backup-key"]

        import httpx

        calls = []

        class MockResponse:
            def __init__(self, status_code, json_data, text=""):
                self.status_code = status_code
                self._json_data = json_data
                self.text = text

            def json(self):
                return self._json_data

        async def mock_post(client_self, url, **kwargs):
            calls.append(url)
            if "key=primary-key" in url:
                return MockResponse(429, {}, "Rate limited")
            elif "key=backup-key" in url:
                return MockResponse(200, {
                    "candidates": [{"content": {"parts": [{"text": "Success from backup"}]}}],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15}
                })
            return MockResponse(500, {}, "Error")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        resp = await prov.generate_text("Test prompt")
        assert resp.text == "Success from backup"
        assert len(calls) == 2


# ==============================================================================
# 3. Citation Validator & Evidence Support Rate Tests
# ==============================================================================

class TestCitationValidatorUnit:
    """Tests automated citation validation, hallucination detection, and Evidence Support Rate."""

    @pytest.fixture
    def sample_citations(self) -> dict:
        return {
            "E1": CitationSource(
                citation_id="E1",
                paper_id=1,
                paper_title="Attention Scaling Limits",
                publication_year=2022,
                page=4,
                section="Complexity Analysis",
                sentence_id=101,
                sentence_text="We confirm the bottleneck: attention memory overhead remains quadratic across all transformer models.",
                evidence_type="SUPPORTING",
                similarity_score=0.92,
            ),
            "E2": CitationSource(
                citation_id="E2",
                paper_id=2,
                paper_title="Sparse Transformer Kernels",
                publication_year=2023,
                page=7,
                section="Experimental Results",
                sentence_id=202,
                sentence_text="We introduce localized block-sparse attention to mitigate memory constraints, achieving sub-quadratic runtime.",
                evidence_type="ADDRESSED_BY",
                similarity_score=0.88,
            ),
        }

    def test_extract_citations_regex(self):
        val = CitationValidator()
        tags = val.extract_citations("Claim statement [E1] corroborated by another paper [e2] and [E15].")
        assert tags == ["E1", "E2", "E15"]

    def test_split_claims(self):
        val = CitationValidator()
        text = """- Quadratic memory scaling is a bottleneck [E1].
- Sparse kernels mitigate this issue [E2]. Another sentence follows here."""
        claims = val.split_claims(text)
        assert len(claims) == 3
        assert "Quadratic memory scaling is a bottleneck [E1]." in claims
        assert "Sparse kernels mitigate this issue [E2]." in claims

    def test_supported_claim_validation(self, sample_citations):
        val = CitationValidator()
        claim = "Attention memory overhead remains quadratic across all transformer architectures [E1]."
        res = val.validate_claim(claim, sample_citations)

        assert res.status == ClaimValidationStatus.SUPPORTED
        assert res.support_score >= 0.70
        assert "E1" in res.cited_ids
        assert len(res.matching_sources) == 1

    def test_contradicted_claim_validation(self, sample_citations):
        val = CitationValidator()
        # E1 states attention memory overhead remains quadratic; claim asserts it is disproven
        claim = "Prior experiments are disproven because quadratic overhead fails to hold [E1]."
        res = val.validate_claim(claim, sample_citations)

        assert res.status == ClaimValidationStatus.CONTRADICTED
        assert res.support_score == 0.0

    def test_unsupported_claim_validation(self, sample_citations):
        val = CitationValidator()
        # E1 is about attention memory scaling; claim makes an unrelated assertion about quantum computing
        claim = "Quantum cryogenic algorithms exhibit super-polynomial entanglement scaling [E1]."
        res = val.validate_claim(claim, sample_citations)

        assert res.status == ClaimValidationStatus.UNSUPPORTED
        assert res.support_score < 0.50

    def test_hallucinated_citation_detection(self, sample_citations):
        val = CitationValidator()
        claim = "A miraculous architecture resolves all memory bounds without loss [E99]."
        res = val.validate_claim(claim, sample_citations)

        assert res.status == ClaimValidationStatus.HALLUCINATED_CITATION
        assert res.support_score == 0.0
        assert "E99" in res.explanation

    def test_missing_evidence_uncited_claim(self, sample_citations):
        val = CitationValidator()
        claim = "This represents an interesting architectural avenue for future work."
        res = val.validate_claim(claim, sample_citations)

        assert res.status == ClaimValidationStatus.INSUFFICIENT_EVIDENCE
        assert res.cited_ids == []

    def test_evidence_support_rate_calculation(self, sample_citations):
        val = CitationValidator()
        text = """
        1. Attention memory overhead remains quadratic across transformer models [E1].
        2. Sparse block-sparse kernels mitigate memory overhead effectively [E2].
        3. Quantum cryogenic algorithms show super-polynomial speedup [E1].
        """
        report = val.validate_text(text, sample_citations)

        # 3 claims with citations: 2 supported (claim 1 and claim 2), 1 unsupported (claim 3)
        assert report.total_claims == 3
        assert report.claims_with_citations == 3
        assert report.supported_claims == 2
        assert report.unsupported_claims == 1
        assert report.hallucinated_citations == 0
        # Expected Evidence Support Rate = 2 / 3 = 0.667
        assert report.evidence_support_rate == pytest.approx(2 / 3, abs=0.01)

    def test_hallucination_report_invalidation(self, sample_citations):
        val = CitationValidator()
        text = "Imaginary benchmarks resolve the issue [E99]."
        report = val.validate_text(text, sample_citations)

        assert report.hallucinated_citations == 1
        assert report.is_valid is False
        assert any("Hallucinated citation" in r for r in report.rejection_reasons)


# ==============================================================================
# 4. RAG Prompt Assembly & Synthesizer Tests
# ==============================================================================

class TestRAGPromptAssemblyUnit:
    """Tests multi-modal RAG context gathering and prompt safety construction."""

    @pytest.fixture
    def mock_gap_data(self):
        cand = ResearchGapCandidateResponse(
            gap_id="gap-transformer-memory-1",
            title="Quadratic Memory Scaling in Transformers",
            description="Quadratic self-attention computational complexity causes memory exhaustion on long contexts.",
            gap_type="repeated_limitation",
            verification_status="potential_gap",
            supporting_papers=[{"paper_id": 1, "title": "Paper 1", "publication_year": 2022}],
            supporting_evidence=[
                GapEvidenceItem(
                    paper_id=1,
                    paper_title="Paper 1",
                    sentence_id=10,
                    source_text="Self-attention memory overhead remains quadratic across all sequences.",
                    section="Analysis",
                    confidence=0.95,
                )
            ],
            signals={"repeated_limitations": 0.85},
            signal_breakdown=[],
            gap_priority_score=0.88,
            confidence=0.90,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        lifecycle = GapLifecycleDetailResponse(
            gap_id=cand.gap_id,
            gap_title=cand.title,
            status=GapLifecycleStatus.PARTIALLY_ADDRESSED,
            status_reasoning="Mitigations introduced in 2023, but residual quadratic bottleneck remains in 2024.",
            evidence_paper_count=3,
            year_span=2,
            first_year=2022,
            latest_year=2024,
            has_attempted_solutions=True,
            is_addressed=False,
            is_reopened=False,
            confidence=0.85,
            supporting_events_count=3,
        )

        genealogy = GapGenealogyResponse(
            gap_id=cand.gap_id,
            gap_title=cand.title,
            root_limitation="Full attention matrix O(N^2) memory footprint",
            evolutionary_chain=[
                "Full Attention Memory Limitation",
                "Sparse Attention Approximation",
                "Residual Accuracy Loss on Dense Reasoning",
            ],
            total_transitions=2,
            summary="Evolved from pure quadratic bottleneck to approximation trade-offs.",
        )

        verification = GapVerificationResponse(
            gap_id=cand.gap_id,
            gap_title=cand.title,
            supporting_evidence=[],
            counter_evidence=[],
            addressed_by_evidence=[],
            contradictory_evidence=[],
            evidence_dates=GapEvidenceDates(earliest_year=2022, latest_year=2024),
            verification_confidence=0.88,
            final_status=GapVerificationFinalStatus.PARTIALLY_ADDRESSED,
            status_reasoning="Corroborated by 3 papers; partial solutions present.",
            verified_at=datetime.now(timezone.utc).isoformat(),
        )

        return cand, lifecycle, genealogy, verification

    def test_assemble_evidence_context_mapping(self, mock_gap_data):
        cand, lifecycle, genealogy, verification = mock_gap_data

        class DummySearch:
            def search(self, query, top_k=5):
                return []

        synthesizer = GapRAGSynthesizer(semantic_search=DummySearch())

        citations, context_str = synthesizer.assemble_evidence_context(
            gap=cand,
            verification=verification,
            top_k_retrieval=5,
        )

        assert len(citations) >= 1
        assert "E1" in citations
        assert citations["E1"].citation_id == "E1"
        assert citations["E1"].paper_id == 1
        assert "quadratic" in citations["E1"].sentence_text.lower()
        assert "[E1]" in context_str

    def test_build_grounded_prompt_safety_invariants(self, mock_gap_data):
        cand, lifecycle, genealogy, verification = mock_gap_data
        synthesizer = GapRAGSynthesizer()

        prompt = synthesizer.build_grounded_prompt(
            gap=cand,
            lifecycle=lifecycle,
            genealogy=genealogy,
            verification=verification,
            evidence_context="[E1] (Paper: 'Paper 1', Year: 2022, Section: Analysis): \"Quadratic memory bottleneck.\"",
        )

        # Invariant checks
        assert "NEVER invent papers" in prompt
        assert "NEVER invent citations" in prompt
        assert "NEVER invent experimental results" in prompt
        assert "NEVER invent datasets" in prompt
        assert "Distinguish Evidence from Inference" in prompt
        assert "Insufficient Evidence" in prompt
        assert cand.title in prompt
        assert "[E1]" in prompt


# ==============================================================================
# 5. End-to-End Synthesizer Unit Tests
# ==============================================================================

class TestGapRAGSynthesizerUnit:
    """Tests synthesizer execution with mocked LLM responses across diverse scenarios."""

    @pytest.fixture
    def test_setup(self):
        class DummyGenerator:
            def generate_candidates(self, db=None, **kwargs):
                return [
                    ResearchGapCandidateResponse(
                        gap_id="gap-trans-1",
                        title="Attention Memory Constraint",
                        description="Self-attention scales quadratically with sequence length [E1].",
                        gap_type="repeated_limitation",
                        supporting_papers=[{"paper_id": 1, "title": "Paper 1", "publication_year": 2022}],
                        supporting_evidence=[
                            GapEvidenceItem(
                                paper_id=1,
                                paper_title="Paper 1",
                                sentence_id=1,
                                source_text="Quadratic memory complexity in self-attention remains a significant scaling bottleneck for long context sequences.",
                                section="Analysis",
                                confidence=0.92,
                            )
                        ],
                        gap_priority_score=0.85,
                        confidence=0.90,
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                ]

        class DummyLifecycleTracker:
            def analyze_lifecycle(self, gap):
                return GapLifecycleDetailResponse(
                    gap_id=gap.gap_id,
                    gap_title=gap.title,
                    status=GapLifecycleStatus.PERSISTENT,
                    status_reasoning="Repeatedly observed across multiple years.",
                    evidence_paper_count=2,
                    year_span=2,
                    first_year=2022,
                    latest_year=2024,
                    has_attempted_solutions=False,
                    is_addressed=False,
                    is_reopened=False,
                    confidence=0.85,
                    supporting_events_count=2,
                )

            def build_genealogy(self, gap):
                return GapGenealogyResponse(
                    gap_id=gap.gap_id,
                    gap_title=gap.title,
                    root_limitation="Memory overhead",
                    evolutionary_chain=["Limitation", "Attempted Mitigation"],
                    total_transitions=1,
                    summary="Genealogy summary",
                )

        class DummyVerificationEngine:
            def verify_candidate_gap(self, gap):
                return GapVerificationResponse(
                    gap_id=gap.gap_id,
                    gap_title=gap.title,
                    supporting_evidence=[],
                    counter_evidence=[],
                    addressed_by_evidence=[
                        CategorizedEvidenceItem(
                            evidence_id="ev-addr-1",
                            evidence_type=EvidenceType.ADDRESSED_BY,
                            paper_id=2,
                            paper_title="Paper 2",
                            publication_year=2023,
                            source_text="Recent sparse attention formulations provide partial mitigation but experience accuracy loss on dense reasoning tasks.",
                            section="Methods",
                            confidence=0.88,
                            retrieval_similarity=0.88,
                        )
                    ],
                    contradictory_evidence=[],
                    evidence_dates=GapEvidenceDates(earliest_year=2022, latest_year=2024),
                    verification_confidence=0.90,
                    final_status=GapVerificationFinalStatus.VERIFIED_OPEN,
                    status_reasoning="Persistent multi-paper bottleneck without counter-evidence.",
                    verified_at=datetime.now(timezone.utc).isoformat(),
                )

        class DummySemanticSearch:
            def search(self, query, top_k=5):
                return []

        synth = GapRAGSynthesizer(
            candidate_generator=DummyGenerator(),
            lifecycle_tracker=DummyLifecycleTracker(),
            verification_engine=DummyVerificationEngine(),
            semantic_search=DummySemanticSearch(),
        )
        return synth

    @pytest.mark.asyncio
    async def test_synthesize_gap_success_grounded(self, test_setup):
        synth = test_setup
        provider = MockLLMProvider(mode="grounded")

        response = await synth.synthesize_gap(
            gap_id="gap-trans-1",
            db=None,
            provider=provider,
        )

        assert isinstance(response, GapSynthesisResponse)
        assert response.gap_id == "gap-trans-1"
        assert response.provider == "mock"
        assert response.gap_explanation != ""
        assert response.why_it_matters != ""
        assert response.supporting_evidence_summary != ""
        assert response.counter_evidence_summary != ""
        assert response.current_status != ""
        assert len(response.potential_research_questions) >= 1
        assert len(response.potential_future_directions) >= 1
        assert response.evidence_limitations != ""
        assert response.insufficient_evidence is False
        assert len(response.citations) >= 1
        assert response.validation_report is not None
        assert response.validation_report.is_valid is True
        assert response.validation_report.evidence_support_rate > 0.50

    @pytest.mark.asyncio
    async def test_synthesize_gap_insufficient_evidence_flag(self, test_setup):
        synth = test_setup
        provider = MockLLMProvider(mode="insufficient_evidence")

        response = await synth.synthesize_gap(
            gap_id="gap-trans-1",
            db=None,
            provider=provider,
        )

        assert response.insufficient_evidence is True
        assert "sparse" in response.gap_explanation.lower() or "preliminary" in response.gap_explanation.lower()

    @pytest.mark.asyncio
    async def test_synthesize_gap_reject_unsupported_raises(self, test_setup):
        synth = test_setup
        provider = MockLLMProvider(mode="hallucination")  # Deliberately cites non-existent [E99]

        req = GapSynthesizeRequest(
            validate_citations=True,
            reject_unsupported=True,
        )

        with pytest.raises(CitationValidationError, match="failed citation validation"):
            await synth.synthesize_gap(
                gap_id="gap-trans-1",
                db=None,
                request=req,
                provider=provider,
            )

    @pytest.mark.asyncio
    async def test_synthesis_cache_retrieval(self, test_setup):
        synth = test_setup
        provider = MockLLMProvider(mode="grounded")

        resp1 = await synth.synthesize_gap(gap_id="gap-trans-1", db=None, provider=provider)
        cached = synth.get_cached_synthesis("gap-trans-1")

        assert cached is not None
        assert cached.synthesized_at == resp1.synthesized_at
        assert cached.gap_explanation == resp1.gap_explanation
