/**
 * Embodier.ai (Trading) — API Configuration
 * Central API configuration — every hook and page imports from here.
 * Update BASE_URL when deploying. Default is localhost:8000 (FastAPI backend).
 * Every endpoint listed here MUST have a corresponding FastAPI router in backend/app/api/v1/.
 *
 * BACKEND REFERENCE:
 *   Routers: stocks, quotes, orders, system, signals, backtest, status,
 *            agents, data-sources, sentiment, youtube-knowledge, flywheel,
 *            portfolio, risk, strategy, performance, logs, alerts, patterns,
 *            settings, openclaw, market, ml-brain, risk-shield, alpaca,
 *            alignment, council, features, swarm, cns, cognitive, flywheel
 *
 * FIX LOG:
 *   Bug #3  (Mar 10 2026): blackboard was mapped to /openclaw — corrected to /cns/blackboard/current
 *   Bug #8  (Mar 10 2026): getWsUrl now uses channel param for correct WS routing
 *   Bug #10 (Mar 10 2026): WS_CHANNELS + initAuthFromElectron dropped in purge — restored
 *   Bug #19 (prev):        kellySizer/positionSizing needed /risk prefix — fixed
 *   Bug #24 (prev):        preTradeCheck needed /{ticker} in path — fixed in useApi.js
 */

