/**
 * Frontend API client service for Scientific Paper Gap Finder.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * Fetch backend health status and system diagnostics.
 */
export async function fetchHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        error: errorData.error?.message || `HTTP ${response.status}: ${response.statusText}`,
        data: null,
      };
    }

    const data = await response.json();
    return {
      success: true,
      error: null,
      data,
    };
  } catch (err) {
    return {
      success: false,
      error: err.message || 'Network connection failed. Backend might be offline.',
      data: null,
    };
  }
}

/**
 * Fetch papers list.
 */
export async function fetchPapers(skip = 0, limit = 50) {
  try {
    const response = await fetch(`${API_BASE_URL}/papers?skip=${skip}&limit=${limit}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch papers: ${response.statusText}`);
    }
    return await response.json();
  } catch (err) {
    console.error('Error fetching papers:', err);
    return [];
  }
}

/**
 * Upload scientific paper PDF.
 */
export async function uploadPaperFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/papers/upload`, {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error?.message || `Upload failed (Status ${response.status})`);
  }
  return data;
}

/**
 * Fetch single structured paper by ID.
 */
export async function fetchPaperDetails(paperId) {
  const response = await fetch(`${API_BASE_URL}/papers/${paperId}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `Failed to fetch paper details`);
  }
  return await response.json();
}
