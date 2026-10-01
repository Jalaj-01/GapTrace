import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  ArrowRight,
  ArrowLeft,
  Calendar,
  BookOpen,
  Quote,
  RefreshCw,
  Sparkles,
  Layers,
  ChevronRight,
  Clock,
  Target,
} from 'lucide-react';
import {
  fetchGapCandidates,
  fetchGapGenealogy,
} from '../services/api';
import { useResearch } from '../contexts/ResearchContext';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

export default function GapGenealogyPage() {
  const { selectedGapId, setSelectedGapId, setActiveView, openGapDetail } = useResearch();

  const [candidatesList, setCandidatesList] = useState([]);
  const [currentGapId, setCurrentGapId] = useState(selectedGapId || null);

  const [genealogy, setGenealogy] = useState(null);
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
    loadGenealogy(currentGapId);
  }, [currentGapId]);

  const loadGenealogy = async (gapId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGapGenealogy(gapId);
      setGenealogy(data);
    } catch (err) {
      setError(err.message || 'Failed to reconstruct gap genealogy.');
    } finally {
      setLoading(false);
    }
  };

  if (!currentGapId && !loading) {
    return (
      <div className="p-6 max-w-5xl mx-auto">
        <EmptyState
          title="No Gap Selected for Genealogy"
          description="Choose a candidate gap to inspect its step-by-step evolutionary trajectory."
          actionLabel="View Potential Gaps"
          onAction={() => setActiveView('gaps')}
        />
      </div>
    );
  }

  return (
    <div className="gap-genealogy-page p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header & Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveView('gaps')}
            className="p-1.5 border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition"
            title="Back to Gaps Catalogue"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <span className="text-xs uppercase tracking-wider text-secondary font-mono">
              Evolutionary Lineage Tracker
            </span>
            <h1 className="text-xl font-bold text-primary flex items-center gap-2">
              <GitBranch size={22} className="text-indigo-400" />
              Gap Genealogy & Developmental Progression
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
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
            onClick={() => loadGenealogy(currentGapId)}
            disabled={loading}
            className="p-1.5 border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition"
            title="Reload Genealogy"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={() => loadGenealogy(currentGapId)} />

      {loading ? (
        <div className="space-y-4">
          <LoadingSpinner text="Reconstructing evolutionary genealogy sequence from knowledge graph..." />
          <SkeletonCard count={3} height={120} />
        </div>
      ) : (
        genealogy && (
          <div className="space-y-6">
            {/* Macro Summary & Root Limitation */}
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-4">
              <div>
                <span className="text-xs font-mono text-secondary">
                  Target Candidate Gap: {genealogy.gap_id}
                </span>
                <h2 className="text-lg font-bold text-primary mt-1">
                  {genealogy.gap_title}
                </h2>
              </div>

              {/* Evolutionary Progression Banner */}
              <div className="p-3 bg-muted/20 border border-subtle rounded-md">
                <span className="text-[11px] font-semibold text-secondary uppercase block mb-2">
                  Evolutionary Sequence Chain:
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  {(genealogy.evolutionary_chain || [
                    'Limitation Identified',
                    'Attempted Solution',
                    'Remaining Limitation',
                    'Current Candidate Gap',
                  ]).map((stage, idx, arr) => (
                    <React.Fragment key={idx}>
                      <span className="px-3 py-1 rounded bg-muted text-xs font-mono font-semibold text-primary border border-subtle">
                        {stage}
                      </span>
                      {idx < arr.length - 1 && (
                        <ChevronRight size={14} className="text-secondary" />
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </div>

              {/* Root Limitation Description */}
              <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-md text-xs space-y-1">
                <span className="font-semibold text-amber-400 block uppercase text-[10px]">
                  Root Limitation Origin:
                </span>
                <p className="text-primary leading-relaxed font-mono">
                  {genealogy.root_limitation}
                </p>
                {genealogy.summary && (
                  <p className="text-secondary leading-relaxed pt-1">
                    {genealogy.summary}
                  </p>
                )}
              </div>
            </div>

            {/* Step-by-Step Transition Nodes Timeline */}
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-4">
              <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">
                Step-by-Step Developmental Progression ({genealogy.total_transitions} Transitions)
              </h3>

              {(!genealogy.transitions || genealogy.transitions.length === 0) ? (
                <EmptyState
                  title="No Transitions Found"
                  description="A multi-paper chain could not be formed. Ensure at least two papers cite or address this limitation."
                />
              ) : (
                <div className="relative pl-6 space-y-6 before:content-[''] before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-subtle">
                  {genealogy.transitions.map((item, idx) => (
                    <div key={idx} className="relative group">
                      {/* Timeline Bullet Marker */}
                      <div className="absolute -left-[23px] top-1.5 w-4 h-4 rounded-full bg-card border-2 border-indigo-400 flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                      </div>

                      {/* Transition Card */}
                      <div className="p-4 border border-subtle rounded-lg bg-muted/15 space-y-2 hover:border-primary/40 transition">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-bold text-primary px-2 py-0.5 rounded bg-muted">
                              Step {item.step_number || idx + 1}
                            </span>
                            <span className="text-xs font-semibold text-indigo-400">
                              {item.stage_name}
                            </span>
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted/60 text-secondary">
                              rel: {item.relationship}
                            </span>
                          </div>
                          {item.year && (
                            <span className="text-xs font-mono text-secondary flex items-center gap-1">
                              <Calendar size={12} />
                              <span>{item.year}</span>
                            </span>
                          )}
                        </div>

                        <p className="text-xs text-primary leading-relaxed">
                          {item.description}
                        </p>

                        {/* Source Sentence Provenance */}
                        {item.source_sentence && (
                          <div className="p-2.5 bg-card border border-subtle rounded text-xs space-y-1 mt-2">
                            <span className="text-[10px] uppercase font-mono text-secondary block">
                              Source Evidence Excerpt
                            </span>
                            <p className="text-secondary leading-relaxed">
                              &ldquo;{item.source_sentence}&rdquo;
                            </p>
                            {item.source_paper && (
                              <div className="text-[10px] font-mono text-secondary pt-0.5">
                                Publication: {item.source_paper.title || `Paper #${item.source_paper.paper_id}`}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )
      )}
    </div>
  );
}
