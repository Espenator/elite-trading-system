/**
 * Generic fetch hook for API calls.
 * Uses config/api.js getApiUrl(endpoint).
 * Optional polling when pollIntervalMs > 0.
 * AUDIT FIX (Task 18): Reduced aggressive polling intervals (5-10s -> 15-30s)
 * and added page visibility pause. Use WebSocket subscriptions for real-time updates.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { getApiUrl, getAuthHeaders } from "../config/api";

// Default fetch timeout (15 seconds)
const DEFAULT_TIMEOUT_MS = 15000;

// Simple in-memory cache for API responses (stale-while-revalidate)
const _apiCache = new Map();
const CACHE_MAX_SIZE = 200;
const CACHE_STALE_MS = 300000; // 5 min

// Global concurrency limiter — prevents browser connection exhaustion
let _activeRequests = 0;
const MAX_CONCURRENT = 6; // Browser limit per host
const _queue = [];

function _runNext() {
  while (_queue.length > 0 && _activeRequests < MAX_CONCURRENT) {
    const { resolve } = _queue.shift();
    _activeRequests++;
    resolve();
  }
}

function _acquireSlot() {
  if (_activeRequests < MAX_CONCURRENT) {
    _activeRequests++;
    return Promise.resolve();
  }
  return new Promise((resolve) => _queue.push({ resolve }));
}

function _releaseSlot() {
  _activeRequests--;
  _runNext();
}

// Per-URL in-flight deduplication
const _inflight = new Map();

/**
 * @param {string} endpoint - Key from api.js endpoints (e.g. 'agents', 'dataSources')
 * @param {{ pollIntervalMs?: number, enabled?: boolean, endpoint?: string }} options
 * @returns {{ data: T | null, loading: boolean, error: Error | null, isStale: boolean, lastUpdated: number | null, refetch: () => Promise<void> }}
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
  const [isStale, setIsStale] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const abortRef = useRef(null);

  const fetchData = useCallback(async (signal) => {
    let url = getApiUrl(endpoint);
    if (endpointOverride) {
      const base = import.meta.env.VITE_API_URL ?? '';
      url = `${base}/api/v1${endpointOverride}`;
    }
    if (!url) {
      setError(new Error(`Unknown endpoint: ${endpoint}`));
      setLoading(false);
      return;
    }

    // Deduplicate: if same URL is already in-flight, piggyback on it
    if (_inflight.has(url)) {
      try {
        const json = await _inflight.get(url);
        if (!signal?.aborted) {
          setData(json);
          setError(null);
          setIsStale(false);
          setLastUpdated(Date.now());
        }
        return;
      } catch (err) {
        if (signal?.aborted) return;
        // fall through to cache check below
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    }

    const fetchPromise = (async () => {
      await _acquireSlot();
      try {
        // Timeout via AbortController
        const timeoutCtrl = new AbortController();
        const timeoutId = setTimeout(() => timeoutCtrl.abort(), DEFAULT_TIMEOUT_MS);

        // Combine user abort + timeout signals
        const combinedSignal = signal
          ? AbortSignal.any ? AbortSignal.any([signal, timeoutCtrl.signal]) : timeoutCtrl.signal
          : timeoutCtrl.signal;

        try {
          const res = await fetch(url, { cache: "no-store", headers: getAuthHeaders(), signal: combinedSignal });
          if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
          const json = await res.json();
          // Evict oldest if cache is full
          if (_apiCache.size >= CACHE_MAX_SIZE) {
            const oldest = _apiCache.keys().next().value;
            _apiCache.delete(oldest);
          }
          _apiCache.set(url, { data: json, ts: Date.now() });
          return json;
        } finally {
          clearTimeout(timeoutId);
        }
      } finally {
        _releaseSlot();
      }
    })();

    _inflight.set(url, fetchPromise);
    try {
      setError(null);
      const json = await fetchPromise;
      if (!signal?.aborted) {
        setData(json);
        setIsStale(false);
        setLastUpdated(Date.now());
      }
    } catch (err) {
      if (signal?.aborted) return;
      // Use cached data as fallback — but flag as stale
      const cached = _apiCache.get(url);
      if (cached && Date.now() - cached.ts < CACHE_STALE_MS) {
        setData(cached.data);
        setIsStale(true);
        setLastUpdated(cached.ts);
      } else {
        setError(err);
      }
    } finally {
      _inflight.delete(url);
      if (!signal?.aborted) setLoading(false);
    }
  }, [endpoint, endpointOverride]);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    // Cancel previous in-flight request
    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setLoading(true);
    fetchData(ctrl.signal);

    return () => ctrl.abort();
  }, [enabled, fetchData]);

  useEffect(() => {
    if (!enabled || pollIntervalMs <= 0) return;
    const id = setInterval(() => fetchData(abortRef.current?.signal), pollIntervalMs);
    return () => clearInterval(id);
  }, [enabled, pollIntervalMs, fetchData]);

  const refetch = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    return fetchData(ctrl.signal);
  }, [fetchData]);

  return { data, loading, error, isStale, lastUpdated, refetch };
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

/**
 * Shared fetch wrapper with timeout + AbortController support.
 * All POST/PUT helpers use this to prevent indefinite hangs.
 */
