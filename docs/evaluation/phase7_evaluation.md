# Phase 7 Evaluation: Gap Genealogy and Gap Lifecycle

## Overview

**Phase 7** implements the **Gap Genealogy and Gap Lifecycle Engine** for **ResearchGapX**. Research gaps are not static entities; they evolve across publication years through successive waves of empirical discovery, proposed algorithmic mitigations, derivative bottlenecks, domain adaptations, and eventual resolution or reopening.

### Core Architectural Invariants

1. **Strict Multi-Paper Invariant**:
   $$\text{Evidence}(\text{gap}) < 2 \text{ papers} \implies \text{Lifecycle Status} = \text{UNCERTAIN}$$
   The engine **never** determines a lifecycle status from a solitary paper or an unsupported sentence. Without multi-paper temporal consensus, the lifecycle status is rigorously classified as `UNCERTAIN`.
2. **Chronological Invariance**:
   All timeline events and genealogy transitions are strictly sorted chronologically ($Y_i \le Y_{i+1}$). Solutions published in later years cannot precede limitations unless explicitly categorized with `is_retrospective=True` (e.g., retrospective citation or claim).
3. **Traceable Evolutionary Transitions**:
   Every transition in a gap genealogy chain must preserve fine-grained provenance: `source_paper`, `source_sentence`, `year`, `relationship`, and `confidence`.

---

## 1. Lifecycle Definitions

The system models gap evolution through **6 distinct lifecycle states**:

| Lifecycle Status | Operational Definition | Temporal & Evidence Criteria |
| :--- | :--- | :--- |
| **`EMERGING`** | Recently surfaced scientific bottleneck gaining active research interest. | First recorded in recent literature ($\text{first\_year} \ge \text{current\_year} - 2$), corroborated by $\ge 2$ distinct publications, with zero attempted solutions proposed yet. |
| **`PERSISTENT`** | Chronic, unresolved bottleneck that endures across multiple publication cycles. | Spans $\Delta Y = Y_{\text{latest}} - Y_{\text{first}} \ge 2$ years, corroborated across $\ge 2$ distinct publications, with no successful or accepted solutions. |
| **`PARTIALLY_ADDRESSED`** | Bottleneck where algorithmic mitigations exist, but residual limitations remain. | Attempted solution(s) exist ($k \ge 1$), but concurrent or subsequent literature explicitly reports residual caveats, subdomain constraints, or partial mitigations. |
| **`ADDRESSED`** | Bottleneck that has been resolved by a high-confidence solution with no subsequent recurrence. | High-confidence solution exists ($\ge 0.80$), and **zero** subsequent or concurrent papers in later literature report recurrence or unaddressed limitations. |
| **`REOPENED`** | Bottleneck previously considered mitigated/solved that has recurred in newer literature. | An attempted solution was published in year $Y_{\text{sol}}$, but subsequent publications at $Y_{\text{later}} > Y_{\text{sol}}$ report that the limitation re-emerged or failed under new benchmarks. |
| **`UNCERTAIN`** | Inconclusive temporal signal, contradictory literature, or solitary paper. | Fewer than 2 distinct papers, single unsupported sentence, or conflicting/irreconcilable claims without consensus. |

---

## 2. Transition Rules & State Machine

```
             ┌────────────────────────────────────────────────────────┐
             │                 Candidate Research Gap                 │
             └──────────────────────────┬─────────────────────────────┘
                                        │
                         Multi-paper evidence >= 2?
                                        │
                        ┌───────────────┴───────────────┐
                       No                              Yes
                        │                               │
                        ▼                               ▼
                 [ UNCERTAIN ]                Attempted solutions exist?
                                                        │
                                        ┌───────────────┴───────────────┐
                                       No                              Yes
                                        │                               │
                        Span >= 2 yrs?          Later publications (Y > Y_sol)
                        ┌───────┴───────┐       report recurring bottleneck?
                       Yes              No              │
                        │               │       ┌───────┴───────┐
                        ▼               ▼      Yes              No
                  [PERSISTENT]      [EMERGING]  │               │
                                                ▼        Partial mitigation /
                                           [REOPENED]    residual caveats reported?
                                                                │
                                                        ┌───────┴───────┐
                                                       Yes              No
                                                        │               │
                                                        ▼               ▼
                                              [PARTIALLY_ADDRESSED] [ADDRESSED]
```

