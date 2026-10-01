import React, { useState, useEffect } from 'react';
import {
  FileCode,
  ArrowLeft,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  BookOpen,
  Quote,
  ShieldCheck,
  ShieldAlert,
  Download,
  Settings,
  Target,
} from 'lucide-react';
import {
  fetchGapCandidates,
  fetchGapSynthesis,
  synthesizeGapReport,
} from '../services/api';
import { useResearch } from '../contexts/ResearchContext';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

export default function ResearchReportPage() {
  const { selectedGapId, setSelectedGapId, setActiveView, openGapDetail } = useResearch();

  const [candidatesList, setCandidatesList] = useState([]);
  const [currentGapId, setCurrentGapId] = useState(selectedGapId || null);

  const [synthesis, setSynthesis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [synthesizing, setSynthesizing] = useState(false);
  const [error, setError] = useState(null);

  // Synthesis Parameters
  const [provider, setProvider] = useState('gemini');
  const [topKEvidence, setTopKEvidence] = useState(10);
  const [validateCitations, setValidateCitations] = useState(true);

  // Load candidate list
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
    loadSynthesis(currentGapId);
  }, [currentGapId]);

  const loadSynthesis = async (gapId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGapSynthesis(gapId);
      setSynthesis(data);
    } catch (err) {
      setError(err.message || 'No prior synthesis found. You can generate a new report.');
      setSynthesis(null);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!currentGapId) return;
    setSynthesizing(true);
    setError(null);
    try {
      const res = await synthesizeGapReport(currentGapId, {
        provider,
        top_k_evidence: topKEvidence,
        validate_citations: validateCitations,
        temperature: 0.2,
        max_tokens: 1500,
      });
      setSynthesis(res);
    } catch (err) {
      setError(`Synthesis failed: ${err.message}`);
    } finally {
      setSynthesizing(false);
    }
  };

  const citations = synthesis?.citations || {};
  const validation = synthesis?.validation_report;

  return (
    <div className="research-report-page p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
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
              Phase 9 Evidence-Grounded Synthesis
            </span>
            <h1 className="text-xl font-bold text-primary flex items-center gap-2">
              <FileCode size={22} className="text-indigo-400" />
              Evidence-Grounded Research Report
            </h1>
          </div>
        </div>

        {/* Gap Selector Dropdown */}
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
            className="px-3 py-1.5 text-xs font-medium border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition flex items-center gap-1"
          >
            <Target size={13} />
            <span>Gap Details</span>
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={() => loadSynthesis(currentGapId)} />

      {/* Synthesis Configuration & Trigger Panel */}
      <div className="bg-card border border-subtle rounded-lg p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-secondary">Provider:</span>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="py-1 px-2 border border-subtle rounded bg-muted/30 text-primary text-xs"
              >
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI GPT-4o</option>
                <option value="local">Local HuggingFace LLM</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="font-semibold text-secondary">Evidence Depth:</span>
              <select
                value={topKEvidence}
                onChange={(e) => setTopKEvidence(Number(e.target.value))}
                className="py-1 px-2 border border-subtle rounded bg-muted/30 text-primary text-xs"
              >
                <option value={5}>Top 5 Passages</option>
                <option value={10}>Top 10 Passages</option>
                <option value={15}>Top 15 Passages</option>
                <option value={20}>Top 20 Passages</option>
              </select>
            </div>

            <label className="flex items-center gap-2 cursor-pointer text-secondary">
              <input
                type="checkbox"
                checked={validateCitations}
                onChange={(e) => setValidateCitations(e.target.checked)}
                className="rounded border-subtle"
              />
              <span>Automated Citation Factuality Check</span>
            </label>
          </div>

          <button
            onClick={handleGenerateReport}
            disabled={synthesizing || !currentGapId}
            className="px-4 py-2 text-xs font-semibold bg-primary text-primary-contrast rounded-md hover:opacity-90 transition flex items-center gap-1.5"
          >
            <Sparkles size={14} className={synthesizing ? 'animate-spin' : ''} />
            <span>{synthesizing ? 'Synthesizing with LLM...' : 'Generate Grounded Report'}</span>
          </button>
        </div>
      </div>

      {/* Report Display */}
      {loading ? (
        <div className="space-y-4">
          <LoadingSpinner text="Retrieving grounded synthesis and provenance citations..." />
          <SkeletonCard count={3} height={140} />
        </div>
      ) : !synthesis ? (
        <EmptyState
          icon={FileCode}
          title="No Synthesis Generated Yet"
          description="Click 'Generate Grounded Report' to have the LLM synthesize this verified research gap grounded strictly in retrieved scientific evidence."
          actionLabel="Generate Report"
          onAction={handleGenerateReport}
        />
      ) : (
        <div className="space-y-6">
          {/* Main Academic Report Document */}
          <div className="bg-card border border-subtle rounded-lg p-6 space-y-6 shadow-sm">
            {/* Header info */}
            <div className="pb-4 border-b border-subtle space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono text-secondary">
                <span>LLM Engine: {synthesis.provider} &bull; Model: {synthesis.model}</span>
                <span>Synthesized: {new Date(synthesis.synthesized_at).toLocaleString()}</span>
              </div>
              <h2 className="text-xl font-bold text-primary">{synthesis.gap_title}</h2>
              <div className="flex items-center gap-2 pt-1">
                <span className="text-xs font-mono px-2.5 py-0.5 rounded bg-muted text-secondary font-semibold">
                  Status: {synthesis.current_status}
                </span>
                {synthesis.insufficient_evidence && (
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    Sparse Evidence Flagged
                  </span>
                )}
              </div>
            </div>

            {/* 1. Gap Explanation */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-secondary">
                1. Scientific Gap Explanation
              </h3>
              <p className="text-xs text-primary leading-relaxed bg-muted/20 border border-subtle p-3.5 rounded-md">
                {synthesis.gap_explanation}
              </p>
            </div>

            {/* 2. Why It Matters */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-secondary">
                2. Practical & Empirical Importance
              </h3>
              <p className="text-xs text-primary leading-relaxed bg-muted/20 border border-subtle p-3.5 rounded-md">
                {synthesis.why_it_matters}
              </p>
            </div>

            {/* 3. Evidence Summaries */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
                  <BookOpen size={14} />
                  <span>Supporting Evidence Summary</span>
                </h3>
                <p className="text-xs text-secondary leading-relaxed bg-muted/20 border border-subtle p-3 rounded-md">
                  {synthesis.supporting_evidence_summary}
                </p>
              </div>

              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                  <ShieldAlert size={14} />
                  <span>Counter-Evidence Summary</span>
                </h3>
                <p className="text-xs text-secondary leading-relaxed bg-muted/20 border border-subtle p-3 rounded-md">
                  {synthesis.counter_evidence_summary}
                </p>
              </div>
            </div>

            {/* 4. Potential Research Questions */}
            {synthesis.potential_research_questions &&
              synthesis.potential_research_questions.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-secondary">
                    4. Candidate Research Questions
                  </h3>
                  <div className="space-y-2">
                    {synthesis.potential_research_questions.map((rq, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-muted/20 border border-subtle rounded-md text-xs font-medium text-primary flex items-start gap-2.5"
                      >
                        <span className="font-mono text-purple-400 font-bold">RQ{idx + 1}:</span>
                        <span>{rq}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* 5. Potential Future Directions */}
            {synthesis.potential_future_directions &&
              synthesis.potential_future_directions.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-secondary">
                    5. Suggested Technical Directions
                  </h3>
                  <ul className="space-y-1.5 text-xs text-secondary list-disc pl-5">
                    {synthesis.potential_future_directions.map((fd, idx) => (
                      <li key={idx} className="leading-relaxed">
                        {fd}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            {/* 6. Evidence Limitations */}
            {synthesis.evidence_limitations && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                  <AlertTriangle size={14} />
                  <span>Evidence Limitations & Boundary Conditions</span>
                </h3>
                <p className="text-xs text-secondary leading-relaxed bg-amber-500/5 border border-amber-500/20 p-3 rounded-md">
                  {synthesis.evidence_limitations}
                </p>
              </div>
            )}
          </div>

          {/* Citation Provenance Table */}
          {Object.keys(citations).length > 0 && (
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-3">
              <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider flex items-center gap-1.5">
                <Quote size={14} className="text-indigo-400" />
                <span>Grounded Evidence Citations Map ({Object.keys(citations).length} In-Text Citations)</span>
              </h3>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted/40 font-mono text-[10px] text-secondary uppercase">
                    <tr>
                      <th className="py-2.5 px-3">Marker</th>
                      <th className="py-2.5 px-3">Source Publication</th>
                      <th className="py-2.5 px-3">Page & Section</th>
                      <th className="py-2.5 px-3">Verbatim Sentence</th>
                      <th className="py-2.5 px-3">Type</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-subtle">
                    {Object.entries(citations).map(([tag, src]) => (
                      <tr key={tag} className="hover:bg-muted/10">
                        <td className="py-2 px-3 font-mono font-bold text-indigo-400">
                          [{tag}]
                        </td>
                        <td className="py-2 px-3 font-semibold text-primary max-w-xs">
                          {src.paper_title || `Paper #${src.paper_id}`}
                        </td>
                        <td className="py-2 px-3 font-mono text-secondary whitespace-nowrap">
                          p. {src.page || 1} &bull; {src.section || 'Unknown'}
                        </td>
                        <td className="py-2 px-3 text-secondary text-[11px] max-w-md leading-relaxed">
                          &ldquo;{src.sentence_text}&rdquo;
                        </td>
                        <td className="py-2 px-3 font-mono text-[10px] text-secondary">
                          {src.evidence_type || 'RETRIEVED'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Automated Citation Validation Report */}
          {validation && (
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-subtle">
                <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-emerald-400" />
                  <span>Automated Factuality & Citation Audit Report</span>
                </h3>
                <span
                  className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded border ${
                    validation.is_valid
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}
                >
                  AUDIT VERDICT: {validation.is_valid ? 'VALID' : 'REJECTED'}
                </span>
              </div>

              {/* Validation Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                <div className="p-3 bg-muted/20 border border-subtle rounded">
                  <span className="text-[10px] uppercase font-mono text-secondary block">
                    Support Rate
                  </span>
                  <span className="text-xl font-bold font-mono text-primary">
                    {Math.round(validation.evidence_support_rate * 100)}%
                  </span>
                </div>
                <div className="p-3 bg-muted/20 border border-subtle rounded">
                  <span className="text-[10px] uppercase font-mono text-secondary block">
                    Total Claims
                  </span>
                  <span className="text-xl font-bold font-mono text-primary">
                    {validation.total_claims}
                  </span>
                </div>
                <div className="p-3 bg-muted/20 border border-subtle rounded">
                  <span className="text-[10px] uppercase font-mono text-secondary block">
                    Supported
                  </span>
                  <span className="text-xl font-bold font-mono text-emerald-400">
                    {validation.supported_claims}
                  </span>
                </div>
                <div className="p-3 bg-muted/20 border border-subtle rounded">
                  <span className="text-[10px] uppercase font-mono text-secondary block">
                    Unsupported
                  </span>
                  <span className="text-xl font-bold font-mono text-amber-400">
                    {validation.unsupported_claims}
                  </span>
                </div>
                <div className="p-3 bg-muted/20 border border-subtle rounded">
                  <span className="text-[10px] uppercase font-mono text-secondary block">
                    Hallucinated
                  </span>
                  <span className="text-xl font-bold font-mono text-rose-400">
                    {validation.hallucinated_citations}
                  </span>
                </div>
              </div>

              {/* Claim-by-Claim Validation Breakdown */}
              {validation.claims && validation.claims.length > 0 && (
                <div className="space-y-2 pt-2">
                  <span className="text-[11px] font-semibold text-secondary uppercase block">
                    Individual Claim Verifications:
                  </span>
                  <div className="space-y-2">
                    {validation.claims.map((claim, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-muted/15 border border-subtle rounded text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span
                            className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                              claim.status === 'SUPPORTED'
                                ? 'bg-emerald-500/10 text-emerald-400'
                                : 'bg-rose-500/10 text-rose-400'
                            }`}
                          >
                            {claim.status}
                          </span>
                          <span className="text-[10px] font-mono text-secondary">
                            Citations: {claim.cited_ids?.join(', ') || 'None'} &bull; Score:{' '}
                            {(claim.support_score || 0).toFixed(2)}
                          </span>
                        </div>
                        <p className="text-primary">&ldquo;{claim.claim_text}&rdquo;</p>
                        <p className="text-secondary text-[11px]">{claim.explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
