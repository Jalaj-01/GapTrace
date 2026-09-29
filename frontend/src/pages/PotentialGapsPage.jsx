import React, { useState } from 'react';
import { Target, Filter, ArrowRight, ShieldCheck, Clock, BookOpen } from 'lucide-react';
import { useResearch } from '../contexts/ResearchContext';
import { RECENT_SESSIONS } from '../services/researchData';

export default function PotentialGapsPage() {
  const { selectSession } = useResearch();
  const [statusFilter, setStatusFilter] = useState('ALL');

  const filtered = RECENT_SESSIONS.filter((item) => {
    if (statusFilter === 'ALL') return true;
    return item.status === statusFilter;
  });

  return (
    <div className="potential-gaps-page-container">
      <div className="page-header-row">
        <div>
          <h2 className="page-title">Potential Research Gaps Catalogue</h2>
          <p className="page-subtitle">
            Systematically verified research gaps classified by temporal persistence across peer-reviewed literature.
          </p>
        </div>

        <div className="filter-button-group">
          {['ALL', 'PERSISTENT', 'EMERGING', 'ADDRESSED'].map((st) => (
            <button
              key={st}
              className={`filter-btn ${statusFilter === st ? 'active' : ''}`}
              onClick={() => setStatusFilter(st)}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      <div className="gaps-catalogue-grid">
        {filtered.map((gap) => (
          <article key={gap.id} className="gap-catalogue-card">
            <div className="gap-card-header">
              <span className={`status-badge-persistent status-${gap.status.toLowerCase()}`}>
                {gap.status}
              </span>
              <span className="gap-year-span font-mono">{gap.yearSpan}</span>
            </div>

            <h3 className="gap-card-title">{gap.gapTitle}</h3>
            <p className="gap-card-summary">{gap.summary}</p>

            <div className="gap-evidence-pills">
              <span className="ev-pill font-mono">{gap.supportingCount} Supporting Papers</span>
              <span className="ev-pill font-mono">{gap.addressingCount} Partial Mitigations</span>
              <span className="ev-pill font-mono">{gap.counterCount} Counter-Evidence</span>
            </div>

            <div className="gap-card-footer">
              <button
                className="btn-open-session"
                onClick={() => selectSession(gap.id)}
              >
                <span>Launch Research Session</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
