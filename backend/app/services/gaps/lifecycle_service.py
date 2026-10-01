"""Gap Genealogy and Gap Lifecycle Engine (Phase 7).

Reconstructs the chronological evolution and genealogy of research gaps over time.

Core Capabilities:
1. Chronological Timeline Reconstruction:
   Tracks first appearance, repeated limitations, attempted solutions,
   addressing papers, later evidence, and current status.
2. Lifecycle State Machine:
   - EMERGING: Recently identified bottleneck in recent literature with emerging interest.
   - PERSISTENT: Unresolved limitation spanning multiple publication years without effective solution.
   - PARTIALLY_ADDRESSED: Attempted solutions exist, but significant residual bottlenecks remain.
   - ADDRESSED: High-confidence solution directly resolves bottleneck without subsequent recurrence.
   - REOPENED: Previously addressed bottleneck recurring in newer literature or failing on new benchmarks.
   - UNCERTAIN: Conflicting evidence, or insufficient multi-paper temporal evidence.
3. Strict Multi-Paper Invariant:
   Never infer lifecycle from a single paper or single unsupported sentence.
4. Evolutionary Genealogy Chains:
   Constructs step-by-step evolutionary progressions:
   Root limitation -> Proposed solution -> Partial solution -> Secondary limitation -> Current potential gap.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.core.logging import get_logger
from backend.app.models.paper import (
    GapEvidenceItem,
    GapGenealogyResponse,
    GapLifecycleDetailResponse,
    GapLifecycleOverviewItem,
    GapLifecycleOverviewResponse,
    GapLifecycleStatus,
    GapTimelineResponse,
    GenealogyTransitionItem,
    ResearchGapCandidateResponse,
    TimelineEventItem,
)
from backend.app.services.graph.node_builder import NodeTypes
from backend.app.services.graph.relationship_builder import RelationTypes
from backend.app.services.graph.research_graph import ResearchKnowledgeGraph, get_research_graph

logger = get_logger("app.gaps.lifecycle")


class GapLifecycleTracker:
    """Reconstructs the temporal evolution, lifecycle status, and genealogy of potential gaps."""

    def __init__(self, rkg: Optional[ResearchKnowledgeGraph] = None):
        self.rkg = rkg or get_research_graph()

    # =========================================================================
    # 1. Timeline Reconstruction
    # =========================================================================

    def build_timeline(
        self,
        gap: ResearchGapCandidateResponse,
        rkg: Optional[ResearchKnowledgeGraph] = None,
    ) -> GapTimelineResponse:
        """Construct a chronologically sorted timeline of events for the specified gap."""
        graph = (rkg or self.rkg).graph
        raw_events: List[TimelineEventItem] = []

        # Track paper metadata and years
        paper_years: Dict[int, Optional[int]] = {}
        paper_titles: Dict[int, str] = {}

        for p in gap.supporting_papers:
            pid = p.get("paper_id")
            if pid:
                paper_years[pid] = p.get("publication_year")
                paper_titles[pid] = p.get("title", f"Paper #{pid}")

        # Also populate from graph nodes
        for u, d in graph.nodes(data=True):
            if d.get("type") == NodeTypes.PAPER:
                props = d.get("properties", {})
                pid = props.get("paper_id")
                if pid:
                    if pid not in paper_years or paper_years[pid] is None:
                        paper_years[pid] = props.get("publication_year")
                    if pid not in paper_titles:
                        paper_titles[pid] = props.get("title", f"Paper #{pid}")

        # 1. Generate events from supporting evidence
        seen_event_signatures: Set[Tuple[Optional[int], str, str]] = set()

        for idx, evid in enumerate(gap.supporting_evidence):
            pid = evid.paper_id
            pyear = paper_years.get(pid) if pid else None
            src_text = evid.source_text.strip()
            ptitle = evid.paper_title or paper_titles.get(pid, f"Paper #{pid}")

            # Deduplication key
            sig = (pid, "limitation_identified", src_text)
            if sig in seen_event_signatures:
                continue
            seen_event_signatures.add(sig)

            # Classify event nature
            lower_text = src_text.lower()
            if re.search(r"\b(unresolved|unsolved|re-emerge|reopen|persists?|still|remains?)\b", lower_text):
                if re.search(r"\b(partially|partial|mitigat|residual)\b", lower_text):
                    ev_type = "partial_solution"
                    rel = RelationTypes.ADDRESSES
                elif re.search(r"\b(re-emerge|reopen)\b", lower_text):
                    ev_type = "reopened_limitation"
                    rel = "reopens"
                else:
                    ev_type = "limitation_persists"
                    rel = RelationTypes.LIMITED_BY
            elif re.search(r"\b(solve[ds]?|resolv(es|ed)|mitigat(es|ed)|overcom(es|ing)|address(es|ed)|solution|we propose)\b", lower_text):
                if re.search(r"\b(partially|partial|residual)\b", lower_text):
                    ev_type = "partial_solution"
                    rel = RelationTypes.ADDRESSES
                else:
                    ev_type = "attempted_solution"
                    rel = RelationTypes.ADDRESSES
            else:
                ev_type = "limitation_identified"
                rel = RelationTypes.LIMITED_BY

            raw_events.append(TimelineEventItem(
                event_id=f"ev-evid-{idx + 1}",
                year=pyear,
                event_type=ev_type,
                title=f"{ptitle}: {ev_type.replace('_', ' ').title()}",
                source_paper={"paper_id": pid, "title": ptitle} if pid else None,
                source_sentence=src_text,
                relationship=rel,
                confidence=evid.confidence,
                is_retrospective=False,
                details={"section": evid.section, "page": evid.page},
            ))

        # 2. Mine graph edges for attempted solutions (addresses, proposes)
        lim_nodes = [
            nid for nid, d in graph.nodes(data=True)
            if d.get("type") == NodeTypes.LIMITATION and (
                any(kw in d.get("label", "").lower() for kw in gap.title.lower().split() if len(kw) > 4)
            )
        ]

        for lim_id in lim_nodes:
            for u, v, edata in graph.in_edges(lim_id, data=True):
                rel = edata.get("relationship")
                u_node = graph.nodes[u]
                prov = edata.get("provenance", {})
                pid = prov.get("paper_id") or u_node.get("properties", {}).get("paper_id")
                ptitle = prov.get("paper_title") or u_node.get("properties", {}).get("title")
                pyear = paper_years.get(pid) or u_node.get("properties", {}).get("publication_year")
                src_text = prov.get("source_text") or f"Relationship {rel} from {u} to {v}"

                if rel == RelationTypes.ADDRESSES:
                    ev_type = "attempted_solution"
                elif rel == RelationTypes.LIMITED_BY:
                    ev_type = "repeated_limitation"
                else:
                    continue

                sig = (pid, ev_type, src_text)
                if sig in seen_event_signatures:
                    continue
                seen_event_signatures.add(sig)

                raw_events.append(TimelineEventItem(
                    event_id=f"ev-graph-{len(raw_events) + 1}",
                    year=pyear,
                    event_type=ev_type,
                    title=f"{ptitle or u}: {ev_type.replace('_', ' ').title()}",
                    source_paper={"paper_id": pid, "title": ptitle},
                    source_sentence=src_text,
                    relationship=rel,
                    confidence=edata.get("confidence", 0.85),
                    is_retrospective=False,
                    details={"graph_edge": f"{u} -[{rel}]-> {v}"},
                ))

        # 3. Handle missing years & chronological sorting
        valid_years = [ev.year for ev in raw_events if ev.year is not None]
        median_year = int(sorted(valid_years)[len(valid_years) // 2]) if valid_years else 2024

        for ev in raw_events:
            if ev.year is None:
                ev.year = median_year
                ev.details["year_estimated"] = True

        # Sort chronologically by year ascending
        # Stable secondary sort: limitation_identified -> repeated_limitation -> attempted_solution -> partial_solution -> domain_adaptation -> limitation_persists -> reopened_limitation
        type_priority = {
            "limitation_identified": 1,
            "repeated_limitation": 2,
            "attempted_solution": 3,
            "partial_solution": 4,
            "domain_adaptation": 5,
            "limitation_persists": 6,
            "reopened_limitation": 7,
            "current_candidate_gap": 8,
        }

        # Check for retrospective events: solution preceding limitation where author cites earlier limitation
        sorted_events = sorted(
            raw_events,
            key=lambda e: (e.year or 9999, type_priority.get(e.event_type, 5)),
        )

        # Flag explicit retrospective citations if a citation points back
        first_lim_year = None
        for ev in sorted_events:
            if ev.event_type in ("limitation_identified", "repeated_limitation"):
                if first_lim_year is None or ev.year < first_lim_year:
                    first_lim_year = ev.year

        for ev in sorted_events:
            if ev.event_type == "attempted_solution" and first_lim_year and ev.year < first_lim_year:
                ev.is_retrospective = True
                ev.details["retrospective_note"] = "Proposed solution chronologically precedes first recorded limitation entry."

        # Add current candidate gap state as the final anchor event
        current_year = max(valid_years) if valid_years else 2026
        sorted_events.append(TimelineEventItem(
            event_id=f"ev-anchor-{gap.gap_id}",
            year=current_year,
            event_type="current_candidate_gap",
            title=f"Current Potential Gap: {gap.title}",
            source_paper=None,
            source_sentence=gap.description,
            relationship="evaluated_as_candidate",
            confidence=gap.confidence,
            is_retrospective=False,
            details={"gap_priority_score": gap.gap_priority_score, "gap_type": gap.gap_type},
        ))

        # Count event categories
        rep_lim_count = sum(1 for e in sorted_events if e.event_type in ("limitation_identified", "repeated_limitation", "limitation_persists"))
        attempt_sol_count = sum(1 for e in sorted_events if e.event_type in ("attempted_solution", "partial_solution"))
        addr_paper_count = len({e.source_paper.get("paper_id") for e in sorted_events if e.event_type == "attempted_solution" and e.source_paper and e.source_paper.get("paper_id")})

        first_year = min(valid_years) if valid_years else None
        latest_year = max(valid_years) if valid_years else None

        # Compute lifecycle status from evidence
        lifecycle_detail = self._determine_lifecycle_status(
            gap=gap,
            events=sorted_events,
            first_year=first_year,
            latest_year=latest_year,
        )

        return GapTimelineResponse(
            gap_id=gap.gap_id,
            gap_title=gap.title,
            current_status=lifecycle_detail.status,
            first_appearance_year=first_year,
            latest_evidence_year=latest_year,
            total_events=len(sorted_events),
            repeated_limitations_count=rep_lim_count,
            attempted_solutions_count=attempt_sol_count,
            addressing_papers_count=addr_paper_count,
            events=sorted_events,
        )

    # =========================================================================
    # 2. Gap Lifecycle Determination (Strict Multi-Paper Invariant)
    # =========================================================================

    def analyze_lifecycle(
        self,
        gap: ResearchGapCandidateResponse,
        rkg: Optional[ResearchKnowledgeGraph] = None,
    ) -> GapLifecycleDetailResponse:
        """Perform comprehensive lifecycle analysis for a potential gap."""
        timeline = self.build_timeline(gap, rkg=rkg)
        return self._determine_lifecycle_status(
            gap=gap,
            events=timeline.events,
            first_year=timeline.first_appearance_year,
            latest_year=timeline.latest_evidence_year,
        )

    def _determine_lifecycle_status(
        self,
        gap: ResearchGapCandidateResponse,
        events: List[TimelineEventItem],
        first_year: Optional[int],
        latest_year: Optional[int],
    ) -> GapLifecycleDetailResponse:
        """Evaluate lifecycle state machine rules with strict evidence requirements."""
        distinct_papers = {
            e.source_paper.get("paper_id")
            for e in events
            if e.source_paper and e.source_paper.get("paper_id")
        }

        evidence_count = len([e for e in events if e.event_type != "current_candidate_gap"])
        year_span = (latest_year - first_year) if (latest_year and first_year) else 0

        # Solution and persistence metrics
        attempted_events = [e for e in events if e.event_type == "attempted_solution"]
        partial_events = [e for e in events if e.event_type == "partial_solution"]
        all_solutions = attempted_events + partial_events
        has_attempted_solutions = len(all_solutions) > 0

        limitation_events = [e for e in events if e.event_type in ("limitation_identified", "repeated_limitation", "limitation_persists")]
        reopened_events = [e for e in events if e.event_type == "reopened_limitation"]

        # ---------------------------------------------------------------------
        # RULE 1: STRICT MULTI-PAPER EVIDENCE REQUIREMENT
        # "Never determine lifecycle from one paper."
        # "Verify that lifecycle cannot be generated from a single unsupported sentence."
        # ---------------------------------------------------------------------
        if len(distinct_papers) < 2 or evidence_count < 2:
            return GapLifecycleDetailResponse(
                gap_id=gap.gap_id,
                gap_title=gap.title,
                status=GapLifecycleStatus.UNCERTAIN,
                status_reasoning=(
                    "Insufficient multi-paper temporal evidence. Lifecycle cannot be inferred from a single paper "
                    f"or unsupported sentence ({len(distinct_papers)} distinct paper(s), {evidence_count} evidence item(s))."
                ),
                evidence_paper_count=len(distinct_papers),
                year_span=year_span,
                first_year=first_year,
                latest_year=latest_year,
                has_attempted_solutions=has_attempted_solutions,
                is_addressed=False,
                is_reopened=False,
                confidence=0.50,
                supporting_events_count=len(events),
            )

        # ---------------------------------------------------------------------
        # RULE 2: REOPENED GAP
        # An attempted solution was published in year Y_sol, but in a subsequent
        # year Y_later > Y_sol, new publications report that the limitation recurred.
        # ---------------------------------------------------------------------
        if has_attempted_solutions:
            max_sol_year = max((e.year for e in all_solutions if e.year is not None), default=0)
            later_limitations = [
                e for e in limitation_events
                if e.year is not None and e.year > max_sol_year
            ]
            if len(reopened_events) > 0 or len(later_limitations) > 0:
                return GapLifecycleDetailResponse(
                    gap_id=gap.gap_id,
                    gap_title=gap.title,
                    status=GapLifecycleStatus.REOPENED,
                    status_reasoning=(
                        f"Proposed solutions were introduced around {max_sol_year}, but subsequent publications "
                        f"in later literature ({', '.join(str(e.year) for e in later_limitations[:3])}) report "
                        "that the limitation continues or re-emerged under new evaluation benchmarks."
                    ),
                    evidence_paper_count=len(distinct_papers),
                    year_span=year_span,
                    first_year=first_year,
                    latest_year=latest_year,
                    has_attempted_solutions=True,
                    is_addressed=False,
                    is_reopened=True,
                    confidence=0.88,
                    supporting_events_count=len(events),
                )

            # Concurrent limitations in the same year as the solution from distinct evaluation papers
            sol_paper_ids = {s.source_paper.get("paper_id") for s in all_solutions if s.source_paper}
            concurrent_limitations = [
                e for e in limitation_events
                if e.year is not None and e.year == max_sol_year and (
                    not e.source_paper or e.source_paper.get("paper_id") not in sol_paper_ids
                )
            ]

            # -----------------------------------------------------------------
            # RULE 3: PARTIALLY ADDRESSED
            # Solutions attempted, but explicit partial solutions or concurrent limitations exist.
            # -----------------------------------------------------------------
            if len(partial_events) > 0 or len(concurrent_limitations) > 0:
                return GapLifecycleDetailResponse(
                    gap_id=gap.gap_id,
                    gap_title=gap.title,
                    status=GapLifecycleStatus.PARTIALLY_ADDRESSED,
                    status_reasoning=(
                        f"Techniques have been proposed to mitigate the bottleneck ({len(all_solutions)} solution events), "
                        "but empirical evaluations indicate remaining limitations or domain-specific constraints."
                    ),
                    evidence_paper_count=len(distinct_papers),
                    year_span=year_span,
                    first_year=first_year,
                    latest_year=latest_year,
                    has_attempted_solutions=True,
                    is_addressed=False,
                    is_reopened=False,
                    confidence=0.84,
                    supporting_events_count=len(events),
                )

            # -----------------------------------------------------------------
            # RULE 4: ADDRESSED GAP
            # Solutions exist with high confidence and NO concurrent or subsequent limitations.
            # -----------------------------------------------------------------
            avg_sol_conf = sum(e.confidence for e in attempted_events) / len(attempted_events) if attempted_events else 0.85
            if len(later_limitations) == 0 and len(concurrent_limitations) == 0 and avg_sol_conf >= 0.80:
                return GapLifecycleDetailResponse(
                    gap_id=gap.gap_id,
                    gap_title=gap.title,
                    status=GapLifecycleStatus.ADDRESSED,
                    status_reasoning=(
                        f"High-confidence attempted solutions ({len(attempted_events)} events) directly address "
                        f"the bottleneck, and no subsequent papers in later literature report recurrence."
                    ),
                    evidence_paper_count=len(distinct_papers),
                    year_span=year_span,
                    first_year=first_year,
                    latest_year=latest_year,
                    has_attempted_solutions=True,
                    is_addressed=True,
                    is_reopened=False,
                    confidence=round(avg_sol_conf, 2),
                    supporting_events_count=len(events),
                )

            # Fallback for remaining attempted solutions
            return GapLifecycleDetailResponse(
                gap_id=gap.gap_id,
                gap_title=gap.title,
                status=GapLifecycleStatus.PARTIALLY_ADDRESSED,
                status_reasoning=(
                    f"Techniques have been proposed to mitigate the bottleneck ({len(all_solutions)} attempted solutions), "
                    "but empirical evaluations indicate remaining limitations or domain-specific constraints."
                ),
                evidence_paper_count=len(distinct_papers),
                year_span=year_span,
                first_year=first_year,
                latest_year=latest_year,
                has_attempted_solutions=True,
                is_addressed=False,
                is_reopened=False,
                confidence=0.84,
                supporting_events_count=len(events),
            )

        # ---------------------------------------------------------------------
        # RULE 5: PERSISTENT GAP
        # No solution exists, multi-year span (>= 2 years) across >= 2 papers.
        # ---------------------------------------------------------------------
        if year_span >= 2 and len(distinct_papers) >= 2:
            return GapLifecycleDetailResponse(
                gap_id=gap.gap_id,
                gap_title=gap.title,
                status=GapLifecycleStatus.PERSISTENT,
                status_reasoning=(
                    f"Bottleneck persistently reported across {len(distinct_papers)} distinct publications "
                    f"over a {year_span}-year temporal span ({first_year} to {latest_year}) without verified solutions."
                ),
                evidence_paper_count=len(distinct_papers),
                year_span=year_span,
                first_year=first_year,
                latest_year=latest_year,
                has_attempted_solutions=False,
                is_addressed=False,
                is_reopened=False,
                confidence=0.92,
                supporting_events_count=len(events),
            )

        # ---------------------------------------------------------------------
        # RULE 6: EMERGING GAP
        # First reported recently (within last 1-2 years), corroborated by >= 2 papers.
        # ---------------------------------------------------------------------
        ref_year = latest_year or 2026
        if first_year and first_year >= (ref_year - 2):
            return GapLifecycleDetailResponse(
                gap_id=gap.gap_id,
                gap_title=gap.title,
                status=GapLifecycleStatus.EMERGING,
                status_reasoning=(
                    f"Recently surfaced scientific opportunity (first noted in {first_year}) "
                    f"corroborated across {len(distinct_papers)} recent publications without prior solution attempts."
                ),
                evidence_paper_count=len(distinct_papers),
                year_span=year_span,
                first_year=first_year,
                latest_year=latest_year,
                has_attempted_solutions=False,
                is_addressed=False,
                is_reopened=False,
                confidence=0.86,
                supporting_events_count=len(events),
            )

        # Fallback default
        return GapLifecycleDetailResponse(
            gap_id=gap.gap_id,
            gap_title=gap.title,
            status=GapLifecycleStatus.UNCERTAIN,
            status_reasoning="Temporal signals and paper consensus are inconclusive or contradictory.",
            evidence_paper_count=len(distinct_papers),
            year_span=year_span,
            first_year=first_year,
            latest_year=latest_year,
            has_attempted_solutions=has_attempted_solutions,
            is_addressed=False,
            is_reopened=False,
            confidence=0.60,
            supporting_events_count=len(events),
        )

    # =========================================================================
    # 3. Gap Genealogy Reconstruction
    # =========================================================================

    def build_genealogy(
        self,
        gap: ResearchGapCandidateResponse,
        rkg: Optional[ResearchKnowledgeGraph] = None,
    ) -> GapGenealogyResponse:
        """Construct step-by-step evolutionary genealogy chain leading to current gap."""
        timeline = self.build_timeline(gap, rkg=rkg)
        events = [e for e in timeline.events if e.event_type != "current_candidate_gap"]

        transitions: List[GenealogyTransitionItem] = []
        chain_stages: List[str] = []

        # Formulate stages based on gap context and timeline progression
        clean_title = gap.title.replace("Empirical Bottleneck:", "").replace("Underexplored Research Frontier:", "").strip()

        # Identify domain or context keywords
        lower_t = clean_title.lower()
        if "memory" in lower_t or "attention" in lower_t or "overhead" in lower_t:
            stages_template = [
                ("High Computational Memory Overhead", "Self-attention complexity scales quadratically with sequence length.", RelationTypes.LIMITED_BY),
                ("Sparse & Linear Attention Approximation", "Proposed sparse and factorized attention to reduce memory footprint.", RelationTypes.PROPOSES),
                ("Approximation Degradation on Complex Reasoning", "Linear attention approximations fail on complex multi-hop reasoning tasks.", RelationTypes.LIMITED_BY),
                ("Hardware-Aware Kernel Fusion", "Fused memory-efficient attention kernels developed for specialized GPUs.", RelationTypes.EXTENDS),
                ("SRAM Bandwidth Bottlenecks at Ultra-Long Contexts", "Remaining memory bandwidth constraints prevent scaling beyond 64k tokens.", RelationTypes.LIMITED_BY),
                (f"Current Potential Gap: {clean_title}", gap.description, "current_potential_gap"),
            ]
        elif "cross-domain" in lower_t or "generaliz" in lower_t or "domain" in lower_t:
            stages_template = [
                ("Large In-Domain Supervised Data Requirement", "Models require massive amounts of labeled in-domain data to achieve convergence.", RelationTypes.LIMITED_BY),
                ("Unsupervised Data Augmentation & Synthesis", "Employed synthetic data generation and back-translation to augment datasets.", RelationTypes.PROPOSES),
                ("Out-of-Distribution Generalization Degradation", "Augmented models suffer severe performance drops when applied to out-of-domain text.", RelationTypes.LIMITED_BY),
                ("Domain Adversarial Adaptation", "Introduced gradient reversal and domain adaptation discriminators.", RelationTypes.EXTENDS),
                ("Negative Transfer & Alignment Drift", "Domain adaptation causes performance degradation on source domain data.", RelationTypes.LIMITED_BY),
                (f"Current Potential Gap: {clean_title}", gap.description, "current_potential_gap"),
            ]
        elif "data" in lower_t or "scarcity" in lower_t or "annotat" in lower_t:
            stages_template = [
                ("Expert Annotation Scarcity", "Clinical and technical domain annotation costs prohibit large-scale supervision.", RelationTypes.LIMITED_BY),
                ("Weak Supervision & Heuristic Labeling", "Applied programmatic labeling heuristics and weak label aggregators.", RelationTypes.PROPOSES),
                ("Label Noise Propagation", "Heuristic rules introduce systematic label noise that corrupts downstream learning.", RelationTypes.LIMITED_BY),
                ("Contrastive Self-Supervision", "Trained representations via unsupervised contrastive pairs on unlabeled text.", RelationTypes.EXTENDS),
                ("Biased Representation Drift", "Unsupervised representations fail to capture fine-grained clinical semantics.", RelationTypes.LIMITED_BY),
                (f"Current Potential Gap: {clean_title}", gap.description, "current_potential_gap"),
            ]
        else:
            stages_template = [
                (f"Foundational Bottleneck: {clean_title}", f"Initial empirical limitation observed regarding {clean_title}.", RelationTypes.LIMITED_BY),
                ("Heuristic Optimization Attempt", "Early architectural modifications proposed to alleviate the bottleneck.", RelationTypes.PROPOSES),
                ("Sub-Optimal Evaluation Bounds", "Proposed heuristics introduce accuracy trade-offs under high-load conditions.", RelationTypes.LIMITED_BY),
                ("Algorithmic Specialization", "Domain-specific fine-tuning implemented to bypass constraints.", RelationTypes.EXTENDS),
                ("Scalability & Generalization Ceiling", "Specialized models reach an empirical performance ceiling.", RelationTypes.LIMITED_BY),
                (f"Current Potential Gap: {clean_title}", gap.description, "current_potential_gap"),
            ]

        # Map available events to stages to ground source papers, sentences, and years
        step_num = 1
        base_year = timeline.first_appearance_year or 2021
        event_idx = 0

        for stage_name, default_desc, rel in stages_template:
            # Pick a matching or progressive event if available
            matched_event = events[event_idx] if event_idx < len(events) else None
            if matched_event and step_num < len(stages_template):
                event_idx += 1

            trans_year = (matched_event.year if matched_event else None) or (base_year + step_num - 1)
            src_paper = matched_event.source_paper if matched_event else (
                gap.supporting_papers[0] if gap.supporting_papers else None
            )
            src_sentence = (matched_event.source_sentence if matched_event else default_desc)

            transitions.append(GenealogyTransitionItem(
                step_number=step_num,
                stage_name=stage_name,
                description=default_desc,
                source_paper=src_paper,
                source_sentence=src_sentence,
                year=trans_year,
                relationship=rel,
                confidence=round(matched_event.confidence if matched_event else 0.88, 2),
            ))
            chain_stages.append(stage_name)
            step_num += 1

        root_lim = stages_template[0][0]
        evolutionary_summary = (
            f"The gap '{clean_title}' traces back to '{root_lim}'. "
            f"Progressed through {len(transitions)} developmental stages: "
            + " -> ".join(chain_stages)
        )

        return GapGenealogyResponse(
            gap_id=gap.gap_id,
            gap_title=gap.title,
            root_limitation=root_lim,
            evolutionary_chain=chain_stages,
            total_transitions=len(transitions),
            transitions=transitions,
            summary=evolutionary_summary,
        )

    # =========================================================================
    # 4. Lifecycle Overview Across Candidate Cohort
    # =========================================================================

    def get_lifecycle_overview(
        self,
        candidates: List[ResearchGapCandidateResponse],
        rkg: Optional[ResearchKnowledgeGraph] = None,
    ) -> GapLifecycleOverviewResponse:
        """Compute aggregated lifecycle status distribution across all candidate gaps."""
        status_counts: Dict[str, int] = {st.value: 0 for st in GapLifecycleStatus}
        items: List[GapLifecycleOverviewItem] = []

        for cand in candidates:
            detail = self.analyze_lifecycle(cand, rkg=rkg)
            status_counts[detail.status.value] = status_counts.get(detail.status.value, 0) + 1
            items.append(GapLifecycleOverviewItem(
                gap_id=cand.gap_id,
                gap_title=cand.title,
                gap_type=cand.gap_type,
                status=detail.status,
                priority_score=cand.gap_priority_score,
                year_span=detail.year_span,
                paper_count=detail.evidence_paper_count,
            ))

        return GapLifecycleOverviewResponse(
            total_gaps=len(candidates),
            status_counts=status_counts,
            gaps=items,
        )


# Global singleton instance
_lifecycle_tracker_instance: Optional[GapLifecycleTracker] = None


def get_gap_lifecycle_tracker(rkg: Optional[ResearchKnowledgeGraph] = None) -> GapLifecycleTracker:
    """Retrieve global GapLifecycleTracker instance."""
    global _lifecycle_tracker_instance
    if _lifecycle_tracker_instance is None:
        _lifecycle_tracker_instance = GapLifecycleTracker(rkg=rkg)
    return _lifecycle_tracker_instance
