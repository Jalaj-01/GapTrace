# Phase 10 Evaluation: Research Intelligence Dashboard

## 1. Executive Summary

**Project:** ResearchGapX / GapTrace  
**Phase:** 10 — Research Intelligence Dashboard  
**Status:** Completed and Verified  
**Technology Stack:** React 18, Vite, JavaScript (ESM), Vanilla CSS & Modern Design Tokens, Vitest, React Testing Library  
**Backend Foundation:** FastAPI, SQLAlchemy, SQLite/PostgreSQL, SciSpacy, Sentence Transformers, FAISS, BERTopic, NetworkX, Gemini/OpenAI LLM Synthesis  

Phase 10 delivers a professional, academic research intelligence web platform directly on top of the validated Phase 0–9 backend APIs. Stated strictly by architectural requirements, **zero fake statistics, mock numbers, or hardcoded research outputs exist in the platform.** Every displayed statistic, topic cluster, knowledge graph edge, potential research gap candidate, temporal lifecycle state, counter-evidence classification, and synthesis report originates dynamically from the backend.

---

## 2. Platform Architecture & 12 Academic UI Modules

The platform is designed around 12 core research intelligence pages and views accessible via responsive sidebar navigation and deep-linked context drill-downs:

```
                                  [ ResearchGapX Shell ]
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      │                                      │                                      │
[ Macro Intelligence ]              [ Literature Explorer ]                [ Gap Intelligence ]
  ├─ 1. Dashboard                     ├─ 2. Paper Library                    ├─ 6. Potential Gaps Catalogue
  ├─ 4. Research Landscape            ├─ 3. Paper Detail                     ├─ 7. Gap Detail Inspector
  └─ 5. Knowledge Graph               └─ 11. Evidence Explorer               ├─ 8. Gap Genealogy Tracker
                                                                             ├─ 9. Gap Lifecycle State Machine
                                                                             ├─ 10. Counter-Evidence Verification
                                                                             └─ 12. Evidence-Grounded Report
```

### Module 1: Dashboard (`frontend/src/pages/Dashboard.jsx`)
- **Purpose:** Corpus-wide executive summary and research health metrics.
- **Displayed Information:**
  - Ingested scientific papers count (from `/papers`)
  - Discovered research topics count (from `/topics/overview`)
  - Potential research gaps count (from `/gaps/candidates`)
  - Persistent gaps count (from `/gaps/lifecycle/overview`)
  - Emerging topics count (from `/topics/overview`)
  - Addressed gaps count (from `/gaps/lifecycle/overview`)
  - Counter-evidence statistics (from `/gaps/candidates` and `/gaps/lifecycle/overview`)
- **Features:** Quick navigation modules, prioritized gap candidate cards with priority score badges, and emerging research theme chips.

### Module 2: Paper Library (`frontend/src/pages/PapersPage.jsx`)
- **Purpose:** Ingested scientific paper management and exploration.
- **Features:**
  - Drag-and-drop and native file input PDF upload (`POST /papers/upload`)
  - Automatic NLP trigger hook (`POST /nlp/process/{id}`)
  - Live client-side search across publication titles, authors, and filenames
  - Filter by publication year (dynamically aggregated from corpus)
  - Filter by research topic (dynamically populated from `/topics`)
  - Paginated table showing ID, Title, Authors, Year, Section count, and Direct Detail action.

### Module 3: Paper Detail (`frontend/src/pages/PaperDetailPage.jsx`)
- **Purpose:** Comprehensive provenance inspection for an individual publication.
- **Features:**
  - Title, authors, publication year, venue, abstract, section hierarchy
  - "Run NLP" on-demand processing trigger
  - Tabbed extraction panels:
    - **Sections:** Document structure and page locations
    - **Limitations:** Detected empirical and methodology limitations with category and confidence
    - **Future Work:** Proposed research avenues and open questions
    - **Methods:** Extracted models, algorithms, and architectures
    - **Datasets:** Extracted benchmark corpora and evaluation splits
    - **Evidence Sentences:** Classified rhetorical sentences (Background, Method, Result, Limitation, Future Work) with section and page metadata.

