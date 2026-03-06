/**
 * Embodier.ai (Trading) - API Configuration
 * Branch: v2-15-feb-espen-embodier-ai
 *
 * OLEH: This is the foundation file. Every hook and page imports from here.
 * OLEH: Update BASE_URL when deploying. Default is localhost:8000 (our FastAPI backend).
 * OLEH: Every endpoint listed here MUST have a corresponding FastAPI router in backend/app/api/v1/
 * OLEH: If an endpoint doesn't exist yet in backend, create the router file first.
 *
 * BACKEND REFERENCE:
 *   Existing routers: stocks, quotes, orders, system, training, signals, backtest, status
 *   NEW routers needed: agents, data-sources, sentiment, youtube-knowledge, flywheel,
 *                       portfolio, risk, strategy, performance, logs, alerts
 */
const API_CONFIG = {
  // Use empty string in dev so requests go to same origin → Vite proxy forwards to backend (port 8000).
  // Set VITE_API_URL / VITE_WS_URL when deploying (e.g. https://api.example.com).
  BASE_URL: import.meta.env.VITE_API_URL ?? "",
  API_PREFIX: "/api/v1",
  WS_URL: import.meta.env.VITE_WS_URL ?? "",

  // Every endpoint maps to a backend FastAPI router
  // Format: frontend_key -> backend_route_path
  endpoints: {
    // ---- EXISTING (already in backend/app/api/v1/) ----
    stocks: "/stocks", // Stock universe data
    quotes: "/quotes", // Real-time price quotes
    orders: "/orders", // Order execution (Alpaca)
    system: "/system", // System status + config
    "system/event-bus/status": "/system/event-bus/status", // Event-bus topics for Agent Command Center
    signals: "/signals/", // Generated trading signals (trailing slash required by FastAPI)
    backtest: "/backtest", // Backtesting engine
    backtestRuns: "/backtest/runs", // Recent backtest runs (for Backtesting page)
        backtestResults: "/backtest/results", // Full backtest results + equity curve
    backtestOptimization: "/backtest/optimization", // Parameter optimization heatmap
    backtestWalkforward: "/backtest/walkforward", // Walk-forward validation periods
    backtestMontecarlo: "/backtest/montecarlo", // Monte Carlo simulation paths
    backtestRegime: "/backtest/regime", // Regime-based performance breakdown
    backtestRollingSharpe: "/backtest/rolling-sharpe", // Rolling Sharpe ratio series
    backtestTradeDistribution: "/backtest/trade-distribution", // P&L distribution histogram
    backtestKellyComparison: "/backtest/kelly-comparison", // Kelly A/B sizing comparison
    backtestCorrelation: "/backtest/correlation", // Asset correlation matrix
    backtestSectorExposure: "/backtest/sector-exposure", // Sector allocation breakdown
    backtestDrawdownAnalysis: "/backtest/drawdown-analysis", // Drawdown period analysis
    openclawSwarmStatus: "/openclaw/swarm-status", // Swarm intelligence metrics
    openclawAgents: "/openclaw/candidates", // Individual agent status + tasks
    status: "/status", // System health check

    // ---- NEW (Oleh needs to create these routers) ----
    agents: "/agents", // Agent control: start/stop/pause/config
    dataSources: "/data-sources/", // Health of all 10 data feeds (trailing slash required by FastAPI)
    sentiment: "/sentiment", // Aggregated sentiment from 4 sources
    youtubeKnowledge: "/youtube-knowledge", // YouTube transcript ingestion
    flywheel: "/flywheel", // ML flywheel metrics + accuracy over time
    portfolio: "/portfolio", // Current positions + P&L
    risk: "/risk", // Risk metrics + position sizing
    strategy: "/strategy", // Active strategies + A/B tests
    performance: "/performance", // Historical performance analytics
    performanceTrades: "/performance/trades", // Realized trades for P&L dist / monthly win rate
    logs: "/logs", // System activity logs
    alerts: "/alerts", // Alert rules + notifications
    patterns: "/patterns", // Chart pattern detections
    settings: "/settings", // User settings load/save
    openclaw: "/openclaw", // OpenClaw bridge: regime, top candidates, health, scan
    market: "/market", // Market indices (SPY, QQQ, DIA) for Dashboard
    marketIndices: "/market/indices", // GET indices snapshot for Dashboard top bar
    openclawRegime: "/openclaw/regime", // Regime state for Signal Intelligence / Market Regime
    mlBrain: "/ml-brain", // ML brain model status + predictions
    riskShield: "/risk-shield", // RiskShield emergency controls + safety checks
        kellySizer: "/risk/kelly-sizer", // Bug #19 fix: was /kelly-sizer, needs /risk prefix
    positionSizing: "/risk/position-sizing", // Bug #19 fix: was /position-sizing, needs /risk prefix
      drawdownCheck: "/risk/drawdown-check", // Drawdown protection check
  dynamicStopLoss: "/risk/dynamic-stop-loss", // ATR-based stop-loss calculator
  riskScore: "/risk/risk-score", // Composite risk score 0-100
  kellyRanked: "/signals/kelly-ranked", // Kelly-ranked ticker opportunities
    preTradeCheck: "/strategy/pre-trade-check", // Pre-trade risk gate (6 checks)
      swarmTopology: "/agents/swarm-topology", // Agent swarm topology + ELO leaderboard
  conference: "/agents/conference", // Conference pipeline status
  teams: "/agents/teams", // Agent team groupings
  drift: "/agents/drift", // Model drift metrics
  systemAlerts: "/agents/alerts", // System alerts for command center
  agentResources: "/agents/resources", // Per-agent resource usage
  blackboard: "/openclaw", // Blackboard pub/sub feed
    
    // ---- MARKET REGIME PAGE (Page 10/15) ----
    "openclaw/regime": "/openclaw/regime", // HMM regime state + VIX + Hurst + confidence
    "openclaw/macro": "/openclaw/macro", // Macro oscillator, wave, bias, VIX, HY spread, F&G
    "strategy/regime-params": "/strategy/regime-params", // Regime trading params + Kelly scaling
    "backtest/regime": "/backtest/regime", // Regime-based performance (GREEN/YELLOW/RED)
    "openclaw/sectors": "/openclaw/sectors", // Sector rotation rankings
    "openclaw/scan": "/openclaw/scan", // Full scan with regime embedded
    "openclaw/memory": "/openclaw/memory", // Memory IQ, agent rankings, expectancy by regime
    "risk/risk-gauges": "/risk/risk-gauges", // 12 risk gauges with regime-aware data
    "openclaw/macro/override": "/openclaw/macro/override", // POST: bias multiplier override (0-5)
    "openclaw/health": "/openclaw/health", // Bridge health + diagnostics
    "risk/risk-score": "/risk/risk-score", // Composite risk score 0-100
    "openclaw/whale-flow": "/openclaw/whale-flow", // Whale flow alerts
    "openclaw/regime/transitions": "/openclaw/regime/transitions", // Last 30 regime changes
    
    // ---- ALPACA PROXY (Trade Execution page) ----
    "alpaca/account": "/alpaca/account", // Alpaca account details
    "alpaca/positions": "/alpaca/positions", // Open positions
    "alpaca/orders": "/alpaca/orders", // Orders list with status filter
    "alpaca/activities": "/alpaca/activities", // Trade activities/fills
    "orders/advanced": "/orders/advanced", // Advanced order creation (bracket/OCO/OTO)

        // ---- ALIGNMENT ENGINE (Constitutive Alignment - 6 patterns) ----
    "alignment/settings": "/alignment/settings", // GET/PUT alignment mode + check toggles
    "alignment/evaluate": "/alignment/evaluate", // POST preflight verdict for a trade intent
    "alignment/verdicts": "/alignment/verdicts", // GET recent verdicts (history + filters)
    "alignment/stats": "/alignment/stats", // GET aggregated alignment stats (blocks, approvals)
    "alignment/bright-lines": "/alignment/bright-lines", // GET current bright line status
    "alignment/constellation": "/alignment/constellation", // GET outcome constellation diagnostics
    "alignment/metacognition": "/alignment/metacognition", // GET metacognition flags + trends
    "alignment/critique": "/alignment/critique", // GET swarm critique role stats

    // ---- COUNCIL (11-Agent Debate Council) ----
    councilEvaluate: "/council/evaluate", // POST: run 11-agent council evaluation
    councilLatest: "/council/latest", // GET: latest council DecisionPacket

    // ---- FEATURE STORE ----
    featuresLatest: "/features/latest", // GET: latest feature vector for symbol
    featuresCompute: "/features/compute", // POST: compute + persist feature vector

    // ---- DEVICE & SYSTEM ----
    deviceInfo: "/system/device", // GET: device identity for multi-PC setups

    // ---- FLYWHEEL SCHEDULER ----
    flywheelScheduler: "/flywheel/scheduler", // GET: scheduler status + next runs

    // ---- CNS (Central Nervous System) ----
    cnsHomeostasis: "/cns/homeostasis/vitals",
    cnsCircuitBreaker: "/cns/circuit-breaker/status",
    cnsAgentsHealth: "/cns/agents/health",
    cnsBlackboard: "/cns/blackboard/current",
    cnsPostmortems: "/cns/postmortems",
    cnsPostmortemsAttribution: "/cns/postmortems/attribution",
    cnsDirectives: "/cns/directives",
    cnsLastVerdict: "/cns/council/last-verdict",
    cnsProfitBrain: "/cns/profit-brain",

    // ---- SWARM INTELLIGENCE ----
    swarmTurboStatus: "/swarm/turbo/status",
    swarmHyperStatus: "/swarm/hyper/status",
    swarmNewsStatus: "/swarm/news/status",
    swarmSweepStatus: "/swarm/sweep/status",
    swarmUnifiedStatus: "/swarm/unified/status",
    swarmOutcomesStatus: "/swarm/outcomes/status",
    swarmOutcomesKelly: "/swarm/outcomes/kelly",
    swarmPositionsManaged: "/swarm/positions/managed",
    swarmMlScorerStatus: "/swarm/ml/scorer/status",

    // ---- Agent Extended Endpoints ----
    agentAllConfig: "/agents/all-config",
    agentHitlBuffer: "/agents/hitl/buffer",
    agentHitlStats: "/agents/hitl/stats",
    agentAttribution: "/agents/attribution",
    agentEloLeaderboard: "/agents/elo-leaderboard",
    agentWsChannels: "/agents/ws-channels",
    agentFlowAnomalies: "/agents/flow-anomalies",
  },
};

