# Phase 9 Evaluation: Evidence-Grounded RAG and LLM Synthesis

## Overview

**Phase 9** implements the **Evidence-Grounded RAG and LLM Synthesis Engine** for **ResearchGapX**. The core architectural invariant of this system is that **the LLM is NOT the primary research-gap detection engine**. Gap candidates originate from Phase 6 empirical signals, gap lifecycles originate from Phase 7 state machines, and counter-evidence verification originates from Phase 8 adversarial search.

The LLM is strictly employed as an **evidence-grounded explanatory synthesizer** that translates verified structured findings into clear, publication-grade explanations with verifiable citations.

### Core Architectural Invariants

1. **Structured Gap Ingestion (Not Freeform Generation)**:
   The LLM synthesizes structured multi-modal inputs:
   - Verified Gap Candidate (Phase 6)
   - Supporting Evidence & Provenance (Phase 2, 6, 8)
   - Counter-Evidence & Addressed-By Literature (Phase 8)
   - Evolutionary Genealogy & Lifecycle Status (Phase 7)
   - Research Knowledge Graph Topology (Phase 5)
   - Relevant Retrieved Passages via Dense Retrieval (Phase 3)
2. **Provider Abstraction Layer**:
   Application logic is completely decoupled from any single provider, supporting:
   - Google Gemini (`gemini-2.5-flash`, `gemini-1.5-pro`)
   - OpenAI (`gpt-4o`, `gpt-4o-mini`)
   - Local Models via OpenAI-compatible endpoints (`Ollama`, `vLLM`, `llama.cpp`)
   - Deterministic Mock Provider for offline testing and fault injection
3. **Strict Prompt Safety & Anti-Hallucination Guardrails**:
   - Never invent papers, authors, or venues.
   - Never invent citations. Only use provided evidence tags (`[E1]`, `[E2]`).
   - Never invent experimental benchmarks, numbers, or metrics.
   - Never invent datasets.
   - Distinguish empirical evidence from conceptual inference.
   - Explicitly report evidence sparsity and set `insufficient_evidence: true`.
4. **Automated Citation Validator & Evidence Support Rate (ESR)**:
   - Parses inline citation tags (`[E1]`, `[E2]`) from generated text.
   - Verifies citation existence (flags unknown tags like `[E99]` as `HALLUCINATED_CITATION`).
   - Evaluates factual alignment using Scientific NLI (`ScientificNLIEngine`) and lexical containment.
   - Rejects or flags unsupported and contradicted statements.
   - Computes:
     $$\text{Evidence Support Rate (ESR)} = \frac{\text{Supported Claims with Citations}}{\text{Total Claims with Citations}}$$

---

## 1. Provider Architecture

```
                    ┌─────────────────────────┐
                    │    GapRAGSynthesizer    │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     BaseLLMProvider     │  (Abstract Base Class)
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  GeminiProvider  │   │  OpenAIProvider  │   │ LocalLLMProvider │
│ (Google REST API)│   │ (OpenAI REST API)│   │  (vLLM / Ollama) │
└──────────────────┘   └──────────────────┘   └──────────────────┘
         │
         ▼
┌──────────────────┐
│ MockLLMProvider  │ (Deterministic Testing & Failure Injection)
└──────────────────┘
```

### Provider Matrix

| Provider | Implementation Module | Default Model | Protocol / Endpoint | Error Translation |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini** | `backend/app/services/llm/gemini_provider.py` | `gemini-2.5-flash` | REST API (`generateContent`) | 429 $\to$ `LLMRateLimitError`, Timeout $\to$ `LLMTimeoutError`, 5xx $\to$ `LLMProviderError` |
| **OpenAI** | `backend/app/services/llm/openai_provider.py` | `gpt-4o` | REST API (`/v1/chat/completions`) | 429 $\to$ `LLMRateLimitError`, Timeout $\to$ `LLMTimeoutError`, 5xx $\to$ `LLMProviderError` |
| **Local** | `backend/app/services/llm/local_provider.py` | `llama3` | REST API (`localhost:11434/v1`) | ConnectError $\to$ `LLMProviderError`, Timeout $\to$ `LLMTimeoutError` |
| **Mock** | `backend/app/services/llm/mock_provider.py` | `mock-model-v1` | In-memory simulated dispatch | Configurable modes: `grounded`, `timeout`, `rate_limit`, `malformed_json`, `hallucination`, `unsupported` |

