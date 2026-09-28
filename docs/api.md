# REST API Specification (v1)

Base URL: `/api/v1`

## Endpoints

### 1. Health Diagnostics
- **Method**: `GET`
- **Route**: `/api/v1/health`
- **Description**: Returns live health status of backend server, database connectivity, dialect, and runtime environment.
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-09-28T17:48:38.210780+00:00",
  "database": {
    "status": "connected",
    "dialect": "sqlite",
    "host": "local_sqlite",
    "database": "./data/metadata/gap_finder_dev.db",
    "fallback_in_use": true
  },
  "services": {
    "api": "operational",
    "llm_provider": "gemini",
    "os": "Windows 11",
    "python": "3.13.11"
  }
}
```

---

### 2. Scientific Paper Ingestion (Phase 1)

#### `POST /api/v1/papers/upload`
Uploads and parses a scientific PDF document into structured sections, authors, abstract, and references.

- **Request Type**: `multipart/form-data`
- **Parameters**: `file`: File upload (`.pdf`, `application/pdf`, max 25MB).
- **Validations Enforced**:
  - File extension (`.pdf`)
  - MIME type (`application/pdf`)
  - Maximum file size (25MB limit)
  - Integrity & corruption check (PyMuPDF stream validation)
  - Duplicate detection (SHA-256 content hash deduplication)
- **Response `201 Created`**:
```json
{
  "paper_id": 1,
  "id": 1,
  "title": "Attention Is All You Need: Discovering Research Gaps in Neural Sequence Models",
  "authors": [
    "Ashish Vaswani",
    "Noam Shazeer",
    "Niki Parmar",
    "Jakob Uszkoreit"
  ],
  "year": 2024,
  "doi": "10.48550/arXiv.1706.03762",
  "abstract": "The dominant sequence transduction models are based on complex recurrent...",
  "page_count": 2,
  "file_path": "data/raw/df969c7b041e_sample_paper.pdf",
  "file_hash": "df969c7b041e1f37e557ecfd70770345e7e0e4223ea05f66b42208b719796bbd",
  "sections": [
    {
      "name": "Introduction",
      "page_start": 1,
      "page_end": 1,
      "text": "...",
      "paragraphs": ["..."]
    },
    {
      "name": "Methodology",
      "page_start": 1,
      "page_end": 2,
      "text": "...",
      "paragraphs": ["..."]
    },
    {
      "name": "Limitations",
      "page_start": 2,
      "page_end": 2,
      "text": "...",
      "paragraphs": ["..."]
    }
  ],
  "references": [
    {
      "ref_index": 1,
      "raw_text": "Dzmitry Bahdanau... In ICLR, 2015.",
      "title": null,
      "authors": [],
      "year": 2015,
      "venue": null
    }
  ]
}
```

- **Error Responses**:
  - `400 Bad Request`: `{"error": {"code": "INVALID_FILE_TYPE", "message": "Only .pdf files are supported"}}`
  - `409 Conflict`: `{"error": {"code": "DUPLICATE_PAPER", "message": "Paper already exists", "details": {"existing_paper_id": 1}}}`
  - `413 Payload Too Large`: `{"error": {"code": "FILE_TOO_LARGE", "message": "Exceeds 25MB limit"}}`
  - `422 Unprocessable Content`: `{"error": {"code": "CORRUPTED_PDF", "message": "PDF is damaged or encrypted"}}`

---

### 3. Paper Retrieval

#### `GET /api/v1/papers`
Returns a list of all ingested papers with basic metadata.
- **Query Params**: `skip` (default: 0), `limit` (default: 50).
- **Response `200 OK`**: Array of paper metadata objects.

#### `GET /api/v1/papers/{paper_id}`
Returns complete structured representation of a paper including sections and references.
- **Response `200 OK`**: `StructuredPaperResponse`.
- **Response `404 Not Found`**: When paper does not exist.

#### `GET /api/v1/papers/{paper_id}/sections`
Returns only the parsed structural sections with page ranges and paragraphs for the paper.
- **Response `200 OK`**: Array of section objects.

#### `GET /api/v1/papers/{paper_id}/references`
Returns parsed bibliographic references cited in the paper.
- **Response `200 OK`**: Array of reference objects.

---

## Standard Error Envelope
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human-readable description",
    "details": {},
    "path": "/api/v1/..."
  }
}
```
