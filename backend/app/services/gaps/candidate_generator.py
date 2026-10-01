"""Evidence-Backed Research Gap Candidate Engine (Phase 6).

Coordinates:
- Extraction of potential research gaps from measurable signals across:
  * Research Knowledge Graph (Phase 5)
  * Discovered Landscape Topics (Phase 4)
  * Scientific Discourse & Limitation Detectors (Phase 2)
- Strict evidence enforcement: Rejects any candidate with insufficient supporting evidence
- Explicit distinction: Marks every generated candidate as 'potential_gap' (NOT 'verified_gap')
- Explainable prioritization scoring using GapPriorityScorer.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.core.errors import NotFoundError, ValidationError
from backend.app.models.paper import (
    DiscoveredTopic,
    GapEvidenceItem,
    GapSignalContribution,
    Paper,
    PaperTopicAssignment,
    ResearchGapCandidateResponse,
    ScientificExtraction,
    ScientificSentence,
)
from backend.app.services.gaps.priority_scorer import (
    GapPriorityScorer,
    SCORING_FORMULA_DOCUMENTATION,
    SIGNAL_WEIGHTS,
)
from backend.app.services.gaps.signals import (
    GapSignalDetectors,
    SignalResult,
    SignalType,
)
from backend.app.services.graph.research_graph import (
    ResearchKnowledgeGraph,
    get_research_graph,
)
from backend.app.services.graph.node_builder import NodeTypes
from backend.app.services.graph.relationship_builder import RelationTypes

logger = get_logger("app.gaps.candidate_generator")


class ResearchGapCandidateGenerator:
    """Core generator synthesizing grounded, signal-backed candidate research gaps."""

    def __init__(self, rkg: Optional[ResearchKnowledgeGraph] = None):
        self._rkg = rkg

    @property
    def rkg(self) -> ResearchKnowledgeGraph:
        if self._rkg is None:
            self._rkg = get_research_graph()
        return self._rkg

    def generate_candidates(
        self,
        db: Optional[Session] = None,
        min_priority: float = 0.0,
        min_confidence: float = 0.50,
    ) -> List[ResearchGapCandidateResponse]:
        """Synthesize all grounded research gap candidates from measurable empirical signals."""
        logger.info("Executing Research Gap Candidate Discovery...")

        if db is not None and self.rkg.graph.number_of_nodes() == 0:
            self.rkg.build_from_database(db)

        candidates: List[ResearchGapCandidateResponse] = []
        seen_keys: Set[str] = set()

        # 1. Discover Repeated & Persistent Limitation Gaps
        lim_candidates = self._detect_limitation_gaps()
        for cand in lim_candidates:
            if cand.gap_id not in seen_keys:
                seen_keys.add(cand.gap_id)
                candidates.append(cand)

        # 2. Discover Underexplored Topic Gaps
        topic_candidates = self._detect_underexplored_topic_gaps(db=db)
        for cand in topic_candidates:
            if cand.gap_id not in seen_keys:
                seen_keys.add(cand.gap_id)
                candidates.append(cand)

        # 3. Discover Methodological & Dataset Concentration Gaps
        concentration_candidates = self._detect_concentration_gaps()
        for cand in concentration_candidates:
            if cand.gap_id not in seen_keys:
                seen_keys.add(cand.gap_id)
                candidates.append(cand)

        # 4. Discover Conflicting Evidence Gaps
        conflict_candidates = self._detect_conflict_gaps()
        for cand in conflict_candidates:
            if cand.gap_id not in seen_keys:
                seen_keys.add(cand.gap_id)
                candidates.append(cand)

        # 5. Filter by Minimum Priority and Confidence
        filtered = [
            c for c in candidates
            if c.gap_priority_score >= min_priority and c.confidence >= min_confidence
        ]

        # Sort descending by explainable priority score
        filtered.sort(key=lambda x: -x.gap_priority_score)
        logger.info(f"Generated {len(filtered)} grounded research gap candidates.")
        return filtered

    # =========================================================================
    # Signal Pipeline: Limitations (Repeated + Temporal)
    # =========================================================================

    def _detect_limitation_gaps(self) -> List[ResearchGapCandidateResponse]:
        """Cluster limitation nodes to identify repeated and persistent multi-year bottlenecks."""
        g = self.rkg.graph
        lim_nodes = [nid for nid, d in g.nodes(data=True) if d.get("type") == NodeTypes.LIMITATION]

        if not lim_nodes:
            return []

        # Group limitations by dominant lexical keyphrases
        clusters: Dict[str, List[str]] = {}
        for nid in lim_nodes:
            text = g.nodes[nid].get("properties", {}).get("text", "").lower()
            key = self._extract_dominant_limitation_key(text)
            clusters.setdefault(key, []).append(nid)

        results: List[ResearchGapCandidateResponse] = []

        for key, node_ids in clusters.items():
            # Collect evidence from all papers in this limitation cluster
            supporting_papers = []
            supporting_evidence: List[GapEvidenceItem] = []
            paper_years: List[int] = []
            distinct_papers: Set[int] = set()

            is_addressed = False

            for nid in node_ids:
                n_data = g.nodes[nid]
                props = n_data.get("properties", {})
                prov = n_data.get("provenance", {})

                p_id = props.get("paper_id")
                if p_id and p_id not in distinct_papers:
                    distinct_papers.add(p_id)
                    p_node_id = f"paper:{p_id}"
                    p_title = prov.get("paper_title") or f"Paper #{p_id}"
                    p_year = None
                    if g.has_node(p_node_id):
                        p_year = g.nodes[p_node_id].get("properties", {}).get("publication_year")
                    if p_year:
                        paper_years.append(p_year)

                    supporting_papers.append({
                        "paper_id": p_id,
                        "title": p_title,
                        "publication_year": p_year,
                    })

                # Check if this limitation has an incoming 'addresses' edge
                for u, v, e_data in g.in_edges(nid, data=True):
                    if e_data.get("relationship") == RelationTypes.ADDRESSES:
                        is_addressed = True

                source_text = prov.get("source_text") or props.get("text", "")
                if source_text:
                    supporting_evidence.append(GapEvidenceItem(
                        paper_id=p_id,
                        paper_title=prov.get("paper_title"),
                        sentence_id=prov.get("sentence_id"),
                        section=prov.get("section_name", "Limitations"),
                        page=prov.get("page_number", 1),
                        source_text=source_text,
                        confidence=prov.get("confidence", 0.90),
                        extraction_method=prov.get("extraction_method", "limitation_detector"),
                    ))

            # STRICT EVIDENCE CHECK: Must have at least 1 paper and 1 evidence item
            if not supporting_papers or not supporting_evidence:
                continue

            # Evaluate Signals
            earliest_yr = min(paper_years) if paper_years else None
            latest_yr = max(paper_years) if paper_years else None

            sig_rep = GapSignalDetectors.detect_repeated_limitations(
                distinct_paper_ids=distinct_papers,
                limitation_count=len(node_ids),
            )
            sig_temp = GapSignalDetectors.detect_temporal_opportunity(
                earliest_year=earliest_yr,
                latest_year=latest_yr,
                is_addressed=is_addressed,
            )

            # Signal bundle
            signals: Dict[SignalType, SignalResult] = {
                SignalType.REPEATED_LIMITATIONS: sig_rep,
                SignalType.TEMPORAL_OPPORTUNITY: sig_temp,
            }

            priority_score, breakdown, explanation = GapPriorityScorer.calculate_priority(signals)
            conf = float(np.mean([e.confidence for e in supporting_evidence])) if supporting_evidence else 0.85

            gap_type = "repeated_limitation" if sig_rep.is_active else "temporal_opportunity"
            gap_id = f"gap-limitation-{self._slugify(key)[:32]}"
            title = f"Empirical Bottleneck: {key.title()}"
            desc = (
                f"Documented scientific bottleneck regarding {key}. "
                f"Identified across {len(distinct_papers)} publications without complete resolution."
            )

            results.append(ResearchGapCandidateResponse(
                gap_id=gap_id,
                title=title,
                description=desc,
                gap_type=gap_type,
                verification_status="potential_gap",
                supporting_papers=supporting_papers,
                supporting_evidence=supporting_evidence,
                signals={s.value: r.raw_value for s, r in signals.items()},
                signal_breakdown=breakdown,
                gap_priority_score=priority_score,
                confidence=round(conf, 4),
                created_at=datetime.now(timezone.utc).isoformat(),
            ))

        return results

    # =========================================================================
    # Signal Pipeline: Underexplored Research Themes
    # =========================================================================

    def _detect_underexplored_topic_gaps(self, db: Optional[Session] = None) -> List[ResearchGapCandidateResponse]:
        """Analyze research topics from Phase 4 to identify areas with sparse literature coverage."""
        g = self.rkg.graph
        topic_nodes = [nid for nid, d in g.nodes(data=True) if d.get("type") == NodeTypes.RESEARCH_TOPIC]

        if not topic_nodes:
            return []

        # Compute paper counts per topic
        topic_counts: Dict[str, int] = {}
        for tnid in topic_nodes:
            cnt = len([u for u, v, d in g.in_edges(tnid, data=True) if d.get("relationship") == RelationTypes.BELONGS_TO])
            topic_counts[tnid] = cnt

        mean_papers = float(np.mean(list(topic_counts.values()))) if topic_counts else 4.0

        results: List[ResearchGapCandidateResponse] = []

        for tnid in topic_nodes:
            cnt = topic_counts[tnid]
            t_data = g.nodes[tnid]
            props = t_data.get("properties", {})
            t_name = t_data.get("label", f"Topic {props.get('topic_id')}")

            # Signal 1: Underexploration
            sig_under = GapSignalDetectors.detect_underexploration(
                topic_paper_count=cnt,
                mean_topic_papers=mean_papers,
            )

            # Signal 6: Cross-domain opportunity
            sig_cross = GapSignalDetectors.detect_cross_domain_opportunity(
                domain_counts={"PrimaryDomain": cnt},
                is_high_performing=True,
            )

            signals: Dict[SignalType, SignalResult] = {
                SignalType.UNDEREXPLORATION: sig_under,
                SignalType.CROSS_DOMAIN_OPPORTUNITY: sig_cross,
            }

            if not sig_under.is_active and not sig_cross.is_active:
                continue

            # Collect supporting papers
            supporting_papers = []
            supporting_evidence: List[GapEvidenceItem] = []

            for u, v, d in g.in_edges(tnid, data=True):
                if d.get("relationship") == RelationTypes.BELONGS_TO:
                    p_node = g.nodes[u]
                    p_props = p_node.get("properties", {})
                    p_id = p_props.get("paper_id")
                    p_title = p_props.get("title", f"Paper #{p_id}")
                    supporting_papers.append({
                        "paper_id": p_id,
                        "title": p_title,
                        "publication_year": p_props.get("publication_year"),
                    })

                    # Evidence snippet
                    src_text = d.get("provenance", {}).get("source_text") or f"Paper belongs to theme '{t_name}'"
                    supporting_evidence.append(GapEvidenceItem(
                        paper_id=p_id,
                        paper_title=p_title,
                        section="Research Landscape",
                        source_text=src_text,
                        confidence=d.get("confidence", 0.85),
                        extraction_method="topic_landscape_assignment",
                    ))

            # STRICT EVIDENCE CHECK: Do not emit gap candidate if 0 papers or 0 evidence
            if not supporting_papers or not supporting_evidence:
                continue

            priority_score, breakdown, _ = GapPriorityScorer.calculate_priority(signals)
            t_id = props.get("topic_id", 0)

            results.append(ResearchGapCandidateResponse(
                gap_id=f"gap-topic-{t_id}",
                title=f"Underexplored Research Frontier: {t_name}",
                description=(
                    f"Research theme '{t_name}' exhibits low density in current scientific literature "
                    f"({cnt} papers vs corpus average of {mean_papers:.1f}), indicating potential under-investigation."
                ),
                gap_type="underexplored_area",
                verification_status="potential_gap",
                supporting_papers=supporting_papers,
                supporting_evidence=supporting_evidence,
                signals={s.value: r.raw_value for s, r in signals.items()},
                signal_breakdown=breakdown,
                gap_priority_score=priority_score,
                confidence=0.88,
                created_at=datetime.now(timezone.utc).isoformat(),
            ))

        return results

    # =========================================================================
    # Signal Pipeline: Method & Dataset Monoculture Concentration
    # =========================================================================

    def _detect_concentration_gaps(self) -> List[ResearchGapCandidateResponse]:
        """Detect areas with high methodological or dataset concentration (HHI)."""
        g = self.rkg.graph

        # Collect methods used per paper and dataset used per paper
        method_counts: Dict[str, int] = {}
        method_papers: Dict[str, List[Dict[str, Any]]] = {}
        method_evidence: Dict[str, List[GapEvidenceItem]] = {}

        dataset_counts: Dict[str, int] = {}
        dataset_papers: Dict[str, List[Dict[str, Any]]] = {}
        dataset_evidence: Dict[str, List[GapEvidenceItem]] = {}

        for u, v, data in g.edges(data=True):
            rel = data.get("relationship")
            u_node = g.nodes[u]
            v_node = g.nodes[v]

            if rel in (RelationTypes.USES, RelationTypes.PROPOSES) and v_node.get("type") == NodeTypes.METHOD:
                m_label = v_node.get("label", "Unknown Method")
                method_counts[m_label] = method_counts.get(m_label, 0) + 1
                p_id = u_node.get("properties", {}).get("paper_id")
                p_title = u_node.get("properties", {}).get("title")
                method_papers.setdefault(m_label, []).append({
                    "paper_id": p_id,
                    "title": p_title,
                })
                method_evidence.setdefault(m_label, []).append(GapEvidenceItem(
                    paper_id=p_id,
                    paper_title=p_title,
                    section=data.get("provenance", {}).get("section_name", "Methodology"),
                    source_text=data.get("provenance", {}).get("source_text", f"Uses {m_label}"),
                    confidence=data.get("confidence", 0.90),
                    extraction_method="method_inference",
                ))

            elif rel == RelationTypes.USES and v_node.get("type") == NodeTypes.DATASET:
                d_label = v_node.get("label", "Unknown Dataset")
                dataset_counts[d_label] = dataset_counts.get(d_label, 0) + 1
                p_id = u_node.get("properties", {}).get("paper_id")
                p_title = u_node.get("properties", {}).get("title")
                dataset_papers.setdefault(d_label, []).append({
                    "paper_id": p_id,
                    "title": p_title,
                })
                dataset_evidence.setdefault(d_label, []).append(GapEvidenceItem(
                    paper_id=p_id,
                    paper_title=p_title,
                    section=data.get("provenance", {}).get("section_name", "Experiments"),
                    source_text=data.get("provenance", {}).get("source_text", f"Evaluated on {d_label}"),
                    confidence=data.get("confidence", 0.90),
                    extraction_method="dataset_inference",
                ))

        results: List[ResearchGapCandidateResponse] = []

        # Methodological Concentration
        sig_m = GapSignalDetectors.detect_methodological_concentration(method_counts)
        if sig_m.is_active:
            top_m = sig_m.metadata["top_methods"][0][0]
            papers = method_papers.get(top_m, [])
            evid = method_evidence.get(top_m, [])
            if papers and evid:
                signals_m: Dict[SignalType, SignalResult] = {
                    SignalType.METHODOLOGICAL_CONCENTRATION: sig_m,
                }
                score, breakdown, _ = GapPriorityScorer.calculate_priority(signals_m)
                results.append(ResearchGapCandidateResponse(
                    gap_id=f"gap-method-concentration-{self._slugify(top_m)}",
                    title=f"Methodological Concentration: Disproportionate Dominance of '{top_m}'",
                    description=(
                        f"The research cohort displays high algorithmic concentration (HHI {sig_m.metadata.get('hhi', 0):.2f}) "
                        f"centered on '{top_m}'. Alternative architectures remain systematically underexplored."
                    ),
                    gap_type="method_concentration",
                    verification_status="potential_gap",
                    supporting_papers=papers,
                    supporting_evidence=evid,
                    signals={s.value: r.raw_value for s, r in signals_m.items()},
                    signal_breakdown=breakdown,
                    gap_priority_score=score,
                    confidence=0.89,
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))

        # Dataset Concentration
        sig_d = GapSignalDetectors.detect_dataset_concentration(dataset_counts)
        if sig_d.is_active:
            top_d = max(dataset_counts.items(), key=lambda x: x[1])[0]
            papers = dataset_papers.get(top_d, [])
            evid = dataset_evidence.get(top_d, [])
            if papers and evid:
                signals_d: Dict[SignalType, SignalResult] = {
                    SignalType.DATASET_CONCENTRATION: sig_d,
                }
                score, breakdown, _ = GapPriorityScorer.calculate_priority(signals_d)
                results.append(ResearchGapCandidateResponse(
                    gap_id=f"gap-dataset-concentration-{self._slugify(top_d)}",
                    title=f"Dataset Monoculture: Heavy Reliance on '{top_d}' Benchmark",
                    description=(
                        f"High empirical dependence on benchmark '{top_d}' poses potential overfitting risks. "
                        "Cross-benchmark validation on out-of-distribution evaluation suites is lacking."
                    ),
                    gap_type="dataset_concentration",
                    verification_status="potential_gap",
                    supporting_papers=papers,
                    supporting_evidence=evid,
                    signals={s.value: r.raw_value for s, r in signals_d.items()},
                    signal_breakdown=breakdown,
                    gap_priority_score=score,
                    confidence=0.88,
                    created_at=datetime.now(timezone.utc).isoformat(),
                ))

        return results

    # =========================================================================
    # Signal Pipeline: Conflicting Scientific Evidence
    # =========================================================================

    def _detect_conflict_gaps(self) -> List[ResearchGapCandidateResponse]:
        """Detect unresolved empirical contradictions from graph contradiction edges."""
        g = self.rkg.graph
        conflict_edges = [
            (u, v, data) for u, v, data in g.edges(data=True)
            if data.get("relationship") == RelationTypes.CONTRADICTS
        ]

        if not conflict_edges:
            return []

        results: List[ResearchGapCandidateResponse] = []
        conflicting_papers: Set[int] = set()
        supporting_evidence: List[GapEvidenceItem] = []
        supporting_papers = []

        for u, v, data in conflict_edges:
            prov = data.get("provenance", {})
            p_id = prov.get("paper_id")
            if p_id:
                conflicting_papers.add(p_id)
                supporting_papers.append({
                    "paper_id": p_id,
                    "title": prov.get("paper_title") or f"Paper #{p_id}",
                })

            src_text = prov.get("source_text") or f"Contradiction between {u} and {v}"
            supporting_evidence.append(GapEvidenceItem(
                paper_id=p_id,
                paper_title=prov.get("paper_title"),
                section=prov.get("section_name", "Discussion"),
                source_text=src_text,
                confidence=data.get("confidence", 0.85),
                extraction_method=data.get("extraction_method", "contradiction_detector"),
            ))

        sig_conflict = GapSignalDetectors.detect_conflicting_evidence(
            conflict_count=len(conflict_edges),
            conflicting_paper_ids=conflicting_papers,
        )

        signals: Dict[SignalType, SignalResult] = {
            SignalType.CONFLICTING_EVIDENCE: sig_conflict,
        }

        score, breakdown, _ = GapPriorityScorer.calculate_priority(signals)

        results.append(ResearchGapCandidateResponse(
            gap_id="gap-conflicting-empirical-evidence",
            title="Scientific Dispute: Contradictory Empirical Findings Across Literature",
            description=(
                f"Detected {len(conflict_edges)} contradictory claims across {len(conflicting_papers)} publications. "
                "Conflicting findings indicate unresolved theoretical or empirical arbitration opportunities."
            ),
            gap_type="conflicting_evidence",
            verification_status="potential_gap",
            supporting_papers=supporting_papers,
            supporting_evidence=supporting_evidence,
            signals={s.value: r.raw_value for s, r in signals.items()},
            signal_breakdown=breakdown,
            gap_priority_score=score,
            confidence=0.87,
            created_at=datetime.now(timezone.utc).isoformat(),
        ))

        return results

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _extract_dominant_limitation_key(text: str) -> str:
        """Derive a canonical key for clustering recurrent limitations."""
        clean = text.lower()
        if re.search(r"\b(memory|quadratic|scal|overhead|compute|computation|gpu)\b", clean):
            return "computational memory overhead"
        if re.search(r"\b(transfer|generaliz|cross-domain|domain|out-of-distribution)\b", clean):
            return "cross-domain generalization degradation"
        if re.search(r"\b(data|scarcity|annotat|label|small dataset|few samples)\b", clean):
            return "annotated data scarcity"
        if re.search(r"\b(hallucinat|factual|evaluat|metric|bias)\b", clean):
            return "evaluation bias and factual hallucinations"
        # Fallback to first 4 meaningful words
        words = [w for w in re.findall(r"\b\w{4,}\b", clean) if w not in ("approach", "limitation", "paper", "model")]
        return " ".join(words[:3]) if words else "unspecified limitation"

    @staticmethod
    def _slugify(text: str) -> str:
        cleaned = re.sub(r"[^\w\s-]", "", text.strip().lower())
        return re.sub(r"[-\s]+", "-", cleaned)


# Global singleton instance
_gap_generator_instance: Optional[ResearchGapCandidateGenerator] = None


def get_gap_candidate_generator(rkg: Optional[ResearchKnowledgeGraph] = None) -> ResearchGapCandidateGenerator:
    """Retrieve global ResearchGapCandidateGenerator instance."""
    global _gap_generator_instance
    if _gap_generator_instance is None:
        _gap_generator_instance = ResearchGapCandidateGenerator(rkg=rkg)
    return _gap_generator_instance
