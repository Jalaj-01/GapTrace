# ResearchGapX: All-Phases End-to-End Testing & Verification Guide

This guide provides step-by-step instructions, isolated test commands, cURL requests, expected JSON payloads, and verification checklists to test **Phases 0 through 4** one by one.

---

## Architecture Pipeline Flow

```
[Phase 0: Core Foundation]
FastAPI Server + DB Engine (PostgreSQL / SQLite Dev Fallback) + Error Envelope
                            │
                            ▼
[Phase 1: PDF Ingestion & Document Structuring]
Upload PDF ──► PyMuPDF Extraction ──► Metadata (Title/Year/Authors) ──► Sections & References
                            │
                            ▼
[Phase 2: Scientific NLP & Discourse Analysis]
Preprocessing ──► Sentence Segmentation ──► Discourse Classification ──► Limitation & Future Work Detectors
                            │
                            ▼
[Phase 3: Semantic Embeddings & Evidence Retrieval]
Sentence Transformers (384-d) ──► FAISS Dense Vector Index ──► TF-IDF Baseline ──► Provenance-Grounded Search
                            │
                            ▼
[Phase 4: Research Landscape & Topic Discovery]
BERTopic + HDBSCAN + c-TF-IDF ──► Longitudinal Trajectory Analysis (Emerging / Persistent / Declining) ──► Trends API
```

---

## Environment Setup & Quick Start

Before running tests, ensure environment variables and terminal settings are configured:

```powershell
# In PowerShell (Project Root: G:\NLP)
$env:OPENBLAS_NUM_THREADS="1"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
```

To run the backend development server:
```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Phase 0: Core Architecture, Database, & Diagnostics

### Goal
Verify the FastAPI backend engine, PostgreSQL/SQLite connection pool, configuration loading, centralized error handling envelopes, and service health diagnostics.

### 1. Isolated Automated Tests
Run only the Phase 0 test suite:
```powershell
python -m pytest backend/tests/test_config.py backend/tests/test_errors.py backend/tests/test_health.py -v
```

### 2. Manual CLI Verification
Run the database connection verification tool:
```powershell
python -m backend.scripts.verify_db
```
*Expected Output*:
- Database connectivity confirmed (PostgreSQL or fallback SQLite at `./data/metadata/gap_finder_dev.db`).
- Table schema check passes (`Base.metadata.create_all`).

### 3. API Verification
**Request: Health Check Endpoint**
```bash
curl -X GET http://localhost:8000/api/v1/health
```
**Expected Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "database": {
    "status": "connected",
    "dialect": "sqlite"
  },
  "services": {
    "api": "operational"
  }
}
```

### Phase 0 Checklist
- [ ] Pytest passes: `test_config.py`, `test_errors.py`, `test_health.py` (6 passed).
- [ ] Database fallback connects to SQLite when PostgreSQL is offline.
- [ ] `GET /api/v1/health` returns status `healthy`.
- [ ] Error envelopes return structured JSON with `"success": false` and `"error": {"code": ...}`.

---

## Phase 1: PDF Ingestion & Document Structuring

### Goal
Extract structured scientific document components (Title, Authors, Abstract, Year, Section hierarchy, and Bibliographic references) from raw PDF papers.

### 1. Isolated Automated Tests
Run only the Phase 1 test suite:
```powershell
python -m pytest backend/tests/test_paper_processor.py backend/tests/test_paper_upload_api.py backend/tests/test_papers_api.py -v
```

### 2. API Verification
**A. Upload a Paper (Multipart Form)**
```bash
curl -X POST http://localhost:8000/api/v1/papers/upload \
  -H "Accept: application/json" \
  -F "file=@data/raw/sample_paper.pdf"
```
**Expected Response:**
```json
{
  "paper_id": 1,
  "title": "Adversarial Adaptation in Cross-Domain Scientific NLP",
  "authors": ["Author One", "Author Two"],
  "year": 2024,
  "page_count": 8,
  "file_hash": "a1b2c3d4e5f6...",
  "sections_count": 5,
  "references_count": 18
}
```

**B. Get Structured Paper with Sections and References**
```bash
curl -X GET http://localhost:8000/api/v1/papers/1
```

