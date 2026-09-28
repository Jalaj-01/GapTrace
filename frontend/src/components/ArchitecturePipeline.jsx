import React from 'react';
import {
  Layers,
  ArrowDown,
  Database,
  Search,
  Share2,
  FileText,
  BrainCircuit,
  Binary,
  Tag,
  Target,
  FileSearch,
  Sparkles,
  Bot
} from 'lucide-react';

export default function ArchitecturePipeline() {
  const nlpModules = [
    { name: 'PDF Processing', desc: 'PyMuPDF / GROBID section parser', icon: FileText, phase: 'Phase 1' },
    { name: 'Scientific NLP', desc: 'spaCy / SciBERT token & entity tagger', icon: BrainCircuit, phase: 'Phase 1' },
    { name: 'Embeddings', desc: 'SPECTER / Sentence Transformers (384-d)', icon: Binary, phase: 'Phase 1' },
    { name: 'Topic Modeling', desc: 'BERTopic + HDBSCAN theme clustering', icon: Tag, phase: 'Phase 1' },
    { name: 'Gap Detection', desc: 'Limitations & contradiction extractor', icon: Target, phase: 'Phase 1' },
    { name: 'Evidence Retrieval', desc: 'Passage reranking & grounding', icon: FileSearch, phase: 'Phase 1' },
    { name: 'RAG Pipeline', desc: 'Context synthesis with citation grounding', icon: Sparkles, phase: 'Phase 1' },
    { name: 'LLM Abstraction', desc: 'Gemini / OpenAI / Local pluggable driver', icon: Bot, phase: 'Phase 0 Ready' },
  ];

  return (
    <div className="pipeline-card glass-card">
      <div className="card-header">
        <div className="card-title-group">
          <Layers className="section-icon text-cyan" size={20} />
          <h2 className="card-title">System Architecture & Pipeline Topology</h2>
        </div>
        <span className="badge badge-indigo">Modular Architecture</span>
      </div>

      <div className="pipeline-container">
        {/* Tier 1: Frontend */}
        <div className="pipeline-node frontend-node">
          <div className="node-tag">Client Tier</div>
          <h3 className="node-title">Frontend</h3>
          <p className="node-sub">React 18 + Vite &bull; Modern Responsive UI</p>
        </div>

        {/* REST API Connector */}
        <div className="connector">
          <div className="connector-line"></div>
          <div className="connector-label">
            <ArrowDown size={14} />
            <span>REST API (/api/v1)</span>
          </div>
          <div className="connector-line"></div>
        </div>

        {/* Tier 2: Backend */}
        <div className="pipeline-node backend-node">
          <div className="node-tag">Application Tier</div>
          <h3 className="node-title">Backend Core</h3>
          <p className="node-sub">Python 3.11+ &bull; FastAPI &bull; Pydantic &bull; SQLAlchemy</p>

          <div className="nlp-pipeline-grid">
            {nlpModules.map((mod, idx) => {
              const Icon = mod.icon;
              return (
                <div key={idx} className="nlp-module-chip">
                  <div className="chip-icon-box">
                    <Icon size={14} />
                  </div>
                  <div className="chip-content">
                    <div className="chip-name">{mod.name}</div>
                    <div className="chip-desc">{mod.desc}</div>
                  </div>
                  <span className={`chip-badge ${mod.phase === 'Phase 0 Ready' ? 'ready' : 'planned'}`}>
                    {mod.phase}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Storage Split Connector */}
        <div className="connector">
          <div className="connector-line"></div>
          <div className="connector-label">
            <ArrowDown size={14} />
            <span>Storage & Indexing Subsystems</span>
          </div>
          <div className="connector-line"></div>
        </div>

        {/* Tier 3: Storage & Graph */}
        <div className="storage-grid">
          {/* PostgreSQL */}
          <div className="storage-column">
            <div className="pipeline-node storage-node">
              <div className="storage-icon-row">
                <Database className="text-indigo" size={20} />
                <h4 className="storage-title">PostgreSQL</h4>
              </div>
              <p className="storage-desc">Paper Metadata, Structural Sections, Ingested Claims</p>
              <div className="storage-status">
                <span className="status-pill status-ok small">SQLAlchemy ORM Ready</span>
              </div>
            </div>

            <div className="sub-connector">
              <ArrowDown size={14} />
            </div>

            <div className="pipeline-node storage-node graph-node">
              <div className="storage-icon-row">
                <Share2 className="text-cyan" size={20} />
                <h4 className="storage-title">NetworkX Graph</h4>
              </div>
              <p className="storage-desc">Citation Networks & Research Knowledge Graph</p>
              <div className="storage-status">
                <span className="status-pill status-ok small">GraphStore Interface Ready</span>
              </div>
            </div>
          </div>

          {/* FAISS Vector Search */}
          <div className="storage-column">
            <div className="pipeline-node storage-node vector-node">
              <div className="storage-icon-row">
                <Search className="text-violet" size={20} />
                <h4 className="storage-title">FAISS</h4>
              </div>
              <p className="storage-desc">Dense Vector Search & Embedding Similarity Index</p>
              <div className="storage-status">
                <span className="status-pill status-warn small">Interface Stubbed for Phase 1</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
