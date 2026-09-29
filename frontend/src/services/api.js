/**
 * GapTrace API Client Service.
 * Connects frontend directly to the FastAPI backend with clean error handling.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * Health check & system diagnostics.
 */
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

/**
 * Retrieve list of ingested scientific papers.
 */
export async function fetchPapers(skip = 0, limit = 50) {
  try {
    const res = await fetch(`${API_BASE_URL}/papers?skip=${skip}&limit=${limit}`);
    if (!res.ok) {
      throw new Error(`Failed to load papers (${res.status})`);
    }
    return await res.json();
  } catch (err) {
    console.warn('API fetchPapers error:', err.message);
    return [];
  }
}

/**
 * Upload a scientific paper PDF file.
 */
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

/**
 * Retrieve single structured paper with parsed sections and references.
 */
export async function fetchPaperDetails(paperId) {
  const res = await fetch(`${API_BASE_URL}/papers/${paperId}`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error?.message || `Paper #${paperId} not found`);
  }
  return await res.json();
}

/**
 * Trigger Phase 2 Scientific NLP pipeline on an ingested paper.
 */
export async function processPaperNLP(paperId) {
  const res = await fetch(`${API_BASE_URL}/nlp/process/${paperId}`, {
    method: 'POST',
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error?.message || `NLP processing failed for paper #${paperId}`);
  }
  return data;
}

/**
 * Fetch classified sentences with full provenance.
 */
export async function fetchPaperSentences(paperId) {
  try {
    const res = await fetch(`${API_BASE_URL}/nlp/papers/${paperId}/sentences`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn('API fetchPaperSentences error:', err.message);
    return [];
  }
}

/**
 * Fetch scientific extractions (methods, datasets, metrics, results).
 */
export async function fetchPaperExtractions(paperId, extractionType = null) {
  try {
    const url = extractionType
      ? `${API_BASE_URL}/nlp/papers/${paperId}/extractions?extraction_type=${encodeURIComponent(extractionType)}`
      : `${API_BASE_URL}/nlp/papers/${paperId}/extractions`;
    const res = await fetch(url);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn('API fetchPaperExtractions error:', err.message);
    return [];
  }
}

/**
 * Fetch detected research limitations for a paper.
 */
export async function fetchPaperLimitations(paperId) {
  try {
    const res = await fetch(`${API_BASE_URL}/nlp/papers/${paperId}/limitations`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn('API fetchPaperLimitations error:', err.message);
    return [];
  }
}

/**
 * Fetch detected future work directions for a paper.
 */
export async function fetchPaperFutureWork(paperId) {
  try {
    const res = await fetch(`${API_BASE_URL}/nlp/papers/${paperId}/future-work`);
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.warn('API fetchPaperFutureWork error:', err.message);
    return [];
  }
}