### Phase 1 Checklist
- [ ] Pytest passes: `test_paper_processor.py`, `test_paper_upload_api.py`, `test_papers_api.py` (19 passed).
- [ ] Magic byte validation rejects non-PDF extensions and corrupted files with HTTP 400/422.
- [ ] SHA-256 deduplication rejects identical PDF uploads with HTTP 409 Conflict.
- [ ] Structural sections (Introduction, Methodology, Limitations, Results) are parsed with line and page numbers.

---

## Phase 2: Scientific NLP & Discourse Classification

### Goal
Segment sections into individual scientific sentences and classify them into scientific discourse types (`PROBLEM`, `OBJECTIVE`, `METHOD`, `DATASET`, `METRIC`, `RESULT`, `LIMITATION`, `FUTURE_WORK`) while tracking end-to-end provenance.

### 1. Isolated Automated Tests
Run only the Phase 2 test suite:
```powershell
python -m pytest backend/tests/test_nlp_unit.py backend/tests/test_nlp_integration.py -v
```

### 2. API Verification
**A. Trigger NLP Pipeline on an Ingested Paper**
```bash
curl -X POST http://localhost:8000/api/v1/nlp/process/1
```
**Expected Response:**
```json
{
  "paper_id": 1,
  "title": "Adversarial Adaptation in Cross-Domain Scientific NLP",
  "total_sentences": 42,
  "total_extractions": 38,
  "extractions_by_type": {
    "PROBLEM": 4,
    "METHOD": 12,
    "RESULT": 8,
    "LIMITATION": 5,
    "FUTURE_WORK": 4,
    "DATASET": 3,
    "METRIC": 2
  },
  "provenance_verified": true
}
```

**B. Fetch Detected Limitations with Provenance**
```bash
curl -X GET http://localhost:8000/api/v1/nlp/papers/1/limitations
```
**Expected Response:**
```json
[
  {
    "id": 10,
    "paper_id": 1,
    "sentence_id": 35,
    "limitation_text": "A primary limitation of our approach is high computational overhead...",
    "limitation_type": "computational",
    "confidence": 0.85,
    "section_name": "Limitations",
    "page_number": 7,
    "provenance": {
      "paper_id": 1,
      "sentence_id": 35,
      "section_name": "Limitations",
      "page_number": 7,
      "paragraph_id": 2
    }
  }
]
```

### Phase 2 Checklist
- [ ] Pytest passes: `test_nlp_unit.py` and `test_nlp_integration.py` (37 passed).
- [ ] Scientific preprocessor normalizes Unicode ligatures and repairs hyphenated line breaks.
- [ ] Sentence segmenter preserves citations (e.g. `[1]`, `et al.`), decimals, and abbreviations without false breaks.
- [ ] Every extracted claim preserves exact provenance (`paper_id`, `section_name`, `page_number`, `sentence_id`).

---

## Phase 3: Semantic Representation & Evidence Retrieval

### Goal
Generate dense 384-dimensional semantic embeddings (using Sentence Transformers), index them into FAISS CPU (`FlatIP` inner product / cosine similarity), provide a statistical TF-IDF baseline, and enable semantic retrieval with filters.

### 1. Isolated Automated Tests
Run only the Phase 3 test suite:
```powershell
python -m pytest backend/tests/test_phase3_retrieval_unit.py backend/tests/test_phase3_retrieval_integration.py -v
```

### 2. Manual Retrieval Benchmark Evaluation
Run the automated Information Retrieval evaluation benchmark:
```powershell
python -m backend.app.services.retrieval.evaluator
```
*Expected Output*:
- Evaluates 5 annotated scientific queries across 10 ground-truth evidence passages.
- Computes Precision@5, Recall@5, Precision@10, Recall@10, and MRR.
- Outputs comparative table: **MRR: 1.0000** for both TF-IDF and Semantic Retrieval.