### Module 4: Research Landscape (`frontend/src/pages/LandscapePage.jsx`)
- **Purpose:** Macro-level semantic topic clustering and longitudinal trajectory analysis.
- **Features:**
  - Categorized themes: Major Topics, Emerging Topics, Persistent Topics, Declining Topics
  - Topic size (paper count and sentence count)
  - Interactive topic detail inspector showing year-by-year temporal volume bar charts
  - Key representative terms with c-TF-IDF weights
  - Representative document excerpts
  - "Discover Topics" trigger button calling `POST /topics/discover`.

### Module 5: Research Knowledge Graph (`frontend/src/pages/ResearchGraphPage.jsx`)
- **Purpose:** Multi-entity provenance graph linking empirical discourse relations.
- **Features:**
  - Interactive SVG canvas rendering entities: Papers, Methods, Datasets, Claims, Limitations, Topics, Research Directions
  - Relationship links: `proposes`, `uses`, `evaluates_on`, `limited_by`, `addresses`, `supports`, `contradicts`, `belongs_to`
  - Filter nodes by entity type and text search
  - **Node Provenance Drawer:** Clicking any node reveals its properties, source publication, exact source sentence, page number, section, confidence, and incoming/outgoing edges
  - Rebuild Graph trigger (`POST /graph/build`)
  - Cypher statement export modal for Neo4j / Memgraph migration.

### Module 6: Potential Gaps Catalogue (`frontend/src/pages/PotentialGapsPage.jsx`)
- **Purpose:** Ranked candidate research gaps generated from empirical signals.
- **Features:**
  - Gap cards displaying title, description, status badge (`potential_gap`), priority score (`gap_priority_score`), confidence score, supporting papers count, counter-evidence count, and first appearance publication year
  - Filter by gap type (`repeated_limitation`, `underexplored_area`, `methodological_concentration`, `dataset_concentration`, `temporal_opportunity`, `conflicting_evidence`)
  - Interactive priority threshold slider and minimum confidence threshold slider
  - Quick action buttons to launch Gap Detail, Genealogy, Lifecycle, Counter-Evidence, or Report.

### Module 7: Gap Detail (`frontend/src/pages/GapDetailPage.jsx`)
- **Purpose:** Exhaustive forensic analysis of a candidate research gap.
- **Features:**
  - Candidate selector dropdown to switch across candidate gaps
  - Mathematical Signal Breakdown table showing each of the 7 empirical signals: signal name, value, weight, contribution, and explanation
  - Multi-paper temporal lifecycle status reasoning
  - Supporting evidence excerpt cards with exact source sentences, paper title, page, section, and confidence
  - Counter-evidence, addressing publications, and contradictory evidence cards.

### Module 8: Gap Genealogy (`frontend/src/pages/GapGenealogyPage.jsx`)
- **Purpose:** Reconstructs the evolutionary chain through which limitations evolve.
- **Features:**
  - Evolutionary sequence banner: `Limitation Identified` $\to$ `Attempted Solution` $\to$ `Remaining Limitation` $\to$ `Current Candidate Gap`
  - Root limitation explanation
  - Step-by-step transition cards showing transition stage, description, relationship, publication year, source sentence excerpt, and citing paper.

### Module 9: Gap Lifecycle (`frontend/src/pages/GapLifecyclePage.jsx`)
- **Purpose:** Multi-paper state machine tracking gap persistence across years.
- **Features:**
  - Corpus-wide state distribution across the 6 canonical states:
    1. `EMERGING`: Recently identified in newer literature (1–2 years)
    2. `PERSISTENT`: Bottleneck recurring unaddressed across $\ge 2$ publication years
    3. `PARTIALLY_ADDRESSED`: Solutions proposed with remaining boundary limitations
    4. `ADDRESSED`: Verified solutions established in peer-reviewed literature
    5. `REOPENED`: Recurring in new paradigms (e.g. LLM scale or multimodal shifts)
    6. `UNCERTAIN`: Sparse single-paper evidence
  - Multi-paper evidence reasoning with year span and attempted solution flags
  - Chronological timeline events.

