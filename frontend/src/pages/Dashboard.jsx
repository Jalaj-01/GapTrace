import React, { useState, useEffect } from 'react';
import {
  FileText,
  Layers,
  Target,
  Clock,
  TrendingUp,
  CheckCircle2,
  ShieldAlert,
  ArrowRight,
  BookOpen,
  Share2,
  FileSearch,
  FileCode,
  Sparkles,
} from 'lucide-react';
import {
  fetchPapers,
  fetchTopicsOverview,
  fetchGapCandidates,
  fetchGapLifecycleOverview,
} from '../services/api';
import { useResearch } from '../contexts/ResearchContext';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

export default function Dashboard() {
  const {
    setActiveView,
    openPaperDetail,
    openGapDetail,
    openGapGenealogy,
    openGapReport,
  } = useResearch();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [stats, setStats] = useState({
    papersCount: 0,
    topicsCount: 0,
    potentialGapsCount: 0,
    persistentGapsCount: 0,
    emergingTopicsCount: 0,
    addressedGapsCount: 0,
    counterEvidenceCount: 0,
    papers: [],
    topics: [],
    emergingTopics: [],
    candidates: [],
    lifecycleSummary: {},
  });

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [papersRes, topicsRes, candidatesRes, lifecycleRes] = await Promise.allSettled([
        fetchPapers(0, 100),
        fetchTopicsOverview(),
        fetchGapCandidates({ limit: 50 }),
        fetchGapLifecycleOverview(),
      ]);

      const papers = papersRes.status === 'fulfilled' && Array.isArray(papersRes.value) ? papersRes.value : [];
      const topicsData = topicsRes.status === 'fulfilled' ? topicsRes.value : null;
      const candidatesData = candidatesRes.status === 'fulfilled' ? candidatesRes.value : null;
      const lifecycleData = lifecycleRes.status === 'fulfilled' ? lifecycleRes.value : null;

      if (
        papersRes.status === 'rejected' &&
        topicsRes.status === 'rejected' &&
        candidatesRes.status === 'rejected'
      ) {
        throw new Error(
          papersRes.reason?.message ||
          topicsRes.reason?.message ||
          'Failed to aggregate dashboard intelligence data.'
        );
      }

      const candidatesList = candidatesData?.candidates || [];
      const topicsList = topicsData?.all_topics || [];
      const emergingList = topicsData?.emerging_topics || [];
      const statusCounts = lifecycleData?.status_counts || {};

      // Calculate counter-evidence count across candidates
      let totalCounterEv = 0;
      candidatesList.forEach((c) => {
        // Signals or supporting evidence
        if (c.signals && c.signals.conflicting_evidence) {
          totalCounterEv += 1;
        }
      });

      setStats({
        papersCount: papers.length,
        topicsCount: topicsData?.total_topics || topicsList.length,
        potentialGapsCount: candidatesData?.total_candidates || candidatesList.length,
        persistentGapsCount: statusCounts['PERSISTENT'] || 0,
        emergingTopicsCount: emergingList.length,
        addressedGapsCount: (statusCounts['ADDRESSED'] || 0) + (statusCounts['PARTIALLY_ADDRESSED'] || 0),
        counterEvidenceCount: totalCounterEv,
        papers: papers.slice(0, 5),
        topics: topicsList.slice(0, 6),
        emergingTopics: emergingList.slice(0, 4),
        candidates: candidatesList.slice(0, 5),
        lifecycleSummary: statusCounts,
      });
    } catch (err) {
      setError(err.message || 'Failed to aggregate dashboard intelligence data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const metricCards = [
    {
      title: 'Scientific Papers',
      value: stats.papersCount,
      icon: FileText,
      description: 'Ingested and parsed in database',
      action: () => setActiveView('papers'),
      color: 'blue',
    },
    {
      title: 'Research Topics',
      value: stats.topicsCount,
      icon: Layers,
      description: 'Discovered semantic clusters',
      action: () => setActiveView('landscape'),
      color: 'indigo',
    },
    {
      title: 'Potential Gaps',
      value: stats.potentialGapsCount,
      icon: Target,
      description: 'Evidence-backed candidates',
      action: () => setActiveView('gaps'),
      color: 'purple',
    },
    {
      title: 'Persistent Gaps',
      value: stats.persistentGapsCount,
      icon: Clock,
      description: 'Unresolved across multiple years',
      action: () => setActiveView('lifecycle'),
      color: 'amber',
    },
    {
      title: 'Emerging Topics',
      value: stats.emergingTopicsCount,
      icon: TrendingUp,
      description: 'Rapidly accelerating themes',
      action: () => setActiveView('landscape'),
      color: 'emerald',
    },
    {
      title: 'Addressed Gaps',
      value: stats.addressedGapsCount,
      icon: CheckCircle2,
      description: 'Mitigated or solved by literature',
      action: () => setActiveView('lifecycle'),
      color: 'cyan',
    },
    {
      title: 'Counter-Evidence Items',
      value: stats.counterEvidenceCount,
      icon: ShieldAlert,
      description: 'Conflicting or boundary claims',
      action: () => setActiveView('counter-evidence'),
      color: 'rose',
    },
  ];

  return (
    <div className="dashboard-page-container p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-primary flex items-center gap-2">
            <Sparkles size={24} className="text-indigo-400" />
            Research Intelligence Dashboard
          </h1>
          <p className="text-sm text-secondary mt-1">
            Corpus-level synthesis, empirical gap indicators, and scientific discourse tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadDashboardData}
            className="px-3 py-1.5 text-xs font-medium border border-subtle rounded-md hover:bg-muted transition text-secondary"
          >
            Refresh Metrics
          </button>
          <button
            onClick={() => setActiveView('welcome')}
            className="px-4 py-1.5 text-xs font-semibold bg-primary text-primary-contrast rounded-md hover:opacity-90 transition flex items-center gap-1.5"
          >
            <span>New Research</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={loadDashboardData} />

      {loading ? (
        <div className="space-y-6">
          <LoadingSpinner text="Aggregating scientific research intelligence..." />
          <SkeletonCard count={4} height={100} />
        </div>
      ) : (
        <>
          {/* Key Intelligence Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {metricCards.map((card, idx) => {
              const Icon = card.icon;
              return (
                <div
                  key={idx}
                  onClick={card.action}
                  role="button"
                  tabIndex={0}
                  className="bg-card border border-subtle rounded-lg p-5 hover:border-primary/40 transition cursor-pointer flex flex-col justify-between group shadow-sm"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-medium text-secondary uppercase tracking-wider">
                      {card.title}
                    </span>
                    <div className="p-2 rounded-md bg-muted text-secondary group-hover:text-primary transition">
                      <Icon size={18} />
                    </div>
                  </div>
                  <div>
                    <div className="text-3xl font-bold font-mono text-primary mb-1">
                      {card.value}
                    </div>
                    <p className="text-xs text-secondary">{card.description}</p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Quick Access Workspace Modules */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { id: 'papers', label: 'Paper Library', icon: BookOpen },
              { id: 'landscape', label: 'Landscape', icon: Layers },
              { id: 'graph', label: 'Research Graph', icon: Share2 },
              { id: 'gaps', label: 'Potential Gaps', icon: Target },
              { id: 'evidence', label: 'Evidence Explorer', icon: FileSearch },
              { id: 'report', label: 'Research Report', icon: FileCode },
            ].map((module) => {
              const ModIcon = module.icon;
              return (
                <button
                  key={module.id}
                  onClick={() => setActiveView(module.id)}
                  className="p-3 border border-subtle rounded-lg bg-card/60 hover:bg-muted text-left transition flex flex-col items-start gap-2"
                >
                  <ModIcon size={16} className="text-secondary" />
                  <span className="text-xs font-semibold text-primary">{module.label}</span>
                </button>
              );
            })}
          </div>

          {/* Two-Column Deep-Dive Overview */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Top Potential Gaps */}
            <div className="border border-subtle rounded-lg bg-card p-5">
              <div className="flex items-center justify-between pb-3 border-b border-subtle mb-4">
                <h2 className="text-sm font-semibold text-primary flex items-center gap-2">
                  <Target size={16} className="text-purple-400" />
                  Prioritized Candidate Gaps
                </h2>
                <button
                  onClick={() => setActiveView('gaps')}
                  className="text-xs text-primary hover:underline flex items-center gap-1"
                >
                  View All ({stats.potentialGapsCount}) <ArrowRight size={12} />
                </button>
              </div>

              {stats.candidates.length === 0 ? (
                <EmptyState
                  title="No candidate gaps generated yet"
                  description="Upload papers to analyze recurring limitations and discover research gaps."
                  actionLabel="Go to Paper Library"
                  onAction={() => setActiveView('papers')}
                />
              ) : (
                <div className="space-y-3">
                  {stats.candidates.map((gap) => (
                    <div
                      key={gap.gap_id}
                      className="p-3.5 border border-subtle rounded-md hover:border-primary/30 transition bg-muted/20"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                          Priority {(gap.gap_priority_score || 0).toFixed(3)}
                        </span>
                        <span className="text-xs text-secondary font-mono">
                          Confidence {Math.round((gap.confidence || 0) * 100)}%
                        </span>
                      </div>
                      <h3
                        onClick={() => openGapDetail(gap.gap_id)}
                        className="text-sm font-semibold text-primary hover:text-indigo-400 transition cursor-pointer"
                      >
                        {gap.title}
                      </h3>
                      <p className="text-xs text-secondary mt-1 line-clamp-2">
                        {gap.description}
                      </p>
                      <div className="flex items-center gap-3 mt-3 text-xs text-secondary">
                        <button
                          onClick={() => openGapDetail(gap.gap_id)}
                          className="hover:text-primary transition"
                        >
                          Details &rarr;
                        </button>
                        <button
                          onClick={() => openGapGenealogy(gap.gap_id)}
                          className="hover:text-primary transition"
                        >
                          Genealogy &rarr;
                        </button>
                        <button
                          onClick={() => openGapReport(gap.gap_id)}
                          className="hover:text-primary transition"
                        >
                          Synthesize Report &rarr;
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Right: Emerging Topics & Research Themes */}
            <div className="border border-subtle rounded-lg bg-card p-5">
              <div className="flex items-center justify-between pb-3 border-b border-subtle mb-4">
                <h2 className="text-sm font-semibold text-primary flex items-center gap-2">
                  <TrendingUp size={16} className="text-emerald-400" />
                  Emerging & Major Research Themes
                </h2>
                <button
                  onClick={() => setActiveView('landscape')}
                  className="text-xs text-primary hover:underline flex items-center gap-1"
                >
                  View Landscape ({stats.topicsCount}) <ArrowRight size={12} />
                </button>
              </div>

              {stats.topics.length === 0 ? (
                <EmptyState
                  title="No topics discovered yet"
                  description="Trigger topic discovery in the Research Landscape to view semantic clusters."
                  actionLabel="Open Research Landscape"
                  onAction={() => setActiveView('landscape')}
                />
              ) : (
                <div className="space-y-3">
                  {stats.topics.map((topic) => (
                    <div
                      key={topic.topic_id}
                      className="p-3 border border-subtle rounded-md bg-muted/20"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="text-xs font-semibold text-primary">
                          {topic.topic_name}
                        </h4>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-muted text-secondary">
                          {topic.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-secondary mt-1">
                        <span>{topic.paper_count} papers</span>
                        <span>{topic.sentence_count} sentences</span>
                      </div>
                      {topic.representative_terms && topic.representative_terms.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {topic.representative_terms.slice(0, 4).map((t, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] px-1.5 py-0.5 rounded bg-muted/60 text-secondary"
                            >
                              {typeof t === 'string' ? t : t.term}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
