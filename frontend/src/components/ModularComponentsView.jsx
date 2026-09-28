import React from 'react';
import { Code, Check, Clock, Box } from 'lucide-react';

export default function ModularComponentsView() {
  const components = [
    {
      title: 'FastAPI Backend & Versioning',
      path: 'backend/app/main.py',
      tests: 'backend/tests/test_health.py',
      status: 'Implemented',
      desc: 'Lifespan manager, CORS, versioned routes (/api/v1), centralized error handling.',
    },
    {
      title: 'Database & SQLAlchemy Models',
      path: 'backend/app/db/session.py',
      tests: 'backend/tests/test_papers_api.py',
      status: 'Implemented',
      desc: 'PostgreSQL connection with dev fallback, declarative models for Papers and Gaps.',
    },
    {
      title: 'LLM Provider-Independent Abstraction',
      path: 'backend/app/services/llm/base.py',
      tests: 'backend/tests/test_config.py',
      status: 'Implemented',
      desc: 'BaseLLMProvider abstract interface; Gemini, OpenAI, and Local provider drivers.',
    },
    {
      title: 'Citation Graph Subsystem',
      path: 'backend/app/retrieval/graph_store.py',
      tests: 'Ready for integration',
      status: 'Implemented',
      desc: 'NetworkX DiGraph store for citation edge modeling and PageRank centrality.',
    },
    {
      title: 'PDF Structure Extractor',
      path: 'backend/app/nlp/pdf_processor.py',
      tests: 'Unit test stubbed',
      status: 'Phase 1 Ready',
      desc: 'BasePDFProcessor interface for PyMuPDF/GROBID structural section parser.',
    },
    {
      title: 'Scientific Embeddings',
      path: 'backend/app/nlp/embeddings.py',
      tests: 'Unit test stubbed',
      status: 'Phase 1 Ready',
      desc: 'BaseEmbeddingService interface for SPECTER / Sentence Transformers (384-d).',
    },
    {
      title: 'Topic Modeling Pipeline',
      path: 'backend/app/nlp/topic_modeling.py',
      tests: 'Unit test stubbed',
      status: 'Phase 1 Ready',
      desc: 'BaseTopicModeler interface for BERTopic and HDBSCAN theme extraction.',
    },
    {
      title: 'Research Gap & Limitation Detector',
      path: 'backend/app/nlp/gap_detector.py',
      tests: 'Unit test stubbed',
      status: 'Phase 1 Ready',
      desc: 'BaseGapDetector for limitations, contradictions, and open question extraction.',
    },
    {
      title: 'FAISS Vector Search Store',
      path: 'backend/app/retrieval/vector_store.py',
      tests: 'Unit test stubbed',
      status: 'Phase 1 Ready',
      desc: 'BaseVectorStore interface for dense vector ingestion and nearest neighbor search.',
    },
    {
      title: 'Evidence Retrieval & Grounded RAG',
      path: 'backend/app/retrieval/rag.py',
      tests: 'Unit test stubbed',
      status: 'Phase 1 Ready',
      desc: 'BaseRAGOrchestrator for evidence retrieval, citation linking, and synthesis.',
    },
  ];

  return (
    <div className="modular-view glass-card">
      <div className="card-header">
        <div className="card-title-group">
          <Box className="section-icon text-indigo" size={20} />
          <h2 className="card-title">Phase 0 Architectural Components & Test Boundaries</h2>
        </div>
        <span className="badge badge-cyan">{components.length} Modular Boundaries</span>
      </div>

      <div className="components-table-wrapper">
        <table className="components-table">
          <thead>
            <tr>
              <th>Subsystem Component</th>
              <th>Source Module Path</th>
              <th>Status</th>
              <th>Verification / Test Path</th>
            </tr>
          </thead>
          <tbody>
            {components.map((c, i) => (
              <tr key={i} className="component-row">
                <td className="component-title-cell">
                  <div className="cell-title">{c.title}</div>
                  <div className="cell-desc">{c.desc}</div>
                </td>
                <td className="component-code-cell">
                  <code>{c.path}</code>
                </td>
                <td>
                  <span className={`status-pill small ${c.status === 'Implemented' ? 'status-ok' : 'status-warn'}`}>
                    {c.status === 'Implemented' ? <Check size={11} /> : <Clock size={11} />}
                    {c.status}
                  </span>
                </td>
                <td className="component-test-cell">
                  <code>{c.tests}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
