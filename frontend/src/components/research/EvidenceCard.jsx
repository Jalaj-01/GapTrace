import React, { useState } from 'react';
import { ExternalLink, Copy, Check, Quote, Bookmark } from 'lucide-react';

export default function EvidenceCard({ evidence, onOpenPaper }) {
  const [copied, setCopied] = useState(false);

  const handleCopyQuote = () => {
    navigator.clipboard.writeText(`"${evidence.quote}" — ${evidence.paperTitle} (${evidence.year})`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getBadgeClass = (badgeType) => {
    switch (badgeType) {
      case 'LIMITATION':
        return 'badge-limitation';
      case 'COUNTER_EVIDENCE':
        return 'badge-counter';
      case 'FUTURE_WORK':
        return 'badge-future';
      default:
        return 'badge-default';
    }
  };

  return (
    <article className="evidence-card-root">
      <div className="evidence-card-header">
        <div className="evidence-id-tag">
          <span className="evidence-num">Evidence #{evidence.number || evidence.id}</span>
          {evidence.badgeType && (
            <span className={`evidence-type-badge ${getBadgeClass(evidence.badgeType)}`}>
              {evidence.badgeType.replace('_', ' ')}
            </span>
          )}
        </div>

        <div className="evidence-header-actions">
          <button
            className="action-icon-btn"
            onClick={handleCopyQuote}
            title={copied ? 'Copied quote!' : 'Copy citation & quote'}
          >
            {copied ? <Check size={14} className="text-emerald" /> : <Copy size={14} />}
          </button>
        </div>
      </div>

      {/* Quote Body */}
      <div className="evidence-quote-container">
        <Quote size={16} className="quote-mark" />
        <blockquote className="evidence-quote-text">
          {evidence.quote}
        </blockquote>
      </div>

      {/* Provenance Metadata Grid */}
      <div className="evidence-provenance-bar">
        <div className="prov-item">
          <span className="prov-label">Paper:</span>
          <span className="prov-value paper-title truncate" title={evidence.paperTitle}>
            {evidence.paperTitle}
          </span>
        </div>

        <div className="prov-meta-row">
          <div className="prov-sub-item">
            <span className="prov-label">Section:</span>
            <span className="prov-value">{evidence.section || 'Unspecified'}</span>
          </div>

          <div className="prov-sub-item">
            <span className="prov-label">Page:</span>
            <span className="prov-value font-mono">{evidence.page ?? 'N/A'}</span>
          </div>

          <div className="prov-sub-item">
            <span className="prov-label">Year:</span>
            <span className="prov-value font-mono">{evidence.year || 2024}</span>
          </div>
        </div>

        <div className="evidence-card-actions">
          <button
            className="open-paper-btn"
            onClick={() => onOpenPaper && onOpenPaper(evidence)}
            title="Inspect source paper and surrounding context"
          >
            <span>Open Paper</span>
            <ExternalLink size={13} />
          </button>
        </div>
      </div>
    </article>
  );
}
