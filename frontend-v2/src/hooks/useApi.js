/**
 * Generic fetch hook for API calls.
 * Uses config/api.js getApiUrl(endpoint).
 * Optional polling when pollIntervalMs > 0.
 */
import { useState, useEffect, useCallback } from 'react';
import { getApiUrl } from '../config/api';

/**
 * @param {string} endpoint - Key from api.js endpoints (e.g. 'agents', 'dataSources')
 * @param {{ pollIntervalMs?: number, enabled?: boolean }} options - Poll interval in ms; if enabled is false, no fetch
 * @returns {{ data: T | null, loading: boolean, error: Error | null, refetch: () => Promise<void> }}
 */
export function useApi(endpoint, options = {}) {
  const { pollIntervalMs = 0, enabled = true } = options;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    const url = getApiUrl(endpoint);
    if (!url) {
      setError(new Error(`Unknown endpoint: ${endpoint}`));
      setLoading(false);
      return;
    }
    try {
      setError(null);
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    setLoading(true);
    fetchData();
  }, [enabled, fetchData]);

  useEffect(() => {
    if (!enabled || pollIntervalMs <= 0) return;
    const id = setInterval(fetchData, pollIntervalMs);
    return () => clearInterval(id);
  }, [enabled, pollIntervalMs, fetchData]);

  return { data, loading, error, refetch: fetchData };
}

export default useApi;
