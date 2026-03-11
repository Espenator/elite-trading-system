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

    // ---- FEATURE STORE ----
    featuresLatest:   "/features/latest",
    featuresCompute:  "/features/compute",

    // ---- TRAINING ----
    training:         "/training/",

    // ---- DEVICE & SYSTEM ----
    "system/health":  "/system",

    // ---- CNS ROUTES ----
    cnsHomeostasis:            "/cns/homeostasis",
    cnsCircuitBreaker:         "/cns/circuit-breaker",
    cnsAgentsHealth:           "/cns/agents/health",
    cnsPostmortems:            "/cns/postmortems",
    cnsPostmortemsAttribution: "/cns/postmortems/attribution",
    cnsDirectives:             "/cns/directives",
    cnsLastVerdict:            "/cns/last-verdict",
    cnsProfitBrain:            "/cns/profit-brain",

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

    // ---- FLYWHEEL SCHEDULER ----
    flywheelScheduler:    "/flywheel/scheduler",
  },
};

/** WebSocket channel names for ws.on(channel, handler) — must match backend WS topics */
export const WS_CHANNELS = {
  market: "market",
  signals: "signals",
  risk: "risk",
  trades: "trades",
  council_verdict: "council_verdict",
  macro: "macro",
};

/**
 * Load auth token from Electron preload bridge when running in desktop app.
 * No-op in browser; in Electron, preload can expose getAuthToken() and we set localStorage.
 */
export function initAuthFromElectron() {
  if (typeof window === "undefined") return;
  try {
    const token = window.electronAPI?.getAuthToken?.();
    if (token) localStorage.setItem("auth_token", token);
  } catch (_) {}
}

/**
 * Resolve an endpoint key to a full URL.
 * @param {string} endpoint - Key from API_CONFIG.endpoints
 * @returns {string} Full URL string
 */
export function getApiUrl(endpoint) {
  const path = API_CONFIG.endpoints[endpoint];
  if (!path) return null;
  return `${API_CONFIG.BASE_URL}${API_CONFIG.API_PREFIX}${path}`;
}

/**
 * Get WebSocket base URL.
 * FIX #8 (Mar 10 2026): channel param now used for topic routing.
 * @param {string} [channel] - WS topic/channel name
 */
export function getWsUrl(channel) {
  const base = API_CONFIG.WS_URL || (typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    : 'ws://localhost:8000');
  return channel ? `${base}/ws/${channel}` : `${base}/ws`;
}

export function getWsBaseUrl() {
  return getWsUrl();
}

/**
 * Auth headers — Bearer token from localStorage.
 * Returns empty object if no token (unauthenticated requests allowed for read-only).
 */
export function getAuthHeaders() {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('auth_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default API_CONFIG;
