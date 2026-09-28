import React from 'react';
import { BookOpen, Activity, Terminal, ShieldCheck, AlertCircle } from 'lucide-react';

export default function Header({ healthData, error, onRefresh, loading }) {
  const isHealthy = healthData?.status === 'healthy';
  const isDegraded = healthData?.status === 'degraded' || (error && healthData);
  const isOffline = !!error && !healthData;

  return (
    <header className="header-container glass-card">
      <div className="header-brand">
        <div className="header-icon-wrapper">
          <BookOpen className="header-icon" />
          <span className="sparkle-dot"></span>
        </div>
        <div>
          <div className="title-row">
            <h1 className="header-title">Scientific Paper Gap Finder</h1>
            <span className="badge phase-badge">Phase 0 Foundation</span>
          </div>
          <p className="header-subtitle">
            Evidence-Grounded NLP Architecture for Identifying Research Gaps & Emerging Questions
          </p>
        </div>
      </div>

      <div className="header-actions">
        {/* Status Pill */}
        <div className={`status-pill ${isHealthy ? 'status-ok' : isDegraded ? 'status-warn' : 'status-err'}`}>
          <span className="status-dot"></span>
          <span className="status-label">
            {isHealthy ? 'System Healthy' : isDegraded ? 'Service Degraded' : 'Backend Offline'}
          </span>
        </div>

        {/* Refresh Button */}
        <button
          className="refresh-btn"
          onClick={onRefresh}
          disabled={loading}
          title="Refresh health status"
        >
          <Activity className={`btn-icon ${loading ? 'spin' : ''}`} size={16} />
          <span>{loading ? 'Checking...' : 'Ping Diagnostics'}</span>
        </button>
      </div>
    </header>
  );
}
