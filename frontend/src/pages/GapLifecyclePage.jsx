import React, { useState, useEffect } from 'react';
import {
  Clock,
  ArrowRight,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  RotateCcw,
  Sparkles,
  RefreshCw,
  Target,
  BookOpen,
} from 'lucide-react';
import {
  fetchGapLifecycleOverview,
  fetchGapLifecycle,
  fetchGapTimeline,
  fetchGapCandidates,
} from '../services/api';
import { useResearch } from '../contexts/ResearchContext';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

const STATUS_CONFIG = {
  EMERGING: {
    label: 'Emerging',
    color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10',
    desc: 'Recently identified bottleneck in newer literature (1-2 years).',
  },
  PERSISTENT: {
    label: 'Persistent',
    color: 'text-amber-400 border-amber-500/20 bg-amber-500/10',
    desc: 'Bottleneck persisting unaddressed across >=2 publication years.',
  },
  PARTIALLY_ADDRESSED: {
    label: 'Partially Addressed',
    color: 'text-blue-400 border-blue-500/20 bg-blue-500/10',
    desc: 'Mitigations proposed, but domain or scale limitations remain.',
  },
  ADDRESSED: {
    label: 'Addressed',
    color: 'text-cyan-400 border-cyan-500/20 bg-cyan-500/10',
    desc: 'Verified solutions established in peer-reviewed literature.',
  },
  REOPENED: {
    label: 'Reopened',
    color: 'text-rose-400 border-rose-500/20 bg-rose-500/10',
    desc: 'Previously addressed issue recurring in new paradigms or larger models.',
  },
  UNCERTAIN: {
    label: 'Uncertain',
    color: 'text-gray-400 border-gray-500/20 bg-gray-500/10',
    desc: 'Single publication or insufficient temporal evidence to determine.',
  },
};

