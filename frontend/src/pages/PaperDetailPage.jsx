import React, { useState, useEffect } from 'react';
import {
  FileText,
  Calendar,
  User,
  Layers,
  AlertTriangle,
  Compass,
  Cpu,
  Database,
  Quote,
  CheckCircle2,
  ArrowLeft,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import {
  fetchPapers,
  fetchPaperDetails,
  fetchPaperSentences,
  fetchPaperExtractions,
  fetchPaperLimitations,
  fetchPaperFutureWork,
  processPaperNLP,
} from '../services/api';
import { useResearch } from '../contexts/ResearchContext';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

export default function PaperDetailPage() {
  const { selectedPaperId, setSelectedPaperId, setActiveView } = useResearch();

  const [papersList, setPapersList] = useState([]);
  const [currentPaperId, setCurrentPaperId] = useState(selectedPaperId || null);

  const [paper, setPaper] = useState(null);
  const [sentences, setSentences] = useState([]);
  const [limitations, setLimitations] = useState([]);
  const [futureWork, setFutureWork] = useState([]);
  const [methods, setMethods] = useState([]);
  const [datasets, setDatasets] = useState([]);

  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'limitations' | 'future_work' | 'methods' | 'datasets' | 'evidence'
  const [loading, setLoading] = useState(false);
  const [processingNLP, setProcessingNLP] = useState(false);
  const [error, setError] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');

  // Load available papers for selection dropdown
  useEffect(() => {
    async function loadPaperOptions() {
      try {
        const papers = await fetchPapers(0, 100);
        setPapersList(Array.isArray(papers) ? papers : []);
        if (!currentPaperId && papers.length > 0) {
          setCurrentPaperId(papers[0].id);
        }
      } catch {
        // Fallback
      }
    }
    loadPaperOptions();
  }, []);

  // Update current paper when context changes
  useEffect(() => {
    if (selectedPaperId) {
      setCurrentPaperId(selectedPaperId);
    }
  }, [selectedPaperId]);

  // Fetch full paper details and extractions whenever currentPaperId changes
  useEffect(() => {
    if (!currentPaperId) return;
    loadFullPaperData(currentPaperId);
  }, [currentPaperId]);

  const loadFullPaperData = async (paperId) => {
    setLoading(true);
    setError(null);
    setStatusMessage('');
    try {
      const [details, sents, limits, fw, meths, dsets] = await Promise.allSettled([
        fetchPaperDetails(paperId),
        fetchPaperSentences(paperId),
        fetchPaperLimitations(paperId),
        fetchPaperFutureWork(paperId),
        fetchPaperExtractions(paperId, 'METHOD'),
        fetchPaperExtractions(paperId, 'DATASET'),
      ]);

      if (details.status === 'fulfilled') {
        setPaper(details.value);
      } else {
        throw new Error(details.reason?.message || `Failed to load paper #${paperId}`);
      }

      setSentences(sents.status === 'fulfilled' && Array.isArray(sents.value) ? sents.value : []);
      setLimitations(limits.status === 'fulfilled' && Array.isArray(limits.value) ? limits.value : []);
      setFutureWork(fw.status === 'fulfilled' && Array.isArray(fw.value) ? fw.value : []);
      setMethods(meths.status === 'fulfilled' && Array.isArray(meths.value) ? meths.value : []);
      setDatasets(dsets.status === 'fulfilled' && Array.isArray(dsets.value) ? dsets.value : []);
    } catch (err) {
      setError(err.message || 'Error loading paper details.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunNLP = async () => {
    if (!currentPaperId) return;
    setProcessingNLP(true);
    setStatusMessage('Executing Phase 2 Scientific NLP pipeline...');
    try {
      const res = await processPaperNLP(currentPaperId);
      setStatusMessage(
        `NLP Processing complete: extracted ${res.sentences_count || 0} sentences and ${res.extractions_count || 0} entities.`
      );
      // Reload extractions
      await loadFullPaperData(currentPaperId);
    } catch (err) {
      setError(`NLP extraction failed: ${err.message}`);
    } finally {
      setProcessingNLP(false);
    }
  };

  if (!currentPaperId && !loading) {
    return (
      <div className="p-6 max-w-5xl mx-auto">
        <EmptyState
          title="No Paper Selected"
          description="Select a paper from the library to view detailed NLP extractions and provenance."
          actionLabel="Go to Paper Library"
          onAction={() => setActiveView('papers')}
        />
      </div>
    );
  }

  return (
    <div className="paper-detail-page p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Navigation & Selector Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-subtle">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveView('papers')}
            className="p-1.5 border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition"
            title="Back to Paper Library"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <span className="text-xs uppercase tracking-wider text-secondary font-mono">
              Paper Intelligence Inspector
            </span>
            <h1 className="text-xl font-bold text-primary truncate max-w-2xl">
              {paper?.title || `Paper #${currentPaperId}`}
            </h1>
          </div>
        </div>

        {/* Paper Selector Dropdown */}
        <div className="flex items-center gap-2">
          <select
            value={currentPaperId || ''}
            onChange={(e) => {
              const pid = Number(e.target.value);
              setCurrentPaperId(pid);
              if (setSelectedPaperId) setSelectedPaperId(pid);
            }}
            className="text-xs border border-subtle rounded-md bg-card px-2.5 py-1.5 text-primary max-w-xs truncate"
          >
            {papersList.map((p) => (
              <option key={p.id} value={p.id}>
                #{p.id} - {p.title || p.filename}
              </option>
            ))}
          </select>

          <button
            onClick={handleRunNLP}
            disabled={processingNLP}
            className="px-3 py-1.5 text-xs font-semibold bg-primary text-primary-contrast rounded-md hover:opacity-90 transition flex items-center gap-1.5"
          >
            <Sparkles size={13} className={processingNLP ? 'animate-spin' : ''} />
            <span>{processingNLP ? 'Processing...' : 'Run NLP'}</span>
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={() => loadFullPaperData(currentPaperId)} />

      {statusMessage && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs rounded-md">
          {statusMessage}
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          <LoadingSpinner text="Loading paper metadata and scientific extractions..." />
          <SkeletonCard count={3} height={120} />
        </div>
      ) : (
        paper && (
          <div className="space-y-6">
            {/* Paper Metadata Card */}
            <div className="bg-card border border-subtle rounded-lg p-5">
              <h2 className="text-lg font-bold text-primary mb-2">{paper.title}</h2>

              <div className="flex flex-wrap items-center gap-4 text-xs text-secondary mb-4">
                {paper.authors && (
                  <div className="flex items-center gap-1">
                    <User size={13} />
                    <span>
                      {Array.isArray(paper.authors)
                        ? paper.authors.join(', ')
                        : JSON.stringify(paper.authors)}
                    </span>
                  </div>
                )}
                {paper.year && (
                  <div className="flex items-center gap-1 font-mono">
                    <Calendar size={13} />
                    <span>{paper.year}</span>
                  </div>
                )}
                {paper.venue && (
                  <div className="flex items-center gap-1">
                    <FileText size={13} />
                    <span>{paper.venue}</span>
                  </div>
                )}
                <div className="text-secondary font-mono">
                  {paper.section_count || paper.sections?.length || 0} Sections
                </div>
              </div>

              {paper.abstract && (
                <div className="bg-muted/30 border border-subtle rounded-md p-4 text-xs leading-relaxed text-secondary">
                  <span className="font-semibold text-primary block mb-1">Abstract:</span>
                  {paper.abstract}
                </div>
              )}
            </div>

            {/* Extraction Navigation Tabs */}
            <div className="flex border-b border-subtle overflow-x-auto gap-2">
              {[
                { id: 'overview', label: 'Paper Sections', count: paper.sections?.length || 0 },
                { id: 'limitations', label: 'Limitations', count: limitations.length, icon: AlertTriangle },
                { id: 'future_work', label: 'Future Work', count: futureWork.length, icon: Compass },
                { id: 'methods', label: 'Methods', count: methods.length, icon: Cpu },
                { id: 'datasets', label: 'Datasets', count: datasets.length, icon: Database },
                { id: 'evidence', label: 'Evidence Sentences', count: sentences.length, icon: Quote },
              ].map((tab) => {
                const isActive = activeTab === tab.id;
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold border-b-2 transition whitespace-nowrap ${
                      isActive
                        ? 'border-primary text-primary bg-muted/20'
                        : 'border-transparent text-secondary hover:text-primary hover:border-subtle'
                    }`}
                  >
                    {Icon && <Icon size={13} />}
                    <span>{tab.label}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-muted text-secondary">
                      {tab.count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* TAB CONTENT */}

            {/* 1. Sections Overview */}
            {activeTab === 'overview' && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">
                  Document Structure & Parsed Hierarchy
                </h3>
                {(!paper.sections || paper.sections.length === 0) ? (
                  <EmptyState
                    title="No sections extracted"
                    description="Run NLP pipeline on this paper to parse headings and text sections."
                    actionLabel="Run NLP Pipeline"
                    onAction={handleRunNLP}
                  />
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {paper.sections.map((sec, idx) => (
                      <div
                        key={idx}
                        className="p-3 border border-subtle rounded-md bg-card flex flex-col justify-between"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-semibold text-primary">
                            {sec.title || `Section ${idx + 1}`}
                          </span>
                          <span className="text-[10px] font-mono text-secondary">
                            Page {sec.page || 1}
                          </span>
                        </div>
                        <p className="text-[11px] text-secondary line-clamp-3 mt-1">
                          {sec.content || sec.text || 'No preview text'}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 2. Limitations */}
            {activeTab === 'limitations' && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">
                  Detected Research Limitations ({limitations.length})
                </h3>
                {limitations.length === 0 ? (
                  <EmptyState
                    title="No limitations extracted"
                    description="Run NLP processing to detect explicit and implicit limitations in this paper."
                    actionLabel="Run NLP Pipeline"
                    onAction={handleRunNLP}
                  />
                ) : (
                  <div className="space-y-3">
                    {limitations.map((lim, idx) => (
                      <div
                        key={idx}
                        className="p-4 border border-subtle rounded-md bg-card space-y-2"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            {lim.category || lim.limitation_type || 'EMPIRICAL_LIMITATION'}
                          </span>
                          <span className="text-[11px] font-mono text-secondary">
                            Confidence: {Math.round((lim.confidence || 1.0) * 100)}%
                          </span>
                        </div>
                        <p className="text-xs text-primary leading-relaxed">
                          &ldquo;{lim.description || lim.text || lim.source_text}&rdquo;
                        </p>
                        <div className="flex items-center gap-3 text-[11px] text-secondary font-mono">
                          <span>Section: {lim.section || 'Unknown'}</span>
                          <span>Page: {lim.page || 1}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 3. Future Work */}
            {activeTab === 'future_work' && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">
                  Proposed Future Directions ({futureWork.length})
                </h3>
                {futureWork.length === 0 ? (
                  <EmptyState
                    title="No future work extracted"
                    description="Run NLP processing to classify forward-looking scientific directions."
                    actionLabel="Run NLP Pipeline"
                    onAction={handleRunNLP}
                  />
                ) : (
                  <div className="space-y-3">
                    {futureWork.map((fwItem, idx) => (
                      <div
                        key={idx}
                        className="p-4 border border-subtle rounded-md bg-card space-y-2"
                      >
                        <p className="text-xs text-primary leading-relaxed">
                          &ldquo;{fwItem.direction || fwItem.text || fwItem.source_text}&rdquo;
                        </p>
                        <div className="flex items-center gap-3 text-[11px] text-secondary font-mono">
                          <span>Section: {fwItem.section || 'Unknown'}</span>
                          <span>Page: {fwItem.page || 1}</span>
                          <span>Confidence: {Math.round((fwItem.confidence || 1.0) * 100)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 4. Methods */}
            {activeTab === 'methods' && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">
                  Extracted Methods & Algorithmic Techniques ({methods.length})
                </h3>
                {methods.length === 0 ? (
                  <EmptyState
                    title="No methods extracted"
                    description="Run NLP processing to extract proposed and baseline methods."
                    actionLabel="Run NLP Pipeline"
                    onAction={handleRunNLP}
                  />
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {methods.map((m, idx) => (
                      <div key={idx} className="p-3 border border-subtle rounded-md bg-card">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-bold text-primary">
                            {m.entity_name || m.text || `Method ${idx + 1}`}
                          </span>
                          <span className="text-[10px] font-mono text-secondary">
                            Section: {m.section || 'Methods'}
                          </span>
                        </div>
                        {m.context && (
                          <p className="text-[11px] text-secondary mt-1 leading-relaxed">
                            {m.context}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 5. Datasets */}
            {activeTab === 'datasets' && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">
                  Extracted Benchmark Datasets & Corpora ({datasets.length})
                </h3>
                {datasets.length === 0 ? (
                  <EmptyState
                    title="No datasets extracted"
                    description="Run NLP processing to extract evaluated benchmarks."
                    actionLabel="Run NLP Pipeline"
                    onAction={handleRunNLP}
                  />
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {datasets.map((d, idx) => (
                      <div key={idx} className="p-3 border border-subtle rounded-md bg-card">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-bold text-primary">
                            {d.entity_name || d.text || `Dataset ${idx + 1}`}
                          </span>
                          <span className="text-[10px] font-mono text-secondary">
                            Section: {d.section || 'Experiments'}
                          </span>
                        </div>
                        {d.context && (
                          <p className="text-[11px] text-secondary mt-1 leading-relaxed">
                            {d.context}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 6. Evidence Sentences */}
            {activeTab === 'evidence' && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">
                  Classified Rhetorical Sentences ({sentences.length})
                </h3>
                {sentences.length === 0 ? (
                  <EmptyState
                    title="No sentences classified"
                    description="Run NLP processing to classify sentences into rhetorical categories."
                    actionLabel="Run NLP Pipeline"
                    onAction={handleRunNLP}
                  />
                ) : (
                  <div className="space-y-2">
                    {sentences.map((sent, idx) => (
                      <div
                        key={idx}
                        className="p-3 border border-subtle rounded-md bg-card flex flex-col md:flex-row md:items-start justify-between gap-3 text-xs"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-secondary">
                              {sent.classification || sent.category || 'SENTENCE'}
                            </span>
                            <span className="text-[10px] font-mono text-secondary">
                              Page {sent.page || 1} &bull; {sent.section || 'Body'}
                            </span>
                          </div>
                          <p className="text-primary leading-relaxed">
                            {sent.text || sent.source_text}
                          </p>
                        </div>
                        {sent.confidence !== undefined && (
                          <div className="text-[10px] font-mono text-secondary whitespace-nowrap self-end md:self-start">
                            {Math.round(sent.confidence * 100)}%
                          </div>
                        )}
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