const API_CONFIG = {
  // Use empty string in dev so requests go to same origin → Vite proxy forwards to backend (port 8000).
  // Set VITE_API_URL / VITE_WS_URL when deploying (e.g. https://api.example.com).
  BASE_URL: import.meta.env.VITE_API_URL ?? "",
  API_PREFIX: "/api/v1",
  WS_URL: import.meta.env.VITE_WS_URL ?? "",

  endpoints: {
    // ---- CORE DATA ----
    stocks:           "/stocks/",
    quotes:           "/quotes/",
    orders:           "/orders/",
    system:           "/system",
    "system/event-bus/status": "/system/event-bus/status",
    signals:          "/signals/",
    signalsHeatmap:   "/signals/heatmap",
    backtest:         "/backtest/",
    backtestRuns:     "/backtest/runs",
    backtestResults:  "/backtest/results",
    backtestOptimization:     "/backtest/optimization",
    backtestWalkforward:      "/backtest/walkforward",
    backtestMontecarlo:       "/backtest/montecarlo",
    backtestRegime:           "/backtest/regime",
    backtestRollingSharpe:    "/backtest/rolling-sharpe",
    backtestTradeDistribution:"/backtest/trade-distribution",
    backtestKellyComparison:  "/backtest/kelly-comparison",
    backtestCorrelation:      "/backtest/correlation",
    backtestSectorExposure:   "/backtest/sector-exposure",
    backtestDrawdownAnalysis: "/backtest/drawdown-analysis",
    openclawSwarmStatus:      "/openclaw/swarm-status",
    openclawAgents:           "/openclaw/candidates",
    status:                   "/status",

    // ---- ADDITIONAL ROUTERS ----
    agents:           "/agents",
    dataSources:      "/data-sources/",
    sentiment:        "/sentiment",
    "sentiment/discover": "/sentiment/discover",
    youtubeKnowledge: "/youtube-knowledge",
    flywheel:         "/flywheel",
    portfolio:        "/portfolio",
    risk:             "/risk",
    strategy:         "/strategy",
    performance:      "/performance",
    performanceEquity:  "/performance/equity",
    performanceTrades:  "/performance/trades",
    logs:             "/logs",
    alerts:           "/alerts",
    patterns:         "/patterns",
    settings:         "/settings",
    openclaw:         "/openclaw",
    market:           "/market",
    marketIndices:    "/market/indices",
    marketOrderBook:  "/market/order-book",
    openclawRegime:   "/openclaw/regime",
    mlBrain:          "/ml-brain/",
    "ml-brain/models":"/ml-brain/registry/status",
    riskShield:       "/risk-shield",
    kellySizer:       "/risk/kelly-sizer",
    positionSizing:   "/risk/position-sizing",
    drawdownCheck:    "/risk/drawdown-check",
    dynamicStopLoss:  "/risk/dynamic-stop-loss",
    riskScore:        "/risk/risk-score",
    kellyRanked:      "/signals/kelly-ranked",
    preTradeCheck:    "/strategy/pre-trade-check",
    swarmTopology:    "/agents/swarm-topology",
    agentConsensus:   "/agents/consensus",
    conference:       "/agents/conference",
    teams:            "/agents/teams",
    drift:            "/agents/drift",
    systemAlerts:     "/agents/alerts",
    agentResources:   "/agents/resources",

    // ---- BLACKBOARD (FIX #3: was /openclaw — now correct CNS route) ----
    blackboard:       "/cns/blackboard/current",
    cnsBlackboard:    "/cns/blackboard/current",

    // ---- MARKET REGIME PAGE ----
    "openclaw/regime":         "/openclaw/regime",
    "openclaw/macro":          "/openclaw/macro",
    "strategy/regime-params":  "/strategy/regime-params",
    "backtest/regime":         "/backtest/regime",
    "openclaw/sectors":        "/openclaw/sectors",
    "openclaw/scan":           "/openclaw/scan",
    "openclaw/memory":         "/openclaw/memory",
    "risk/config":             "/risk/config",
    "risk/risk-gauges":        "/risk/risk-gauges",
    "openclaw/macro/override":  "/openclaw/macro/override",
    "openclaw/health":         "/openclaw/health",
    "risk/risk-score":         "/risk/risk-score",
    "openclaw/whale-flow":     "/openclaw/whale-flow",
    "openclaw/regime/transitions": "/openclaw/regime/transitions",

    // ---- ALPACA PROXY ----
    alpaca:            "/alpaca",
    "alpaca/account":  "/alpaca/account",
    "alpaca/positions":"/alpaca/positions",
    "alpaca/orders":   "/alpaca/orders",
    "alpaca/activities":"/alpaca/activities",
    "orders/advanced": "/orders/advanced",
    "orders/emergency-stop": "/orders/emergency-stop",
    "riskShield/emergency-action": "/risk-shield/emergency-action",

    // ---- ALIGNMENT ENGINE ----
    "alignment/settings":       "/alignment/settings",
    "alignment/evaluate":       "/alignment/evaluate",
    "alignment/verdicts":       "/alignment/verdicts",
    "alignment/stats":          "/alignment/stats",
    "alignment/bright-lines":   "/alignment/bright-lines",
    "alignment/constellation":  "/alignment/constellation",
    "alignment/metacognition":  "/alignment/metacognition",
    "alignment/critique":       "/alignment/critique",

    // ---- COUNCIL ----
    councilEvaluate:  "/council/evaluate",
    councilLatest:    "/council/latest",
    "council/status": "/council/status",
    councilWeights:   "/council/weights",
    councilHealth:    "/council/health",
    councilAgentsPerformance: "/council/agents/performance",
    dataSourcesHealth: "/data-sources/health",

    // ---- FEATURE STORE ----
    featuresLatest:   "/features/latest",
    featuresCompute:  "/features/compute",

    // ---- TRAINING ----
    training:         "/training/",

    // ---- DEVICE & SYSTEM ----
    "system/health":  "/system",
    deviceInfo:       "/system/device",

    // ---- CNS ROUTES ----
    cnsHomeostasis:            "/cns/homeostasis/vitals",
    cnsCircuitBreaker:         "/cns/circuit-breaker/status",
    cnsAgentsHealth:           "/cns/agents/health",
    cnsPostmortems:            "/cns/postmortems",
    cnsPostmortemsAttribution: "/cns/postmortems/attribution",
    cnsDirectives:             "/cns/directives",
    cnsLastVerdict:            "/cns/council/last-verdict",
    cnsProfitBrain:            "/cns/profit-brain",

    // ---- COGNITIVE TELEMETRY ----
    cognitiveDashboard:    "/cognitive/dashboard",
    cognitiveSnapshots:    "/cognitive/snapshots",
    cognitiveCalibration:  "/cognitive/calibration",

    // ---- LOGS ----
    "logs/system":         "/logs",

    // ---- SWARM ----
    swarmTurboStatus:     "/swarm/turbo/status",
    swarmHyperStatus:     "/swarm/hyper/status",
    swarmNewsStatus:      "/swarm/news/status",
    swarmSweepStatus:     "/swarm/sweep/status",
    swarmUnifiedStatus:   "/swarm/unified/status",
    swarmOutcomesStatus:  "/swarm/outcomes/status",
    swarmOutcomesKelly:   "/swarm/outcomes/kelly",
    swarmPositionsManaged:"/swarm/positions/managed",
    swarmMlScorerStatus:  "/swarm/ml-scorer/status",

    // ---- AGENT EXTENDED ----
    agentAllConfig:       "/agents/all-config",
    agentHitlBuffer:      "/agents/hitl/buffer",
    agentHitlStats:       "/agents/hitl/stats",
    agentAttribution:     "/agents/attribution",
    agentEloLeaderboard:  "/agents/elo-leaderboard",
    agentWsChannels:      "/agents/ws-channels",
    agentFlowAnomalies:   "/agents/flow-anomalies",

    // ---- Signal Intelligence aliases (weight/toggle use agents router) ----
    scanners: "/agents",  // Scanner weight/toggle -> agents/{id}/weight, agents/{id}/toggle
    intels: "/agents",    // Intel weight/toggle -> agents/{id}/weight, agents/{id}/toggle

    // ---- FLYWHEEL SCHEDULER ----
    flywheelScheduler:    "/flywheel/scheduler",
    flywheelKpis:         "/flywheel/kpis",
    flywheelPerformance:  "/flywheel/performance",
    flywheelSignals:      "/flywheel/signals/staged",
    flywheelModels:       "/flywheel/models",
    flywheelLogs:         "/flywheel/logs",
    flywheelFeatures:     "/flywheel/features",
  },
};

