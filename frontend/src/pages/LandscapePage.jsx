import React, { useState, useEffect } from 'react';
import {
  Layers,
  TrendingUp,
  TrendingDown,
  Clock,
  Sparkles,
  RefreshCw,
  FileText,
  Calendar,
  Filter,
  BarChart3,
  ArrowRight,
} from 'lucide-react';
import {
  fetchTopicsOverview,
  discoverTopics,
  fetchTopicTrends,
} from '../services/api';
import { useResearch } from '../contexts/ResearchContext';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

export default function LandscapePage() {
  const { openPaperDetail } = useResearch();

  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [error, setError] = useState(null);
  const [overview, setOverview] = useState(null);

  const [selectedTrajectory, setSelectedTrajectory] = useState('ALL'); // 'ALL' | 'EMERGING' | 'PERSISTENT' | 'DECLINING' | 'MAJOR'
  const [selectedTopic, setSelectedTopic] = useState(null);

  const loadLandscape = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTopicsOverview();
      setOverview(data);
      if (data?.all_topics?.length > 0 && !selectedTopic) {
        setSelectedTopic(data.all_topics[0]);
      }
    } catch (err) {
      setError(err.message || 'Failed to load research landscape.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLandscape();
  }, []);

  const handleRunDiscovery = async () => {
    setDiscovering(true);
    setError(null);
    try {
      const res = await discoverTopics(2);
      setOverview(res);
      if (res?.all_topics?.length > 0) {
        setSelectedTopic(res.all_topics[0]);
      }
    } catch (err) {
      setError(`Topic discovery failed: ${err.message}`);
    } finally {
      setDiscovering(false);
    }
  };

  const allTopics = overview?.all_topics || [];

  const filteredTopics = allTopics.filter((t) => {
    if (selectedTrajectory === 'ALL') return true;
    return t.status?.toUpperCase() === selectedTrajectory;
  });

  return (
    <div className="landscape-page-container p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-primary flex items-center gap-2">
            <Layers size={24} className="text-indigo-400" />
            Research Landscape & Topic Discovery
          </h1>
          <p className="text-sm text-secondary mt-1">
            Semantic topic modeling, longitudinal evolution, and trajectory classification (emerging, persistent, declining).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRunDiscovery}
            disabled={discovering}
            className="px-3.5 py-1.5 text-xs font-semibold bg-primary text-primary-contrast rounded-md hover:opacity-90 transition flex items-center gap-1.5"
          >
            <Sparkles size={13} className={discovering ? 'animate-spin' : ''} />
            <span>{discovering ? 'Running BERTopic...' : 'Discover Topics'}</span>
          </button>
          <button
            onClick={loadLandscape}
            disabled={loading}
            className="p-1.5 border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition"
            title="Reload Landscape"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={loadLandscape} />

      {loading ? (
        <div className="space-y-4">
          <LoadingSpinner text="Computing topic clusters and temporal distributions..." />
          <SkeletonCard count={3} height={140} />
        </div>
      ) : allTopics.length === 0 ? (
        <EmptyState
          icon={Layers}
          title="No Topics Discovered"
          description="Click 'Discover Topics' to run BERTopic clustering across all ingested scientific papers."
          actionLabel="Run Topic Discovery"
          onAction={handleRunDiscovery}
        />
      ) : (
        <div className="space-y-6">
          {/* Macro Category KPI Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              {
                id: 'MAJOR',
                label: 'Major Topics',
                count: overview?.major_topics?.length || 0,
                icon: Layers,
                color: 'text-blue-400 border-blue-500/20 bg-blue-500/5',
              },
              {
                id: 'EMERGING',
                label: 'Emerging Topics',
                count: overview?.emerging_topics?.length || 0,
                icon: TrendingUp,
                color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5',
              },
              {
                id: 'PERSISTENT',
                label: 'Persistent Topics',
                count: overview?.persistent_topics?.length || 0,
                icon: Clock,
                color: 'text-amber-400 border-amber-500/20 bg-amber-500/5',
              },
              {
                id: 'DECLINING',
                label: 'Declining Topics',
                count: overview?.declining_topics?.length || 0,
                icon: TrendingDown,
                color: 'text-rose-400 border-rose-500/20 bg-rose-500/5',
              },
            ].map((cat) => {
              const Icon = cat.icon;
              const isActive = selectedTrajectory === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() =>
                    setSelectedTrajectory((prev) => (prev === cat.id ? 'ALL' : cat.id))
                  }
                  className={`p-3.5 rounded-lg border text-left transition flex items-center justify-between ${
                    cat.color
                  } ${isActive ? 'ring-2 ring-primary' : 'hover:opacity-90'}`}
                >
                  <div>
                    <span className="text-[11px] font-semibold text-secondary uppercase block mb-1">
                      {cat.label}
                    </span>
                    <span className="text-xl font-bold font-mono text-primary">
                      {cat.count}
                    </span>
                  </div>
                  <Icon size={20} className="opacity-80" />
                </button>
              );
            })}
          </div>

          {/* Main Grid: Topic List & Detail Panel */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: Filtered Topics List (7 cols) */}
            <div className="lg:col-span-7 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-semibold text-secondary uppercase tracking-wider">
                  Discovered Topics ({filteredTopics.length})
                </h2>
                {selectedTrajectory !== 'ALL' && (
                  <button
                    onClick={() => setSelectedTrajectory('ALL')}
                    className="text-xs text-primary hover:underline"
                  >
                    Clear Filter
                  </button>
                )}
              </div>

              <div className="space-y-3">
                {filteredTopics.map((topic) => {
                  const isSelected = selectedTopic?.topic_id === topic.topic_id;
                  return (
                    <div
                      key={topic.topic_id}
                      onClick={() => setSelectedTopic(topic)}
                      className={`p-4 border rounded-lg bg-card transition cursor-pointer flex flex-col justify-between ${
                        isSelected
                          ? 'border-primary ring-1 ring-primary'
                          : 'border-subtle hover:border-primary/40'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono text-secondary">
                          Topic #{topic.topic_id}
                        </span>
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                            topic.status === 'EMERGING'
                              ? 'bg-emerald-500/10 text-emerald-400'
                              : topic.status === 'PERSISTENT'
                              ? 'bg-amber-500/10 text-amber-400'
                              : topic.status === 'DECLINING'
                              ? 'bg-rose-500/10 text-rose-400'
                              : 'bg-muted text-secondary'
                          }`}
                        >
                          {topic.status}
                        </span>
                      </div>

                      <h3 className="text-sm font-bold text-primary mb-1">
                        {topic.topic_name}
                      </h3>

                      <div className="flex items-center gap-4 text-xs text-secondary mt-1">
                        <span>{topic.paper_count} Papers</span>
                        <span>{topic.sentence_count} Sentences</span>
                        {topic.topic_probability && (
                          <span className="font-mono">
                            Prob: {(topic.topic_probability * 100).toFixed(1)}%
                          </span>
                        )}
                      </div>

                      {/* Representative Terms */}
                      {topic.representative_terms && topic.representative_terms.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {topic.representative_terms.slice(0, 5).map((termItem, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] px-2 py-0.5 rounded bg-muted text-secondary"
                            >
                              {typeof termItem === 'string' ? termItem : termItem.term}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right: Selected Topic Deep Dive (5 cols) */}
            <div className="lg:col-span-5">
              {selectedTopic ? (
                <div className="border border-subtle rounded-lg bg-card p-5 space-y-5 sticky top-4">
                  <div className="pb-3 border-b border-subtle">
                    <span className="text-xs font-mono text-secondary block mb-1">
                      Topic #{selectedTopic.topic_id} &bull; {selectedTopic.status}
                    </span>
                    <h3 className="text-base font-bold text-primary">
                      {selectedTopic.topic_name}
                    </h3>
                  </div>

                  {/* Temporal Trend Distribution */}
                  {selectedTopic.temporal_distribution && (
                    <div>
                      <h4 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <BarChart3 size={13} />
                        <span>Temporal Progression</span>
                      </h4>
                      <div className="space-y-1.5 bg-muted/20 border border-subtle rounded-md p-3">
                        {Object.entries(selectedTopic.temporal_distribution)
                          .sort(([a], [b]) => Number(a) - Number(b))
                          .map(([year, count]) => {
                            const maxVal = Math.max(
                              ...Object.values(selectedTopic.temporal_distribution)
                            );
                            const pct = maxVal > 0 ? (count / maxVal) * 100 : 0;
                            return (
                              <div key={year} className="flex items-center gap-3 text-xs">
                                <span className="font-mono text-secondary w-10">{year}</span>
                                <div className="flex-1 bg-muted rounded-full h-2 overflow-hidden">
                                  <div
                                    className="bg-indigo-500 h-2 rounded-full"
                                    style={{ width: `${Math.max(5, pct)}%` }}
                                  />
                                </div>
                                <span className="font-mono text-primary w-6 text-right">
                                  {count}
                                </span>
                              </div>
                            );
                          })}
                      </div>
                    </div>
                  )}

                  {/* Representative Terms with Weights */}
                  {selectedTopic.representative_terms && (
                    <div>
                      <h4 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-2">
                        Key Representative Terms
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedTopic.representative_terms.map((termItem, idx) => (
                          <span
                            key={idx}
                            className="text-xs px-2.5 py-1 rounded-md bg-muted/60 text-primary border border-subtle flex items-center gap-1"
                          >
                            <span>
                              {typeof termItem === 'string' ? termItem : termItem.term}
                            </span>
                            {termItem.weight && (
                              <span className="text-[10px] font-mono text-secondary">
                                {Number(termItem.weight).toFixed(2)}
                              </span>
                            )}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Representative Documents Snippets */}
                  {selectedTopic.representative_documents &&
                    selectedTopic.representative_documents.length > 0 && (
                      <div>
                        <h4 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-2">
                          Representative Document Excerpts
                        </h4>
                        <div className="space-y-2">
                          {selectedTopic.representative_documents.slice(0, 3).map((doc, idx) => (
                            <div
                              key={idx}
                              className="p-2.5 bg-muted/20 border border-subtle rounded text-xs text-secondary leading-relaxed"
                            >
                              &ldquo;{typeof doc === 'string' ? doc : doc.text || doc.source_text}&rdquo;
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              ) : (
                <div className="border border-subtle rounded-lg bg-card p-6 text-center text-secondary text-xs">
                  Select a topic on the left to inspect its temporal trend and representative keywords.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