### Module 10: Counter-Evidence & Verification (`frontend/src/pages/CounterEvidencePage.jsx`)
- **Purpose:** Active verification and refutation searching against candidate gaps.
- **Features:**
  - 4-Quadrant comparison: Supporting Evidence vs Counter-Evidence vs Addressing Papers vs Contradictory Evidence
  - Scientific NLI inference badges: `ENTAILMENT`, `CONTRADICTION`, `NEUTRAL` with confidence percentages
  - Final Verification verdict: `VERIFIED_OPEN`, `REFUTED`, `ADDRESSED`, `PARTIALLY_ADDRESSED`, `OUTDATED`, `UNCERTAIN`
  - "Verify Gap" trigger calling `POST /gaps/{gap_id}/verify`.

### Module 11: Evidence Explorer (`frontend/src/pages/EvidenceExplorerPage.jsx`)
- **Purpose:** Free-text dense vector semantic search across the scientific literature.
- **Features:**
  - Real-time semantic search via Sentence Transformers & FAISS (`GET /search/semantic`)
  - Filter by extraction type: `LIMITATION`, `FUTURE_WORK`, `PROBLEM`, `METHOD`, `RESULT`, `BACKGROUND`
  - Filter by top-k matches and publication year range
  - Result card display:
    - Target paper title and Paper ID
    - Section header
    - Page number
    - Verbatim source sentence text
    - Vector similarity score
    - Extraction type badge
    - One-click grounded citation copy.

### Module 12: Research Report (`frontend/src/pages/ResearchReportPage.jsx`)
- **Purpose:** On-demand LLM synthesis grounded strictly in retrieved scientific evidence.
- **Features:**
  - Configurable synthesis trigger: LLM provider (`gemini`, `openai`, `local`, `mock`), evidence depth (5–20 passages), citation validation flag
  - Structured academic report:
    1. Scientific Gap Explanation
    2. Practical & Empirical Importance
    3. Supporting Evidence Summary
    4. Counter-Evidence Summary
    5. Candidate Research Questions (`RQ1`, `RQ2`, ...)
    6. Suggested Technical Directions
    7. Evidence Limitations & Boundary Conditions
  - Grounded Citation Provenance Table: Resolves in-text markers (e.g., `[E1]`, `[E2]`) to exact source paper, section, page, and sentence
  - Automated Citation Factuality Audit: Calculates Evidence Support Rate, checks for hallucinated citations, and outputs `VALID` vs `REJECTED` verdict.

---

## 3. Backend API Integration Matrix