---

## 2. RAG Flow & Citation Resolution

The RAG pipeline extracts specific evidence excerpts without blindly passing full PDF texts into LLM contexts:

```
[Candidate Gap] + [Lifecycle Status] + [Verification Results]
                          │
                          ▼
            [Phase 3 Dense Semantic Retrieval]
     (FAISS IndexFlatIP + Sentence Transformers all-MiniLM-L6-v2)
                          │
                          ▼
            [Multi-Modal Evidence Assembler]
     Assigns unique tags [E1], [E2], ..., [En] to:
     - Supporting evidence sentences
     - Counter-evidence and addressed-by passages
     - Top-k retrieved semantic evidence
                          │
                          ▼
            [Citation Map Resolution Table]
     [E1] ──> { Paper: "Attention Limits", Page: 4, Section: "Analysis", Text: "..." }
     [E2] ──> { Paper: "Sparse Transformers", Page: 7, Section: "Methods", Text: "..." }
                          │
                          ▼
             [Grounded Prompt Construction]
     Injects strict anti-hallucination rules, structured gap metadata,
     and numbered [E1]..[En] excerpts into strict JSON schema
                          │
                          ▼
               [LLM Provider Synthesis]
                          │
                          ▼
            [Automated Citation Validator]
     Extracts claims, verifies citations, checks NLI consistency,
     flags hallucinated citations ([E99]), computes ESR
                          │
                          ▼
               [GapSynthesisResponse]
```

### Synthesis Output Schema (8 Core Sections)

1. **`gap_explanation`**: Clear definition of the bottleneck citing `[E1]`.
2. **`why_it_matters`**: Theoretical and practical significance of the research gap.
3. **`supporting_evidence_summary`**: Multi-paper corroboration of the unresolved constraint.
4. **`counter_evidence_summary`**: Mitigations, partial resolutions, or opposing viewpoints.
5. **`current_status`**: Grounded assessment of current standing based on temporal evidence.
6. **`potential_research_questions`**: Concrete, open empirical questions for future investigation.
7. **`potential_future_directions`**: Algorithmic avenues, model architectures, or benchmark proposals.
8. **`evidence_limitations`**: Explicit evaluation of evidence density, dataset bias, and gaps.
9. **`insufficient_evidence`**: Boolean indicator (`true` if evidence is sparse or uncorroborated).

---

## 3. Automated Citation Validation & Evidence Support Rate

### Citation Audit Rules

For every extracted claim statement:
1. **Citation Extraction**: Regex pattern `r"\[(E\d+)\]"` captures all cited tags.
2. **Hallucination Detection**:
   $$\exists \text{ tag } \notin \text{Context Citations} \implies \text{Status} = \text{HALLUCINATED\_CITATION}, \text{ is\_valid} = \text{False}$$
3. **NLI Factual Verification**:
   The cited source sentence serves as premise and the claim statement serves as hypothesis:
   - If NLI classifies as `CONTRADICTION`:
     $$\text{Status} = \text{CONTRADICTED}, \quad \text{Support Score} = 0.0, \quad \text{is\_valid} = \text{False}$$
   - If NLI classifies as `ENTAILMENT`:
     $$\text{Status} = \text{SUPPORTED}, \quad \text{Support Score} = \max(0.85, \text{Confidence})$$
   - If NLI classifies as `NEUTRAL`:
     Lexical overlap is evaluated via combined Jaccard and containment metrics:
     $$\text{Overlap} = \max\left(\frac{|T_1 \cap T_2|}{|T_1 \cup T_2|}, \frac{|T_1 \cap T_2|}{\min(|T_1|, |T_2|)}\right)$$
     If $\text{Overlap} \ge 0.20$ or $|T_1 \cap T_2| \ge 2$: $\text{Status} = \text{SUPPORTED}$. Otherwise: $\text{Status} = \text{UNSUPPORTED}$.