### 3. API Verification
**A. Dense Semantic Search**
```bash
curl -X GET "http://localhost:8000/api/v1/search/semantic?q=cross-domain+generalization+in+low-resource+settings&top_k=3"
```
**Expected Response:**
```json
{
  "query": "cross-domain generalization in low-resource settings",
  "total_results": 3,
  "retrieval_method": "faiss_semantic",
  "model_name": "sentence-transformers/all-MiniLM-L6-v2",
  "results": [
    {
      "source_text": "Cross-domain generalization degrades substantially when evaluating the model on out-of-distribution abstracts...",
      "similarity_score": 0.8124,
      "paper": {
        "id": 1,
        "title": "Adversarial Adaptation in Cross-Domain Scientific NLP",
        "year": 2024
      },
      "section": "Limitations",
      "page": 8,
      "extraction_type": "LIMITATION",
      "provenance": {
        "paper_id": 1,
        "section_name": "Limitations",
        "page_number": 8,
        "sentence_id": 35
      }
    }
  ]
}
```

**B. Evidence Search with Section Filter & TF-IDF Baseline Switch**
```bash
curl -X GET "http://localhost:8000/api/v1/evidence/search?q=computational+complexity&method=tfidf&section=Limitations"
```

**C. Check Vector Store Diagnostics**
```bash
curl -X GET http://localhost:8000/api/v1/evidence/stats
```
**Expected Response:**
```json
{
  "model_name": "sentence-transformers/all-MiniLM-L6-v2",
  "embedding_dimension": 384,
  "total_faiss_vectors": 45,
  "total_tfidf_documents": 45,
  "status": "operational"
}
```

### Phase 3 Checklist
- [ ] Pytest passes: `test_phase3_retrieval_unit.py` and `test_phase3_retrieval_integration.py` (24 passed).
- [ ] FAISS index persists to disk (`faiss_index.bin`) and metadata loads from `vector_metadata.json`.
- [ ] Querying with empty query string returns validation error (HTTP 400/422).
- [ ] Filters (`paper_id`, `section`, `year`, `extraction_type`) restrict returned results correctly.
- [ ] Both `method=semantic` and `method=tfidf` return valid responses with matching provenance structures.

---

## Phase 4: Research Landscape & Topic Discovery

### Goal
Perform unsupervised theme discovery across the scientific corpus using BERTopic, HDBSCAN, and c-TF-IDF; track longitudinal progression by publication year; and categorize themes into `EMERGING`, `DECLINING`, `PERSISTENT`, and `OUTLIER`.

### 1. Isolated Automated Tests
Run only the Phase 4 test suite:
```powershell
python -m pytest backend/tests/test_phase4_landscape_unit.py backend/tests/test_phase4_landscape_integration.py -v
```

### 2. Manual Topic Coherence Comparison
Run the topic coherence evaluation tool:
```powershell
python -c "
import json
from backend.app.services.landscape.coherence_evaluator import TopicCoherenceEvaluator

with open('data/evaluation/phase3_retrieval_benchmark.json') as f:
    corpus = [item['text'] for item in json.load(f)['corpus']]

evaluator = TopicCoherenceEvaluator()
res = evaluator.evaluate_comparison(corpus, n_clusters=3)
print(json.dumps(res, indent=2))
"
```
*Expected Output*:
- Baseline KMeans Coherence: ~`0.2579`
- BERTopic Semantic Coherence: ~`0.2790` (Higher coherence reflecting superior semantic grouping).

### 3. API Verification
**A. Trigger Landscape Topic Discovery**
```bash
curl -X POST "http://localhost:8000/api/v1/topics/discover?min_cluster_size=2"
```
**Expected Response:**
```json
{
  "total_topics": 5,
  "total_papers_analyzed": 5,
  "outlier_papers_count": 0,
  "major_topics": [...],
  "emerging_topics": [...],
  "declining_topics": [...],
  "persistent_topics": [...],
  "algorithm_used": "BERTopic",
  "generated_at": "2026-10-01T..."
}
```

**B. List Discovered Topics**
```bash
curl -X GET http://localhost:8000/api/v1/topics
```

**C. Get Topic Details with Assigned Papers and Temporal Trends**
```bash
curl -X GET http://localhost:8000/api/v1/topics/0
```
**Expected Response:**
```json
{
  "topic_id": 0,
  "topic_name": "Topic 0: Cross-Domain & Generalization",
  "status": "EMERGING",
  "paper_count": 2,
  "sentence_count": 6,
  "representative_terms": [
    {"term": "cross-domain", "weight": 0.4821},
    {"term": "generalization", "weight": 0.4419}
  ],
  "trends": [
    {"year": 2024, "paper_count": 1, "percentage": 50.0},
    {"year": 2025, "paper_count": 1, "percentage": 50.0}
  ],
  "papers": [
    {"paper_id": 1, "title": "Adversarial Adaptation in Cross-Domain Scientific NLP", "year": 2024, "probability": 0.92}
  ]
}
```