/**
 * Get full API URL for an endpoint.
 * When BASE_URL is "" (dev), returns relative path so Vite proxy forwards to backend.
 * Usage: getApiUrl('agents') => '/api/v1/agents' (dev) or 'https://api.example.com/api/v1/agents' (prod)
 *
 * Bug #25 fix: fallback now ensures leading slash for unmapped endpoints
 * so 'backtest/results' becomes '/backtest/results' not 'backtest/results'.
 */
export const getApiUrl = (endpoint) => {
  // If given a full path (e.g. /api/v1/agents), avoid double prefix
  const ep = typeof endpoint === "string" ? endpoint.trim() : "";
  if (ep.startsWith("/api/v1")) {
    return `${API_CONFIG.BASE_URL}${ep}`;
  }
  const mapped = API_CONFIG.endpoints[ep];
  if (mapped) {
    return `${API_CONFIG.BASE_URL}${API_CONFIG.API_PREFIX}${mapped}`;
  }
  // Fallback: treat endpoint as raw path, ensure leading slash
  const path = ep.startsWith('/') ? ep : `/${ep}`;
  return `${API_CONFIG.BASE_URL}${API_CONFIG.API_PREFIX}${path}`;
};

/**
 * Get auth headers for state-changing requests (POST/PUT/DELETE).
 * Reads API_AUTH_TOKEN from VITE_API_AUTH_TOKEN env var.
 * Returns headers object to spread into fetch options.
 */
export const getAuthHeaders = () => {
  const token = import.meta.env.VITE_API_AUTH_TOKEN;
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
};

/**
 * Get WebSocket base URL. When WS_URL is "" (dev), uses current host so Vite proxy is used.
 */
export const getWsBaseUrl = () =>
  API_CONFIG.WS_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`
    : "ws://localhost:3000/ws");

/**
 * Get WebSocket URL for a channel
 * Usage: getWsUrl('agents') => '/ws/agents' (via proxy in dev) or 'ws://host/ws/agents'
 */
export const getWsUrl = (channel) => `${getWsBaseUrl()}/${channel}`;

/** WebSocket channel names for real-time updates (backend must expose these). */
export const WS_CHANNELS = {
  agents: "agents",
  datasources: "datasources",
  signals: "signals",
  trades: "trades",
  logs: "logs",
  sentiment: "sentiment",
  risk: "risk",
  kelly: "kelly",
  alignment: "alignment",
  council: "council",
  council_verdict: "council_verdict",
  homeostasis: "homeostasis",
  circuit_breaker: "circuit_breaker",
};

export default API_CONFIG;
