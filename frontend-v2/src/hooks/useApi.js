/**
 * Generic fetch hook for API calls.
 * Uses config/api.js getApiUrl(endpoint).
 * Optional polling when pollIntervalMs > 0.
 *
 * FIX LOG (Mar 10 2026):
 *  - AbortSignal.any fallback was dropping user abort signal (memory leaks on unmount)
 *    Fixed: user signal + timeout signal now combined via addEventListener
 *  - Added page visibility pause: polling stops when tab is hidden, resumes when visible
 *  - Reduced aggressive polling intervals (5-10s → 15-30s)
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { getApiUrl, getAuthHeaders } from "../config/api";

const DEFAULT_TIMEOUT_MS = 15000;
// healthz uses extended timeout — backend event loop can be busy (scouts, streams) causing 15–25s latency
const HEALTHZ_TIMEOUT_MS = 25000;

// Simple in-memory cache (stale-while-revalidate)
const _apiCache = new Map();
const CACHE_MAX_SIZE = 200;
const CACHE_STALE_MS = 300000; // 5 min

// Global concurrency limiter — prevents browser connection exhaustion
let _activeRequests = 0;
const MAX_CONCURRENT = 6;
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

// Per-URL in-flight deduplication + short-lived result cache (2s window)
// _inflight: URL -> Promise (for concurrent in-flight requests)
// _fetchCache: URL -> { promise, timestamp } (for near-simultaneous requests within DEDUP_WINDOW_MS)
const _inflight = new Map();
const _fetchCache = new Map();
const DEDUP_WINDOW_MS = 2000;

/**
 * Combine two AbortSignals without requiring AbortSignal.any (ES2023+).
 * Works in all browsers including older Electron Chromium builds.
 * Returns a new AbortController that aborts when EITHER input signal aborts.
 */
function _combineSignals(sig1, sig2) {
  const ctrl = new AbortController();
  const abort = () => ctrl.abort();
  if (sig1) sig1.addEventListener('abort', abort, { once: true });
  if (sig2) sig2.addEventListener('abort', abort, { once: true });
  // Abort immediately if either is already aborted
  if (sig1?.aborted || sig2?.aborted) ctrl.abort();
  return ctrl;
}

/**
 * @param {string} endpoint - Key from api.js endpoints (e.g. 'agents', 'dataSources')
 * @param {{ pollIntervalMs?: number, enabled?: boolean, endpoint?: string, timeoutMs?: number }} options
 */