export default function GapLifecyclePage() {
  const { selectedGapId, setSelectedGapId, setActiveView, openGapDetail } = useResearch();

  const [overview, setOverview] = useState(null);
  const [candidatesList, setCandidatesList] = useState([]);
  const [currentGapId, setCurrentGapId] = useState(selectedGapId || null);

  const [lifecycleDetail, setLifecycleDetail] = useState(null);
  const [timeline, setTimeline] = useState(null);

  const [loading, setLoading] = useState(true);
  const [loadingGap, setLoadingGap] = useState(false);
  const [error, setError] = useState(null);

  // Load overview and candidates
  const loadOverviewData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ovRes, candRes] = await Promise.allSettled([
        fetchGapLifecycleOverview(),
        fetchGapCandidates({ limit: 100 }),
      ]);

      const ov = ovRes.status === 'fulfilled' ? ovRes.value : null;
      const cands = candRes.status === 'fulfilled' && candRes.value?.candidates ? candRes.value.candidates : [];

      setOverview(ov);
      setCandidatesList(cands);

      if (!currentGapId && cands.length > 0) {
        setCurrentGapId(cands[0].gap_id);
      }
    } catch (err) {
      setError(err.message || 'Failed to load gap lifecycle overview.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverviewData();
  }, []);

  useEffect(() => {
    if (selectedGapId) {
      setCurrentGapId(selectedGapId);
    }
  }, [selectedGapId]);

  useEffect(() => {
    if (!currentGapId) return;
    loadSelectedGapLifecycle(currentGapId);
  }, [currentGapId]);

  const loadSelectedGapLifecycle = async (gapId) => {
    setLoadingGap(true);
    try {
      const [lifeRes, timeRes] = await Promise.allSettled([
        fetchGapLifecycle(gapId),
        fetchGapTimeline(gapId),
      ]);

      setLifecycleDetail(lifeRes.status === 'fulfilled' ? lifeRes.value : null);
      setTimeline(timeRes.status === 'fulfilled' ? timeRes.value : null);
    } catch {
      // Non-blocking
    } finally {
      setLoadingGap(false);
    }
  };

  const statusCounts = overview?.status_counts || {};

  return (
    <div className="gap-lifecycle-page p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <button
            onClick={() => setActiveView('gaps')}
            className="p-1.5 border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition flex-shrink-0"
            title="Back to Gaps Catalogue"
          >
            <ArrowLeft size={16} />
          </button>
          <div className="min-w-0">
            <span className="text-xs uppercase tracking-wider text-secondary font-mono block">
              Temporal Evidence & Trajectory Analysis
            </span>
            <h1 className="text-xl font-bold text-primary flex items-center gap-2 truncate">
              <Clock size={22} className="text-amber-400 flex-shrink-0" />
              <span>Gap Lifecycle State Machine</span>
            </h1>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 flex-shrink-0">
          <select
            value={currentGapId || ''}
            onChange={(e) => {
              const gid = e.target.value;
              setCurrentGapId(gid);
              if (setSelectedGapId) setSelectedGapId(gid);
            }}
            className="text-xs border border-subtle rounded-md bg-card px-2.5 py-1.5 text-primary max-w-xs truncate"
          >
            {candidatesList.map((c) => (
              <option key={c.gap_id} value={c.gap_id}>
                {c.title}
              </option>
            ))}
          </select>

          <button
            onClick={() => openGapDetail(currentGapId)}
            className="px-3 py-1.5 text-xs font-semibold bg-primary text-primary-contrast rounded-md hover:opacity-90 transition flex items-center gap-1.5"
          >
            <Target size={13} />
            <span>Gap Details</span>
          </button>
          <button
            onClick={loadOverviewData}
            disabled={loading}
            className="p-1.5 border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition"
            title="Reload Lifecycle"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={loadOverviewData} />

      {/* Corpus Lifecycle Status Breakdown Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {['EMERGING', 'PERSISTENT', 'PARTIALLY_ADDRESSED', 'ADDRESSED', 'REOPENED', 'UNCERTAIN'].map(
          (statusKey) => {
            const cfg = STATUS_CONFIG[statusKey] || {};
            const count = statusCounts[statusKey] || 0;
            return (
              <div
                key={statusKey}
                className={`p-3.5 rounded-lg border flex flex-col justify-between ${cfg.color}`}
              >
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider block font-semibold">
                    {cfg.label}
                  </span>
                  <div className="text-2xl font-bold font-mono text-primary mt-1">
                    {count}
                  </div>
                </div>
                <p className="text-[10px] opacity-80 mt-2 line-clamp-2">
                  {cfg.desc}
                </p>
              </div>
            );
          }
        )}
      </div>

      {loadingGap ? (
        <div className="space-y-4">
          <LoadingSpinner text="Computing lifecycle status & chronological timeline..." />
          <SkeletonCard count={3} height={120} />
        </div>
      ) : (
        lifecycleDetail && (
          <div className="space-y-6">
            {/* Selected Gap Lifecycle Detail Card */}
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-mono font-bold px-3 py-1 rounded border ${
                      STATUS_CONFIG[lifecycleDetail.status]?.color || 'bg-muted text-secondary'
                    }`}
                  >
                    STATUS: {lifecycleDetail.status}
                  </span>
                  <span className="text-xs font-mono text-secondary">
                    Temporal Confidence: {Math.round((lifecycleDetail.confidence || 0) * 100)}%
                  </span>
                </div>
                <span className="text-xs font-mono text-secondary">
                  Gap ID: {lifecycleDetail.gap_id}
                </span>
              </div>

              <div>
                <h2 className="text-lg font-bold text-primary">
                  {lifecycleDetail.gap_title}
                </h2>
              </div>

              {/* Status Reasoning Box */}
              <div className="p-4 bg-muted/20 border border-subtle rounded-md space-y-2">
                <span className="text-xs font-semibold text-primary block">
                  Temporal Lifecycle Classification Reasoning:
                </span>
                <p className="text-xs text-secondary leading-relaxed">
                  {lifecycleDetail.status_reasoning}
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-subtle text-xs font-mono text-secondary">
                  <div>
                    <span className="text-[10px] uppercase block">Evidence Papers</span>
                    <strong className="text-primary text-sm">
                      {lifecycleDetail.evidence_paper_count}
                    </strong>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase block">Year Span</span>
                    <strong className="text-primary text-sm">
                      {lifecycleDetail.year_span} yrs ({lifecycleDetail.first_year}–{lifecycleDetail.latest_year})
                    </strong>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase block">Attempted Solutions</span>
                    <strong className="text-primary text-sm">
                      {lifecycleDetail.has_attempted_solutions ? 'Detected' : 'None'}
                    </strong>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase block">Addressed State</span>
                    <strong className="text-primary text-sm">
                      {lifecycleDetail.is_addressed ? 'Yes' : 'Open'}
                    </strong>
                  </div>
                </div>
              </div>
            </div>

            {/* Chronological Lifecycle Timeline */}
            {timeline && (
              <div className="bg-card border border-subtle rounded-lg p-5 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-subtle">
                  <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider flex items-center gap-1.5">
                    <Calendar size={14} className="text-indigo-400" />
                    <span>Chronological Temporal Events ({timeline.total_events} Events)</span>
                  </h3>
                  <div className="flex items-center gap-3 text-xs font-mono text-secondary">
                    <span>First: {timeline.first_appearance_year || 'Unknown'}</span>
                    <span>Latest: {timeline.latest_evidence_year || 'Unknown'}</span>
                  </div>
                </div>

                {(!timeline.events || timeline.events.length === 0) ? (
                  <p className="text-xs text-secondary">No timeline events recorded.</p>
                ) : (
                  <div className="relative pl-6 space-y-5 before:content-[''] before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-subtle">
                    {timeline.events.map((ev, idx) => (
                      <div key={ev.event_id || idx} className="relative group">
                        <div className="absolute -left-[23px] top-1.5 w-4 h-4 rounded-full bg-card border-2 border-amber-400 flex items-center justify-center">
                          <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                        </div>
                        <div className="p-3.5 border border-subtle rounded-md bg-muted/15 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-muted text-secondary font-semibold">
                                {ev.event_type}
                              </span>
                              <span className="text-xs font-semibold text-primary">
                                {ev.title}
                              </span>
                            </div>
                            {ev.year && (
                              <span className="text-xs font-mono text-secondary flex items-center gap-1">
                                <Calendar size={12} />
                                <span>{ev.year}</span>
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-secondary leading-relaxed">
                            &ldquo;{ev.source_sentence}&rdquo;
                          </p>
                          {ev.source_paper && (
                            <div className="text-[10px] font-mono text-secondary pt-0.5">
                              Source: {ev.source_paper.title || `Paper #${ev.source_paper.paper_id}`}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      )}
    </div>
  );
}