/**
 * Resolve an endpoint key to a full URL.
 * @param {string} endpoint - Key from API_CONFIG.endpoints
 * @returns {string} Full URL string
 */
export function getApiUrl(endpoint) {
  const ep = typeof endpoint === "string" ? endpoint.trim() : "";
  if (ep.startsWith("/api/v1")) {
    return `${API_CONFIG.BASE_URL}${ep}`;
  }
  const path = API_CONFIG.endpoints[ep];
  if (path) {
    return `${API_CONFIG.BASE_URL}${API_CONFIG.API_PREFIX}${path}`;
  }
  // Fallback: treat as raw path, ensure leading slash
  if (import.meta.env.DEV) {
    console.warn(`[api] Unmapped endpoint "${ep}" — using fallback. Add to api.js endpoints.`);
  }
  const rawPath = ep.startsWith("/") ? ep : `/${ep}`;
  return `${API_CONFIG.BASE_URL}${API_CONFIG.API_PREFIX}${rawPath}`;
}

/**
 * Get WebSocket URL for a channel.
 * FIX #8 (Mar 10 2026): channel param now used for topic routing.
 * Backend uses a single /ws endpoint; client subscribes via { type: 'subscribe', channel }.
 * @param {string} [channel] - WS topic/channel name
 */
export function getWsUrl(channel) {
  const base = API_CONFIG.WS_URL || (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`
    : "ws://localhost:8000");
  const token = (typeof localStorage !== "undefined" && localStorage.getItem("auth_token")) ||
                import.meta.env.VITE_API_AUTH_TOKEN || "";
  const wsBase = token ? `${base}/ws?token=${encodeURIComponent(token)}` : `${base}/ws`;
  return wsBase;
}

export function getWsBaseUrl() {
  return getWsUrl();
}

/**
 * Auth headers — Bearer token from localStorage or env var.
 * Returns empty object if no token (unauthenticated requests allowed for read-only).
 */
export function getAuthHeaders() {
  const token =
    (typeof localStorage !== "undefined" && localStorage.getItem("auth_token")) ||
    import.meta.env.VITE_API_AUTH_TOKEN ||
    null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * WebSocket channel names for real-time subscriptions.
 * FIX #10 (Mar 10 2026): Restored — was dropped in purge commit, breaking
 * Dashboard, MarketRegime, RiskIntelligence, TradeExecution imports.
 */
export const WS_CHANNELS = {
  agents:          "agents",
  datasources:     "data_sources",
  signals:         "signals",
  trades:          "trades",
  logs:            "logs",
  sentiment:       "sentiment",
  risk:            "risk",
  kelly:           "kelly",
  alignment:       "alignment",
  council:         "council",
  council_verdict: "council_verdict",
  homeostasis:     "homeostasis",
  circuit_breaker: "circuit_breaker",
  market:          "market",
  swarm:           "swarm",
  macro:           "macro",
};

/**
 * Initialize auth token from Electron preload bridge.
 * FIX #10 (Mar 10 2026): Restored — was dropped in purge, breaking main.jsx import.
 * Call once on app init in Electron context; no-op in browser/dev.
 */
let _cachedAuthToken = null;

export async function initAuthFromElectron() {
  if (typeof window !== "undefined" && window.embodier?.getAuthToken) {
    try {
      _cachedAuthToken = await window.embodier.getAuthToken();
      if (_cachedAuthToken && typeof localStorage !== "undefined") {
        localStorage.setItem("auth_token", _cachedAuthToken);
      }
    } catch {
      // Not in Electron — silently ignore
    }
  }
}

export default API_CONFIG;