### Evidence Support Rate (ESR) Formula

$$\text{Evidence Support Rate (ESR)} = \frac{N_{\text{supported claims with citations}}}{N_{\text{total claims with citations}}}$$

A synthesis is marked valid (`is_valid = True`) if and only if:
1. $\text{Hallucinated Citations} = 0$
2. $\text{Contradicted Claims} = 0$
3. $\text{Evidence Support Rate} \ge 0.60$ (configurable threshold)

---

## 4. Failure Modes & Resilience Matrix

| Failure Mode | Trigger / Condition | System Response | HTTP Code |
| :--- | :--- | :--- | :--- |
| **Provider Timeout** | Network latency exceeds configured threshold (e.g. 30s) | Catches timeout, raises `LLMTimeoutError` | `504 Gateway Timeout` |
| **Provider Rate Limit** | Upstream API returns HTTP 429 quota exhaustion | Catches 429, raises `LLMRateLimitError` | `429 Too Many Requests` |
| **Provider Outage** | 502/503 from LLM vendor or connection refused | Catches exception, raises `LLMProviderError` | `502 Bad Gateway` |
| **Malformed JSON** | Model outputs non-JSON text or broken braces | Regex JSON substring extraction with fallback, raises `LLMProviderError` if unrecoverable | `502 Bad Gateway` |
| **Hallucinated Citations** | Model cites unprovided tags like `[E99]` | Flagged as `HALLUCINATED_CITATION`, marked `is_valid = False` | `200` (or `422` with `reject_unsupported=True`) |
| **Contradicted Assertions** | Model claims bottleneck solved when cited text states persistent | Classified as `CONTRADICTED`, `Support Score = 0.0`, `is_valid = False` | `200` (or `422` with `reject_unsupported=True`) |
| **Sparse / Insufficient Data** | Candidate supported by only 1 paper | Synthesizer sets `insufficient_evidence: true` and elaborates in `evidence_limitations` | `200 OK` |

---

## 5. Verification & Test Suite Summary

### Phase 9 Test Coverage (32 Tests)

- **Unit Tests (`backend/tests/test_phase9_synthesis_unit.py`)**: 26 passed
  - Provider Abstraction (Gemini, OpenAI, Local, Mock instantiation and factory resolution)
  - Fault injection (timeout, rate limit, provider upstream failure, malformed JSON)
  - Citation Validator (extraction, split claims, supported, contradicted, unsupported, hallucinated tags, ESR calculation)
  - RAG prompt assembly (multi-modal evidence context, prompt safety invariants)
  - Synthesizer execution (grounded synthesis, insufficient evidence flag, rejection of unsupported claims, cache retrieval)
- **Integration Tests (`backend/tests/test_phase9_synthesis_integration.py`)**: 6 passed
  - `POST /api/v1/gaps/{gap_id}/synthesize`
  - `GET /api/v1/gaps/{gap_id}/synthesis`
  - `POST /api/v1/gaps/validate-citations`
  - 404 response on unknown candidate gap
  - 504 Gateway Timeout on provider timeout
  - 429 Too Many Requests on provider rate limit

### Full Project Regression Status

- **Phases 0–9 Suite**: **214 passed** across 12 test suites in under 30 seconds.

---

## 6. Known Limitations

1. **Local Model Availability**:
   `LocalLLMProvider` requires an active OpenAI-compatible local server (e.g. Ollama or vLLM). When offline, it gracefully reports connection errors.
2. **Context Window Limits**:
   While dense retrieval selectively passes top-$k$ evidence snippets rather than full PDFs, extremely complex research topics with $> 50$ conflicting papers require snippet truncation to adhere to context budgets.
3. **Paraphrase Sensitivity**:
   Highly creative or abstract LLM restatements may achieve lower lexical overlap with cited source sentences, requiring the semantic NLI entailment branch to corroborate alignment.