### Detailed Transition Logic

1. **Multi-Paper Guard**:
   If `distinct_papers < 2` or `evidence_count < 2`:
   $$\text{status} \leftarrow \text{UNCERTAIN}$$
   $$\text{reason} \leftarrow \text{"Insufficient multi-paper temporal evidence. Lifecycle cannot be inferred from a single paper or unsupported sentence."}$$

2. **Reopening Trigger**:
   If solutions exist at year $Y_{\text{sol}}$ and any subsequent paper at $Y_{\text{later}} > Y_{\text{sol}}$ reports the bottleneck:
   $$\text{status} \leftarrow \text{REOPENED}$$

3. **Partial Mitigation Trigger**:
   If solutions exist, but partial solution events or concurrent limitations occur at $Y = Y_{\text{sol}}$:
   $$\text{status} \leftarrow \text{PARTIALLY_ADDRESSED}$$

4. **Addressed Trigger**:
   If solutions exist with average confidence $\ge 0.80$ and zero limitations occur at $Y \ge Y_{\text{sol}}$:
   $$\text{status} \leftarrow \text{ADDRESSED}$$

5. **Persistence Trigger**:
   If no solutions exist and $\Delta Y \ge 2$ years across $\ge 2$ papers:
   $$\text{status} \leftarrow \text{PERSISTENT}$$

6. **Emergence Trigger**:
   If no solutions exist and $Y_{\text{first}} \ge Y_{\text{ref}} - 2$:
   $$\text{status} \leftarrow \text{EMERGING}$$

---

## 3. Genealogy Examples

The genealogy engine models the evolutionary trajectory of scientific challenges through structured multi-stage chains.

### Example A: Attention Memory Complexity Progression

```
[Step 1: 2021] High Computational Memory Overhead
  └── Relationship: limited_by
  └── Source: Scaling Transformer Sequences (Paper #1)
  └── Evidence: "Self-attention complexity scales quadratically O(N^2) with sequence length."
        │
        ▼
[Step 2: 2022] Sparse & Linear Attention Approximation
  └── Relationship: proposes
  └── Source: Factorized Attention Kernels (Paper #5)
  └── Evidence: "We propose block-sparse factorized attention to reduce memory footprint."
        │
        ▼
[Step 3: 2023] Approximation Degradation on Complex Reasoning
  └── Relationship: limited_by
  └── Source: Long-Range Reasoning Benchmarks (Paper #9)
  └── Evidence: "Linear attention approximations fail on complex multi-hop reasoning tasks."
        │
        ▼
[Step 4: 2024] Hardware-Aware Kernel Fusion
  └── Relationship: extends
  └── Source: FlashAttention-2 Evaluation (Paper #12)
  └── Evidence: "Fused memory-efficient attention kernels developed for specialized GPUs."
        │
        ▼
[Step 5: 2025] SRAM Bandwidth Bottlenecks at Ultra-Long Contexts
  └── Relationship: limited_by
  └── Source: 128k Context Frontier (Paper #15)
  └── Evidence: "Remaining SRAM memory bandwidth constraints prevent scaling beyond 64k tokens."
        │
        ▼
[Step 6: 2026] Current Potential Gap: Computational Memory Overhead
  └── Relationship: current_potential_gap
  └── Description: Documented scientific bottleneck regarding computational memory overhead.
```

### Example B: Cross-Domain Adaptation Progression

$$\begin{aligned}
\text{Step 1: Supervised Data Requirement} &\xrightarrow{\text{proposes}} \text{Step 2: Synthetic Data Augmentation} \\
&\xrightarrow{\text{limited\_by}} \text{Step 3: Out-of-Distribution Degradation} \\
&\xrightarrow{\text{extends}} \text{Step 4: Domain Adversarial Adaptation} \\
&\xrightarrow{\text{limited\_by}} \text{Step 5: Negative Transfer \& Alignment Drift} \\
&\xrightarrow{\text{candidate}} \text{Step 6: Current Potential Gap: Cross-Domain Generalization}
\end{aligned}$$

---

## 4. Synthetic Test Results

