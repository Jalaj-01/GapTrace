"""Evidence-Grounded RAG and LLM Synthesis Engine (Phase 9).

Synthesizes verified research gaps using retrieved scientific evidence and structured
signals from Phase 3 (Retrieval), Phase 5 (Graph), Phase 6 (Candidates), Phase 7
(Lifecycle), and Phase 8 (Verification).

Strict Architectural Invariant:
The LLM is NOT the primary gap discovery engine. It only explains and synthesizes
structured findings grounded in retrieved multi-paper evidence snippets.
"""

from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from backend.app.core.errors import (
    CitationValidationError,
    LLMProviderError,
    NotFoundError,
)
from backend.app.core.logging import get_logger
from backend.app.models.paper import (
    CitationSource,
    CitationValidationReport,
    GapGenealogyResponse,
    GapLifecycleDetailResponse,
    GapSynthesisResponse,
    GapSynthesizeRequest,
    GapVerificationResponse,
    ResearchGapCandidateResponse,
)
from backend.app.services.gaps.candidate_generator import (
    ResearchGapCandidateGenerator,
    get_gap_candidate_generator,
)
from backend.app.services.gaps.lifecycle_service import (
    GapLifecycleTracker,
    get_gap_lifecycle_tracker,
)
from backend.app.services.gaps.verification_service import (
    GapVerificationEngine,
    get_gap_verification_engine,
)
from backend.app.services.llm.base import BaseLLMProvider
from backend.app.services.llm.citation_validator import CitationValidator, get_citation_validator
from backend.app.services.llm.factory import get_llm_provider
from backend.app.services.retrieval.semantic_search import (
    SemanticSearchService,
    get_semantic_search_service,
)

logger = get_logger("app.llm.synthesis")


