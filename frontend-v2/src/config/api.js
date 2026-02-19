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
  // OLEH: Change this to production URL when deploying
  BASE_URL: import.meta.env.VITE_API_URL || "http://localhost:8001",
  API_PREFIX: "/api/v1",
  WS_URL: import.meta.env.VITE_WS_URL || "ws://localhost:8001/ws",

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
    logs: "/logs", // System activity logs
    alerts: "/alerts", // Alert rules + notifications
  },
};

/**
 * Get full API URL for an endpoint
 * Usage: getApiUrl('agents') => 'http://localhost:8001/api/v1/agents'
 */
export const getApiUrl = (endpoint) =>
  `${API_CONFIG.BASE_URL}${API_CONFIG.API_PREFIX}${API_CONFIG.endpoints[endpoint] || endpoint}`;

/**
 * Get WebSocket URL for a channel
 * Usage: getWsUrl('agents') => 'ws://localhost:8001/ws/agents'
 * OLEH: Backend needs WebSocket support via FastAPI WebSocket routes
 */
export const getWsUrl = (channel) => `${API_CONFIG.WS_URL}/${channel}`;

/** WebSocket channel names for real-time updates (backend must expose these). */
export const WS_CHANNELS = {
  agents: "agents",
  datasources: "datasources",
  signals: "signals",
  trades: "trades",
  logs: "logs",
};

export default API_CONFIG;