export function useApi(endpoint, options = {}) {
  const {
    pollIntervalMs = 0,
    enabled = true,
    endpoint: endpointOverride,
    timeoutMs = null,
  } = options;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const [isStale, setIsStale] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const abortRef = useRef(null);
  // Track whether the tab is visible — pause polling when hidden
  const visibleRef = useRef(!document.hidden);

  // Page visibility listener — pause/resume polling
  useEffect(() => {
    const handleVisibility = () => {
      visibleRef.current = !document.hidden;
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);

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

    // Deduplicate: if same URL was fetched within DEDUP_WINDOW_MS, reuse result
    const cached = _fetchCache.get(url);
    if (cached && Date.now() - cached.timestamp < DEDUP_WINDOW_MS) {
      try {
        const json = await cached.promise;
        if (!signal?.aborted) {
          setData(json);
          setError(null);
          setIsStale(false);
          setLastUpdated(Date.now());
        }
        return;
      } catch {
        if (signal?.aborted) return;
        // Cache entry failed — fall through to fresh fetch
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
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
      } catch {
        if (signal?.aborted) return;
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    }

    const fetchPromise = (async () => {
      await _acquireSlot();
      try {
        const MAX_RETRIES = 3;
        const effectiveTimeout = timeoutMs ?? (endpoint === "healthz" ? HEALTHZ_TIMEOUT_MS : DEFAULT_TIMEOUT_MS);
        for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
          const timeoutCtrl = new AbortController();
          const timeoutId = setTimeout(() => timeoutCtrl.abort(), effectiveTimeout);
          const combinedCtrl = _combineSignals(signal, timeoutCtrl.signal);

          try {
            const res = await fetch(url, {
              cache: "no-store",
              headers: getAuthHeaders(),
              signal: combinedCtrl.signal,
            });
            // Retry on 503 Service Unavailable with exponential backoff
            if (res.status === 503 && attempt < MAX_RETRIES) {
              clearTimeout(timeoutId);
              await new Promise((r) => setTimeout(r, 1000 * Math.pow(2, attempt)));
              continue;
            }
            if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            const json = await res.json();
            if (_apiCache.size >= CACHE_MAX_SIZE) {
              const oldest = _apiCache.keys().next().value;
              _apiCache.delete(oldest);
            }
            _apiCache.set(url, { data: json, ts: Date.now() });
            return json;
          } finally {
            clearTimeout(timeoutId);
          }
        }
      } finally {
        _releaseSlot();
      }
    })();

    _inflight.set(url, fetchPromise);
    // Store in dedup cache so near-simultaneous requests share this result
    _fetchCache.set(url, { promise: fetchPromise, timestamp: Date.now() });
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
      const staleCached = _apiCache.get(url);
      if (staleCached && Date.now() - staleCached.ts < CACHE_STALE_MS) {
        setData(staleCached.data);
        setIsStale(true);
        setLastUpdated(staleCached.ts);
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
    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setLoading(true);
    fetchData(ctrl.signal);
    return () => ctrl.abort();
  }, [enabled, fetchData]);

  // Polling with visibility pause — skips tick when tab is hidden
  useEffect(() => {
    if (!enabled || pollIntervalMs <= 0) return;
    const id = setInterval(() => {
      if (!visibleRef.current) return; // FIX: pause when tab hidden
      fetchData(abortRef.current?.signal);
    }, pollIntervalMs);
    return () => clearInterval(id);
  }, [enabled, pollIntervalMs, fetchData]);

  // 24/7 recovery: when API was down (error set) and we use polling, retry every 5s until back up
  const RECOVERY_RETRY_MS = 5000;
  useEffect(() => {
    if (!enabled || !error || pollIntervalMs <= 0) return;
    const id = setInterval(() => {
      if (!visibleRef.current) return;
      fetchData(abortRef.current?.signal);
    }, RECOVERY_RETRY_MS);
    return () => clearInterval(id);
  }, [enabled, error, pollIntervalMs, fetchData]);

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

export async function fetchDynamicStopLoss(symbol, entryPrice, side = 'buy') {
  return apiFetch(getApiUrl('dynamicStopLoss'), {
    method: 'POST',
    body: JSON.stringify({ symbol, entry_price: entryPrice, side }),
  });
}

/**
 * Pre-trade risk check.
 * Backend route: POST /api/v1/strategy/pre-trade-check/{ticker}
 */
export async function fetchPreTradeCheck(symbol, side = 'buy') {
  return apiFetch(`${getApiUrl('preTradeCheck')}/${encodeURIComponent(symbol)}`, {
    method: 'POST',
    body: JSON.stringify({ symbol, side }),
  });
}

// --- Agent Command Center Hooks ---

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
  // FIX #3: was 'blackboard' → '/openclaw'. Now correctly hits /cns/blackboard/current
  return useApi('cnsBlackboard', { pollIntervalMs: pollMs });
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

// ---- Backtesting Hooks ----

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

// ---- Market Regime Hooks ----

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

// ---- Council Hooks ----

export function useCouncilLatest(pollMs = 15000) {
  return useApi('councilLatest', { pollIntervalMs: pollMs });
}

export async function fetchCouncilEvaluate(symbol, timeframe = '1d', context = '') {
  return apiFetch(getApiUrl('councilEvaluate'), {
    method: 'POST',
    body: JSON.stringify({ symbol, timeframe, context }),
  }, 30000);
}

// ---- Feature Store Hooks ----

export function useFeaturesLatest(symbol, timeframe = '1d', enabled = true) {
  return useApi('featuresLatest', {
    enabled,
    endpoint: `/features/latest?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}`,
  });
}

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

export async function postBiasOverride(biasMultiplier) {
  return apiFetch(getApiUrl('openclaw/macro/override'), {
    method: 'POST',
    body: JSON.stringify({ bias_multiplier: biasMultiplier }),
  });
}

// ---- CNS Hooks ----

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

// ---- Swarm Hooks ----

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

export async function postAgentOverrideStatus(agentName, action) {
  return apiFetch(`${getApiUrl('cnsAgentsHealth').replace('/health', '')}/${encodeURIComponent(agentName)}/override-status`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  });
}

export async function postAgentOverrideWeight(agentName, alpha, beta) {
  return apiFetch(`${getApiUrl('cnsAgentsHealth').replace('/health', '')}/${encodeURIComponent(agentName)}/override-weight`, {
    method: 'POST',
    body: JSON.stringify({ alpha, beta }),
  });
}

export async function putDirective(filename, content) {
  return apiFetch(`${getApiUrl('cnsDirectives')}/${encodeURIComponent(filename)}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}