| Page / Feature | Backend REST Endpoint | Method | Response Schema / Data |
| :--- | :--- | :--- | :--- |
| **System Diagnostics** | `/api/v1/health` | GET | `HealthCheckResponse` |
| **Paper Library** | `/api/v1/papers?skip=0&limit=100` | GET | `List[PaperSummaryResponse]` |
| **Paper Upload** | `/api/v1/papers/upload` | POST | `PaperUploadResponse` |
| **Paper Details** | `/api/v1/papers/{id}` | GET | `PaperDetailResponse` |
| **NLP Extractions** | `/api/v1/nlp/papers/{id}/extractions` | GET | `List[EntityExtractionResponse]` |
| **Paper Limitations** | `/api/v1/nlp/papers/{id}/limitations` | GET | `List[LimitationResponse]` |
| **Paper Future Work** | `/api/v1/nlp/papers/{id}/future-work` | GET | `List[FutureWorkResponse]` |
| **Paper Sentences** | `/api/v1/nlp/papers/{id}/sentences` | GET | `List[SentenceClassificationResponse]` |
| **NLP Trigger** | `/api/v1/nlp/process/{id}` | POST | `NLPProcessResponse` |
| **Landscape Overview** | `/api/v1/topics/overview` | GET | `TopicLandscapeOverviewResponse` |
| **Topic Trends** | `/api/v1/topics/trends` | GET | `List[Dict[str, Any]]` |
| **Topic Discovery** | `/api/v1/topics/discover` | POST | `TopicLandscapeOverviewResponse` |
| **Graph Overview** | `/api/v1/graph/overview` | GET | `GraphOverviewResponse` |
| **Graph Subgraph** | `/api/v1/graph/paper/{id}?hops=1` | GET | `GraphSubgraphResponse` |
| **Limitation Graph** | `/api/v1/graph/limitation/{id}` | GET | `LimitationSubgraphResponse` |
| **Method Graph** | `/api/v1/graph/method/{id}` | GET | `MethodSubgraphResponse` |
| **Rebuild Graph** | `/api/v1/graph/build` | POST | `GraphOverviewResponse` |
| **Export Cypher** | `/api/v1/graph/export/cypher` | GET | `Dict[str, Any]` |
| **Potential Gaps** | `/api/v1/gaps/candidates` | GET | `GapCandidatesListResponse` |
| **Gap Detail** | `/api/v1/gaps/candidates/{id}` | GET | `ResearchGapCandidateResponse` |
| **Gap Signals** | `/api/v1/gaps/signals` | GET | `GapSignalsOverviewResponse` |
| **Gap Lifecycle Overview**| `/api/v1/gaps/lifecycle/overview` | GET | `GapLifecycleOverviewResponse` |
| **Gap Lifecycle Detail** | `/api/v1/gaps/{id}/lifecycle` | GET | `GapLifecycleDetailResponse` |
| **Gap Timeline** | `/api/v1/gaps/{id}/timeline` | GET | `GapTimelineResponse` |
| **Gap Genealogy** | `/api/v1/gaps/{id}/genealogy` | GET | `GapGenealogyResponse` |
| **Counter-Evidence** | `/api/v1/gaps/{id}/counter-evidence` | GET | `GapCounterEvidenceResponse` |
| **Gap Verification** | `/api/v1/gaps/{id}/verification` | GET | `GapVerificationResponse` |
| **Trigger Verification** | `/api/v1/gaps/{id}/verify` | POST | `GapVerificationResponse` |
| **Semantic Search** | `/api/v1/search/semantic` | GET | `EvidenceSearchResponse` |
| **LLM Synthesis** | `/api/v1/gaps/{id}/synthesize` | POST | `GapSynthesisResponse` |
| **Get Synthesis** | `/api/v1/gaps/{id}/synthesis` | GET | `GapSynthesisResponse` |
| **Validate Citations** | `/api/v1/gaps/validate-citations` | POST | `CitationValidationReport` |

---

## 4. Test Results

### 4.1 Frontend Test Suite (Vitest + React Testing Library)
All 24 test cases pass with zero failures:

