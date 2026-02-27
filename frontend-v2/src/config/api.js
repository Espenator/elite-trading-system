/**
 * Embodier.ai (Trading) - API Configuration
 * Branch: v2-15-feb-espen-embodier-ai
 *
 * OLEH: This is the foundation file. Every hook and page imports from here.
 * OLEH: Update BASE_URL when deploying. Default is localhost:8001 (our FastAPI backend).
 * OLEH: Every endpoint listed here MUST have a corresponding FastAPI router in backend/app/api/v1/
 * OLEH: If an endpoint doesn't exist yet in backend, create the router file first.
 *
 * BACKEND REFERENCE:
 *   Existing routers: stocks, quotes, orders, system, training, signals, backtest, status
 *   NEW routers needed: agents, data-sources, sentiment, youtube-knowledge, flywheel,
 *                       portfolio, risk, strategy, performance, logs, alerts
 */
const API_CONFIG = {
  // Use empty string in dev so requests go to same origin → Vite proxy forwards to backend (port 8001).
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
    training: "/training", // ML model training
    signals: "/signals", // Generated trading signals
    backtest: "/backtest", // Backtesting engine
    backtestRuns: "/backtest/runs", // Recent backtest runs (for Backtesting page)
    status: "/status", // System health check

    // ---- NEW (Oleh needs to create these routers) ----
    agents: "/agents", // Agent control: start/stop/pause/config
    dataSources: "/data-sources", // Health of all 10 data feeds
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
    mlBrain: "/ml-brain", // ML brain model status + predictions
    riskShield: "/risk-shield", // RiskShield emergency controls + safety checks
        kellySizer: "/kelly-sizer", // Kelly criterion position sizing calculator
    positionSizing: "/position-sizing", // Portfolio-level position sizing
      drawdownCheck: "/risk/drawdown-check", // Drawdown protection check
  dynamicStopLoss: "/risk/dynamic-stop-loss", // ATR-based stop-loss calculator
  riskScore: "/risk/risk-score", // Composite risk score 0-100
  kellyRanked: "/signals/kelly-ranked", // Kelly-ranked ticker opportunities
  },
};

/**
 * Get full API URL for an endpoint.
 * When BASE_URL is "" (dev), returns relative path so Vite proxy forwards to backend.
 * Usage: getApiUrl('agents') => '/api/v1/agents' (dev) or 'https://api.example.com/api/v1/agents' (prod)
 */
export const getApiUrl = (endpoint) =>
  `${API_CONFIG.BASE_URL}${API_CONFIG.API_PREFIX}${API_CONFIG.endpoints[endpoint] || endpoint}`;

/**
 * Get WebSocket base URL. When WS_URL is "" (dev), uses current host so Vite proxy is used.
 */
export const getWsBaseUrl = () =>
  API_CONFIG.WS_URL ||
  (typeof window !== "undefined"
    ? `ws://${window.location.host}/ws`
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
};

export default API_CONFIG;
