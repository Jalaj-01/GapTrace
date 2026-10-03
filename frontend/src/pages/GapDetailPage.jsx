import React, { useState, useEffect } from 'react';
import {
  Target,
  ArrowLeft,
  RefreshCw,
  GitBranch,
  Clock,
  ShieldAlert,
  ShieldCheck,
  FileCode,
  Layers,
  BookOpen,
  Quote,
  BarChart2,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import {
  fetchGapCandidates,
  fetchGapCandidateDetail,
  fetchGapLifecycle,
  fetchGapGenealogy,
  fetchGapCounterEvidence,
} from '../services/api';
import { useResearch } from '../contexts/ResearchContext';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

export default function GapDetailPage() {
  const {
    selectedGapId,
    setSelectedGapId,
    setActiveView,
    openGapGenealogy,
    openGapLifecycle,
    openGapCounterEvidence,
    openGapReport,
  } = useResearch();

  const [candidatesList, setCandidatesList] = useState([]);
  const [currentGapId, setCurrentGapId] = useState(selectedGapId || null);

  const [candidate, setCandidate] = useState(null);
  const [lifecycle, setLifecycle] = useState(null);
  const [genealogy, setGenealogy] = useState(null);
  const [counterEv, setCounterEv] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load candidate list for dropdown
  useEffect(() => {
    async function loadCandidates() {
      try {
        const data = await fetchGapCandidates({ limit: 100 });
        const list = data?.candidates || [];
        setCandidatesList(list);
        if (!currentGapId && list.length > 0) {
          setCurrentGapId(list[0].gap_id);
        }
      } catch {
        // Fallback
      }
    }
    loadCandidates();
  }, []);

  useEffect(() => {
    if (selectedGapId) {
      setCurrentGapId(selectedGapId);
    }
  }, [selectedGapId]);

  useEffect(() => {
    if (!currentGapId) return;
    loadGapData(currentGapId);
  }, [currentGapId]);

  const loadGapData = async (gapId) => {
    setLoading(true);
    setError(null);
    try {
      const [candRes, lifeRes, genRes, counterRes] = await Promise.allSettled([
        fetchGapCandidateDetail(gapId),
        fetchGapLifecycle(gapId),
        fetchGapGenealogy(gapId),
        fetchGapCounterEvidence(gapId),
      ]);

      if (candRes.status === 'fulfilled') {
        setCandidate(candRes.value);
      } else {
        throw new Error(candRes.reason?.message || `Candidate gap '${gapId}' not found.`);
      }

      setLifecycle(lifeRes.status === 'fulfilled' ? lifeRes.value : null);
      setGenealogy(genRes.status === 'fulfilled' ? genRes.value : null);
      setCounterEv(counterRes.status === 'fulfilled' ? counterRes.value : null);
    } catch (err) {
      setError(err.message || 'Failed to load gap details.');
    } finally {
      setLoading(false);
    }
  };

  if (!currentGapId && !loading) {
    return (
      <div className="p-6 max-w-5xl mx-auto">
        <EmptyState
          title="No Research Gap Selected"
          description="Select a candidate gap from the potential gaps catalogue to inspect grounded evidence and lifecycle."
          actionLabel="View Potential Gaps"
          onAction={() => setActiveView('gaps')}
        />
      </div>
    );
  }

  return (
    <div className="gap-detail-page p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header & Selector */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <button
            onClick={() => setActiveView('gaps')}
            className="p-1.5 border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition flex-shrink-0"
            title="Back to Potential Gaps"
          >
            <ArrowLeft size={16} />
          </button>
          <div className="min-w-0">
            <span className="text-xs uppercase tracking-wider text-secondary font-mono block">
              Research Gap Deep Dive
            </span>
            <h1 className="text-xl font-bold text-primary truncate">
              {candidate?.title || currentGapId}
            </h1>
          </div>
        </div>

        {/* Gap Selector Dropdown & Quick Actions */}
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
            onClick={() => openGapGenealogy(currentGapId)}
            className="px-2.5 py-1.5 text-xs font-medium border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition flex items-center gap-1"
          >
            <GitBranch size={13} />
            <span>Genealogy</span>
          </button>
          <button
            onClick={() => openGapLifecycle(currentGapId)}
            className="px-2.5 py-1.5 text-xs font-medium border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition flex items-center gap-1"
          >
            <Clock size={13} />
            <span>Lifecycle</span>
          </button>
          <button
            onClick={() => openGapCounterEvidence(currentGapId)}
            className="px-2.5 py-1.5 text-xs font-medium border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition flex items-center gap-1"
          >
            <ShieldAlert size={13} />
            <span>Counter-Ev</span>
          </button>
          <button
            onClick={() => openGapReport(currentGapId)}
            className="px-3 py-1.5 text-xs font-semibold bg-primary text-primary-contrast rounded-md hover:opacity-90 transition flex items-center gap-1.5"
          >
            <FileCode size={13} />
            <span>Generate Report</span>
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={() => loadGapData(currentGapId)} />

      {loading ? (
        <div className="space-y-4">
          <LoadingSpinner text="Retrieving multi-paper provenance, signals, and lifecycle..." />
          <SkeletonCard count={3} height={140} />
        </div>
      ) : (
        candidate && (
          <div className="space-y-6">
            {/* Top Overview Card */}
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono px-2.5 py-1 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-semibold">
                    Priority Score: {(candidate.gap_priority_score || 0).toFixed(3)}
                  </span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted text-secondary">
                    {candidate.gap_type}
                  </span>
                  {lifecycle?.status && (
                    <span
                      className={`text-xs font-mono px-2.5 py-1 rounded font-semibold ${
                        lifecycle.status === 'PERSISTENT'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : lifecycle.status === 'EMERGING'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-muted text-secondary'
                      }`}
                    >
                      Lifecycle: {lifecycle.status}
                    </span>
                  )}
                </div>
                <div className="text-xs font-mono text-secondary">
                  Confidence: {Math.round((candidate.confidence || 0) * 100)}% &bull; ID: {candidate.gap_id}
                </div>
              </div>

              <div>
                <h2 className="text-lg font-bold text-primary mb-2">{candidate.title}</h2>
                <p className="text-xs text-secondary leading-relaxed bg-muted/20 border border-subtle p-3 rounded-md">
                  {candidate.description}
                </p>
              </div>

              {/* Lifecycle & Multi-Paper Reasoning */}
              {lifecycle?.status_reasoning && (
                <div className="p-3 bg-muted/30 border border-subtle rounded-md text-xs space-y-1">
                  <span className="font-semibold text-primary block">
                    Temporal Lifecycle Reasoning:
                  </span>
                  <p className="text-secondary leading-relaxed">
                    {lifecycle.status_reasoning}
                  </p>
                  <div className="flex items-center gap-4 text-[11px] font-mono text-secondary pt-1">
                    <span>Evidence Papers: {lifecycle.evidence_paper_count}</span>
                    <span>Year Span: {lifecycle.year_span} years ({lifecycle.first_year}–{lifecycle.latest_year})</span>
                    <span>Attempted Solutions: {lifecycle.has_attempted_solutions ? 'Yes' : 'None detected'}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Empirical Signals Breakdown */}
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-3">
              <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider flex items-center gap-1.5">
                <BarChart2 size={14} className="text-indigo-400" />
                <span>Empirical Signal Breakdown & Mathematical Weights</span>
              </h3>

              {candidate.signal_breakdown && candidate.signal_breakdown.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-muted/40 text-secondary uppercase font-mono text-[10px]">
                      <tr>
                        <th className="py-2.5 px-3">Signal Name</th>
                        <th className="py-2.5 px-3">Signal Value</th>
                        <th className="py-2.5 px-3">Weight</th>
                        <th className="py-2.5 px-3">Contribution</th>
                        <th className="py-2.5 px-3">Empirical Explanation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-subtle">
                      {candidate.signal_breakdown.map((sig, idx) => (
                        <tr key={idx} className="hover:bg-muted/10">
                          <td className="py-2 px-3 font-semibold text-primary">
                            {sig.signal_name}
                          </td>
                          <td className="py-2 px-3 font-mono text-secondary">
                            {(sig.signal_value || 0).toFixed(3)}
                          </td>
                          <td className="py-2 px-3 font-mono text-secondary">
                            {(sig.weight || 0).toFixed(2)}
                          </td>
                          <td className="py-2 px-3 font-mono font-semibold text-purple-400">
                            +{(sig.contribution || 0).toFixed(3)}
                          </td>
                          <td className="py-2 px-3 text-secondary text-[11px]">
                            {sig.explanation}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-secondary">No signal breakdown details available.</p>
              )}
            </div>

            {/* Two-Column Provenance: Supporting Evidence vs Counter/Conflicting */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Supporting Evidence Sentences */}
              <div className="bg-card border border-subtle rounded-lg p-5 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-subtle">
                  <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider flex items-center gap-1.5">
                    <BookOpen size={14} className="text-blue-400" />
                    <span>Exact Source Sentences & Supporting Evidence</span>
                  </h3>
                  <span className="text-xs font-mono text-secondary">
                    {candidate.supporting_evidence?.length || 0} excerpts
                  </span>
                </div>

                {(!candidate.supporting_evidence || candidate.supporting_evidence.length === 0) ? (
                  <p className="text-xs text-secondary">No supporting evidence items recorded.</p>
                ) : (
                  <div className="space-y-3">
                    {candidate.supporting_evidence.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-muted/20 border border-subtle rounded-md space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-[10px] font-mono text-secondary">
                          <span className="font-semibold text-primary">
                            {item.paper_title || `Paper #${item.paper_id || 'N/A'}`}
                          </span>
                          <span>Section: {item.section || 'Unknown'} &bull; Page {item.page || 1}</span>
                        </div>
                        <p className="text-xs text-primary leading-relaxed">
                          &ldquo;{item.source_text}&rdquo;
                        </p>
                        <div className="text-[10px] font-mono text-secondary">
                          Confidence: {Math.round((item.confidence || 1.0) * 100)}%
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Counter-Evidence, Addressed-By & Conflicting */}
              <div className="bg-card border border-subtle rounded-lg p-5 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-subtle">
                  <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider flex items-center gap-1.5">
                    <ShieldAlert size={14} className="text-rose-400" />
                    <span>Counter-Evidence, Addressed-By & Conflicts</span>
                  </h3>
                  <button
                    onClick={() => openGapCounterEvidence(currentGapId)}
                    className="text-xs text-primary hover:underline"
                  >
                    View All &rarr;
                  </button>
                </div>

                {/* Counter Evidence snippets */}
                <div className="space-y-3">
                  {counterEv?.counter_evidence && counterEv.counter_evidence.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[11px] font-semibold text-rose-400 uppercase">
                        Counter-Evidence ({counterEv.counter_evidence.length})
                      </span>
                      {counterEv.counter_evidence.slice(0, 2).map((ce, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 bg-rose-500/5 border border-rose-500/20 rounded text-xs space-y-1"
                        >
                          <div className="text-[10px] font-mono text-secondary">
                            {ce.paper_title} ({ce.publication_year || 'Unknown'})
                          </div>
                          <p className="text-primary leading-relaxed">
                            &ldquo;{ce.source_text}&rdquo;
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Addressed-by papers */}
                  {counterEv?.addressed_by_evidence && counterEv.addressed_by_evidence.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[11px] font-semibold text-emerald-400 uppercase">
                        Addressed-By Publications ({counterEv.addressed_by_evidence.length})
                      </span>
                      {counterEv.addressed_by_evidence.slice(0, 2).map((ae, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 bg-emerald-500/5 border border-emerald-500/20 rounded text-xs space-y-1"
                        >
                          <div className="text-[10px] font-mono text-secondary">
                            {ae.paper_title} ({ae.publication_year || 'Unknown'})
                          </div>
                          <p className="text-primary leading-relaxed">
                            &ldquo;{ae.source_text}&rdquo;
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Contradictory evidence */}
                  {counterEv?.contradictory_evidence && counterEv.contradictory_evidence.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[11px] font-semibold text-amber-400 uppercase">
                        Conflicting Findings ({counterEv.contradictory_evidence.length})
                      </span>
                      {counterEv.contradictory_evidence.slice(0, 2).map((conte, idx) => (
                        <div
                          key={idx}
                          className="p-2.5 bg-amber-500/5 border border-amber-500/20 rounded text-xs space-y-1"
                        >
                          <p className="text-primary leading-relaxed">
                            &ldquo;{conte.source_text}&rdquo;
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  {(!counterEv ||
                    ((counterEv.counter_evidence?.length || 0) === 0 &&
                      (counterEv.addressed_by_evidence?.length || 0) === 0 &&
                      (counterEv.contradictory_evidence?.length || 0) === 0)) && (
                    <p className="text-xs text-secondary">
                      No active counter-evidence or refutations found yet in corpus for this candidate.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )
      )}
    </div>
  );
}