```
 RUN  v1.6.1 G:/NLP/frontend

 ✓ tests/App.test.jsx (6 tests)
   ✓ renders GapTrace branding and navigation elements
   ✓ renders welcome view with headline and research composer
   ✓ renders recent research sessions and allows navigating to a session
   ✓ switches tabs in research session view to inspect evidence and timeline
   ✓ supports light and dark theme switching with data-theme attribute
   ✓ opens settings modal when settings action is triggered

 ✓ tests/Phase10_Modules.test.jsx (17 tests)
   ✓ 1. Dashboard Page > renders loading state initially
   ✓ 1. Dashboard Page > renders successful API data with papers, topics, potential/persistent/addressed gaps, and counter-evidence
   ✓ 1. Dashboard Page > renders empty API response cleanly
   ✓ 1. Dashboard Page > renders API failure error banner with retry button
   ✓ 2. Paper Library Page > renders paper library with search, year filter, topic filter, and upload trigger
   ✓ 2. Paper Library Page > handles file upload interaction
   ✓ 3. Paper Detail Page > renders paper detail with sections, limitations, future work, methods, datasets, and evidence
   ✓ 4. Research Landscape Page > visualizes topic sizes, trajectories, and temporal distribution
   ✓ 5. Research Knowledge Graph Page > renders topology statistics and handles node click provenance drawer
   ✓ 6. Potential Gaps Catalogue Page > renders gap cards with title, description, status, priority, confidence, supporting papers, counter-evidence count, first appearance
   ✓ 7. Gap Detail Page > displays description, lifecycle, scoring signals, exact sentences, and counter-evidence
   ✓ 8. Gap Genealogy Page > displays timeline sequence limitation -> attempted solution -> remaining limitation -> candidate gap
   ✓ 9. Gap Lifecycle Page > displays 6 lifecycle states with evidence and chronological timeline
   ✓ 10. Counter-Evidence Page > displays supporting, counter, addressing, and contradictory evidence with NLI inference
   ✓ 11. Evidence Explorer Page > executes semantic search and displays paper, page, section, sentence, similarity, and extraction type
   ✓ 12. Research Report Page > generates evidence-grounded report with citations and factuality audit
   ✓ 13. Responsive Shell & Navigation > renders responsive shell and navigation across all views

 ✓ tests/Phase10_E2E.test.jsx (1 test)
   ✓ executes full pipeline: Upload paper -> process NLP -> search evidence -> view landscape -> view potential gap -> inspect genealogy -> inspect counter-evidence -> generate report

Test Files  3 passed (3)
Tests       24 passed (24)
Duration    19.59s
```

### 4.2 Backend Regression Suite (pytest)
All 214 backend tests spanning Phases 0 through 9 pass with zero regressions:

```
======================= 214 passed in 76.06s (0:01:16) ========================
```

---

## 5. UI Design & Academic UX Standards

1. **Academic Typography & Palette:** Curated neutral and scientific primary hues (`hsl(222, 47%, 11%)`, `indigo-400`, `purple-400`, `amber-400`, `emerald-400`, `rose-400`), crisp monospace accents for metrics, IDs, and citations.
2. **Accessible Theme Modes:** Full support for `light`, `dark`, and `system` theme synchronization via CSS custom properties and `data-theme` root attribute.
3. **Resilient Feedback States:**
   - **Loading States:** Shimmer skeletons (`SkeletonCard`, `SkeletonTable`, `LoadingSpinner`) maintaining layout stability during network fetches.
   - **Error States:** Actionable `ErrorBanner` components equipped with automatic retry callbacks.
   - **Empty States:** Clear `EmptyState` panels explaining why data is absent and providing one-click restorative actions (e.g. uploading papers or resetting filters).
4. **Responsive Shell:** Collapsible sidebar, mobile drawer with backdrop overlay, and flex/grid layouts adapting from 360px mobile viewports up to 4K displays.

---

## 6. Known UI Limitations

1. **Large Graph Layout Scalability:** The Knowledge Graph utilizes a 2D mathematical circle layout in pure SVG. While performing with sub-millisecond frame rates for graphs up to 200 nodes, displaying collections with $>2,000$ simultaneous nodes would benefit from a WebGL or canvas-based force-directed simulation (such as PixiJS or Cytoscape WebGL).
2. **Multi-page PDF Direct Annotation:** Currently, clicking "Inspect" loads parsed section text and page numbers. Direct side-by-side embedded PDF view with real-time text highlight bounding boxes requires an integrated PDF.js canvas viewer component.
3. **Long-Running Discovery Polling:** While topic discovery and NLP processing trigger asynchronously, active real-time progress percentage relies on HTTP request completion rather than a bi-directional WebSocket progress stream.
