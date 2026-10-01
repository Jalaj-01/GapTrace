import React, { useState, useEffect } from 'react';
import {
  FileSearch,
  Search,
  Filter,
  Copy,
  Check,
  Quote,
  Sparkles,
  RefreshCw,
  BookOpen,
} from 'lucide-react';
import { searchSemanticEvidence, fetchPapers } from '../services/api';
import { useResearch } from '../contexts/ResearchContext';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

export default function EvidenceExplorerPage() {
  const { openPaperDetail } = useResearch();

  const [query, setQuery] = useState('limitation generalization attention dataset');
  const [topK, setTopK] = useState(15);
  const [selectedType, setSelectedType] = useState('ALL');
  const [minYear, setMinYear] = useState('');
  const [maxYear, setMaxYear] = useState('');

  const [results, setResults] = useState([]);
  const [retrievalMeta, setRetrievalMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await searchSemanticEvidence({
        q: query.trim(),
        topK,
        extractionType: selectedType !== 'ALL' ? selectedType : null,
        minYear: minYear ? parseInt(minYear, 10) : null,
        maxYear: maxYear ? parseInt(maxYear, 10) : null,
      });

      setResults(data?.results || []);
      setRetrievalMeta({
        query: data.query,
        total_results: data.total_results,
        retrieval_method: data.retrieval_method,
        model_name: data.model_name,
      });
    } catch (err) {
      setError(err.message || 'Semantic search failed.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  // Run initial search on mount
  useEffect(() => {
    handleSearch();
  }, [selectedType]);

  const handleCopyCitation = (item, idx) => {
    const text = `"${item.source_text}" (${item.paper?.title || 'Unknown publication'}, p. ${item.page}, sec. ${item.section})`;
    navigator.clipboard.writeText(text);
    setCopiedId(idx);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="evidence-explorer-page p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-primary flex items-center gap-2">
            <FileSearch size={24} className="text-blue-400" />
            Semantic Evidence Explorer
          </h1>
          <p className="text-sm text-secondary mt-1">
            Perform dense vector similarity retrieval across scientific evidence passages with exact section and page provenance.
          </p>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={handleSearch} />

      {/* Semantic Search Box */}
      <form onSubmit={handleSearch} className="bg-card border border-subtle rounded-lg p-4 space-y-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3.5 top-3 text-secondary" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search scientific evidence semantically (e.g., 'subpopulation shifts degrade generalization')..."
              className="w-full pl-10 pr-4 py-2 text-xs bg-muted/30 border border-subtle rounded-md text-primary focus:outline-none focus:border-primary"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-xs font-semibold bg-primary text-primary-contrast rounded-md hover:opacity-90 transition flex items-center gap-1.5"
          >
            <Sparkles size={14} className={loading ? 'animate-spin' : ''} />
            <span>{loading ? 'Searching...' : 'Search Evidence'}</span>
          </button>
        </div>

        {/* Filter Controls Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
          {/* Extraction Type */}
          <div>
            <label className="text-[10px] uppercase font-mono text-secondary block mb-1">
              Extraction Type
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full py-1.5 px-2 bg-muted/30 border border-subtle rounded-md text-primary text-xs"
            >
              <option value="ALL">All Extractions</option>
              <option value="LIMITATION">Limitation</option>
              <option value="FUTURE_WORK">Future Work</option>
              <option value="PROBLEM">Problem / Gap</option>
              <option value="METHOD">Method</option>
              <option value="RESULT">Result</option>
              <option value="BACKGROUND">Background</option>
            </select>
          </div>

          {/* Top K */}
          <div>
            <label className="text-[10px] uppercase font-mono text-secondary block mb-1">
              Top Matches ({topK})
            </label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full py-1.5 px-2 bg-muted/30 border border-subtle rounded-md text-primary text-xs"
            >
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={15}>Top 15</option>
              <option value={25}>Top 25</option>
              <option value={50}>Top 50</option>
            </select>
          </div>

          {/* Min Year */}
          <div>
            <label className="text-[10px] uppercase font-mono text-secondary block mb-1">
              Min Publication Year
            </label>
            <input
              type="number"
              placeholder="e.g. 2021"
              value={minYear}
              onChange={(e) => setMinYear(e.target.value)}
              className="w-full py-1 px-2 bg-muted/30 border border-subtle rounded-md text-primary text-xs"
            />
          </div>

          {/* Max Year */}
          <div>
            <label className="text-[10px] uppercase font-mono text-secondary block mb-1">
              Max Publication Year
            </label>
            <input
              type="number"
              placeholder="e.g. 2026"
              value={maxYear}
              onChange={(e) => setMaxYear(e.target.value)}
              className="w-full py-1 px-2 bg-muted/30 border border-subtle rounded-md text-primary text-xs"
            />
          </div>
        </div>
      </form>

      {/* Retrieval Metadata Bar */}
      {retrievalMeta && (
        <div className="flex items-center justify-between text-xs text-secondary px-1">
          <div className="flex items-center gap-2">
            <span>Query: &ldquo;{retrievalMeta.query}&rdquo;</span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-muted text-secondary">
              Method: {retrievalMeta.retrieval_method}
            </span>
          </div>
          <span className="font-mono text-xs">
            {retrievalMeta.total_results} evidence passages retrieved
          </span>
        </div>
      )}

      {/* Evidence Results List */}
      {loading ? (
        <div className="space-y-4">
          <LoadingSpinner text="Computing dense vector cosine similarities..." />
          <SkeletonCard count={4} height={110} />
        </div>
      ) : results.length === 0 ? (
        <EmptyState
          icon={FileSearch}
          title="No Evidence Excerpts Found"
          description="Try modifying your semantic search terms or expanding filter constraints."
          actionLabel="Clear Filters"
          onAction={() => {
            setQuery('limitation attention model');
            setSelectedType('ALL');
            setMinYear('');
            setMaxYear('');
            handleSearch();
          }}
        />
      ) : (
        <div className="space-y-3">
          {results.map((item, idx) => {
            const paperTitle = item.paper?.title || `Paper #${item.paper?.paper_id || 'N/A'}`;
            const similarityScore = (item.similarity_score || 0).toFixed(4);

            return (
              <div
                key={idx}
                className="p-4 border border-subtle rounded-lg bg-card hover:border-primary/40 transition space-y-2.5"
              >
                {/* Header row: Paper Title, Extraction Type, Similarity */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-semibold">
                      {item.extraction_type || 'EMPIRICAL_EVIDENCE'}
                    </span>
                    <button
                      onClick={() => item.paper?.paper_id && openPaperDetail(item.paper.paper_id)}
                      className="text-xs font-semibold text-primary hover:text-blue-400 transition truncate max-w-md text-left"
                    >
                      {paperTitle}
                    </button>
                  </div>

                  <div className="flex items-center gap-3 text-xs font-mono text-secondary">
                    <span>
                      Similarity:{' '}
                      <strong className="text-emerald-400 font-bold">
                        {similarityScore}
                      </strong>
                    </span>
                    <button
                      onClick={() => handleCopyCitation(item, idx)}
                      className="p-1 border border-subtle rounded hover:bg-muted text-secondary hover:text-primary transition"
                      title="Copy grounded citation"
                    >
                      {copiedId === idx ? (
                        <Check size={13} className="text-emerald-400" />
                      ) : (
                        <Copy size={13} />
                      )}
                    </button>
                  </div>
                </div>

                {/* Exact Sentence Text */}
                <p className="text-xs text-primary leading-relaxed bg-muted/20 border border-subtle p-3 rounded-md">
                  &ldquo;{item.source_text}&rdquo;
                </p>

                {/* Provenance Footer: Section, Page, Year */}
                <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono text-secondary">
                  <span>Section: <strong className="text-primary font-normal">{item.section || 'Unknown'}</strong></span>
                  <span>Page: <strong className="text-primary font-normal">{item.page || 1}</strong></span>
                  {item.paper?.year && (
                    <span>Year: <strong className="text-primary font-normal">{item.paper.year}</strong></span>
                  )}
                  {item.paper?.paper_id && (
                    <button
                      onClick={() => openPaperDetail(item.paper.paper_id)}
                      className="text-blue-400 hover:underline ml-auto"
                    >
                      Inspect Paper &rarr;
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