**D. Query Yearly Topic Progression Trends**
```bash
curl -X GET http://localhost:8000/api/v1/topics/trends
```

### Phase 4 Checklist
- [ ] Pytest passes: `test_phase4_landscape_unit.py` and `test_phase4_landscape_integration.py` (21 passed).
- [ ] Topics generate representative terms with c-TF-IDF weights.
- [ ] Statuses (`EMERGING`, `DECLINING`, `PERSISTENT`, `OUTLIER`) are mathematically assigned based on regression slope $\beta$ and recent volume ratio $R_{\text{recent}}$.
- [ ] Small datasets ($N < 5$), single documents, and missing publication years are handled gracefully without exceptions.
- [ ] Nonexistent topic IDs return HTTP 404 Not Found.

---

## Phase 5: Provenance-Aware Research Knowledge Graph

### Goal
Synthesize all extracted entities, citations, claims, empirical findings, methods, datasets, limitations, and future directions into a directed knowledge graph with evidence grounding and graph database migration export.

### 1. Isolated Automated Tests
Run only the Phase 5 test suite:
```powershell
python -m pytest backend/tests/test_phase5_graph_unit.py backend/tests/test_phase5_graph_integration.py -v
```
*(21 passed: 14 unit tests + 7 integration tests)*

### 2. API Verification
**A. Knowledge Graph Overview**
```bash
curl -X GET http://localhost:8000/api/v1/graph/overview
```
**Expected Response:**
```json
{
  "total_nodes": 48,
  "total_edges": 62,
  "density": 0.0274,
  "connected_components_count": 3,
  "node_counts_by_type": {
    "Paper": 5,
    "Author": 8,
    "Method": 12,
    "Dataset": 4,
    "Limitation": 6,
    "FutureDirection": 5,
    "Finding": 8
  },
  "edge_counts_by_type": {
    "cites": 6,
    "uses": 18,
    "proposes": 22,
    "extends": 4,
    "limited_by": 6,
    "addresses": 3,
    "belongs_to": 5
  },
  "graph_database_engine": "NetworkX (Ready for Neo4j / Memgraph migration)"
}
```

**B. Get Paper Ego-Subgraph**
```bash
curl -X GET "http://localhost:8000/api/v1/graph/paper/1?hops=1"
```

**C. Execute Targeted Scientific Queries**
```bash
# Query 1: Papers addressing a limitation
curl -X GET "http://localhost:8000/api/v1/graph/query?query_type=addressing_limitation&text=computational+overhead"

# Query 2: Papers extending a method
curl -X GET "http://localhost:8000/api/v1/graph/query?query_type=extending_method&text=FlashAttention"

# Query 3: Methods used for a dataset
curl -X GET "http://localhost:8000/api/v1/graph/query?query_type=methods_for_dataset&text=SQuAD"

# Query 6: Papers connected to a topic
curl -X GET "http://localhost:8000/api/v1/graph/query?query_type=papers_for_topic&topic_id=0"
```

**D. Export Cypher Ingestion Statements for Neo4j**
```bash
curl -X GET http://localhost:8000/api/v1/graph/export/cypher
```

### Phase 5 Checklist
- [ ] Pytest passes: `test_phase5_graph_unit.py` and `test_phase5_graph_integration.py` (21 passed).
- [ ] All 10 node types created with provenance (`paper_id`, `section_name`, `page_number`, `source_text`).
- [ ] All 11 directed relationship types maintain confidence scores and extraction method provenance.
- [ ] Duplicate entity handling merges aliases (`bert`, `bert base` -> `BERT`) without fabricating nodes.
- [ ] Disconnected and isolated papers are safely represented without topological corruption.
- [ ] Neo4j / Memgraph Cypher export outputs executable `MERGE` statements.

---

## Phase 6: Research Gap Candidate Engine