class GapRAGSynthesizer:
    """Orchestrates evidence retrieval, prompt safety assembly, and LLM synthesis."""

    def __init__(
        self,
        candidate_generator: Optional[ResearchGapCandidateGenerator] = None,
        lifecycle_tracker: Optional[GapLifecycleTracker] = None,
        verification_engine: Optional[GapVerificationEngine] = None,
        semantic_search: Optional[SemanticSearchService] = None,
        citation_validator: Optional[CitationValidator] = None,
    ):
        self._candidate_generator = candidate_generator
        self._lifecycle_tracker = lifecycle_tracker
        self._verification_engine = verification_engine
        self._semantic_search = semantic_search
        self._citation_validator = citation_validator
        # Cache for syntheses keyed by gap_id
        self._synthesis_cache: Dict[str, GapSynthesisResponse] = {}

    @property
    def candidate_generator(self) -> ResearchGapCandidateGenerator:
        if self._candidate_generator is None:
            self._candidate_generator = get_gap_candidate_generator()
        return self._candidate_generator

    @property
    def lifecycle_tracker(self) -> GapLifecycleTracker:
        if self._lifecycle_tracker is None:
            self._lifecycle_tracker = get_gap_lifecycle_tracker()
        return self._lifecycle_tracker

    @property
    def verification_engine(self) -> GapVerificationEngine:
        if self._verification_engine is None:
            self._verification_engine = get_gap_verification_engine()
        return self._verification_engine

    @property
    def semantic_search(self) -> SemanticSearchService:
        if self._semantic_search is None:
            self._semantic_search = get_semantic_search_service()
        return self._semantic_search

    @property
    def citation_validator(self) -> CitationValidator:
        if self._citation_validator is None:
            self._citation_validator = get_citation_validator()
        return self._citation_validator

    def assemble_evidence_context(
        self,
        gap: ResearchGapCandidateResponse,
        verification: GapVerificationResponse,
        top_k_retrieval: int = 10,
    ) -> Tuple[Dict[str, CitationSource], str]:
        """Aggregate evidence from verification, candidate support, and Phase 3 retrieval.

        Builds:
        1. A mapping of citation tags (e.g. 'E1', 'E2') -> CitationSource.
        2. Formatted prompt string with numbered evidence snippets.
        """
        citations: Dict[str, CitationSource] = {}
        seen_texts: Set[str] = set()

        def add_evidence(
            text: str,
            paper_id: Optional[int] = None,
            paper_title: Optional[str] = None,
            year: Optional[int] = None,
            page: int = 1,
            section: str = "Unknown",
            sentence_id: Optional[int] = None,
            evidence_type: str = "RETRIEVED",
            score: Optional[float] = None,
        ) -> Optional[str]:
            clean = text.strip()
            if not clean or clean in seen_texts:
                return None
            seen_texts.add(clean)

            tag = f"E{len(citations) + 1}"
            citations[tag] = CitationSource(
                citation_id=tag,
                paper_id=paper_id,
                paper_title=paper_title or (f"Paper #{paper_id}" if paper_id else "Unknown Paper"),
                publication_year=year,
                page=page,
                section=section,
                sentence_id=sentence_id,
                sentence_text=clean,
                evidence_type=evidence_type,
                similarity_score=score,
            )
            return tag

        # 1. Primary Supporting Evidence (Candidate + Verification)
        for ev in gap.supporting_evidence:
            add_evidence(
                text=ev.source_text,
                paper_id=ev.paper_id,
                paper_title=ev.paper_title,
                page=ev.page or 1,
                section=ev.section or "Unknown",
                sentence_id=ev.sentence_id,
                evidence_type="SUPPORTING",
            )

        for item in verification.supporting_evidence:
            add_evidence(
                text=item.source_text,
                paper_id=item.paper_id,
                paper_title=item.paper_title,
                year=item.publication_year,
                section=item.section or "Unknown",
                evidence_type="SUPPORTING",
                score=item.retrieval_similarity,
            )

        # 2. Counter-evidence & Addressed-by Evidence
        for item in verification.counter_evidence:
            add_evidence(
                text=item.source_text,
                paper_id=item.paper_id,
                paper_title=item.paper_title,
                year=item.publication_year,
                section=item.section or "Unknown",
                evidence_type="COUNTER",
                score=item.retrieval_similarity,
            )

        for item in verification.addressed_by_evidence:
            add_evidence(
                text=item.source_text,
                paper_id=item.paper_id,
                paper_title=item.paper_title,
                year=item.publication_year,
                section=item.section or "Unknown",
                evidence_type="ADDRESSED_BY",
                score=item.retrieval_similarity,
            )

        # 4. Dense semantic retrieval (Phase 3)
        try:
            retrieved = self.semantic_search.search(
                query=f"{gap.title} {gap.description}",
                top_k=top_k_retrieval,
            )
            for r in retrieved:
                paper_dict = r.get("paper", {})
                add_evidence(
                    text=r.get("source_text", ""),
                    paper_id=paper_dict.get("id"),
                    paper_title=paper_dict.get("title"),
                    year=paper_dict.get("year"),
                    page=r.get("page", 1),
                    section=r.get("section", "Unknown"),
                    sentence_id=r.get("sentence", {}).get("id") if r.get("sentence") else None,
                    evidence_type="RETRIEVED",
                    score=r.get("similarity_score"),
                )
        except Exception as exc:
            logger.warning(f"Phase 3 semantic search yielded error during RAG assembly: {exc}")

        # Assemble formatted text lines
        evidence_lines = []
        for tag, src in citations.items():
            meta_str = f"Paper: '{src.paper_title}'"
            if src.publication_year:
                meta_str += f", Year: {src.publication_year}"
            if src.section:
                meta_str += f", Section: {src.section}"
            meta_str += f", Page: {src.page}"
            evidence_lines.append(f"[{tag}] ({meta_str}): \"{src.sentence_text}\"")

        formatted_context = "\n".join(evidence_lines) if evidence_lines else "No retrieved evidence passages available."
        return citations, formatted_context

    def build_grounded_prompt(
        self,
        gap: ResearchGapCandidateResponse,
        lifecycle: GapLifecycleDetailResponse,
        genealogy: GapGenealogyResponse,
        verification: GapVerificationResponse,
        evidence_context: str,
    ) -> str:
        """Construct the prompt adhering strictly to prompt safety and citation rules."""
        genealogy_steps = " -> ".join(genealogy.evolutionary_chain) if genealogy.evolutionary_chain else "Direct bottleneck"

        prompt = f"""You are the scientific research gap synthesis engine of ResearchGapX.
Your task is to synthesize the verified research gap described below, grounded exclusively in the provided retrieved evidence.

=========================
CORE ARCHITECTURAL RULES & SAFETY INVARIANTS:
1. Grounding Only: Base all factual assertions on the retrieved evidence passages provided below.
2. Citation Requirement: Every factual claim must map to at least one evidence tag, e.g., [E1], [E2].
3. NO INVENTIONS:
   - NEVER invent papers, author names, or publication venues.
   - NEVER invent citations. Only use citation tags present in the RETRIEVED EVIDENCE list.
   - NEVER invent experimental results, numbers, or benchmark metrics.
   - NEVER invent datasets.
4. Distinguish Evidence from Inference: State clearly where claims are backed by citations versus where research questions/future directions are logical extrapolations.
5. Insufficient Evidence: If evidence is sparse, solitary, or inadequate, explicitly report this in 'evidence_limitations' and set 'insufficient_evidence': true.
6. JSON Output: Respond ONLY with a valid JSON object matching the requested schema. Do not enclose in markdown blocks.

=========================
STRUCTURED GAP CONTEXT:
- Gap Identifier: {gap.gap_id}
- Gap Title: {gap.title}
- Description: {gap.description}
- Gap Type: {gap.gap_type}
- Priority Score: {gap.gap_priority_score:.2f}
- Lifecycle Status: {lifecycle.status.value} (Reason: {lifecycle.status_reasoning})
- Genealogy Progression: {genealogy_steps}
- Verification Status: {verification.final_status.value} (Confidence: {verification.verification_confidence:.2f})
- Verification Reasoning: {verification.status_reasoning}

=========================
RETRIEVED EVIDENCE SNIPPETS:
{evidence_context}

=========================
REQUIRED OUTPUT FORMAT (Valid JSON with these 9 exact keys):
{{
  "gap_explanation": "Clear explanation of the research gap citing evidence e.g. [E1].",
  "why_it_matters": "Theoretical or practical significance citing evidence e.g. [E1].",
  "supporting_evidence_summary": "Summary of supporting evidence corroborating the bottleneck with citations.",
  "counter_evidence_summary": "Summary of counter-evidence, attempted mitigations, or solutions with citations.",
  "current_status": "Summary of current lifecycle and verification standing based on temporal evidence.",
  "potential_research_questions": [
    "Specific open question 1 addressing unverified aspects.",
    "Specific open question 2..."
  ],
  "potential_future_directions": [
    "Promising future direction 1...",
    "Promising future direction 2..."
  ],
  "evidence_limitations": "Explicit discussion of benchmark limits, missing evaluation datasets, or evidence sparsity.",
  "insufficient_evidence": false
}}
"""
        return prompt

    def _parse_llm_json(self, raw_text: str) -> Dict[str, Any]:
        """Robustly extract and parse JSON object from LLM response text."""
        clean = raw_text.strip()
        # Strip markdown code fences if present
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
            clean = clean.strip()

        # Try direct JSON parsing
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON object substring
        match = re.search(r"(\{.*\})", clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        raise LLMProviderError(
            f"Failed to parse valid JSON from LLM generation response. Content preview: {raw_text[:200]}"
        )

    async def synthesize_gap(
        self,
        gap_id: str,
        db: Session,
        request: Optional[GapSynthesizeRequest] = None,
        provider: Optional[BaseLLMProvider] = None,
    ) -> GapSynthesisResponse:
        """Execute end-to-end evidence-grounded RAG synthesis for a research gap."""
        req = request or GapSynthesizeRequest()

        # 1. Locate gap candidate
        candidates = self.candidate_generator.generate_candidates(db=db)
        target_cand = None
        for cand in candidates:
            if cand.gap_id == gap_id or cand.gap_id.endswith(gap_id):
                target_cand = cand
                break

        if not target_cand:
            raise NotFoundError(f"Research gap candidate '{gap_id}' not found.")

        # 2. Gather lifecycle, genealogy, and verification
        lifecycle = self.lifecycle_tracker.analyze_lifecycle(target_cand)
        genealogy = self.lifecycle_tracker.build_genealogy(target_cand)
        verification = self.verification_engine.verify_candidate_gap(target_cand)

        # 3. Assemble multi-modal evidence context and citations
        citations, evidence_context = self.assemble_evidence_context(
            gap=target_cand,
            verification=verification,
            top_k_retrieval=req.top_k_evidence,
        )

        # 4. Construct grounded prompt
        prompt = self.build_grounded_prompt(
            gap=target_cand,
            lifecycle=lifecycle,
            genealogy=genealogy,
            verification=verification,
            evidence_context=evidence_context,
        )

        # 5. Acquire LLM provider
        active_provider = provider or get_llm_provider(
            provider_type=req.provider,
            model=req.model,
        )

        # 6. Execute LLM generation
        llm_resp = await active_provider.generate_text(
            prompt=prompt,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )

        # 7. Parse structured output
        parsed_data = self._parse_llm_json(llm_resp.text)

        # Extract sections
        gap_explanation = parsed_data.get("gap_explanation", "")
        why_it_matters = parsed_data.get("why_it_matters", "")
        supporting_evidence_summary = parsed_data.get("supporting_evidence_summary", "")
        counter_evidence_summary = parsed_data.get("counter_evidence_summary", "")
        current_status = parsed_data.get("current_status", "")
        potential_rqs = parsed_data.get("potential_research_questions", [])
        potential_fds = parsed_data.get("potential_future_directions", [])
        evidence_limitations = parsed_data.get("evidence_limitations", "")
        insufficient_ev = bool(parsed_data.get("insufficient_evidence", False))

        # 8. Automated Citation Validation
        validation_report: Optional[CitationValidationReport] = None
        if req.validate_citations:
            sections_to_validate = {
                "gap_explanation": gap_explanation,
                "why_it_matters": why_it_matters,
                "supporting_evidence_summary": supporting_evidence_summary,
                "counter_evidence_summary": counter_evidence_summary,
                "current_status": current_status,
                "evidence_limitations": evidence_limitations,
            }
            validation_report = self.citation_validator.validate_sections(
                sections=sections_to_validate,
                citations=citations,
            )

            # Check if rejection requested on invalid output
            if req.reject_unsupported and not validation_report.is_valid:
                raise CitationValidationError(
                    f"Generated synthesis failed citation validation: {'; '.join(validation_report.rejection_reasons)}",
                    details={"validation_report": validation_report.model_dump()},
                )

        now_iso = datetime.now(timezone.utc).isoformat()
        response = GapSynthesisResponse(
            gap_id=target_cand.gap_id,
            gap_title=target_cand.title,
            provider=active_provider.provider_name,
            model=active_provider.model or "default",
            gap_explanation=gap_explanation,
            why_it_matters=why_it_matters,
            supporting_evidence_summary=supporting_evidence_summary,
            counter_evidence_summary=counter_evidence_summary,
            current_status=current_status,
            potential_research_questions=potential_rqs,
            potential_future_directions=potential_fds,
            evidence_limitations=evidence_limitations,
            insufficient_evidence=insufficient_ev,
            citations=citations,
            validation_report=validation_report,
            synthesized_at=now_iso,
            raw_prompt=prompt,
            metadata={
                "usage": llm_resp.usage,
                "verification_status": verification.final_status.value,
                "lifecycle_status": lifecycle.status.value,
                "priority_score": target_cand.gap_priority_score,
            },
        )

        # Store in cache
        self._synthesis_cache[target_cand.gap_id] = response
        return response

    def get_cached_synthesis(self, gap_id: str) -> Optional[GapSynthesisResponse]:
        """Retrieve previously generated synthesis if available in cache."""
        for gid, item in self._synthesis_cache.items():
            if gid == gap_id or gid.endswith(gap_id):
                return item
        return None


_global_rag_synthesizer: Optional[GapRAGSynthesizer] = None


def get_gap_rag_synthesizer() -> GapRAGSynthesizer:
    """Retrieve global GapRAGSynthesizer singleton."""
    global _global_rag_synthesizer
    if _global_rag_synthesizer is None:
        _global_rag_synthesizer = GapRAGSynthesizer()
    return _global_rag_synthesizer
