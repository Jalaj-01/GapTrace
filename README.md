# Scientific Paper "Gap Finder"

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg?logo=react&logoColor=black)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4+-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Pytest](https://img.shields.io/badge/Pytest-8.0+-0A9EDC.svg?logo=pytest&logoColor=white)](https://pytest.org/)
[![Vitest](https://img.shields.io/badge/Vitest-1.6+-FCC72B.svg?logo=vitest&logoColor=black)](https://vitest.dev/)

An evidence-grounded NLP system designed to analyze scientific research papers and automatically discover potential **research gaps**, **recurring limitations**, **emerging research topics**, **contradictions**, and **candidate research questions**.

---

## Architecture & Topology

```
Frontend (React + Vite)
      │
      │ REST API (/api/v1)
      ▼
Backend (Python + FastAPI)
      │
      ├── PDF Processing (PyMuPDF / GROBID)
      ├── Scientific NLP (spaCy / SciBERT)
      ├── Embeddings (SPECTER / Sentence Transformers)
      ├── Topic Modeling (BERTopic + HDBSCAN)
      ├── Gap Detection (Limitations, Questions, Contradictions)
      ├── Evidence Retrieval (Passage Reranking)
      ├── RAG (Citation-grounded synthesis)
      └── LLM Abstraction (Gemini / OpenAI / Local Provider Bridge)
      │
      ├───────────────────────────────┐
      ▼                               ▼
PostgreSQL (Metadata & Sections)   FAISS (Dense Vector Index)
      │
      ▼
NetworkX (Citation & Research Graph)
```

### Current Status: Phase 0 Foundation
- **Phase 0 (Completed)**: Core system architecture, FastAPI backend with structured logging and centralized error handling, React/Vite dashboard with live system diagnostics, PostgreSQL configuration with development fallback, provider-independent LLM abstraction layer, API versioning (`/api/v1`), health check endpoint, Docker compose setup, and end-to-end backend + frontend test suites.
- **Phase 1 (Upcoming)**: PDF ingestion pipelines, sentence embeddings, BERTopic modeling, FAISS vector indexing, citation graph construction, and LLM-grounded evidence synthesis.

---

## Directory Structure

```
scientific-gap-finder/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── health.py         # GET /api/v1/health
│   │   │       │   └── papers.py         # REST CRUD for scientific papers
│   │   │       └── router.py             # Master v1 router
│   │   ├── core/
│   │   │   ├── config.py                 # Pydantic Settings & environment variables
│   │   │   ├── logging.py                # Structured JSON logging
│   │   │   └── errors.py                 # Centralized exception handlers & envelope
│   │   ├── db/
│   │   │   ├── base.py                   # SQLAlchemy declarative base & mixins
│   │   │   └── session.py                # Connection pool, probe & dev fallback
│   │   ├── models/
│   │   │   └── paper.py                  # Paper, PaperSection, ResearchGap models
│   │   ├── services/
│   │   │   └── llm/                      # Provider-independent LLM abstraction
│   │   │       ├── base.py               # BaseLLMProvider interface
│   │   │       ├── gemini_provider.py    # Google Gemini driver stub
│   │   │       ├── openai_provider.py    # OpenAI GPT driver stub
│   │   │       ├── local_provider.py     # Local / Ollama driver stub
│   │   │       └── factory.py            # Provider instantiation factory
│   │   ├── nlp/                          # Modular NLP component interfaces
│   │   │   ├── pdf_processor.py          # PDF section parser interface
│   │   │   ├── embeddings.py             # Sentence embeddings interface
│   │   │   ├── topic_modeling.py         # BERTopic theme clustering interface
│   │   │   └── gap_detector.py           # Limitation & contradiction interface
│   │   ├── retrieval/                    # Retrieval & Graph interfaces
│   │   │   ├── vector_store.py           # FAISS vector store interface
│   │   │   ├── graph_store.py            # NetworkX citation graph store
│   │   │   └── rag.py                    # Evidence retrieval & RAG orchestrator
│   │   └── main.py                       # FastAPI application entry point
│   │
│   ├── tests/
│   │   ├── conftest.py                   # Pytest fixtures & isolated in-memory DB
│   │   ├── test_health.py                # Health & root endpoint tests
│   │   ├── test_config.py                # Environment & CORS configuration tests
│   │   ├── test_errors.py                # Error handlers & envelope tests
│   │   └── test_papers_api.py            # Papers CRUD endpoint tests
│   ├── scripts/
│   │   └── verify_db.py                  # Database connection verification tool
│   ├── Dockerfile                        # Backend container specification
│   ├── pytest.ini                        # Pytest configuration
│   └── requirements.txt                  # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx                # Branding & live status pill
│   │   │   ├── HealthCard.jsx            # System diagnostics metric boxes
│   │   │   ├── ArchitecturePipeline.jsx  # Interactive system topology tree
│   │   │   └── ModularComponentsView.jsx # Architectural boundary table
│   │   ├── pages/
│   │   │   └── Dashboard.jsx             # Main dashboard page
│   │   ├── services/
│   │   │   └── api.js                    # Fetch client for REST endpoints
│   │   ├── hooks/
│   │   │   └── useHealth.js              # Auto-polling health diagnostics hook
│   │   ├── index.css                     # Design tokens & glassmorphism theme
│   │   ├── App.jsx                       # Root application component
│   │   ├── App.css                       # Dashboard styles & animations
│   │   └── main.jsx                      # Vite React DOM entry
│   ├── tests/
│   │   └── App.test.jsx                  # Vitest + React Testing Library suite
│   ├── Dockerfile                        # Frontend production container
│   ├── vite.config.js                    # Vite dev server & API proxy config
│   ├── vitest.config.js                  # Vitest test runner config
│   └── package.json                      # Node dependencies & test scripts
│
├── data/
│   ├── raw/                              # Original PDF papers (.gitkeep)
│   ├── processed/                        # Extracted text & JSON sections (.gitkeep)
│   ├── embeddings/                       # FAISS binary vector index (.gitkeep)
│   └── metadata/                         # SQLite dev fallback / metadata (.gitkeep)
│
├── notebooks/                            # Exploratory NLP research notebooks (.gitkeep)
├── experiments/                          # Model evaluation & benchmark logs (.gitkeep)
├── docs/                                 # Architectural & API documentation
│   ├── architecture.md
│   └── api.md
│
├── .env.example                          # Environment variable templates
├── .gitignore                            # Git exclusion rules
├── README.md                             # Project reference guide
└── docker-compose.yml                    # Multi-container orchestration
```

---

## Environment Configuration

A template configuration is provided in [`.env.example`](file:///g:/NLP/.env.example). Copy it to `.env`:

```bash
cp .env.example .env
```

### Key Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Runtime environment (`development`, `production`, `test`) |
| `DEBUG` | `true` | Enables auto-reload and verbose debugging |
| `HOST` | `0.0.0.0` | Backend bind address |
| `PORT` | `8000` | Backend HTTP port |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/scientific_gap_finder` | Primary PostgreSQL database connection string |
| `ALLOW_SQLITE_DEV_FALLBACK` | `true` | Enables automatic SQLite dev fallback if PostgreSQL is offline |
| `CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | Allowed web origins |
| `LLM_PROVIDER` | `gemini` | Pluggable LLM provider (`gemini`, `openai`, `local`) |
| `GEMINI_API_KEY` | `""` | Google Gemini API key (for Phase 1) |
| `OPENAI_API_KEY` | `""` | OpenAI API key (for Phase 1) |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API URL accessed by frontend |

---

## Quickstart & Local Setup

### 1. Prerequisites
- **Python**: 3.11+
- **Node.js**: v20+ with `npm`
- **PostgreSQL**: 15+ (optional for Phase 0 dev; SQLite fallback is built-in)
- **Docker**: (optional for containerized execution)

### 2. Backend Setup

```bash
# 1. Install backend dependencies
pip install -r backend/requirements.txt

# 2. Verify database connectivity & schema tables
python -m backend.scripts.verify_db

# 3. Start the FastAPI development server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be accessible at:
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 3. Frontend Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

Frontend dashboard will be accessible at:
- **Web UI**: [http://localhost:5173](http://localhost:5173)

---

## Docker Compose Setup

To launch the full stack (PostgreSQL, FastAPI Backend, and React Frontend) with a single command:

```bash
docker compose up --build -d
```

- PostgreSQL will start with automated healthchecks on port `5432`.
- Backend will wait for PostgreSQL to be healthy before starting on port `8000`.
- Frontend will serve on port `5173`.

---

## Testing

Both backend and frontend are configured with isolated, automated test suites.

### Backend Tests (Pytest)
The test suite utilizes an isolated in-memory SQLite database and `TestClient` to verify configuration, error handling, health diagnostics, and REST endpoints:

```bash
# Run all backend tests
pytest backend/tests
```

**Results:**
- `test_config.py`: Validates Pydantic settings and CORS origin parsing.
- `test_errors.py`: Validates centralized exception handling and JSON error envelopes.
- `test_health.py`: Validates `/` root metadata and `/api/v1/health` diagnostics.
- `test_papers_api.py`: Validates paper registration, retrieval, and listing.

### Frontend Tests (Vitest)
The frontend test suite uses Vitest and `@testing-library/react` to verify component rendering and state interactions:

```bash
cd frontend
npm test
```

---

## Modular Component Design (Phase 0 -> Phase 1)

Each NLP and retrieval component has been created as an abstract base class (`ABC`) with strict type annotations, allowing independent testing and incremental implementation in Phase 1:

1. **`backend.app.nlp.pdf_processor.BasePDFProcessor`**: Abstract section extractor.
2. **`backend.app.nlp.embeddings.BaseEmbeddingService`**: Vector embedding generator.
3. **`backend.app.nlp.topic_modeling.BaseTopicModeler`**: BERTopic theme clustering.
4. **`backend.app.nlp.gap_detector.BaseGapDetector`**: Limitation, contradiction, and research question detector.
5. **`backend.app.retrieval.vector_store.BaseVectorStore`**: FAISS similarity search index.
6. **`backend.app.retrieval.graph_store.BaseGraphStore`**: NetworkX citation network graph.
7. **`backend.app.retrieval.rag.BaseRAGOrchestrator`**: Grounded citation retrieval and evidence synthesizer.
8. **`backend.app.services.llm.base.BaseLLMProvider`**: Provider-independent LLM driver.