### Goals Verified
- Generation of evidence-grounded potential research gaps from measurable signals.
- Strict enforcement: candidates originate from NLP and graph signals, not hallucinated LLM prompts.
- Explicit distinction between `potential_gap` and `verified_gap` (`verification_status="potential_gap"`).
- Strict evidence requirement: rejection of candidates without supporting papers or source sentence evidence.
- Fully explainable prioritization scoring ($S_{\text{priority}} = \sum w_k \cdot s_k$) with documented weights summing to 1.00.
- Detection of all 7 signals: Underexploration, Repeated Limitations, Methodological Concentration, Dataset Concentration, Temporal Opportunity, Cross-Domain Opportunity, and Conflicting Evidence.

### Automated Testing

Run the Phase 6 test suite:

```powershell
$env:OPENBLAS_NUM_THREADS="1"; $env:OMP_NUM_THREADS="1"; python -m pytest backend/tests/test_phase6_gaps_unit.py backend/tests/test_phase6_gaps_integration.py -v
```

*Expected Result*: **19/19 passed** in ~9-11 seconds.

### Manual Verification via cURL / HTTP Requests

**A. Retrieve All Detected Research Gap Candidates**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/candidates?min_priority=0.20&limit=10"
```

**B. Filter Candidates by Gap Type**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/candidates?gap_type=repeated_limitation"
```

**C. Inspect Candidate Detail and Score Breakdown**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/candidates/gap-limitation-computational-memory-overhead"
```

**D. Retrieve Grounded Source Evidence for a Candidate Gap**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/candidates/gap-limitation-computational-memory-overhead/evidence"
```

**E. Inspect the 7 Measurable Gap Signals Registry and Canonical Weights**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/signals"
```

### Phase 6 Checklist
- [ ] Pytest passes: `test_phase6_gaps_unit.py` and `test_phase6_gaps_integration.py` (19 passed).
- [ ] All 7 signals activate on synthetic and graph patterns (HHI, contradiction edges, multi-year persistence).
- [ ] Prioritization score is explainable with weights summing to 1.00 ($w_{\text{rep}}=0.25, w_{\text{under}}=0.20, \dots$).
- [ ] Candidates strictly declare `verification_status="potential_gap"`.
- [ ] Insufficient evidence rejection: candidates lacking source papers or sentences are rejected.
- [ ] Precision@5 (1.00) and Recall@10 (0.80) verified against expert-curated ground truth benchmark.

---

## Phase 7: Gap Genealogy and Gap Lifecycle

### Goals Verified
- Tracking of gap evolution across publication years.
- Lifecycle classification into 6 states: `EMERGING`, `PERSISTENT`, `PARTIALLY_ADDRESSED`, `ADDRESSED`, `REOPENED`, `UNCERTAIN`.
- Strict multi-paper evidence invariant: lifecycle cannot be determined from a solitary paper or an unsupported sentence.
- Chronologically ordered evolution timeline tracking first appearance, repeated limitations, attempted solutions, later evidence, and current status.
- Step-by-step evolutionary genealogy chains with provenance (root problem -> attempted mitigation -> secondary bottleneck -> current candidate gap).
- Graceful handling of missing publication years and duplicate event deduplication.

### Automated Testing

Run the Phase 7 test suite:

```powershell
$env:OPENBLAS_NUM_THREADS="1"; $env:OMP_NUM_THREADS="1"; python -m pytest backend/tests/test_phase7_lifecycle_unit.py backend/tests/test_phase7_lifecycle_integration.py -v
```

*Expected Result*: **18/18 passed** in ~1 second.

### Manual Verification via cURL / HTTP Requests

**A. Retrieve Global Gap Lifecycle Distribution Overview**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/lifecycle/overview"
```

**B. Retrieve Chronological Evolution Timeline for a Specific Gap**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/gap-limitation-computational-memory-overhead/timeline"
```

**C. Retrieve Evolutionary Genealogy Chain for a Specific Gap**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/gap-limitation-computational-memory-overhead/genealogy"
```

