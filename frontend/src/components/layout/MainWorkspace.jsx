import React from 'react';
import { useResearch } from '../../contexts/ResearchContext';
import ResearchComposer from '../research/ResearchComposer';
import ResearchSessionView from '../research/ResearchSessionView';
import Dashboard from '../../pages/Dashboard';
import PapersPage from '../../pages/PapersPage';
import PaperDetailPage from '../../pages/PaperDetailPage';
import LandscapePage from '../../pages/LandscapePage';
import ResearchGraphPage from '../../pages/ResearchGraphPage';
import PotentialGapsPage from '../../pages/PotentialGapsPage';
import GapDetailPage from '../../pages/GapDetailPage';
import GapGenealogyPage from '../../pages/GapGenealogyPage';
import GapLifecyclePage from '../../pages/GapLifecyclePage';
import CounterEvidencePage from '../../pages/CounterEvidencePage';
import EvidenceExplorerPage from '../../pages/EvidenceExplorerPage';
import ResearchReportPage from '../../pages/ResearchReportPage';
import PaperUploaderModal from '../research/PaperUploaderModal';
import SettingsModal from '../ui/SettingsModal';
import AboutModal from '../ui/AboutModal';

export default function MainWorkspace() {
  const { activeView, runAnalysis } = useResearch();

  const samplePromptStarters = [
    'Cross-dataset generalization under subpopulation shifts in biomedical NLP',
    'Associative recall degradation in sub-quadratic linear attention models',
    'Morphological divergence in low-resource cross-lingual transfer',
    'Hallucination and clinical reasoning calibration in diagnostic LLMs',
  ];

  return (
    <main className="main-workspace-root" role="main">
      <div className="workspace-scroll-area">
        {/* ================= VIEW: DASHBOARD ================= */}
        {activeView === 'dashboard' && (
          <div className="page-wrapper animate-fade-in">
            <Dashboard />
          </div>
        )}

        {/* ================= VIEW: WELCOME / NEW RESEARCH ================= */}
        {activeView === 'welcome' && (
          <div className="welcome-screen-container animate-fade-in">
            <div className="welcome-center-content">
              {/* Subtle GapTrace Logo Glyph */}
              <div className="welcome-logo-glyph">
                <svg width="44" height="44" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 2L2 7L12 12L22 7L12 2Z"
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

              {/* Minimal Heading & Subheading */}
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

            {/* Bottom-Center Input Composer */}
            <div className="composer-anchor-bottom">
              <ResearchComposer />
            </div>
          </div>
        )}

        {/* ================= VIEW: RESEARCH SESSION ================= */}
        {activeView === 'session' && (
          <div className="session-screen-container animate-fade-in">
            <ResearchSessionView />
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

        {/* ================= VIEW: PAPER DETAIL ================= */}
        {activeView === 'paper-detail' && (
          <div className="page-wrapper animate-fade-in">
            <PaperDetailPage />
          </div>
        )}

        {/* ================= VIEW: LANDSCAPE ================= */}
        {activeView === 'landscape' && (
          <div className="page-wrapper animate-fade-in">
            <LandscapePage />
          </div>
        )}

        {/* ================= VIEW: RESEARCH GRAPH ================= */}
        {activeView === 'graph' && (
          <div className="page-wrapper animate-fade-in">
            <ResearchGraphPage />
          </div>
        )}

        {/* ================= VIEW: POTENTIAL GAPS ================= */}
        {activeView === 'gaps' && (
          <div className="page-wrapper animate-fade-in">
            <PotentialGapsPage />
          </div>
        )}

        {/* ================= VIEW: GAP DETAIL ================= */}
        {activeView === 'gap-detail' && (
          <div className="page-wrapper animate-fade-in">
            <GapDetailPage />
          </div>
        )}

        {/* ================= VIEW: GAP GENEALOGY ================= */}
        {activeView === 'genealogy' && (
          <div className="page-wrapper animate-fade-in">
            <GapGenealogyPage />
          </div>
        )}

        {/* ================= VIEW: GAP LIFECYCLE ================= */}
        {activeView === 'lifecycle' && (
          <div className="page-wrapper animate-fade-in">
            <GapLifecyclePage />
          </div>
        )}

        {/* ================= VIEW: COUNTER-EVIDENCE ================= */}
        {activeView === 'counter-evidence' && (
          <div className="page-wrapper animate-fade-in">
            <CounterEvidencePage />
          </div>
        )}

        {/* ================= VIEW: EVIDENCE EXPLORER ================= */}
        {activeView === 'evidence' && (
          <div className="page-wrapper animate-fade-in">
            <EvidenceExplorerPage />
          </div>
        )}

        {/* ================= VIEW: RESEARCH REPORT ================= */}
        {activeView === 'report' && (
          <div className="page-wrapper animate-fade-in">
            <ResearchReportPage />
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
