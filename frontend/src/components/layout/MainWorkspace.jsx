import React from 'react';
import { useResearch } from '../../contexts/ResearchContext';
import ResearchComposer from '../research/ResearchComposer';
import ResearchSessionView from '../research/ResearchSessionView';
import PapersPage from '../../pages/PapersPage';
import LandscapePage from '../../pages/LandscapePage';
import PotentialGapsPage from '../../pages/PotentialGapsPage';
import EvidenceExplorerPage from '../../pages/EvidenceExplorerPage';
import ResearchGraphView from '../research/ResearchGraphView';
import PaperUploaderModal from '../research/PaperUploaderModal';
import SettingsModal from '../ui/SettingsModal';
import AboutModal from '../ui/AboutModal';

export default function MainWorkspace() {
  const { activeView, activeSession, stagedFiles, runAnalysis } = useResearch();

  const samplePromptStarters = [
    'Cross-dataset generalization under subpopulation shifts in biomedical NLP',
    'Associative recall degradation in sub-quadratic linear attention models',
    'Morphological divergence in low-resource cross-lingual transfer',
    'Hallucination and clinical reasoning calibration in diagnostic LLMs',
  ];

  return (
    <main className="main-workspace-root" role="main">
      <div className="workspace-scroll-area">
        {/* ================= VIEW: WELCOME / NEW RESEARCH ================= */}
        {activeView === 'welcome' && (
          <div className="welcome-screen-container animate-fade-in">
            <div className="welcome-center-content">
              {/* Subtle GapTrace Logo Glyph */}
              <div className="welcome-logo-glyph">
                <svg width="44" height="44" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 2L2 7L12 12L22 7L12 12Z"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M2 17L12 22L22 17"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M2 12L12 17L22 12"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>

              {/* Minimal Heading & Subheading (Section 4) */}
              <h1 className="welcome-heading">What would you like to research?</h1>
              <p className="welcome-subheading">
                Upload scientific papers and trace how research gaps emerge, evolve, and are addressed.
              </p>

              {/* Subtle Quick Starters */}
              <div className="quick-starters-grid">
                {samplePromptStarters.map((starter, idx) => (
                  <button
                    key={idx}
                    className="starter-chip"
                    onClick={() => runAnalysis(starter)}
                  >
                    <span>{starter}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Bottom-Center Input Composer (Section 5) */}
            <div className="composer-anchor-bottom">
              <ResearchComposer />
            </div>
          </div>
        )}

        {/* ================= VIEW: RESEARCH SESSION ================= */}
        {activeView === 'session' && (
          <div className="session-screen-container animate-fade-in">
            <ResearchSessionView />
            {/* Ambient Composer for iterative follow-up inquiries */}
            <div className="composer-anchor-sticky">
              <ResearchComposer />
            </div>
          </div>
        )}

        {/* ================= VIEW: PAPERS LIBRARY ================= */}
        {activeView === 'papers' && (
          <div className="page-wrapper animate-fade-in">
            <PapersPage />
          </div>
        )}

        {/* ================= VIEW: LANDSCAPE ================= */}
        {activeView === 'landscape' && (
          <div className="page-wrapper animate-fade-in">
            <LandscapePage />
          </div>
        )}

        {/* ================= VIEW: POTENTIAL GAPS ================= */}
        {activeView === 'gaps' && (
          <div className="page-wrapper animate-fade-in">
            <PotentialGapsPage />
          </div>
        )}

        {/* ================= VIEW: RESEARCH GRAPH ================= */}
        {activeView === 'graph' && (
          <div className="page-wrapper animate-fade-in">
            <div className="full-graph-wrapper">
              <div className="page-header-row mb-4">
                <div>
                  <h2 className="page-title">Interactive Research Knowledge Graph</h2>
                  <p className="page-subtitle">
                    Discourse relations linking papers, methods, datasets, empirical claims, and persistent limitations.
                  </p>
                </div>
              </div>
              <ResearchGraphView graphData={activeSession?.graphData} />
            </div>
          </div>
        )}

        {/* ================= VIEW: EVIDENCE EXPLORER ================= */}
        {activeView === 'evidence' && (
          <div className="page-wrapper animate-fade-in">
            <EvidenceExplorerPage />
          </div>
        )}
      </div>

      {/* Global Modals */}
      <PaperUploaderModal />
      <SettingsModal />
      <AboutModal />
    </main>
  );
}