A comprehensive suite of **18 test cases** was implemented in [`backend/tests/test_phase7_lifecycle_unit.py`](file:///g:/NLP/backend/tests/test_phase7_lifecycle_unit.py) and [`backend/tests/test_phase7_lifecycle_integration.py`](file:///g:/NLP/backend/tests/test_phase7_lifecycle_integration.py).

| Test Group | Test Case | Target Invariant Verified | Result |
| :--- | :--- | :--- | :--- |
| **State Machine** | `test_emerging_gap_lifecycle` | Detects recent onset ($2024\text{--}2025$) with $\ge 2$ papers. | **PASSED** |
| | `test_persistent_gap_lifecycle` | Detects multi-year span ($\ge 2$ yrs) without solutions. | **PASSED** |
| | `test_partially_addressed_gap_lifecycle` | Detects solution with concurrent residual limitations. | **PASSED** |
| | `test_addressed_gap_lifecycle` | Detects high-confidence solution with no subsequent limitations. | **PASSED** |
| | `test_reopened_gap_lifecycle` | Detects solution at $Y_1$ followed by recurrence at $Y_2 > Y_1$. | **PASSED** |
| **Evidence Guards** | `test_single_paper_cannot_determine_lifecycle` | Single paper yields `UNCERTAIN` status. | **PASSED** |
| | `test_single_unsupported_sentence_cannot_determine_lifecycle` | Solo unsupported sentence yields `UNCERTAIN` status. | **PASSED** |
| | `test_missing_publication_year_graceful_handling` | Missing years mapped to median with estimation flag. | **PASSED** |
| | `test_duplicate_events_deduplication` | Deduplicates identical (paper, type, text) events. | **PASSED** |
| **Chronology & Genealogy** | `test_timeline_chronological_ordering` | Verifies strictly non-decreasing event years ($Y_i \le Y_{i+1}$). | **PASSED** |
| | `test_genealogy_chain_consistency` | Verifies 6-step sequential chain with provenance. | **PASSED** |
| | `test_lifecycle_overview_aggregation` | Aggregates accurate status counts across candidate cohort. | **PASSED** |
| **REST APIs** | `test_lifecycle_overview_endpoint` | `GET /api/v1/gaps/lifecycle/overview` returns 200 and schema. | **PASSED** |
| | `test_gap_timeline_endpoint` | `GET /api/v1/gaps/{gap_id}/timeline` returns chronological timeline. | **PASSED** |
| | `test_gap_genealogy_endpoint` | `GET /api/v1/gaps/{gap_id}/genealogy` returns evolutionary chain. | **PASSED** |
| | `test_gap_lifecycle_detail_endpoint` | `GET /api/v1/gaps/{gap_id}/lifecycle` returns status & reasoning. | **PASSED** |
| | `test_candidate_path_aliases` | Verifies `/candidates/{gap_id}/...` aliases function identically. | **PASSED** |
| | `test_nonexistent_gap_returns_404` | Verifies 404 response on unknown candidate ID. | **PASSED** |

---

## 5. Known System Limitations

1. **Corpus Temporal Discontinuity**:
   If an ingested database lacks papers for an intervening 3-year window, an addressed bottleneck may appear `PERSISTENT` due to un-ingested literature.
2. **Retrospective Citation Ambiguity**:
   When a 2025 review paper retrospectively describes a 2018 limitation, heuristic parsing places the event at 2025 with an `is_retrospective=True` flag unless the cited year is explicitly extracted from the sentence text.
3. **No Dynamic Lifecycle Mutation by Users**:
   Candidates and lifecycles reflect literature consensus rather than manual user edits.
4. **Scope Boundary**:
   In strict adherence to Phase 7 specifications, counter-evidence verification and adversarial claims arbitration are reserved for Phase 8.

---

## 6. API Verification Summary

| Endpoint | Method | Status | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/gaps/lifecycle/overview` | GET | `200 OK` | Global distribution of gap lifecycle statuses (`EMERGING`, `PERSISTENT`, etc.) across the ingested literature. |
| `/api/v1/gaps/{gap_id}/timeline` | GET | `200 OK` | Chronologically ordered event sequence from first appearance to current potential gap state. |
| `/api/v1/gaps/{gap_id}/genealogy` | GET | `200 OK` | Step-by-step evolutionary genealogy chain with source paper, sentence, year, and relationship. |
| `/api/v1/gaps/{gap_id}/lifecycle` | GET | `200 OK` | Lifecycle status classification with detailed explanatory reasoning and temporal metrics. |
