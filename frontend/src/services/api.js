/**
 * ResearchGapX / GapTrace API Client Service.
 * Connects frontend directly to the FastAPI backend endpoints with robust error handling.
 * All research intelligence statistics and outputs originate dynamically from backend APIs.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * Generic helper for JSON fetch requests with unified error parsing.
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      let errorMsg = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        errorMsg = errorJson.error?.message || errorJson.detail || errorMsg;
      } catch {
        // Fallback to status text
      }
      throw new Error(errorMsg);
    }
    return await res.json();
  } catch (err) {
    console.warn(`[API] Error on ${url}:`, err.message);
    throw err;
  }
}

// =============================================================================
// 1. System Health & Diagnostics
// =============================================================================

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { success: false, error: err.error?.message || `HTTP ${res.status}`, data: null };
    }
    const data = await res.json();
    return { success: true, error: null, data };
  } catch (err) {
    return { success: false, error: err.message || 'Backend connection failed', data: null };
  }
}

// =============================================================================
// 2. Paper Management & NLP Pipeline
// =============================================================================

export async function fetchPapers(skip = 0, limit = 100) {
  try {
    return await apiRequest(`/papers?skip=${skip}&limit=${limit}`);
  } catch {
    return [];
  }
}

export async function uploadPaperFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE_URL}/papers/upload`, {
    method: 'POST',
    body: formData,
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error?.message || data.detail || `Upload failed with status ${res.status}`);
  }
  return data;
}

export async function fetchPaperDetails(paperId) {
  return await apiRequest(`/papers/${paperId}`);
}

export async function processPaperNLP(paperId) {
  return await apiRequest(`/nlp/process/${paperId}`, { method: 'POST' });
}

export async function fetchPaperSentences(paperId) {
  try {
    return await apiRequest(`/nlp/papers/${paperId}/sentences`);
  } catch {
    return [];
  }
}

export async function fetchPaperExtractions(paperId, extractionType = null) {
  try {
    const url = extractionType
      ? `/nlp/papers/${paperId}/extractions?extraction_type=${encodeURIComponent(extractionType)}`
      : `/nlp/papers/${paperId}/extractions`;
    return await apiRequest(url);
  } catch {
    return [];
  }
}

export async function fetchPaperLimitations(paperId) {
  try {
    return await apiRequest(`/nlp/papers/${paperId}/limitations`);
  } catch {
    return [];
  }
}

export async function fetchPaperFutureWork(paperId) {
  try {
    return await apiRequest(`/nlp/papers/${paperId}/future-work`);
  } catch {
    return [];
  }
}

// =============================================================================
// 3. Research Landscape & Topic Discovery (Phase 4)
// =============================================================================

export async function fetchTopicsOverview() {
  return await apiRequest('/topics/overview');
}

export async function fetchTopics() {
  try {
    return await apiRequest('/topics');
  } catch {
    return [];
  }
}

export async function fetchTopicDetails(topicId) {
  return await apiRequest(`/topics/${topicId}`);
}

export async function fetchTopicTrends(topicId = null) {
  const url = topicId !== null ? `/topics/trends?topic_id=${topicId}` : '/topics/trends';
  try {
    return await apiRequest(url);
  } catch {
    return [];
  }
}

export async function discoverTopics(minClusterSize = 2) {
  return await apiRequest(`/topics/discover?min_cluster_size=${minClusterSize}`, {
    method: 'POST',
  });
}

// =============================================================================
// 4. Research Knowledge Graph (Phase 5)
// =============================================================================

export async function fetchGraphOverview() {
  return await apiRequest('/graph/overview');
}

export async function buildGraph() {
  return await apiRequest('/graph/build', { method: 'POST' });
}

export async function fetchPaperSubgraph(paperId, hops = 1) {
  return await apiRequest(`/graph/paper/${paperId}?hops=${hops}`);
}

export async function fetchLimitationGraph(limitationId) {
  return await apiRequest(`/graph/limitation/${encodeURIComponent(limitationId)}`);
}

export async function fetchMethodGraph(methodId) {
  return await apiRequest(`/graph/method/${encodeURIComponent(methodId)}`);
}

export async function queryGraph(queryType, targetId = null, text = null, topicId = null) {
  const params = new URLSearchParams();
  params.append('query_type', queryType);
  if (targetId) params.append('target_id', targetId);
  if (text) params.append('text', text);
  if (topicId !== null && topicId !== undefined) params.append('topic_id', topicId);
  return await apiRequest(`/graph/query?${params.toString()}`);
}

export async function exportCypher() {
  return await apiRequest('/graph/export/cypher');
}

// =============================================================================
// 5. Research Gap Candidates & Scoring Signals (Phase 6)
// =============================================================================

export async function fetchGapCandidates({
  gapType = null,
  minPriority = 0.0,
  minConfidence = 0.5,
  limit = 50,
} = {}) {
  const params = new URLSearchParams();
  if (gapType) params.append('gap_type', gapType);
  if (minPriority !== undefined) params.append('min_priority', minPriority);
  if (minConfidence !== undefined) params.append('min_confidence', minConfidence);
  params.append('limit', limit);
  return await apiRequest(`/gaps/candidates?${params.toString()}`);
}

export async function fetchGapCandidateDetail(gapId) {
  return await apiRequest(`/gaps/candidates/${encodeURIComponent(gapId)}`);
}

export async function fetchGapCandidateEvidence(gapId) {
  try {
    return await apiRequest(`/gaps/candidates/${encodeURIComponent(gapId)}/evidence`);
  } catch {
    return [];
  }
}

export async function fetchGapSignalsOverview() {
  return await apiRequest('/gaps/signals');
}

// =============================================================================
// 6. Gap Lifecycle & Gap Genealogy (Phase 7)
// =============================================================================

export async function fetchGapLifecycleOverview() {
  return await apiRequest('/gaps/lifecycle/overview');
}

export async function fetchGapTimeline(gapId) {
  return await apiRequest(`/gaps/${encodeURIComponent(gapId)}/timeline`);
}

export async function fetchGapGenealogy(gapId) {
  return await apiRequest(`/gaps/${encodeURIComponent(gapId)}/genealogy`);
}

export async function fetchGapLifecycle(gapId) {
  return await apiRequest(`/gaps/${encodeURIComponent(gapId)}/lifecycle`);
}

// =============================================================================
// 7. Counter-Evidence Search & Verification (Phase 8)
// =============================================================================

export async function fetchGapVerification(gapId) {
  return await apiRequest(`/gaps/${encodeURIComponent(gapId)}/verification`);
}

export async function fetchGapCounterEvidence(gapId) {
  return await apiRequest(`/gaps/${encodeURIComponent(gapId)}/counter-evidence`);
}

export async function verifyGap(gapId, { minConfidence = 0.6, includeNli = true } = {}) {
  return await apiRequest(`/gaps/${encodeURIComponent(gapId)}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ min_confidence: minConfidence, include_nli: includeNli }),
  });
}

// =============================================================================
// 8. Evidence Retrieval & Semantic Search (Phase 3)
// =============================================================================

export async function searchSemanticEvidence({
  q,
  topK = 10,
  paperId = null,
  section = null,
  extractionType = null,
  year = null,
  minYear = null,
  maxYear = null,
}) {
  const params = new URLSearchParams();
  params.append('q', q);
  params.append('top_k', topK);
  if (paperId) params.append('paper_id', paperId);
  if (section) params.append('section', section);
  if (extractionType) params.append('extraction_type', extractionType);
  if (year) params.append('year', year);
  if (minYear) params.append('min_year', minYear);
  if (maxYear) params.append('max_year', maxYear);
  return await apiRequest(`/search/semantic?${params.toString()}`);
}

// =============================================================================
// 9. Evidence-Grounded RAG and LLM Synthesis (Phase 9)
// =============================================================================

export async function synthesizeGapReport(gapId, payload = {}) {
  return await apiRequest(`/gaps/${encodeURIComponent(gapId)}/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function fetchGapSynthesis(gapId) {
  return await apiRequest(`/gaps/${encodeURIComponent(gapId)}/synthesis`);
}

export async function validateCitations(payload) {
  return await apiRequest('/gaps/validate-citations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
