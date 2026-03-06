/**
 * Generic fetch hook for API calls.
 * Uses config/api.js getApiUrl(endpoint).
 * Optional polling when pollIntervalMs > 0.
 */
import { useState, useEffect, useCallback } from "react";
import { getApiUrl, getAuthHeaders } from "../config/api";

// Simple in-memory cache for API responses (stale-while-revalidate)
const _apiCache = new Map();

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
        setData(json);
        setError(null);
        return;
      } catch (err) {
        // fall through to cache check below
      } finally {
        setLoading(false);
      }
    }

    const fetchPromise = (async () => {
      await _acquireSlot();
      try {
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const json = await res.json();
        _apiCache.set(url, { data: json, ts: Date.now() });
        return json;
      } finally {
        _releaseSlot();
      }
    })();

    _inflight.set(url, fetchPromise);
    try {
      setError(null);
      const json = await fetchPromise;
      setData(json);
    } catch (err) {
      // Use cached data as fallback
      const cached = _apiCache.get(url);
      if (cached && Date.now() - cached.ts < 300000) {
        setData(cached.data);
      } else {
        setError(err);
      }
    } finally {
      _inflight.delete(url);
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
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ symbol, entry_price: entryPrice, side }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** POST helper for pre-trade risk check
 *  Bug #24 fix: backend route is POST /api/v1/strategy/pre-trade-check/{ticker}
 *  Symbol must be in the URL path, not just the JSON body.
 */
export async function fetchPreTradeCheck(symbol, side = 'buy') {
  const url = `${getApiUrl('preTradeCheck')}/${encodeURIComponent(symbol)}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ symbol, side }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
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

export function useSystemAlerts(pollMs = 10000) {
  return useApi('systemAlerts', { pollIntervalMs: pollMs });
}

export function useAgentResources(pollMs = 15000) {
  return useApi('agentResources', { pollIntervalMs: pollMs });
}

export function useBlackboardFeed(pollMs = 5000) {
  return useApi('blackboard', { pollIntervalMs: pollMs });
}

// ---- Agent Extended Hooks ----
export function useAgentAllConfig(pollMs = 15000) {
  return useApi('agentAllConfig', { pollIntervalMs: pollMs });
}

export function useHitlBuffer(pollMs = 5000) {
  return useApi('agentHitlBuffer', { pollIntervalMs: pollMs });
}

export function useHitlStats(pollMs = 10000) {
  return useApi('agentHitlStats', { pollIntervalMs: pollMs });
}

export function useAgentAttribution(pollMs = 30000) {
  return useApi('agentAttribution', { pollIntervalMs: pollMs });
}

export function useEloLeaderboard(pollMs = 30000) {
  return useApi('agentEloLeaderboard', { pollIntervalMs: pollMs });
}

export function useWsChannels(pollMs = 10000) {
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

export function useRegimeState(pollMs = 10000) {
  return useApi('openclaw/regime', { pollIntervalMs: pollMs });
}

export function useMacroState(pollMs = 10000) {
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

export function useWhaleFlow(pollMs = 20000) {
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
  const url = getApiUrl('councilEvaluate');
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ symbol, timeframe, context }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
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
  const url = getApiUrl('featuresCompute');
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ symbol, timeframe }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- Flywheel Scheduler Hook ----

export function useSchedulerStatus(pollMs = 60000) {
  return useApi('flywheelScheduler', { pollIntervalMs: pollMs });
}

/** POST helper for bias multiplier override */
export async function postBiasOverride(biasMultiplier) {
  const url = getApiUrl('openclaw/macro/override');
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ bias_multiplier: biasMultiplier }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ---- CNS (Central Nervous System) Hooks ----

export function useHomeostasis(pollMs = 10000) {
  return useApi('cnsHomeostasis', { pollIntervalMs: pollMs });
}

export function useCircuitBreakerStatus(pollMs = 15000) {
  return useApi('cnsCircuitBreaker', { pollIntervalMs: pollMs });
}

export function useCnsAgentsHealth(pollMs = 15000) {
  return useApi('cnsAgentsHealth', { pollIntervalMs: pollMs });
}

export function useCnsBlackboard(pollMs = 10000) {
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

export function useCnsLastVerdict(pollMs = 10000) {
  return useApi('cnsLastVerdict', { pollIntervalMs: pollMs });
}

export function useProfitBrain(pollMs = 10000) {
  return useApi('cnsProfitBrain', { pollIntervalMs: pollMs });
}

// ---- Swarm Intelligence Hooks ----

export function useSwarmTurbo(pollMs = 10000) {
  return useApi('swarmTurboStatus', { pollIntervalMs: pollMs });
}

export function useSwarmHyper(pollMs = 10000) {
  return useApi('swarmHyperStatus', { pollIntervalMs: pollMs });
}

export function useSwarmNews(pollMs = 10000) {
  return useApi('swarmNewsStatus', { pollIntervalMs: pollMs });
}

export function useSwarmSweep(pollMs = 10000) {
  return useApi('swarmSweepStatus', { pollIntervalMs: pollMs });
}

export function useSwarmUnified(pollMs = 10000) {
  return useApi('swarmUnifiedStatus', { pollIntervalMs: pollMs });
}

export function useSwarmOutcomes(pollMs = 10000) {
  return useApi('swarmOutcomesStatus', { pollIntervalMs: pollMs });
}

export function useSwarmKelly(pollMs = 10000) {
  return useApi('swarmOutcomesKelly', { pollIntervalMs: pollMs });
}

export function useSwarmPositions(pollMs = 10000) {
  return useApi('swarmPositionsManaged', { pollIntervalMs: pollMs });
}

export function useSwarmMlScorer(pollMs = 10000) {
  return useApi('swarmMlScorerStatus', { pollIntervalMs: pollMs });
}

/** POST helper to override agent streak status */
export async function postAgentOverrideStatus(agentName, action) {
  const url = `${getApiUrl('cnsAgentsHealth').replace('/health', '')}/${encodeURIComponent(agentName)}/override-status`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** POST helper to override agent Bayesian weight */
export async function postAgentOverrideWeight(agentName, alpha, beta) {
  const url = `${getApiUrl('cnsAgentsHealth').replace('/health', '')}/${encodeURIComponent(agentName)}/override-weight`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ alpha, beta }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** PUT helper to update a directive file */
export async function putDirective(filename, content) {
  const url = `${getApiUrl('cnsDirectives')}/${encodeURIComponent(filename)}`;
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
