/**
 * Generic fetch hook for API calls.
 * Uses config/api.js getApiUrl(endpoint).
 * Optional polling when pollIntervalMs > 0.
 */
import { useState, useEffect, useCallback } from "react";
import { getApiUrl } from "../config/api";

// Simple in-memory cache for API responses (stale-while-revalidate)
const _apiCache = new Map();

/**
 * @param {string} endpoint - Key from api.js endpoints (e.g. 'agents', 'dataSources')
 * @param {{ pollIntervalMs?: number, enabled?: boolean, endpoint?: string }} options - Poll interval in ms; if enabled is false, no fetch; endpoint override for custom paths
 * @returns {{ data: T | null, loading: boolean, error: Error | null, refetch: () => Promise<void> }}
 */
export function useApi(endpoint, options = {}) {
  const {
    pollIntervalMs = 0,
    enabled = true,
    endpoint: endpointOverride,
  } = options;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    let url = getApiUrl(endpoint);
    if (endpointOverride) {
      // Override endpoint path (e.g., '/heatmap' appended to signals endpoint)
      const baseUrl = getApiUrl(endpoint);
      url = baseUrl + endpointOverride;
    }
    if (!url) {
      setError(new Error(`Unknown endpoint: ${endpoint}`));
      setLoading(false);
      return;
    }
    try {
      setError(null);
      // Retry with exponential backoff (max 3 attempts)
      let lastErr;
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          const res = await fetch(url, { cache: "no-store" });
          if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
          const json = await res.json();
          setData(json);
          // Cache successful response
          _apiCache.set(url, { data: json, ts: Date.now() });
          lastErr = null;
          break;
        } catch (fetchErr) {
          lastErr = fetchErr;
          if (attempt < 2) {
            await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt)));
          }
        }
      }
      if (lastErr) {
        // Use cached data as fallback
        const cached = _apiCache.get(url);
        if (cached && Date.now() - cached.ts < 300000) { // 5 min stale
          setData(cached.data);
        } else {
          throw lastErr;
        }
      }
    } catch (err) {
      setError(err);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [endpoint, endpointOverride]);

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


// --- Specialized Risk & Kelly Hooks ---

export function useRiskScore(pollMs = 30000) {
  return useApi('riskScore', { pollIntervalMs: pollMs });
}

export function useDrawdownCheck(pollMs = 15000) {
  return useApi('drawdownCheck', { pollIntervalMs: pollMs });
}

export function useKellyRanked(enabled = true) {
  return useApi('kellyRanked', { enabled });
}

/** POST helper for dynamic stop-loss calculation */
export async function fetchDynamicStopLoss(symbol, entryPrice, side = 'buy') {
  const url = getApiUrl('dynamicStopLoss');
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, entry_price: entryPrice, side }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** POST helper for pre-trade risk check */
export async function fetchPreTradeCheck(symbol, side = 'buy') {
  const url = getApiUrl('preTradeCheck');
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, side }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}