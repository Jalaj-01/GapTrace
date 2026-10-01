import React, { useState } from 'react';
import {
  FileText,
  Clock,
  Share2,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  GitBranch,
  Filter,
  Layers,
  ChevronRight,
  ExternalLink,
  BookOpen,
  ArrowRight,
  Play,
  RotateCw,
} from 'lucide-react';
import { useResearch } from '../../contexts/ResearchContext';
import EvidenceCard from './EvidenceCard';
import GapTimeline from './GapTimeline';
import ResearchGraphView from './ResearchGraphView';

export default function ResearchSessionView() {
  const {
    activeSession,
    activeTab,
    setActiveTab,
    stagedFiles,
    runAnalysis,
    isAnalyzing,
    analysisOptions,
    setAnalysisOptions,
    setActiveView,
  } = useResearch();

  const [focusInput, setFocusInput] = useState(activeSession?.title || 'Cross-domain generalization');
  const [selectedPaperModal, setSelectedPaperModal] = useState(null);

  if (!activeSession) return null;

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'evidence', label: 'Evidence', count: activeSession.evidence?.length || 0 },
    { id: 'timeline', label: 'Timeline' },
    { id: 'genealogy', label: 'Genealogy' },
    { id: 'counter-evidence', label: 'Counter-Evidence', count: activeSession.counterCount || 0 },
    { id: 'graph', label: 'Graph' },
    { id: 'questions', label: 'Research Questions', count: activeSession.researchQuestions?.length || 0 },
  ];

  const handleStartAnalysis = () => {
    runAnalysis(focusInput);
  };

  return (
    <div className="research-session-container">
      {/* 1. Compact Paper Collection Banner (Section 7) */}
      <div className="session-top-banner">
        <div className="banner-left">
          <span className="banner-badge">Research Session</span>
          <h2 className="banner-title truncate">{activeSession.title}</h2>
          <span className="banner-meta">
            {activeSession.papersCount || 0} Papers • {activeSession.yearSpan || '2020–2026'}
          </span>
        </div>

        <div className="banner-right">
          <button
            className="view-papers-btn"
            onClick={() => setActiveView('papers')}
            title="Inspect papers participating in this session"
          >
            <BookOpen size={14} />
            <span>View Papers</span>
          </button>
        </div>
      </div>

      {/* 2. Research Focus & Controls Bar (Section 7) */}
      <div className="research-controls-card">
        <div className="focus-row">
          <label className="focus-label">Research focus:</label>
          <div className="focus-input-wrapper">
            <input
              type="text"
              className="focus-text-input"
              value={focusInput}
              onChange={(e) => setFocusInput(e.target.value)}
              placeholder="e.g. Cross-domain generalization in biomedical NLP"
            />
          </div>
          <button
            className="start-analysis-btn"
            onClick={handleStartAnalysis}
            disabled={isAnalyzing}
          >
            {isAnalyzing ? <RotateCw size={14} className="spin-icon" /> : <Play size={14} />}
            <span>{isAnalyzing ? 'Analyzing...' : 'Start Analysis'}</span>
          </button>
        </div>

        <div className="analysis-options-row">
          <span className="options-title">Analysis options:</span>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={analysisOptions.limitations}
              onChange={(e) =>
                setAnalysisOptions((prev) => ({ ...prev, limitations: e.target.checked }))
              }
            />
            <span>Research limitations</span>
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={analysisOptions.emergingTopics}
              onChange={(e) =>
                setAnalysisOptions((prev) => ({ ...prev, emergingTopics: e.target.checked }))
              }
            />
            <span>Emerging topics</span>
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={analysisOptions.researchGaps}
              onChange={(e) =>
                setAnalysisOptions((prev) => ({ ...prev, researchGaps: e.target.checked }))
              }
            />
            <span>Research gaps</span>
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={analysisOptions.counterEvidence}
              onChange={(e) =>
                setAnalysisOptions((prev) => ({ ...prev, counterEvidence: e.target.checked }))
              }
            />
            <span>Counter-evidence</span>
          </label>
        </div>
      </div>

      {/* 3. Top Result Navigation Tabs (Section 9) */}
      <div className="result-nav-tabs">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              className={`nav-tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span>{tab.label}</span>
              {typeof tab.count === 'number' && (
                <span className="tab-count-pill">{tab.count}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* 4. Tab Content Area */}
      <div className="session-tab-content">
        {/* ================= OVERVIEW TAB ================= */}
        {activeTab === 'overview' && (
          <div className="overview-tab-pane animate-fade-in">
            {/* Potential Gap Summary Card (Section 8) */}
            <div className="gap-summary-card">
              <div className="gap-card-header">
                <span className="gap-kicker">Potential Research Gap</span>
                <span className={`status-badge-persistent status-${activeSession.status?.toLowerCase() || 'persistent'}`}>
                  {activeSession.status || 'PERSISTENT'}
                </span>
              </div>

              <h3 className="gap-heading">{activeSession.gapTitle}</h3>
              <p className="gap-summary-text">{activeSession.summary}</p>

              {/* Three Metric Pillars */}
              <div className="evidence-metrics-grid">
                <div
                  className="metric-stat-card supporting"
                  onClick={() => setActiveTab('evidence')}
                  role="button"
                >
                  <span className="stat-label">Supporting evidence</span>
                  <span className="stat-number font-mono">{activeSession.supportingCount || 0} papers</span>
                  <span className="stat-hint">Consistent limitations reported</span>
                </div>

                <div
                  className="metric-stat-card addressing"
                  onClick={() => setActiveTab('evidence')}
                  role="button"
                >
                  <span className="stat-label">Addressing evidence</span>
                  <span className="stat-number font-mono">{activeSession.addressingCount || 0} papers</span>
                  <span className="stat-hint">Partial solutions attempted</span>
                </div>

                <div
                  className="metric-stat-card counter"
                  onClick={() => setActiveTab('counter-evidence')}
                  role="button"
                >
                  <span className="stat-label">Counter-evidence</span>
                  <span className="stat-number font-mono">{activeSession.counterCount || 0} papers</span>
                  <span className="stat-hint">Competing empirical claims</span>
                </div>
              </div>
            </div>

            {/* Why this gap appears */}
            <div className="why-it-appears-card">
              <h4 className="card-section-title">Why this gap appears</h4>
              <div className="why-reasons-list">
                {(activeSession.whyItAppears || []).map((reason, idx) => (
                  <div key={idx} className="reason-item">
                    <div className="reason-number font-mono">{idx + 1}</div>
                    <div className="reason-text">
                      <strong className="reason-title">{reason.title}</strong>
                      <p className="reason-desc">{reason.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ================= EVIDENCE TAB ================= */}
        {activeTab === 'evidence' && (
          <div className="evidence-tab-pane animate-fade-in">
            <div className="evidence-tab-header">
              <div>
                <h4 className="tab-pane-title">Evidence-Grounded Scientific Provenance</h4>
                <p className="tab-pane-subtitle">
                  Sentences extracted with page numbers, section headers, and verified limitations.
                </p>
              </div>
            </div>

            <div className="evidence-cards-stream">
              {(activeSession.evidence || []).map((ev) => (
                <EvidenceCard
                  key={ev.id}
                  evidence={ev}
                  onOpenPaper={(item) => setSelectedPaperModal(item)}
                />
              ))}
            </div>
          </div>
        )}

        {/* ================= TIMELINE TAB ================= */}
        {activeTab === 'timeline' && (
          <div className="timeline-tab-pane animate-fade-in">
            <GapTimeline timeline={activeSession.timeline} />
          </div>
        )}

        {/* ================= GENEALOGY TAB ================= */}
        {activeTab === 'genealogy' && (
          <div className="genealogy-tab-pane animate-fade-in">
            <div className="genealogy-intro">
              <h4 className="tab-pane-title">Methodological Lineage & Problem Ancestry</h4>
              <p className="tab-pane-subtitle">
                How underlying algorithmic assumptions were inherited and passed down across generations.
              </p>
            </div>

            <div className="genealogy-steps-list">
              {(activeSession.genealogy || []).map((g, idx) => (
                <div key={idx} className="genealogy-card">
                  <div className="genealogy-era-badge font-mono">{g.era}</div>
                  <h5 className="genealogy-method-name">{g.method}</h5>
                  <p className="genealogy-issue-text">
                    <span className="issue-label">Inherited limitation:</span> {g.issue}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ================= COUNTER-EVIDENCE TAB ================= */}
        {activeTab === 'counter-evidence' && (
          <div className="counter-tab-pane animate-fade-in">
            <div className="counter-intro">
              <h4 className="tab-pane-title">Verified Counter-Evidence & Boundary Claims</h4>
              <p className="tab-pane-subtitle">
                Papers claiming this limitation does not hold or is resolved under specific architectural conditions.
              </p>
            </div>

            <div className="counter-evidence-list">
              {(activeSession.counterEvidence || []).map((c, idx) => (
                <div key={idx} className="counter-card">
                  <div className="counter-card-header">
                    <h5 className="counter-paper-title">{c.title}</h5>
                    <span className="counter-author font-mono">{c.author}</span>
                  </div>
                  <div className="counter-claim-box">
                    <span className="claim-label">Claim:</span>
                    <p className="claim-content">"{c.claim}"</p>
                  </div>
                  <div className="counter-rebuttal-box">
                    <span className="rebuttal-label">GapTrace Cross-Examination:</span>
                    <p className="rebuttal-content">{c.counterpoint}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ================= GRAPH TAB ================= */}
        {activeTab === 'graph' && (
          <div className="graph-tab-pane animate-fade-in">
            <ResearchGraphView
              graphData={activeSession.graphData}
              onOpenPaper={(node) => setSelectedPaperModal(node)}
            />
          </div>
        )}

        {/* ================= RESEARCH QUESTIONS TAB ================= */}
        {activeTab === 'questions' && (
          <div className="questions-tab-pane animate-fade-in">
            <div className="questions-intro">
              <h4 className="tab-pane-title">Synthesized Unresolved Research Questions</h4>
              <p className="tab-pane-subtitle">
                Concrete research hypotheses derived from this gap for upcoming grant proposals or dissertations.
              </p>
            </div>

            <div className="questions-grid">
              {(activeSession.researchQuestions || []).map((q, idx) => (
                <div key={idx} className="question-card">
                  <div className="question-number-pill font-mono">RQ-{idx + 1}</div>
                  <p className="question-text">{q}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Simple Paper Preview Modal */}
      {selectedPaperModal && (
        <div className="modal-backdrop" onClick={() => setSelectedPaperModal(null)}>
          <div className="modal-container paper-quick-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h4 className="modal-title">
                {selectedPaperModal.paperTitle || selectedPaperModal.paper || 'Scientific Paper Source'}
              </h4>
              <button className="modal-close-btn" onClick={() => setSelectedPaperModal(null)}>
                &times;
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-lead">
                Section: <strong>{selectedPaperModal.section || 'Experiments'}</strong> • Page: <strong>{selectedPaperModal.page || 8}</strong>
              </p>
              <div className="modal-quote-box">
                <blockquote>"{selectedPaperModal.quote || selectedPaperModal.label}"</blockquote>
              </div>
              <p className="modal-provenance-note">
                Verified with complete provenance: Ingested & parsed by GapTrace Phase 1 & Phase 2 Scientific NLP pipeline.
              </p>
            </div>
            <div className="modal-footer">
              <button className="btn-primary" onClick={() => setSelectedPaperModal(null)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
