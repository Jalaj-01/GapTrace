# System Architecture & Design Specification

## Overview
The **Scientific Paper "Gap Finder"** is an evidence-grounded NLP system designed to analyze large corpora of scientific literature. Its goal is to extract structural sections, model emerging themes, identify explicit limitations, uncover contradictory findings across papers, and synthesize candidate research questions.

## Tiered Architecture

### 1. Presentation Tier (Frontend)
- **Framework**: React 18 + Vite
- **Styling**: Vanilla CSS custom design system with glassmorphism, responsive grid, and dark mode aesthetic tokens.
- **State & API**: Custom hooks (`useHealth`), REST client (`api.js`), real-time diagnostic polling.
- **Phase 1 UI**: `PaperUploadCard` component supporting drag-and-drop ingestion, section navigation with page range tags, and JSON payload viewer.

### 2. Application Core (Backend)
- **Framework**: FastAPI
- **Configuration**: Pydantic Settings with multi-file `.env` resolution.
- **Middleware**: CORS middleware with origin whitelist.
- **Error Handling**: Centralized domain exception handlers (`AppException`, `NotFoundError`, `InvalidFileTypeError`, `FileTooLargeError`, `CorruptedPDFError`, `DuplicatePaperError`) returning standardized JSON error envelopes.
- **Logging**: Structured JSON formatter logging request contexts, module origins, and tracebacks.

### 3. Ingestion & PDF Processing Pipeline (Phase 1 Implemented)
- **PDF Extraction Engine**: PyMuPDF (`fitz`) extracting layout blocks, multi-column reading orders, and span-level font sizes.
- **Heuristic Layout Analyzer**: `PaperProcessor` service identifying:
  - **Title**: Font size hierarchy on page 1 with running header suppression.
  - **Authors**: Interstitial layout blocks between title and abstract, cleaned of email and affiliation noise.
  - **Abstract**: Header detection and boundary delimitation.
  - **Sections**: Regex header matching and formatting cues (Introduction, Methodology, Experiments, Results, Discussion, Limitations, Conclusion).
  - **Paragraphs**: Text normalization and line-broken hyphenation repair (`transfor-\nmer` &rarr; `transformer`).
  - **References**: Regex bibliography splitting (`[1]`, `1.`), title discovery, and publication year extraction.
  - **Deduplication**: SHA-256 binary hash checking before persistence.

### 4. Storage Subsystems
- **PostgreSQL**: Primary relational database with connection pooling and schema creation for `papers`, `paper_sections`, and `paper_references`.
- **Development Fallback**: In local development where PostgreSQL server may not be active, the session manager safely falls back to a persistent SQLite database (`./data/metadata/gap_finder_dev.db`), reporting its fallback status in health check diagnostics.
- **Raw File Storage**: Uploaded files stored securely in `data/raw/` with sanitized, collision-resistant names (`{hash[:12]}_{filename}.pdf`).
- **Upcoming Indices (Phase 2+)**: FAISS vector index at `./data/embeddings/faiss_index.bin` and NetworkX citation graph.
