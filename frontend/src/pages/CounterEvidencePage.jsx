import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  RefreshCw,
  Sparkles,
  BookOpen,
  Calendar,
  Layers,
  Target,
  FileCode,
} from 'lucide-react';
import {
  fetchGapCandidates,
  fetchGapCounterEvidence,
  fetchGapVerification,
  verifyGap,
} from '../services/api';
import { useResearch } from '../contexts/ResearchContext';
import { LoadingSpinner, SkeletonCard } from '../components/ui/LoadingSkeleton';
import ErrorBanner from '../components/ui/ErrorBanner';
import EmptyState from '../components/ui/EmptyState';

export default function CounterEvidencePage() {
  const { selectedGapId, setSelectedGapId, setActiveView, openGapDetail, openGapReport } = useResearch();

  const [candidatesList, setCandidatesList] = useState([]);
  const [currentGapId, setCurrentGapId] = useState(selectedGapId || null);

  const [counterData, setCounterData] = useState(null);
  const [verificationData, setVerificationData] = useState(null);

  const [loading, setLoading] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState(null);
  const [verifyMessage, setVerifyMessage] = useState('');

  // Active Category Tab
  const [activeCategory, setActiveCategory] = useState('ALL'); // 'ALL' | 'SUPPORTING' | 'COUNTER' | 'ADDRESSED_BY' | 'CONTRADICTORY'

  // Load candidate options
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
    loadEvidence(currentGapId);
  }, [currentGapId]);

  const loadEvidence = async (gapId) => {
    setLoading(true);
    setError(null);
    setVerifyMessage('');
    try {
      const [counterRes, verifRes] = await Promise.allSettled([
        fetchGapCounterEvidence(gapId),
        fetchGapVerification(gapId),
      ]);

      setCounterData(counterRes.status === 'fulfilled' ? counterRes.value : null);
      setVerificationData(verifRes.status === 'fulfilled' ? verifRes.value : null);
    } catch (err) {
      setError(err.message || 'Failed to retrieve counter-evidence.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunVerification = async () => {
    if (!currentGapId) return;
    setIsVerifying(true);
    setVerifyMessage('Running active counter-evidence retrieval and scientific NLI inference...');
    try {
      const res = await verifyGap(currentGapId, { minConfidence: 0.6, includeNli: true });
      setVerificationData(res);
      setVerifyMessage(
        `Verification updated: Final Status is ${res.final_status} (Confidence: ${Math.round(
          res.verification_confidence * 100
        )}%)`
      );
      await loadEvidence(currentGapId);
    } catch (err) {
      setError(`Active verification failed: ${err.message}`);
    } finally {
      setIsVerifying(false);
    }
  };

  const supportingItems = verificationData?.supporting_evidence || [];
  const counterItems = counterData?.counter_evidence || verificationData?.counter_evidence || [];
  const addressedItems = counterData?.addressed_by_evidence || verificationData?.addressed_by_evidence || [];
  const contradictoryItems = counterData?.contradictory_evidence || verificationData?.contradictory_evidence || [];

  return (
    <div className="counter-evidence-page p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header & Selector */}
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
              Empirical Verification & Refutation Engine
            </span>
            <h1 className="text-xl font-bold text-primary flex items-center gap-2">
              <ShieldAlert size={22} className="text-rose-400" />
              Counter-Evidence & Verification
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
            onClick={handleRunVerification}
            disabled={isVerifying}
            className="px-3.5 py-1.5 text-xs font-semibold bg-primary text-primary-contrast rounded-md hover:opacity-90 transition flex items-center gap-1.5"
          >
            <Sparkles size={13} className={isVerifying ? 'animate-spin' : ''} />
            <span>{isVerifying ? 'Verifying NLI...' : 'Verify Gap'}</span>
          </button>

          <button
            onClick={() => openGapDetail(currentGapId)}
            className="px-3 py-1.5 text-xs font-medium border border-subtle rounded-md hover:bg-muted text-secondary hover:text-primary transition"
          >
            Gap Detail
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onRetry={() => loadEvidence(currentGapId)} />

      {verifyMessage && (
        <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs rounded-md">
          {verifyMessage}
        </div>
      )}

      {/* Verification Status Overview Banner */}
      {verificationData && (
        <div className="bg-card border border-subtle rounded-lg p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span
                className={`text-xs font-mono font-bold px-3 py-1 rounded border ${
                  verificationData.final_status === 'VERIFIED_OPEN'
                    ? 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                    : verificationData.final_status === 'ADDRESSED'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : 'bg-muted text-secondary'
                }`}
              >
                VERIFICATION: {verificationData.final_status}
              </span>
              <span className="text-xs font-mono text-secondary">
                Confidence: {Math.round((verificationData.verification_confidence || 0) * 100)}%
              </span>
            </div>
            <div className="text-xs font-mono text-secondary">
              Verified: {verificationData.verified_at ? new Date(verificationData.verified_at).toLocaleDateString() : 'Active'}
            </div>
          </div>

          <h2 className="text-base font-bold text-primary">
            {verificationData.gap_title}
          </h2>

          <p className="text-xs text-secondary leading-relaxed bg-muted/20 border border-subtle p-3 rounded-md">
            {verificationData.status_reasoning}
          </p>

          {/* Temporal Evidence Years */}
          {verificationData.evidence_dates && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono text-secondary pt-2 border-t border-subtle">
              <div>
                <span className="text-[10px] uppercase block">Earliest Citation</span>
                <strong className="text-primary">
                  {verificationData.evidence_dates.earliest_year || 'Unknown'}
                </strong>
              </div>
              <div>
                <span className="text-[10px] uppercase block">Latest Citation</span>
                <strong className="text-primary">
                  {verificationData.evidence_dates.latest_year || 'Unknown'}
                </strong>
              </div>
              <div>
                <span className="text-[10px] uppercase block">Supporting Years</span>
                <strong className="text-primary">
                  {verificationData.evidence_dates.supporting_years?.join(', ') || 'None'}
                </strong>
              </div>
              <div>
                <span className="text-[10px] uppercase block">Counter Years</span>
                <strong className="text-primary">
                  {verificationData.evidence_dates.counter_years?.join(', ') || 'None'}
                </strong>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 4-Category Counter-Evidence KPI Tabs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          {
            id: 'SUPPORTING',
            label: 'Supporting Evidence',
            count: supportingItems.length,
            color: 'border-blue-500/20 bg-blue-500/5 text-blue-400',
          },
          {
            id: 'COUNTER',
            label: 'Counter-Evidence',
            count: counterItems.length,
            color: 'border-rose-500/20 bg-rose-500/5 text-rose-400',
          },
          {
            id: 'ADDRESSED_BY',
            label: 'Addressing Papers',
            count: addressedItems.length,
            color: 'border-emerald-500/20 bg-emerald-500/5 text-emerald-400',
          },
          {
            id: 'CONTRADICTORY',
            label: 'Contradictory Evidence',
            count: contradictoryItems.length,
            color: 'border-amber-500/20 bg-amber-500/5 text-amber-400',
          },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveCategory(activeCategory === tab.id ? 'ALL' : tab.id)}
            className={`p-3.5 rounded-lg border text-left transition flex items-center justify-between ${
              tab.color
            } ${activeCategory === tab.id ? 'ring-2 ring-primary' : 'hover:opacity-90'}`}
          >
            <div>
              <span className="text-[11px] font-semibold text-secondary uppercase block mb-1">
                {tab.label}
              </span>
              <span className="text-xl font-bold font-mono text-primary">
                {tab.count}
              </span>
            </div>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-4">
          <LoadingSpinner text="Retrieving multi-paper evidence classifications..." />
          <SkeletonCard count={3} height={120} />
        </div>
      ) : (
        <div className="space-y-6">
          {/* 1. Supporting Evidence Section */}
          {(activeCategory === 'ALL' || activeCategory === 'SUPPORTING') && (
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-3">
              <h3 className="text-xs font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                <BookOpen size={14} />
                <span>Supporting Evidence ({supportingItems.length})</span>
              </h3>

              {supportingItems.length === 0 ? (
                <p className="text-xs text-secondary">No supporting evidence recorded.</p>
              ) : (
                <div className="space-y-3">
                  {supportingItems.map((item, idx) => (
                    <div
                      key={item.evidence_id || idx}
                      className="p-3.5 bg-blue-500/5 border border-blue-500/20 rounded-md space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono text-secondary">
                        <span className="font-semibold text-primary">
                          {item.paper_title || `Paper #${item.paper_id}`}
                        </span>
                        <span>Section: {item.section || 'Unknown'} &bull; Year: {item.publication_year || 'N/A'}</span>
                      </div>
                      <p className="text-xs text-primary leading-relaxed">
                        &ldquo;{item.source_text}&rdquo;
                      </p>
                      {item.nli_result && (
                        <div className="flex items-center gap-2 pt-1 text-[10px] font-mono">
                          <span className="px-1.5 py-0.5 rounded bg-muted text-secondary">
                            NLI: {item.nli_result.label} ({Math.round(item.nli_result.confidence * 100)}%)
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 2. Counter-Evidence Section */}
          {(activeCategory === 'ALL' || activeCategory === 'COUNTER') && (
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-3">
              <h3 className="text-xs font-semibold text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldAlert size={14} />
                <span>Counter-Evidence & Refutations ({counterItems.length})</span>
              </h3>

              {counterItems.length === 0 ? (
                <p className="text-xs text-secondary">No direct counter-evidence identified in corpus.</p>
              ) : (
                <div className="space-y-3">
                  {counterItems.map((item, idx) => (
                    <div
                      key={item.evidence_id || idx}
                      className="p-3.5 bg-rose-500/5 border border-rose-500/20 rounded-md space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono text-secondary">
                        <span className="font-semibold text-primary">
                          {item.paper_title || `Paper #${item.paper_id}`}
                        </span>
                        <span>Year: {item.publication_year || 'N/A'}</span>
                      </div>
                      <p className="text-xs text-primary leading-relaxed">
                        &ldquo;{item.source_text}&rdquo;
                      </p>
                      {item.nli_result && (
                        <div className="text-[10px] font-mono text-secondary pt-1">
                          NLI Label: <strong className="text-rose-400">{item.nli_result.label}</strong> ({Math.round(item.nli_result.confidence * 100)}%)
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 3. Addressing Papers Section */}
          {(activeCategory === 'ALL' || activeCategory === 'ADDRESSED_BY') && (
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-3">
              <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 size={14} />
                <span>Publications Addressing This Gap ({addressedItems.length})</span>
              </h3>

              {addressedItems.length === 0 ? (
                <p className="text-xs text-secondary">No publications claiming solutions have been indexed.</p>
              ) : (
                <div className="space-y-3">
                  {addressedItems.map((item, idx) => (
                    <div
                      key={item.evidence_id || idx}
                      className="p-3.5 bg-emerald-500/5 border border-emerald-500/20 rounded-md space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono text-secondary">
                        <span className="font-semibold text-primary">
                          {item.paper_title || `Paper #${item.paper_id}`}
                        </span>
                        <span>Year: {item.publication_year || 'N/A'}</span>
                      </div>
                      <p className="text-xs text-primary leading-relaxed">
                        &ldquo;{item.source_text}&rdquo;
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 4. Contradictory Evidence Section */}
          {(activeCategory === 'ALL' || activeCategory === 'CONTRADICTORY') && (
            <div className="bg-card border border-subtle rounded-lg p-5 space-y-3">
              <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                <AlertTriangle size={14} />
                <span>Contradictory & Disputed Evidence ({contradictoryItems.length})</span>
              </h3>

              {contradictoryItems.length === 0 ? (
                <p className="text-xs text-secondary">No contradictory evidence edges detected.</p>
              ) : (
                <div className="space-y-3">
                  {contradictoryItems.map((item, idx) => (
                    <div
                      key={item.evidence_id || idx}
                      className="p-3.5 bg-amber-500/5 border border-amber-500/20 rounded-md space-y-1.5"
                    >
                      <div className="text-[10px] font-mono text-secondary">
                        {item.paper_title || `Paper #${item.paper_id}`}
                      </div>
                      <p className="text-xs text-primary leading-relaxed">
                        &ldquo;{item.source_text}&rdquo;
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