**D. Retrieve Lifecycle State and Temporal Evidence Reasoning**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/gap-limitation-computational-memory-overhead/lifecycle"
```

### Phase 7 Checklist
- [ ] Pytest passes: `test_phase7_lifecycle_unit.py` and `test_phase7_lifecycle_integration.py` (18 passed).
- [ ] All 6 lifecycle states validated on synthetic chronological fixtures.
- [ ] Strict multi-paper guard: solitary papers or unsupported sentences yield `UNCERTAIN` status.
- [ ] Timeline events are chronologically non-decreasing ($Y_i \le Y_{i+1}$).
- [ ] Retrospective citations properly tagged (`is_retrospective=True`).
- [ ] Genealogy transitions contain source paper, sentence, year, relationship, and confidence.
- [ ] Both root paths (`/{gap_id}/...`) and candidate aliases (`/candidates/{gap_id}/...`) function identically.

---

## Phase 8: Counter-Evidence Search and Gap Verification

### Goals Verified
- Active adversarial search for opposing and contradictory scientific evidence.
- Multi-category evidence exposure (Supporting, Counter, Addressed By, Contradictory).
- Avoidance of opaque "truth scores" by maintaining explicit evidence buckets.
- Scientific Natural Language Inference (`ENTAILMENT`, `CONTRADICTION`, `NEUTRAL`).
- Verification decision logic: `VERIFIED_OPEN`, `REFUTED`, `ADDRESSED`, `PARTIALLY_ADDRESSED`, `OUTDATED`, `UNCERTAIN`.
- Strict multi-paper guard: solitary papers or unsupported assertions cannot be verified.
- Strong counter-evidence directly reduces confidence and refutes candidates.

### Automated Testing

Run the Phase 8 test suite:

```powershell
$env:OPENBLAS_NUM_THREADS="1"; $env:OMP_NUM_THREADS="1"; python -m pytest backend/tests/test_phase8_verification_unit.py backend/tests/test_phase8_verification_integration.py -v
```

*Expected Result*: **17/17 passed** in ~1 second.

### Manual Verification via cURL / HTTP Requests

**A. Retrieve Multi-Category Gap Verification Analysis**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/gap-limitation-computational-memory-overhead/verification"
```

**B. Retrieve Targeted Counter-Evidence and Refutations**
```bash
curl -X GET "http://localhost:8000/api/v1/gaps/gap-limitation-computational-memory-overhead/counter-evidence"
```

**C. Trigger Active Verification and Scientific NLI Evaluation**
```bash
curl -X POST "http://localhost:8000/api/v1/gaps/gap-limitation-computational-memory-overhead/verify" \
     -H "Content-Type: application/json" \
     -d '{"min_confidence": 0.60, "include_nli": true}'
```

### Phase 8 Checklist
- [ ] Pytest passes: `test_phase8_verification_unit.py` and `test_phase8_verification_integration.py` (17 passed).
- [ ] Scientific NLI correctly classifies entailment, contradiction, and neutral premise-hypothesis pairs.
- [ ] 7 synthetic scenarios verified (`VERIFIED_OPEN`, `OUTDATED`, `PARTIALLY_ADDRESSED`, `UNCERTAIN`, `REFUTED`).
- [ ] Counter-evidence penalties significantly reduce verification confidence when refutations occur.
- [ ] All 3 verification endpoints and candidate path aliases return HTTP 200 with valid schema.

---

## Full Regression Test Suite (All Phases Combined)

To run the complete suite of **182 backend tests** across all phases (Phases 0 through 8):

```powershell
$env:OPENBLAS_NUM_THREADS="1"; $env:OMP_NUM_THREADS="1"; python -m pytest backend/tests -v
```

### Expected Output Summary
```
============================ 182 passed in 20.30s =============================
- Phase 0 Tests (Config, Errors, Health):          6 PASSED
- Phase 1 Tests (PDF Processing, Papers API):      19 PASSED
- Phase 2 Tests (Scientific NLP, Detectors):        37 PASSED
- Phase 3 Tests (Embeddings, FAISS, Retrieval):     24 PASSED
- Phase 4 Tests (Landscape, Topics, Dynamics):      21 PASSED
- Phase 5 Tests (Knowledge Graph, Queries, Cypher): 21 PASSED
- Phase 6 Tests (Gap Signals, Priorities, APIs):    19 PASSED
- Phase 7 Tests (Genealogy, Lifecycle, Timeline):   18 PASSED
- Phase 8 Tests (Counter-Evidence, Verification):   17 PASSED
```

To run the frontend test suite:
```powershell
cd frontend
npm test
```
*Expected Result*: **6/6 passed** (Tests rendering, header metrics, and UI components).
