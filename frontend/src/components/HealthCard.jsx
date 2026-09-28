import React from 'react';
import { Database, Cpu, Server, Clock, CheckCircle2, AlertTriangle, XCircle, Shield } from 'lucide-react';

export default function HealthCard({ healthData, error, lastChecked }) {
  const db = healthData?.database || {};
  const services = healthData?.services || {};
  const isDbConnected = db.status === 'connected';

  return (
    <div className="health-card glass-card">
      <div className="card-header">
        <div className="card-title-group">
          <Server className="section-icon text-indigo" size={20} />
          <h2 className="card-title">Live System Diagnostics</h2>
        </div>
        <div className="timestamp-badge">
          <Clock size={13} />
          <span>{lastChecked ? lastChecked.toLocaleTimeString() : 'Awaiting check...'}</span>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <AlertTriangle size={18} className="text-amber" />
          <div className="error-text">
            <strong>Connection Notice:</strong> {error}
          </div>
        </div>
      )}

      <div className="metrics-grid">
        {/* Metric 1: Backend API */}
        <div className="metric-box">
          <div className="metric-header">
            <span className="metric-label">FastAPI Backend</span>
            {healthData ? (
              <CheckCircle2 size={16} className="text-green" />
            ) : (
              <XCircle size={16} className="text-rose" />
            )}
          </div>
          <div className="metric-value">{healthData?.status || (error ? 'Unreachable' : 'Connecting...')}</div>
          <div className="metric-sub">Version {healthData?.version || '0.1.0'} &bull; {healthData?.environment || 'development'}</div>
        </div>

        {/* Metric 2: Database Connection */}
        <div className="metric-box">
          <div className="metric-header">
            <span className="metric-label">Database Subsystem</span>
            {isDbConnected ? (
              <CheckCircle2 size={16} className="text-green" />
            ) : (
              <AlertTriangle size={16} className="text-amber" />
            )}
          </div>
          <div className="metric-value">
            {isDbConnected ? `Connected (${db.dialect})` : 'Disconnected'}
          </div>
          <div className="metric-sub">
            {db.fallback_in_use
              ? 'SQLite dev fallback active'
              : db.host
              ? `Host: ${db.host}`
              : 'Target: PostgreSQL'}
          </div>
        </div>

        {/* Metric 3: LLM Provider Abstraction */}
        <div className="metric-box">
          <div className="metric-header">
            <span className="metric-label">LLM Provider Bridge</span>
            <Cpu size={16} className="text-cyan" />
          </div>
          <div className="metric-value text-capitalize">
            {services.llm_provider || 'Provider-Independent'}
          </div>
          <div className="metric-sub">Abstract Base Interface Ready</div>
        </div>

        {/* Metric 4: Runtime Environment */}
        <div className="metric-box">
          <div className="metric-header">
            <span className="metric-label">Host Environment</span>
            <Shield size={16} className="text-indigo" />
          </div>
          <div className="metric-value">
            {services.python ? `Python ${services.python}` : 'Python 3.11+'}
          </div>
          <div className="metric-sub">{services.os || 'Windows / POSIX'}</div>
        </div>
      </div>
    </div>
  );
}
