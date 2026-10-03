import React, { useState, useEffect, useMemo } from 'react';
import {
  Target,
  Filter,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Clock,
  BookOpen,
  Sparkles,
  Search,
  RefreshCw,
  GitBranch,
  FileCode,
  CheckCircle2,
} from 'lucide-react';
import { useResearch } from '../contexts/ResearchContext';
import { fetchGapCandidates, fetchGapSignalsOverview } from '../services/api';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

export default function PotentialGapsPage() {
  const {
    openGapDetail,
    openGapGenealogy,
    openGapLifecycle,
    openGapCounterEvidence,
    openGapReport,
    setActiveView,
  } = useResearch();

  const [candidates, setCandidates] = useState([]);
  const [signalsOverview, setSignalsOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('ALL');
  const [minPriority, setMinPriority] = useState(0.0);
  const [minConfidence, setMinConfidence] = useState(0.5);

  const loadCandidates = async () => {
    setLoading(true);
    setError(null);
    try {
      const [res, sigs] = await Promise.allSettled([
        fetchGapCandidates({
          gapType: selectedType !== 'ALL' ? selectedType : null,
          minPriority,
          minConfidence,
          limit: 100,
        }),
        fetchGapSignalsOverview(),
      ]);

      if (res.status === 'fulfilled' && res.value?.candidates) {
        setCandidates(res.value.candidates);
      } else {
        setCandidates([]);
      }

      if (sigs.status === 'fulfilled') {
        setSignalsOverview(sigs.value);
      }
    } catch (err) {
      setError(err.message || 'Failed to retrieve research gap candidates.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCandidates();
  }, [selectedType, minPriority, minConfidence]);

  // Client-side search query filtering
  const filteredCandidates = useMemo(() => {
    if (!searchQuery) return candidates;
    const q = searchQuery.toLowerCase();
    return candidates.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q) ||
        c.gap_id.toLowerCase().includes(q)
    );
  }, [candidates, searchQuery]);

  return (
    <div className="potential-gaps-page-container p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-primary flex items-center gap-2">
            <Target size={24} className="text-purple-400" />
            Potential Research Gaps Catalogue
          </h1>
          <p className="text-sm text-secondary mt-1">
            Measurable, evidence-backed candidate research gaps prioritized via multi-signal ranking algorithms.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadCandidates}
            disabled={loading}
            className="p-1.5 border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition"
            title="Reload Candidates"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={loadCandidates} />

      {/* Filter and Control Toolbar */}
      <div className="bg-card border border-subtle rounded-lg p-4 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
          {/* Search */}
          <div className="sm:col-span-5 relative">
            <Search size={14} className="absolute left-3 top-2.5 text-secondary" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search gaps by keyword, limitation, topic..."
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-muted/30 border border-subtle rounded-md text-primary focus:outline-none focus:border-primary"
            />
          </div>

          {/* Gap Type Filter */}
          <div className="sm:col-span-3 flex items-center gap-2">
            <Filter size={14} className="text-secondary flex-shrink-0" />
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full py-1.5 px-2 text-xs bg-muted/30 border border-subtle rounded-md text-primary"
            >
              <option value="ALL">All Gap Types</option>
              <option value="repeated_limitation">Repeated Limitations</option>
              <option value="underexplored_area">Underexplored Areas</option>
              <option value="methodological_concentration">Methodological Concentration</option>
              <option value="dataset_concentration">Dataset Concentration</option>
              <option value="temporal_opportunity">Temporal Opportunities</option>
              <option value="conflicting_evidence">Conflicting Evidence</option>
            </select>
          </div>

          {/* Priority Slider */}
          <div className="sm:col-span-2 flex flex-col justify-center">
            <div className="flex justify-between text-[11px] text-secondary mb-1">
              <span>Min Priority</span>
              <span className="font-mono">{minPriority.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="0.8"
              step="0.05"
              value={minPriority}
              onChange={(e) => setMinPriority(parseFloat(e.target.value))}
              className="h-1 bg-muted rounded appearance-none cursor-pointer"
            />
          </div>

          {/* Confidence Slider */}
          <div className="sm:col-span-2 flex flex-col justify-center">
            <div className="flex justify-between text-[11px] text-secondary mb-1">
              <span>Min Conf</span>
              <span className="font-mono">{Math.round(minConfidence * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.4"
              max="0.9"
              step="0.05"
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              className="h-1 bg-muted rounded appearance-none cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Main Content */}
      {loading ? (
        <div className="space-y-4">
          <LoadingSpinner text="Evaluating empirical signals and scoring candidates..." />
          <SkeletonCard count={4} height={140} />
        </div>
      ) : filteredCandidates.length === 0 ? (
        <EmptyState
          icon={Target}
          title="No Potential Gaps Found"
          description={
            candidates.length === 0
              ? 'No research gap candidates have been generated yet. Ingest scientific papers to extract limitations and compute signals.'
              : 'No candidate gaps match your current filters. Try lowering priority or confidence thresholds.'
          }
          actionLabel={candidates.length === 0 ? 'Upload Papers' : 'Reset Filters'}
          onAction={() => {
            if (candidates.length === 0) {
              setActiveView('papers');
            } else {
              setSelectedType('ALL');
              setMinPriority(0.0);
              setMinConfidence(0.5);
              setSearchQuery('');
            }
          }}
        />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-secondary px-1">
            <span>
              Showing {filteredCandidates.length} potential research gap candidates
            </span>
            <span className="font-mono text-[11px]">
              Status: Candidates (Pre-Verification)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredCandidates.map((gap) => {
              // Calculate supporting papers
              const suppPapers = gap.supporting_papers || [];
              const validYears = suppPapers
                .map((p) => p.year)
                .filter((y) => typeof y === 'number' && y > 1900);
              const firstYear = validYears.length > 0 ? Math.min(...validYears) : null;

              // Extract counter-evidence count from signals or supporting items
              const counterCount = gap.signals?.conflicting_evidence
                ? Math.round(gap.signals.conflicting_evidence * 5)
                : 0;

              return (
                <article
                  key={gap.gap_id}
                  className="bg-card border border-subtle rounded-lg p-5 hover:border-primary/40 transition flex flex-col justify-between shadow-sm space-y-4"
                >
                  <div className="space-y-2">
                    {/* Top Tag Row */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-semibold">
                          Priority {(gap.gap_priority_score || 0).toFixed(3)}
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-muted text-secondary">
                          {gap.gap_type || 'repeated_limitation'}
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400">
                          {gap.verification_status || 'potential_gap'}
                        </span>
                      </div>
                      <span className="text-xs font-mono text-secondary">
                        Conf: {Math.round((gap.confidence || 0) * 100)}%
                      </span>
                    </div>

                    {/* Gap Title */}
                    <h3
                      onClick={() => openGapDetail(gap.gap_id)}
                      className="text-base font-bold text-primary hover:text-indigo-400 transition cursor-pointer"
                    >
                      {gap.title}
                    </h3>

                    {/* Description */}
                    <p className="text-xs text-secondary leading-relaxed line-clamp-3">
                      {gap.description}
                    </p>
                  </div>

                  {/* Grounded Provenance Metadata Row */}
                  <div className="pt-3 border-t border-subtle space-y-2 text-xs text-secondary">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <BookOpen size={13} />
                        <span>Supporting Papers:</span>
                        <strong className="text-primary font-mono font-semibold">
                          {suppPapers.length}
                        </strong>
                      </span>
                      <span className="flex items-center gap-1.5">
                        <ShieldAlert size={13} className="text-rose-400" />
                        <span>Counter-Evidence:</span>
                        <strong className="text-primary font-mono font-semibold">
                          {counterCount}
                        </strong>
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] font-mono text-secondary">
                      <span>First Appearance: {firstYear ? firstYear : 'Temporal data pending'}</span>
                      <span>Gap ID: {gap.gap_id.slice(0, 16)}</span>
                    </div>
                  </div>

                  {/* Actions Footer */}
                  <div className="pt-2 flex flex-wrap items-center gap-2">
                    <button
                      onClick={() => openGapDetail(gap.gap_id)}
                      className="px-3 py-1 text-xs font-semibold bg-primary text-primary-contrast rounded hover:opacity-90 transition flex items-center gap-1"
                    >
                      <span>Gap Detail</span>
                      <ArrowRight size={12} />
                    </button>
                    <button
                      onClick={() => openGapGenealogy(gap.gap_id)}
                      className="px-2.5 py-1 text-xs font-medium border border-subtle rounded hover:bg-muted text-secondary hover:text-primary transition flex items-center gap-1"
                    >
                      <GitBranch size={12} />
                      <span>Genealogy</span>
                    </button>
                    <button
                      onClick={() => openGapLifecycle(gap.gap_id)}
                      className="px-2.5 py-1 text-xs font-medium border border-subtle rounded hover:bg-muted text-secondary hover:text-primary transition flex items-center gap-1"
                    >
                      <Clock size={12} />
                      <span>Lifecycle</span>
                    </button>
                    <button
                      onClick={() => openGapCounterEvidence(gap.gap_id)}
                      className="px-2.5 py-1 text-xs font-medium border border-subtle rounded hover:bg-muted text-secondary hover:text-primary transition flex items-center gap-1"
                    >
                      <ShieldAlert size={12} />
                      <span>Counter-Ev</span>
                    </button>
                    <button
                      onClick={() => openGapReport(gap.gap_id)}
                      className="px-2.5 py-1 text-xs font-medium border border-subtle rounded hover:bg-muted text-secondary hover:text-primary transition flex items-center gap-1"
                    >
                      <FileCode size={12} />
                      <span>Report</span>
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