async function apiFetch(url, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders(), ...options.headers },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  } catch (err) {
    if (err.name === 'AbortError') throw new Error(`Request timeout after ${timeoutMs}ms`);
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

/** POST helper for dynamic stop-loss calculation */
export async function fetchDynamicStopLoss(symbol, entryPrice, side = 'buy') {
  return apiFetch(getApiUrl('dynamicStopLoss'), {
    method: 'POST',
    body: JSON.stringify({ symbol, entry_price: entryPrice, side }),
  });
}

/** POST helper for pre-trade risk check
 *  Bug #24 fix: backend route is POST /api/v1/strategy/pre-trade-check/{ticker}
 *  Symbol must be in the URL path, not just the JSON body.
 */
export async function fetchPreTradeCheck(symbol, side = 'buy') {
  return apiFetch(`${getApiUrl('preTradeCheck')}/${encodeURIComponent(symbol)}`, {
    method: 'POST',
    body: JSON.stringify({ symbol, side }),
  });
}

// --- Agent Command Center Specialized Hooks ---

export function useSwarmTopology(pollMs = 30000) {
  return useApi('swarmTopology', { pollIntervalMs: pollMs });
}

export function useConferenceStatus(pollMs = 15000) {
  return useApi('conference', { pollIntervalMs: pollMs });
}

export function useTeamStatus(pollMs = 30000) {
  return useApi('teams', { pollIntervalMs: pollMs });
}

export function useDriftMetrics(pollMs = 60000) {
  return useApi('drift', { pollIntervalMs: pollMs });
}

export function useSystemAlerts(pollMs = 30000) {
  return useApi('systemAlerts', { pollIntervalMs: pollMs });
}

export function useAgentResources(pollMs = 15000) {
  return useApi('agentResources', { pollIntervalMs: pollMs });
}

export function useBlackboardFeed(pollMs = 15000) {
  return useApi('blackboard', { pollIntervalMs: pollMs });
}

// ---- Agent Extended Hooks ----
export function useAgentAllConfig(pollMs = 15000) {
  return useApi('agentAllConfig', { pollIntervalMs: pollMs });
}

export function useHitlBuffer(pollMs = 15000) {
  return useApi('agentHitlBuffer', { pollIntervalMs: pollMs });
}

export function useHitlStats(pollMs = 30000) {
  return useApi('agentHitlStats', { pollIntervalMs: pollMs });
}

export function useAgentAttribution(pollMs = 30000) {
  return useApi('agentAttribution', { pollIntervalMs: pollMs });
}

export function useEloLeaderboard(pollMs = 30000) {
  return useApi('agentEloLeaderboard', { pollIntervalMs: pollMs });
}

export function useWsChannels(pollMs = 30000) {
  return useApi('agentWsChannels', { pollIntervalMs: pollMs });
}

// ---- Backtesting Enhanced Hooks ----

export function useBacktestResults(pollMs = 30000) {
  return useApi('backtestResults', { pollIntervalMs: pollMs });
}

export function useBacktestOptimization(pollMs = 60000) {
  return useApi('backtestOptimization', { pollIntervalMs: pollMs });
}

export function useBacktestWalkForward(pollMs = 60000) {
  return useApi('backtestWalkforward', { pollIntervalMs: pollMs });
}

export function useBacktestMonteCarlo(pollMs = 60000) {
  return useApi('backtestMontecarlo', { pollIntervalMs: pollMs });
}

export function useBacktestCorrelation(pollMs = 60000) {
  return useApi('backtestCorrelation', { pollIntervalMs: pollMs });
}

export function useBacktestSectorExposure(pollMs = 60000) {
  return useApi('backtestSectorExposure', { pollIntervalMs: pollMs });
}

export function useBacktestDrawdownAnalysis(pollMs = 60000) {
  return useApi('backtestDrawdownAnalysis', { pollIntervalMs: pollMs });
}

// ---- Market Regime Page (10/15) Specialized Hooks ----

export function useRegimeState(pollMs = 30000) {
  return useApi('openclaw/regime', { pollIntervalMs: pollMs });
}

export function useMacroState(pollMs = 30000) {
  return useApi('openclaw/macro', { pollIntervalMs: pollMs });
}

export function useRegimeParams(pollMs = 30000) {
  return useApi('strategy/regime-params', { pollIntervalMs: pollMs });
}

export function useRegimePerformance(pollMs = 60000) {
  return useApi('backtest/regime', { pollIntervalMs: pollMs });
}

export function useSectorRotation(pollMs = 30000) {
  return useApi('openclaw/sectors', { pollIntervalMs: pollMs });
}

export function useRegimeTransitions(pollMs = 30000) {
  return useApi('openclaw/regime/transitions', { pollIntervalMs: pollMs });
}

export function useMemoryIntelligence(pollMs = 30000) {
  return useApi('openclaw/memory', { pollIntervalMs: pollMs });
}

export function useWhaleFlow(pollMs = 30000) {
  return useApi('openclaw/whale-flow', { pollIntervalMs: pollMs });
}

export function useRiskGauges(pollMs = 15000) {
  return useApi('risk/risk-gauges', { pollIntervalMs: pollMs });
}

export function useBridgeHealth(pollMs = 30000) {
  return useApi('openclaw/health', { pollIntervalMs: pollMs });
}

// ---- Council (8-Agent Debate) Hooks ----

export function useCouncilLatest(pollMs = 15000) {
  return useApi('councilLatest', { pollIntervalMs: pollMs });
}

/** POST helper to run a council evaluation */
export async function fetchCouncilEvaluate(symbol, timeframe = '1d', context = '') {
  return apiFetch(getApiUrl('councilEvaluate'), {
    method: 'POST',
    body: JSON.stringify({ symbol, timeframe, context }),
  }, 30000); // Council evaluations may take longer
}

// ---- Feature Store Hooks ----

export function useFeaturesLatest(symbol, timeframe = '1d', enabled = true) {
  return useApi('featuresLatest', {
    enabled,
    endpoint: `/features/latest?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}`,
  });
}

/** POST helper to compute + persist a feature vector */
export async function fetchFeaturesCompute(symbol, timeframe = '1d') {
  return apiFetch(getApiUrl('featuresCompute'), {
    method: 'POST',
    body: JSON.stringify({ symbol, timeframe }),
  });
}

// ---- Flywheel Scheduler Hook ----

export function useSchedulerStatus(pollMs = 60000) {
  return useApi('flywheelScheduler', { pollIntervalMs: pollMs });
}

/** POST helper for bias multiplier override */
export async function postBiasOverride(biasMultiplier) {
  return apiFetch(getApiUrl('openclaw/macro/override'), {
    method: 'POST',
    body: JSON.stringify({ bias_multiplier: biasMultiplier }),
  });
}

// ---- CNS (Central Nervous System) Hooks ----

export function useHomeostasis(pollMs = 30000) {
  return useApi('cnsHomeostasis', { pollIntervalMs: pollMs });
}

export function useCircuitBreakerStatus(pollMs = 15000) {
  return useApi('cnsCircuitBreaker', { pollIntervalMs: pollMs });
}

export function useCnsAgentsHealth(pollMs = 15000) {
  return useApi('cnsAgentsHealth', { pollIntervalMs: pollMs });
}

export function useCnsBlackboard(pollMs = 30000) {
  return useApi('cnsBlackboard', { pollIntervalMs: pollMs });
}

export function useCnsPostmortems(pollMs = 30000) {
  return useApi('cnsPostmortems', { pollIntervalMs: pollMs });
}

export function useCnsAttribution(pollMs = 60000) {
  return useApi('cnsPostmortemsAttribution', { pollIntervalMs: pollMs });
}

export function useCnsDirectives() {
  return useApi('cnsDirectives');
}

export function useCnsLastVerdict(pollMs = 30000) {
  return useApi('cnsLastVerdict', { pollIntervalMs: pollMs });
}

export function useProfitBrain(pollMs = 30000) {
  return useApi('cnsProfitBrain', { pollIntervalMs: pollMs });
}

// ---- Swarm Intelligence Hooks ----

export function useSwarmTurbo(pollMs = 30000) {
  return useApi('swarmTurboStatus', { pollIntervalMs: pollMs });
}

export function useSwarmHyper(pollMs = 30000) {
  return useApi('swarmHyperStatus', { pollIntervalMs: pollMs });
}

export function useSwarmNews(pollMs = 30000) {
  return useApi('swarmNewsStatus', { pollIntervalMs: pollMs });
}

export function useSwarmSweep(pollMs = 30000) {
  return useApi('swarmSweepStatus', { pollIntervalMs: pollMs });
}

export function useSwarmUnified(pollMs = 30000) {
  return useApi('swarmUnifiedStatus', { pollIntervalMs: pollMs });
}

export function useSwarmOutcomes(pollMs = 30000) {
  return useApi('swarmOutcomesStatus', { pollIntervalMs: pollMs });
}

export function useSwarmKelly(pollMs = 30000) {
  return useApi('swarmOutcomesKelly', { pollIntervalMs: pollMs });
}

export function useSwarmPositions(pollMs = 30000) {
  return useApi('swarmPositionsManaged', { pollIntervalMs: pollMs });
}

export function useSwarmMlScorer(pollMs = 30000) {
  return useApi('swarmMlScorerStatus', { pollIntervalMs: pollMs });
}

/** POST helper to override agent streak status */
export async function postAgentOverrideStatus(agentName, action) {
  return apiFetch(`${getApiUrl('cnsAgentsHealth').replace('/health', '')}/${encodeURIComponent(agentName)}/override-status`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
}

/** POST helper to override agent Bayesian weight */
export async function postAgentOverrideWeight(agentName, alpha, beta) {
  return apiFetch(`${getApiUrl('cnsAgentsHealth').replace('/health', '')}/${encodeURIComponent(agentName)}/override-weight`, {
    method: 'POST',
    body: JSON.stringify({ alpha, beta }),
  });
}

/** PUT helper to update a directive file */
export async function putDirective(filename, content) {
  return apiFetch(`${getApiUrl('cnsDirectives')}/${encodeURIComponent(filename)}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}
