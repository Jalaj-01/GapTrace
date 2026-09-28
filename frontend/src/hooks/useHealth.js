import { useState, useEffect, useCallback } from 'react';
import { fetchHealth } from '../services/api';

/**
 * Custom hook to monitor backend health and diagnostic states.
 */
export function useHealth(pollIntervalMs = 15000) {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);

  const checkHealth = useCallback(async () => {
    setLoading(true);
    const result = await fetchHealth();
    if (result.success) {
      setHealthData(result.data);
      setError(null);
    } else {
      setError(result.error);
    }
    setLastChecked(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    checkHealth();
    if (pollIntervalMs > 0) {
      const interval = setInterval(checkHealth, pollIntervalMs);
      return () => clearInterval(interval);
    }
  }, [checkHealth, pollIntervalMs]);

  return {
    healthData,
    loading,
    error,
    lastChecked,
    refetch: checkHealth,
  };
}
