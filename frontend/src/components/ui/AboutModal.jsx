import React from 'react';
import { X, HelpCircle, BookOpen, GitBranch, ShieldCheck } from 'lucide-react';
import { useResearch } from '../../contexts/ResearchContext';

export default function AboutModal() {
  const { isAboutOpen, setIsAboutOpen } = useResearch();

  if (!isAboutOpen) return null;

  return (
    <div className="modal-backdrop" onClick={() => setIsAboutOpen(false)}>
      <div
        className="modal-container about-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="about-modal-title"
      >
        <div className="modal-header">
          <div className="title-lockup">
            <BookOpen size={18} />
            <h3 id="about-modal-title" className="modal-title">About GapTrace</h3>
          </div>
          <button className="modal-close-btn" onClick={() => setIsAboutOpen(false)}>
            <X size={18} />
          </button>
        </div>

        <div className="about-body">
          <div className="about-hero">
            <span className="about-kicker">Research Intelligence Framework</span>
            <h4 className="about-name">
              GapTrace: An Evidence-Grounded NLP Framework for Temporal Research Gap Discovery and Verification
            </h4>
            <p className="about-desc">
              GapTrace transforms how researchers, doctoral scholars, and principal investigators synthesize scientific literature. Rather than summarizing text superficially, GapTrace segments scientific discourse into atomic propositions, detects reported limitations across publication timelines, cross-examines counter-evidence, and constructs verifiable gap genealogies.
            </p>
          </div>

          <div className="architecture-summary-box">
            <h5 className="box-heading">Framework Architecture Pipeline</h5>
            <div className="pipeline-steps-chips">
              <span className="chip">Phase 0: Foundation & Core Schemas</span>
              <span className="chip">Phase 1: PDF Ingestion & Section Parsing</span>
              <span className="chip">Phase 2: Scientific NLP & Discourse Classification</span>
              <span className="chip">Phase 3: Dense Retrieval & Evidence Verification</span>
              <span className="chip">Phase 4: Temporal Gap Reasoning & Synthesis</span>
            </div>
          </div>

          <div className="citation-box">
            <span className="citation-title">Citation</span>
            <pre className="citation-code font-mono">
{`@article{gupta2026gaptrace,
  title={GapTrace: An Evidence-Grounded NLP Framework for Temporal Research Gap Discovery and Verification},
  author={Gupta, Jalaj and Research Consortium},
  journal={arXiv preprint arXiv:2603.xxxxx},
  year={2026}
}`}
            </pre>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-primary" onClick={() => setIsAboutOpen(false)}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
