import React from 'react';
import { Clock, ArrowDown, BookOpen, AlertTriangle, CheckCircle, Lightbulb } from 'lucide-react';

export default function GapTimeline({ timeline = [] }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="empty-state-box">
        <Clock size={32} />
        <p className="empty-title">No timeline data available</p>
        <p className="empty-sub">Run gap verification to trace the temporal evolution across years.</p>
      </div>
    );
  }

  const getPhaseIcon = (badge) => {
    switch (badge) {
      case 'IDENTIFIED':
        return <AlertTriangle size={14} className="icon-identified" />;
      case 'SOLUTION':
      case 'EXPLORATION':
        return <Lightbulb size={14} className="icon-solution" />;
      case 'PERSISTENCE':
      case 'ACTIVE_GAP':
        return <Clock size={14} className="icon-active-gap" />;
      default:
        return <BookOpen size={14} className="icon-default" />;
    }
  };

  return (
    <div className="timeline-container">
      <div className="timeline-intro">
        <h4 className="timeline-title">Temporal Evolution of Research Gap</h4>
        <p className="timeline-subtitle">
          Tracing how this problem emerged in the literature, initial mitigations proposed, and why it remains an active gap in 2026.
        </p>
      </div>

      <div className="timeline-spine">
        {timeline.map((step, idx) => {
          const isLast = idx === timeline.length - 1;
          return (
            <div key={idx} className={`timeline-node-row ${isLast ? 'is-current-gap' : ''}`}>
              {/* Year column */}
              <div className="timeline-year-col">
                <span className="year-pill font-mono">{step.year}</span>
              </div>

              {/* Connecting line & bullet */}
              <div className="timeline-track-col">
                <div className="timeline-marker">
                  {getPhaseIcon(step.badge)}
                </div>
                {!isLast && <div className="timeline-line-segment" />}
              </div>

              {/* Event card */}
              <div className="timeline-content-card">
                <div className="timeline-card-header">
                  <span className="timeline-phase-label">{step.phase}</span>
                  {step.citation && (
                    <span className="timeline-citation-badge">{step.citation}</span>
                  )}
                </div>
                <p className="timeline-desc">{step.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
