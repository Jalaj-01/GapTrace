import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Search,
  UploadCloud,
  FileText,
  RotateCw,
  ExternalLink,
  ChevronDown,
  CheckCircle2,
  Calendar,
  Layers,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { useResearch } from '../contexts/ResearchContext';
import { fetchPaperDetails, fetchPaperSentences, fetchPaperLimitations, processPaperNLP } from '../services/api';

export default function PapersPage() {
  const { backendPapers, loadPapers, isLoadingPapers, setIsUploaderOpen, runAnalysis } = useResearch();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [paperDetails, setPaperDetails] = useState(null);
  const [paperSentences, setPaperSentences] = useState([]);
  const [paperLimitations, setPaperLimitations] = useState([]);
  const [isProcessingNLP, setIsProcessingNLP] = useState(false);
  const [nlpMessage, setNlpMessage] = useState('');

  // Filter papers by search
  const filteredPapers = backendPapers.filter((p) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      p.title?.toLowerCase().includes(q) ||
      p.filename?.toLowerCase().includes(q) ||
      p.authors?.some((a) => a.toLowerCase().includes(q))
    );
  });

  const handleSelectPaper = async (paper) => {
    setSelectedPaper(paper);
    setNlpMessage('');
    try {
      const details = await fetchPaperDetails(paper.id);
      setPaperDetails(details);

      // Fetch sentences & limitations if already processed
      const sents = await fetchPaperSentences(paper.id);
      setPaperSentences(sents);

      const limits = await fetchPaperLimitations(paper.id);
      setPaperLimitations(limits);
    } catch {
      // Ignore
    }
  };

  const handleProcessNLP = async (paperId) => {
    setIsProcessingNLP(true);
    setNlpMessage('Running Phase 2 Scientific NLP pipeline...');
    try {
      const res = await processPaperNLP(paperId);
      setNlpMessage(`Successfully processed! Extracted ${res.sentences_count} sentences and ${res.extractions_count} entities.`);
      const sents = await fetchPaperSentences(paperId);
      setPaperSentences(sents);
      const limits = await fetchPaperLimitations(paperId);
      setPaperLimitations(limits);
    } catch (err) {
      setNlpMessage(`Error: ${err.message}`);
    } finally {
      setIsProcessingNLP(false);
    }
  };

  return (
    <div className="papers-page-container">
      {/* Page Header */}
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Scientific Paper Library</h2>
          <p className="page-subtitle">
            Manage ingested PDF papers, inspect section hierarchies, and run Phase 2 NLP discourse extraction.
          </p>
        </div>

        <div className="page-header-actions">
          <button className="btn-secondary" onClick={loadPapers} disabled={isLoadingPapers}>
            <RotateCw size={14} className={isLoadingPapers ? 'spin-icon' : ''} />
            <span>Refresh</span>
          </button>
          <button className="btn-primary" onClick={() => setIsUploaderOpen(true)}>
            <UploadCloud size={15} />
            <span>Upload New PDF</span>
          </button>
        </div>
      </div>

      {/* Search Toolbar */}
      <div className="papers-search-bar">
        <Search size={16} className="search-icon" />
        <input
          type="text"
          placeholder="Search ingested papers by title, author, or filename..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <span className="results-count font-mono">{filteredPapers.length} papers</span>
      </div>

      {/* Main Content Area */}
      <div className="papers-layout-grid">
        {/* Left: Paper List */}
        <div className="papers-list-column">
          {filteredPapers.length === 0 ? (
            <div className="empty-state-box">
              <BookOpen size={36} />
              <p className="empty-title">No papers found</p>
              <p className="empty-sub">
                {searchQuery
                  ? 'No papers match your search query.'
                  : 'Upload your first research paper to begin.'}
              </p>
              <button
                className="btn-primary mt-3"
                onClick={() => setIsUploaderOpen(true)}
              >
                Upload Paper
              </button>
            </div>
          ) : (
            <div className="papers-cards-stream">
              {filteredPapers.map((paper) => {
                const isSelected = selectedPaper?.id === paper.id;
                return (
                  <article
                    key={paper.id}
                    className={`paper-item-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleSelectPaper(paper)}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="paper-card-top">
                      <span className="paper-year font-mono">{paper.year || '2024'}</span>
                      <span className="paper-id-tag font-mono">#{paper.id}</span>
                    </div>

                    <h4 className="paper-card-title truncate" title={paper.title}>
                      {paper.title || paper.filename}
                    </h4>

                    <div className="paper-card-authors truncate">
                      {paper.authors && paper.authors.length > 0
                        ? paper.authors.join(', ')
                        : 'Authors unspecified'}
                    </div>

                    <div className="paper-card-footer">
                      <span className="file-size-badge font-mono">
                        {(paper.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                      </span>
                      <span className="sections-badge font-mono">
                        {paper.section_count || 0} sections
                      </span>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Selected Paper Detail Panel */}
        <div className="paper-detail-column">
          {selectedPaper ? (
            <div className="paper-detail-card">
              <div className="detail-header">
                <div className="detail-meta-pill">Paper ID #{selectedPaper.id}</div>
                <h3 className="detail-title">{selectedPaper.title || selectedPaper.filename}</h3>
                <div className="detail-authors">
                  {selectedPaper.authors?.join(', ') || 'Authors extracted from PDF'}
                </div>
              </div>

              {/* Action Toolbar */}
              <div className="detail-actions-bar">
                <button
                  className="btn-nlp-process"
                  onClick={() => handleProcessNLP(selectedPaper.id)}
                  disabled={isProcessingNLP}
                >
                  <Sparkles size={14} className={isProcessingNLP ? 'spin-icon' : ''} />
                  <span>{isProcessingNLP ? 'Processing NLP...' : 'Run Phase 2 NLP'}</span>
                </button>

                <button
                  className="btn-secondary"
                  onClick={() => runAnalysis(selectedPaper.title)}
                >
                  <ArrowRight size={14} />
                  <span>Trace Gaps For This Paper</span>
                </button>
              </div>

              {nlpMessage && <div className="nlp-status-alert">{nlpMessage}</div>}

              {/* Abstract */}
              {selectedPaper.abstract && (
                <div className="detail-section">
                  <h4 className="section-label">Abstract</h4>
                  <p className="abstract-text">{selectedPaper.abstract}</p>
                </div>
              )}

              {/* Detected Limitations */}
              <div className="detail-section">
                <h4 className="section-label">
                  Detected Limitations ({paperLimitations.length})
                </h4>
                {paperLimitations.length === 0 ? (
                  <p className="empty-hint">
                    No limitations classified yet. Click "Run Phase 2 NLP" to extract discourse categories.
                  </p>
                ) : (
                  <div className="limitations-micro-list">
                    {paperLimitations.map((lim, idx) => (
                      <div key={idx} className="micro-limitation-pill">
                        <span className="lim-badge">{lim.subtype || 'Limitation'}</span>
                        <span className="lim-text">{lim.source_text}</span>
                        <span className="lim-page font-mono">Page {lim.page_number}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Section Hierarchy */}
              {paperDetails?.sections && paperDetails.sections.length > 0 && (
                <div className="detail-section">
                  <h4 className="section-label">
                    Parsed Section Hierarchy ({paperDetails.sections.length})
                  </h4>
                  <div className="sections-tree-list">
                    {paperDetails.sections.map((sec, idx) => (
                      <div key={idx} className="section-tree-item">
                        <span className="sec-order font-mono">§{idx + 1}</span>
                        <span className="sec-title">{sec.section_name}</span>
                        <span className="sec-page font-mono">Page {sec.page_start}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="detail-placeholder-box">
              <FileText size={40} />
              <h4>Select a Paper</h4>
              <p>Choose any paper from the library to inspect its parsed sections, metadata, and extracted limitations.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
