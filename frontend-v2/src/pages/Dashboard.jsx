// OLEH: This is the MAIN Intelligence Dashboard - the operator's Glass House overview
// OLEH: Connects to ALL backend modules simultaneously for real-time system-wide visibility
// OLEH: Backend endpoints needed: GET /api/v1/system/status, GET /api/v1/agents,
//       GET /api/v1/signals, GET /api/v1/risk, GET /api/v1/performance,
//       GET /api/v1/data-sources, GET /api/v1/training/status, GET /api/v1/flywheel/metrics
// OLEH: WebSocket channels: 'system', 'agents', 'signals', 'risk', 'performance'
// OLEH: Every panel is scrollable, collapsible, and configurable by the operator

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getApiUrl } from '../config/api';

// ============================================================
// CONFIGURABLE PANEL COMPONENT - Reusable scrollable/collapsible wrapper
// OLEH: Every section on the dashboard uses this wrapper
// ============================================================
function ConfigPanel({ title, icon, collapsed, onToggle, maxHeight = '400px', children, badge, headerActions }) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between px-4 py-3 bg-gray-800 cursor-pointer hover:bg-gray-750 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon}</span>
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          {badge && <span className="px-2 py-0.5 text-xs rounded-full bg-cyan-900 text-cyan-300">{badge}</span>}
        </div>
        <div className="flex items-center gap-2">
          {headerActions}
          <svg className={`w-4 h-4 text-gray-400 transition-transform ${collapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
      {!collapsed && (
        <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight }}>
          {children}
        </div>
      )}
    </div>
  );
}

// ============================================================
// AGENT STATUS MINI-CARD - Shows each agent's live status
// OLEH: Pulls from GET /api/v1/agents - shows running/paused/stopped
// ============================================================
function AgentMiniCard({ agent }) {
  const statusColors = {
    running: 'bg-emerald-500',
    paused: 'bg-yellow-500',
    stopped: 'bg-red-500',
    error: 'bg-red-600 animate-pulse',
  };
  return (
    <div className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors">
      <div className="flex items-center gap-3">
        <div className={`w-2.5 h-2.5 rounded-full ${statusColors[agent.status] || 'bg-gray-500'}`} />
        <div>
          <p className="text-sm font-medium text-white">{agent.name}</p>
          <p className="text-xs text-gray-400">{agent.currentTask || 'Idle'}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-xs text-gray-400">CPU {agent.cpu}% | RAM {agent.memory}MB</p>
        <p className="text-xs text-gray-500">Last: {agent.lastAction}</p>
      </div>
    </div>
  );
}

// ============================================================
// DATA SOURCE HEALTH BADGE - Shows each of the 10 feeds
// OLEH: Pulls from GET /api/v1/data-sources - latency and status
// ============================================================
function DataSourceBadge({ source }) {
  const statusColors = {
    healthy: 'text-emerald-400 border-emerald-800',
    degraded: 'text-yellow-400 border-yellow-800',
    down: 'text-red-400 border-red-800',
  };
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded border ${statusColors[source.status] || 'text-gray-400 border-gray-700'} bg-gray-800`}>
      <div className={`w-1.5 h-1.5 rounded-full ${source.status === 'healthy' ? 'bg-emerald-400' : source.status === 'degraded' ? 'bg-yellow-400' : 'bg-red-400'}`} />
      <span className="text-xs font-medium">{source.name}</span>
      <span className="text-xs text-gray-500">{source.latency}ms</span>
    </div>
  );
}

// ============================================================
// SIGNAL ROW - Granular signal display with all 10 source scores
// OLEH: Each signal shows WHY it was generated - Glass House transparency
// ============================================================
function SignalRow({ signal }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
      <div className="w-16 text-xs text-gray-500">{signal.time}</div>
      <div className="w-16 font-bold text-white text-sm">{signal.symbol}</div>
      <div className={`w-8 h-6 flex items-center justify-center rounded text-xs font-bold ${signal.tier === 'A' ? 'bg-emerald-900 text-emerald-300' : signal.tier === 'B' ? 'bg-blue-900 text-blue-300' : 'bg-yellow-900 text-yellow-300'}`}>{signal.tier}</div>
      <div className="w-12 text-sm text-cyan-400 font-mono">{signal.score}%</div>
      <div className={`w-12 text-sm font-semibold ${signal.direction === 'BUY' ? 'text-emerald-400' : 'text-red-400'}`}>{signal.direction}</div>
      <div className="w-20 text-xs text-gray-400 font-mono">${signal.entry}</div>
      <div className="w-20 text-xs text-gray-400 font-mono">${signal.target}</div>
      <div className="w-20 text-xs text-gray-400 font-mono">${signal.stop}</div>
      <div className="w-12 text-xs text-gray-400">{signal.rr}</div>
      {/* Source breakdown - shows which of 10 sources contributed */}
      <div className="flex gap-1 flex-1">
        {signal.sources && signal.sources.map((src, i) => (
          <div key={i} title={`${src.name}: ${src.score}/100`} className={`w-4 h-4 rounded-sm text-[8px] flex items-center justify-center ${src.score > 70 ? 'bg-emerald-900 text-emerald-300' : src.score > 40 ? 'bg-yellow-900 text-yellow-300' : 'bg-gray-800 text-gray-500'}`}>
            {src.abbr}
          </div>
        ))}
      </div>
      <Link to={`/signals?id=${signal.id}`} className="text-xs text-cyan-500 hover:text-cyan-300">Detail</Link>
    </div>
  );
}

// ============================================================
// MAIN DASHBOARD COMPONENT
// OLEH: This is the master Glass House Intelligence Dashboard
// OLEH: Every panel is independently scrollable, collapsible, configurable
// OLEH: Operator can hide/show any panel, resize, reorder
// ============================================================
export default function Dashboard() {
  // Panel collapse state - operator can collapse any section
  const [panels, setPanels] = useState({
    systemHealth: false,
    agents: false,
    dataSources: false,
    liveSignals: false,
    activePositions: false,
    riskShield: false,
    mlInsights: false,
    flywheel: false,
    performance: false,
    activityLog: false,
    marketOverview: false,
    sentimentPulse: false,
  });

  // Dashboard config - operator can configure refresh rates, visible columns
  const [config, setConfig] = useState({
    refreshRate: 5, // seconds
    signalMinScore: 60, // only show signals above this score
    maxSignals: 50,
    showSourceBreakdown: true,
    autoScrollLog: true,
    compactMode: false,
  });

  const [showConfig, setShowConfig] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const togglePanel = (panel) => {
    setPanels(prev => ({ ...prev, [panel]: !prev[panel] }));
  };

  // OLEH: Replace these with real API calls using useApi hook
  // OLEH: Each section polls its own endpoint at config.refreshRate interval

  // Mock system health data
  const systemHealth = {
    overallScore: 94,
    uptime: '47h 23m',
    cpuTotal: 34,
    memoryTotal: 62,
    gpuUtil: 28,
    gpuTemp: 67,
    diskUsage: 45,
    networkLatency: 12,
    activeAlerts: 2,
    wsConnections: 5,
    apiCalls24h: 14523,
    errorRate: 0.02,
  };

  // Mock agents data - all 5 agents
  const agents = [
    { id: 1, name: 'Market Data Agent', status: 'running', cpu: 12, memory: 245, currentTask: 'Scanning Finviz Elite + Alpaca', lastAction: '3s ago', scansToday: 847, tickersTracked: 156 },
    { id: 2, name: 'Signal Generation Agent', status: 'running', cpu: 18, memory: 312, currentTask: 'Computing composite scores', lastAction: '5s ago', signalsToday: 34, avgScore: 72 },
    { id: 3, name: 'ML Learning Agent', status: 'running', cpu: 45, memory: 1024, currentTask: 'Feature engineering (batch 12/20)', lastAction: '12s ago', accuracy: 73.2, lastTrain: '2h ago' },
    { id: 4, name: 'Sentiment Agent', status: 'running', cpu: 8, memory: 180, currentTask: 'Polling Stockgeist + News API', lastAction: '8s ago', sourcesActive: 4, sentimentBias: 'Bullish' },
    { id: 5, name: 'YouTube Knowledge Agent', status: 'paused', cpu: 0, memory: 95, currentTask: 'Paused - awaiting next video queue', lastAction: '45m ago', videosProcessed: 12, conceptsExtracted: 87 },
  ];

  // Mock data sources - all 10 feeds
  const dataSources = [
    { id: 1, name: 'Finviz Elite', status: 'healthy', latency: 45, records24h: 12400, lastPull: '3s ago' },
    { id: 2, name: 'Alpaca', status: 'healthy', latency: 12, records24h: 89500, lastPull: '1s ago' },
    { id: 3, name: 'Unusual Whales', status: 'healthy', latency: 78, records24h: 3400, lastPull: '15s ago' },
    { id: 4, name: 'FRED', status: 'healthy', latency: 120, records24h: 45, lastPull: '1h ago' },
    { id: 5, name: 'SEC EDGAR', status: 'healthy', latency: 230, records24h: 12, lastPull: '30m ago' },
    { id: 6, name: 'Stockgeist', status: 'degraded', latency: 340, records24h: 2100, lastPull: '8s ago' },
    { id: 7, name: 'News API', status: 'healthy', latency: 65, records24h: 890, lastPull: '12s ago' },
    { id: 8, name: 'Discord', status: 'healthy', latency: 34, records24h: 1560, lastPull: '5s ago' },
    { id: 9, name: 'X (Twitter)', status: 'healthy', latency: 89, records24h: 4300, lastPull: '4s ago' },
    { id: 10, name: 'YouTube', status: 'paused', latency: 0, records24h: 12, lastPull: '45m ago' },
  ];

  // Mock signals - granular with source breakdown
  const signals = [
    { id: 1, time: '14:30:15', symbol: 'MSFT', tier: 'A', score: 92, direction: 'BUY', entry: '420.10', target: '425.50', stop: '418.00', rr: '2.5:1', sources: [
      { name: 'Finviz', abbr: 'FV', score: 88 }, { name: 'Alpaca', abbr: 'AL', score: 90 }, { name: 'UW', abbr: 'UW', score: 95 },
      { name: 'FRED', abbr: 'FR', score: 72 }, { name: 'EDGAR', abbr: 'ED', score: 60 }, { name: 'Stockgeist', abbr: 'SG', score: 85 },
      { name: 'News', abbr: 'NW', score: 91 }, { name: 'Discord', abbr: 'DC', score: 78 }, { name: 'X', abbr: 'X', score: 82 }, { name: 'YouTube', abbr: 'YT', score: 65 },
    ]},
    { id: 2, time: '14:29:40', symbol: 'AAPL', tier: 'B', score: 88, direction: 'BUY', entry: '172.55', target: '175.00', stop: '171.80', rr: '3.2:1', sources: [
      { name: 'Finviz', abbr: 'FV', score: 82 }, { name: 'Alpaca', abbr: 'AL', score: 85 }, { name: 'UW', abbr: 'UW', score: 90 },
      { name: 'FRED', abbr: 'FR', score: 68 }, { name: 'EDGAR', abbr: 'ED', score: 55 }, { name: 'Stockgeist', abbr: 'SG', score: 88 },
      { name: 'News', abbr: 'NW', score: 79 }, { name: 'Discord', abbr: 'DC', score: 92 }, { name: 'X', abbr: 'X', score: 87 }, { name: 'YouTube', abbr: 'YT', score: 70 },
    ]},
    { id: 3, time: '14:28:05', symbol: 'NVDA', tier: 'A', score: 90, direction: 'SELL', entry: '915.20', target: '905.00', stop: '920.00', rr: '2.0:1', sources: [
      { name: 'Finviz', abbr: 'FV', score: 91 }, { name: 'Alpaca', abbr: 'AL', score: 88 }, { name: 'UW', abbr: 'UW', score: 93 },
      { name: 'FRED', abbr: 'FR', score: 65 }, { name: 'EDGAR', abbr: 'ED', score: 70 }, { name: 'Stockgeist', abbr: 'SG', score: 45 },
      { name: 'News', abbr: 'NW', score: 86 }, { name: 'Discord', abbr: 'DC', score: 80 }, { name: 'X', abbr: 'X', score: 75 }, { name: 'YouTube', abbr: 'YT', score: 72 },
    ]},
  ];

  // Mock active positions
  const positions = [
    { symbol: 'MSFT', shares: 150, avgEntry: 415.50, current: 420.10, pnl: 690, pnlPct: 1.11, strategy: 'Momentum', holdTime: '2h 15m', riskScore: 3 },
    { symbol: 'GOOG', shares: 50, avgEntry: 154.00, current: 155.00, pnl: 50, pnlPct: 0.32, strategy: 'Mean Reversion', holdTime: '45m', riskScore: 2 },
    { symbol: 'AMZN', shares: 80, avgEntry: 182.00, current: 180.30, pnl: -136, pnlPct: -0.93, strategy: 'Breakout', holdTime: '1h 20m', riskScore: 5 },
    { symbol: 'TSLA', shares: 20, avgEntry: 185.00, current: 187.50, pnl: 50, pnlPct: 1.35, strategy: 'Momentum', holdTime: '3h', riskScore: 7 },
    { symbol: 'NVDA', shares: 30, avgEntry: 920.00, current: 915.20, pnl: -144, pnlPct: -0.52, strategy: 'Swing', holdTime: '5h', riskScore: 4 },
  ];

  // Mock risk data
  const riskData = {
    totalExposure: 125000,
    maxDrawdownYTD: -8.2,
    currentDrawdown: -2.1,
    riskScore: 3,
    dailyPnl: 510,
    dailyLossLimit: { used: 5000, max: 10000 },
    positionLimit: { used: 5, max: 10 },
    sectorExposure: [
      { sector: 'Technology', pct: 65, limit: 70 },
      { sector: 'Healthcare', pct: 15, limit: 30 },
      { sector: 'Finance', pct: 12, limit: 25 },
      { sector: 'Energy', pct: 8, limit: 20 },
    ],
    correlationAlert: false,
    varDaily: 3200,
    sharpeRatio: 1.87,
  };

  // Mock ML / Flywheel data
  const mlData = {
    modelAccuracy: 73.2,
    accuracyTrend: '+2.1%',
    lastTrainDate: '2025-02-15 02:00',
    nextTrainDate: 'Sunday 02:00 AM',
    totalPredictions: 1847,
    correctPredictions: 1352,
    topFeatures: [
      { name: 'RSI_14', importance: 0.18, trend: 'up' },
      { name: 'MACD_Signal', importance: 0.15, trend: 'stable' },
      { name: 'Volume_Spike', importance: 0.13, trend: 'up' },
      { name: 'Sentiment_Score', importance: 0.11, trend: 'up' },
      { name: 'Options_Flow', importance: 0.09, trend: 'down' },
    ],
    flywheelCycles: 47,
    improvementRate: 0.34,
    conceptsFromYouTube: 87,
    newFeaturesAdded: 12,
  };

  // Mock performance data
  const perfData = {
    todayPnl: 510,
    weekPnl: 2340,
    monthPnl: 8920,
    ytdPnl: 34500,
    winRate: 64.2,
    avgWin: 245,
    avgLoss: -178,
    profitFactor: 1.92,
    tradesTotal: 342,
    tradesToday: 8,
    bestTrade: { symbol: 'NVDA', pnl: 1250, date: 'Feb 12' },
    worstTrade: { symbol: 'AMZN', pnl: -890, date: 'Feb 10' },
  };

  // Mock activity log - scrollable real-time feed
  const activityLog = [
    { time: '14:30:15', agent: 'Signal Gen', type: 'signal', msg: 'New A-tier signal: MSFT BUY @ 420.10 (score: 92)' },
    { time: '14:29:45', agent: 'Market Data', type: 'scan', msg: 'Finviz scan complete: 156 tickers, 3 new setups' },
    { time: '14:29:40', agent: 'Signal Gen', type: 'signal', msg: 'New B-tier signal: AAPL BUY @ 172.55 (score: 88)' },
    { time: '14:29:12', agent: 'Sentiment', type: 'alert', msg: 'Unusual bullish sentiment spike detected: MSFT (+3.2 std dev)' },
    { time: '14:28:30', agent: 'ML Learning', type: 'training', msg: 'Feature engineering batch 12/20 complete - RSI_14 importance increased' },
    { time: '14:28:05', agent: 'Signal Gen', type: 'signal', msg: 'New A-tier signal: NVDA SELL @ 915.20 (score: 90)' },
    { time: '14:27:45', agent: 'Market Data', type: 'data', msg: 'Unusual Whales: Large put flow detected TSLA $180P 02/21' },
    { time: '14:27:10', agent: 'Sentiment', type: 'data', msg: 'News API: Fed minutes show hawkish tilt - rate sensitivity UP' },
    { time: '14:26:30', agent: 'Market Data', type: 'scan', msg: 'SEC EDGAR: New 13F filing from Berkshire Hathaway' },
    { time: '14:25:00', agent: 'ML Learning', type: 'flywheel', msg: 'Flywheel cycle #47: Outcome resolver updated 23 predictions' },
    { time: '14:24:15', agent: 'YouTube', type: 'knowledge', msg: 'Video processed: "Market structure shift signals" - 5 concepts extracted' },
    { time: '14:23:00', agent: 'Sentiment', type: 'data', msg: 'Discord: High activity in #trading-alerts (45 msgs/5min)' },
  ];

  // Mock market overview
  const marketOverview = {
    spy: { price: 498.75, change: 0.85, pct: 0.17 },
    vix: { price: 17.20, change: -0.27, pct: -1.52 },
    dxy: { price: 104.32, change: 0.15, pct: 0.14 },
    us10y: { price: 4.28, change: -0.03, pct: -0.70 },
    breadth: { advDec: '+1,250', pct: 8.3 },
    sectorLeader: { name: 'Technology', pct: 1.1 },
    sectorLaggard: { name: 'Utilities', pct: -0.4 },
    marketRegime: 'Bullish Trend',
    regimeConfidence: 78,
  };

  // ============================================================
  // RETURN: Full Glass House Dashboard Layout
  // Every panel: scrollable, collapsible, with micro-controls
  // ============================================================
  return (
    <div className="space-y-4 p-4 min-h-screen bg-gray-950">
      {/* ===== HEADER: Title + Config + Last Update ===== */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Intelligence Dashboard</h1>
          <p className="text-sm text-gray-400">Glass House Overview | All systems visible | Last update: {lastUpdate.toLocaleTimeString()}</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Refresh rate control */}
          <div className="flex items-center gap-2 bg-gray-800 px-3 py-2 rounded-lg">
            <span className="text-xs text-gray-400">Refresh:</span>
            <input
              type="range" min="1" max="30" value={config.refreshRate}
              onChange={(e) => setConfig(prev => ({ ...prev, refreshRate: Number(e.target.value) }))}
              className="w-20 h-1 accent-cyan-500"
            />
            <span className="text-xs text-cyan-400 w-6">{config.refreshRate}s</span>
          </div>
          {/* Compact mode toggle */}
          <button
            onClick={() => setConfig(prev => ({ ...prev, compactMode: !prev.compactMode }))}
            className={`px-3 py-2 rounded-lg text-xs ${config.compactMode ? 'bg-cyan-900 text-cyan-300' : 'bg-gray-800 text-gray-400'}`}
          >
            {config.compactMode ? 'Compact' : 'Full'}
          </button>
          {/* Dashboard config button */}
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="px-3 py-2 bg-gray-800 rounded-lg text-xs text-gray-400 hover:text-white"
          >
            Config
          </button>
        </div>
      </div>

      {/* ===== CONFIG MODAL - Operator adjusts every dashboard parameter ===== */}
      {showConfig && (
        <div className="bg-gray-900 border border-cyan-800 rounded-lg p-4 space-y-4">
          <h3 className="text-sm font-bold text-cyan-400">Dashboard Configuration</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Min Signal Score Filter</label>
              <input type="range" min="0" max="100" value={config.signalMinScore}
                onChange={(e) => setConfig(prev => ({ ...prev, signalMinScore: Number(e.target.value) }))}
                className="w-full h-1 accent-cyan-500" />
              <span className="text-xs text-cyan-400">{config.signalMinScore}%</span>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Max Signals Displayed</label>
              <input type="range" min="5" max="200" value={config.maxSignals}
                onChange={(e) => setConfig(prev => ({ ...prev, maxSignals: Number(e.target.value) }))}
                className="w-full h-1 accent-cyan-500" />
              <span className="text-xs text-cyan-400">{config.maxSignals}</span>
            </div>
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 text-xs text-gray-400">
                <input type="checkbox" checked={config.showSourceBreakdown}
                  onChange={(e) => setConfig(prev => ({ ...prev, showSourceBreakdown: e.target.checked }))}
                  className="accent-cyan-500" />
                Show Source Breakdown
              </label>
              <label className="flex items-center gap-2 text-xs text-gray-400">
                <input type="checkbox" checked={config.autoScrollLog}
                  onChange={(e) => setConfig(prev => ({ ...prev, autoScrollLog: e.target.checked }))}
                  className="accent-cyan-500" />
                Auto-scroll Activity Log
              </label>
            </div>
          </div>
        </div>
      )}

      {/* ===== ROW 1: SYSTEM HEALTH BAR - Granular metrics with manual override ===== */}
      <ConfigPanel
        title="System Health & Hardware"
        icon="\u2764"
        collapsed={panels.systemHealth}
        onToggle={() => togglePanel('systemHealth')}
        badge={`${systemHealth.overallScore}%`}
        maxHeight="200px"
      >
        <div className="p-4">
          <div className="grid grid-cols-6 gap-3">
            {/* Each metric is individually displayed with bar visualization */}
            <div className="bg-gray-800 rounded p-2">
              <p className="text-[10px] text-gray-500 uppercase">Overall</p>
              <p className="text-lg font-bold text-emerald-400">{systemHealth.overallScore}%</p>
              <div className="w-full bg-gray-700 rounded-full h-1 mt-1">
                <div className="bg-emerald-500 h-1 rounded-full" style={{ width: `${systemHealth.overallScore}%` }} />
              </div>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-[10px] text-gray-500 uppercase">CPU</p>
              <p className="text-lg font-bold text-white">{systemHealth.cpuTotal}%</p>
              <div className="w-full bg-gray-700 rounded-full h-1 mt-1">
                <div className="bg-cyan-500 h-1 rounded-full" style={{ width: `${systemHealth.cpuTotal}%` }} />
              </div>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-[10px] text-gray-500 uppercase">RAM</p>
              <p className="text-lg font-bold text-white">{systemHealth.memoryTotal}%</p>
              <div className="w-full bg-gray-700 rounded-full h-1 mt-1">
                <div className={`h-1 rounded-full ${systemHealth.memoryTotal > 80 ? 'bg-red-500' : 'bg-blue-500'}`} style={{ width: `${systemHealth.memoryTotal}%` }} />
              </div>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-[10px] text-gray-500 uppercase">GPU (RTX 4080)</p>
              <p className="text-lg font-bold text-white">{systemHealth.gpuUtil}%</p>
              <p className="text-[10px] text-gray-500">{systemHealth.gpuTemp}C</p>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-[10px] text-gray-500 uppercase">Uptime</p>
              <p className="text-lg font-bold text-white">{systemHealth.uptime}</p>
              <p className="text-[10px] text-gray-500">Latency: {systemHealth.networkLatency}ms</p>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-[10px] text-gray-500 uppercase">API/24h</p>
              <p className="text-lg font-bold text-white">{systemHealth.apiCalls24h.toLocaleString()}</p>
              <p className="text-[10px] text-gray-500">Err: {systemHealth.errorRate}% | WS: {systemHealth.wsConnections}</p>
            </div>
          </div>
        </div>
      </ConfigPanel>

      {/* ===== ROW 2: MARKET OVERVIEW + AGENT STATUS (side by side) ===== */}
      <div className="grid grid-cols-12 gap-4">
        {/* Market Overview - Left 5 cols */}
        <div className="col-span-5">
          <ConfigPanel
            title="Market Overview"
            icon="\u{1F4CA}"
            collapsed={panels.marketOverview}
            onToggle={() => togglePanel('marketOverview')}
            badge={marketOverview.marketRegime}
            maxHeight="280px"
          >
            <div className="p-3 space-y-3">
              {/* Key indices row */}
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-gray-800 rounded p-2 flex justify-between items-center">
                  <span className="text-xs text-gray-400">SPY</span>
                  <div className="text-right">
                    <span className="text-sm font-bold text-white">${marketOverview.spy.price}</span>
                    <span className={`text-xs ml-2 ${marketOverview.spy.pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{marketOverview.spy.pct >= 0 ? '+' : ''}{marketOverview.spy.pct}%</span>
                  </div>
                </div>
                <div className="bg-gray-800 rounded p-2 flex justify-between items-center">
                  <span className="text-xs text-gray-400">VIX</span>
                  <div className="text-right">
                    <span className="text-sm font-bold text-white">{marketOverview.vix.price}</span>
                    <span className={`text-xs ml-2 ${marketOverview.vix.pct >= 0 ? 'text-red-400' : 'text-emerald-400'}`}>{marketOverview.vix.pct >= 0 ? '+' : ''}{marketOverview.vix.pct}%</span>
                  </div>
                </div>
                <div className="bg-gray-800 rounded p-2 flex justify-between items-center">
                  <span className="text-xs text-gray-400">DXY</span>
                  <div className="text-right">
                    <span className="text-sm font-bold text-white">{marketOverview.dxy.price}</span>
                    <span className={`text-xs ml-2 ${marketOverview.dxy.pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{marketOverview.dxy.pct >= 0 ? '+' : ''}{marketOverview.dxy.pct}%</span>
                  </div>
                </div>
                <div className="bg-gray-800 rounded p-2 flex justify-between items-center">
                  <span className="text-xs text-gray-400">US10Y</span>
                  <div className="text-right">
                    <span className="text-sm font-bold text-white">{marketOverview.us10y.price}%</span>
                    <span className={`text-xs ml-2 ${marketOverview.us10y.pct >= 0 ? 'text-red-400' : 'text-emerald-400'}`}>{marketOverview.us10y.pct >= 0 ? '+' : ''}{marketOverview.us10y.pct}%</span>
                  </div>
                </div>
              </div>
              {/* Market regime + breadth */}
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Regime</p>
                  <p className="text-xs font-bold text-cyan-400">{marketOverview.marketRegime}</p>
                  <p className="text-[10px] text-gray-500">Confidence: {marketOverview.regimeConfidence}%</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Breadth</p>
                  <p className="text-xs font-bold text-emerald-400">{marketOverview.breadth.advDec}</p>
                  <p className="text-[10px] text-gray-500">+{marketOverview.breadth.pct}%</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Sectors</p>
                  <p className="text-[10px] text-emerald-400">Lead: {marketOverview.sectorLeader.name} +{marketOverview.sectorLeader.pct}%</p>
                  <p className="text-[10px] text-red-400">Lag: {marketOverview.sectorLaggard.name} {marketOverview.sectorLaggard.pct}%</p>
                </div>
              </div>
            </div>
          </ConfigPanel>
        </div>

        {/* Agent Status - Right 7 cols */}
        <div className="col-span-7">
          <ConfigPanel
            title="Agent Status (5 Agents)"
            icon="\u{1F916}"
            collapsed={panels.agents}
            onToggle={() => togglePanel('agents')}
            badge={`${agents.filter(a => a.status === 'running').length}/5 Running`}
            maxHeight="280px"
            headerActions={
              <Link to="/agents" className="text-xs text-cyan-500 hover:text-cyan-300 mr-2">Full Control</Link>
            }
          >
            <div className="p-3 space-y-2">
              {agents.map(agent => (
                <AgentMiniCard key={agent.id} agent={agent} />
              ))}
            </div>
          </ConfigPanel>
        </div>
      </div>

      {/* ===== ROW 3: DATA SOURCES (all 10 feeds) - scrollable with latency bars ===== */}
      <ConfigPanel
        title="Data Sources (10 Feeds)"
        icon="\u{1F4E1}"
        collapsed={panels.dataSources}
        onToggle={() => togglePanel('dataSources')}
        badge={`${dataSources.filter(d => d.status === 'healthy').length}/10 Healthy`}
        maxHeight="180px"
        headerActions={
          <Link to="/data-sources" className="text-xs text-cyan-500 hover:text-cyan-300 mr-2">Monitor</Link>
        }
      >
        <div className="p-3">
          <div className="flex flex-wrap gap-2">
            {dataSources.map(source => (
              <DataSourceBadge key={source.id} source={source} />
            ))}
          </div>
          {/* Granular table below badges */}
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left py-1 px-2">Source</th>
                  <th className="text-right py-1 px-2">Latency</th>
                  <th className="text-right py-1 px-2">Records/24h</th>
                  <th className="text-right py-1 px-2">Last Pull</th>
                  <th className="text-right py-1 px-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {dataSources.map(ds => (
                  <tr key={ds.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-1 px-2 text-white">{ds.name}</td>
                    <td className="py-1 px-2 text-right">
                      <span className={ds.latency > 200 ? 'text-yellow-400' : ds.latency > 500 ? 'text-red-400' : 'text-gray-400'}>{ds.latency}ms</span>
                    </td>
                    <td className="py-1 px-2 text-right text-gray-400">{ds.records24h.toLocaleString()}</td>
                    <td className="py-1 px-2 text-right text-gray-500">{ds.lastPull}</td>
                    <td className="py-1 px-2 text-right">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${ds.status === 'healthy' ? 'bg-emerald-900 text-emerald-300' : ds.status === 'degraded' ? 'bg-yellow-900 text-yellow-300' : 'bg-red-900 text-red-300'}`}>{ds.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </ConfigPanel>

      {/* ===== ROW 4: LIVE SIGNALS - scrollable with 10-source breakdown + operator controls ===== */}
      <ConfigPanel
        title="Live Trading Signals"
        icon="\u26A1"
        collapsed={panels.liveSignals}
        onToggle={() => togglePanel('liveSignals')}
        badge={`${signals.length} Active | Min: ${config.signalMinScore}%`}
        maxHeight="350px"
        headerActions={
          <div className="flex items-center gap-2 mr-2">
            <span className="text-[10px] text-gray-500">Min Score:</span>
            <input type="range" min="0" max="100" value={config.signalMinScore}
              onChange={(e) => setConfig(prev => ({ ...prev, signalMinScore: Number(e.target.value) }))}
              className="w-16 h-1 accent-cyan-500" onClick={(e) => e.stopPropagation()} />
            <span className="text-[10px] text-cyan-400">{config.signalMinScore}%</span>
            <Link to="/signals" className="text-xs text-cyan-500 hover:text-cyan-300">Full View</Link>
          </div>
        }
      >
        <div>
          {/* Column headers */}
          <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-700 bg-gray-800/50 text-[10px] text-gray-500 uppercase">
            <div className="w-16">Time</div>
            <div className="w-16">Symbol</div>
            <div className="w-8">Tier</div>
            <div className="w-12">Score</div>
            <div className="w-12">Dir</div>
            <div className="w-20">Entry</div>
            <div className="w-20">Target</div>
            <div className="w-20">Stop</div>
            <div className="w-12">R:R</div>
            {config.showSourceBreakdown && <div className="flex-1">Sources (10)</div>}
            <div>Action</div>
          </div>
          {/* Signal rows - scrollable */}
          {signals.filter(s => s.score >= config.signalMinScore).map(signal => (
            <SignalRow key={signal.id} signal={signal} />
          ))}
        </div>
      </ConfigPanel>

      {/* ===== ROW 5: ACTIVE POSITIONS + RISK SHIELD (side by side) ===== */}
      <div className="grid grid-cols-12 gap-4">
        {/* Active Positions - Left 7 cols */}
        <div className="col-span-7">
          <ConfigPanel
            title="Active Positions"
            icon="\u{1F4B0}"
            collapsed={panels.activePositions}
            onToggle={() => togglePanel('activePositions')}
            badge={`${positions.length} Open | P&L: $${positions.reduce((s, p) => s + p.pnl, 0).toLocaleString()}`}
            maxHeight="300px"
            headerActions={
              <Link to="/trades" className="text-xs text-cyan-500 hover:text-cyan-300 mr-2">Execute</Link>
            }
          >
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-700 bg-gray-800/50">
                    <th className="text-left py-2 px-3">Symbol</th>
                    <th className="text-right py-2 px-3">Shares</th>
                    <th className="text-right py-2 px-3">Avg Entry</th>
                    <th className="text-right py-2 px-3">Current</th>
                    <th className="text-right py-2 px-3">P&L</th>
                    <th className="text-right py-2 px-3">P&L %</th>
                    <th className="text-left py-2 px-3">Strategy</th>
                    <th className="text-right py-2 px-3">Hold</th>
                    <th className="text-center py-2 px-3">Risk</th>
                    <th className="text-center py-2 px-3">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos, i) => (
                    <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                      <td className="py-2 px-3 font-bold text-white">{pos.symbol}</td>
                      <td className="py-2 px-3 text-right text-gray-300">{pos.shares}</td>
                      <td className="py-2 px-3 text-right text-gray-400 font-mono">${pos.avgEntry.toFixed(2)}</td>
                      <td className="py-2 px-3 text-right text-white font-mono">${pos.current.toFixed(2)}</td>
                      <td className={`py-2 px-3 text-right font-mono font-bold ${pos.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                      </td>
                      <td className={`py-2 px-3 text-right ${pos.pnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {pos.pnlPct >= 0 ? '+' : ''}{pos.pnlPct}%
                      </td>
                      <td className="py-2 px-3 text-gray-400">{pos.strategy}</td>
                      <td className="py-2 px-3 text-right text-gray-500">{pos.holdTime}</td>
                      <td className="py-2 px-3 text-center">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${pos.riskScore <= 3 ? 'bg-emerald-900 text-emerald-300' : pos.riskScore <= 6 ? 'bg-yellow-900 text-yellow-300' : 'bg-red-900 text-red-300'}`}>{pos.riskScore}/10</span>
                      </td>
                      <td className="py-2 px-3 text-center">
                        <button className="px-2 py-1 bg-red-900 text-red-300 rounded text-[10px] hover:bg-red-800">Close</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ConfigPanel>
        </div>

        {/* Risk Shield - Right 5 cols */}
        <div className="col-span-5">
          <ConfigPanel
            title="Risk Shield"
            icon="\u{1F6E1}"
            collapsed={panels.riskShield}
            onToggle={() => togglePanel('riskShield')}
            badge={`Score: ${riskData.riskScore}/10`}
            maxHeight="300px"
            headerActions={
              <Link to="/risk" className="text-xs text-cyan-500 hover:text-cyan-300 mr-2">Full Risk</Link>
            }
          >
            <div className="p-3 space-y-3">
              {/* Key risk metrics */}
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Total Exposure</p>
                  <p className="text-sm font-bold text-white">${riskData.totalExposure.toLocaleString()}</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Daily P&L</p>
                  <p className={`text-sm font-bold ${riskData.dailyPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${riskData.dailyPnl >= 0 ? '+' : ''}${riskData.dailyPnl}</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Max DD (YTD)</p>
                  <p className="text-sm font-bold text-red-400">{riskData.maxDrawdownYTD}%</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Sharpe Ratio</p>
                  <p className="text-sm font-bold text-cyan-400">{riskData.sharpeRatio}</p>
                </div>
              </div>
              {/* Daily loss limit bar - adjustable */}
              <div className="bg-gray-800 rounded p-2">
                <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                  <span>Daily Loss Limit</span>
                  <span>${riskData.dailyLossLimit.used.toLocaleString()} / ${riskData.dailyLossLimit.max.toLocaleString()}</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div className={`h-2 rounded-full ${(riskData.dailyLossLimit.used / riskData.dailyLossLimit.max) > 0.8 ? 'bg-red-500' : 'bg-cyan-500'}`}
                    style={{ width: `${(riskData.dailyLossLimit.used / riskData.dailyLossLimit.max) * 100}%` }} />
                </div>
              </div>
              {/* Sector exposure bars */}
              <div className="space-y-1">
                <p className="text-[10px] text-gray-500">Sector Exposure</p>
                {riskData.sectorExposure.map((sec, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-400 w-20">{sec.sector}</span>
                    <div className="flex-1 bg-gray-700 rounded-full h-1.5">
                      <div className={`h-1.5 rounded-full ${sec.pct > sec.limit * 0.9 ? 'bg-red-500' : 'bg-cyan-500'}`}
                        style={{ width: `${sec.pct}%` }} />
                    </div>
                    <span className="text-[10px] text-gray-500 w-16">{sec.pct}% / {sec.limit}%</span>
                  </div>
                ))}
              </div>
            </div>
          </ConfigPanel>
        </div>
      </div>

      {/* ===== ROW 6: ML BRAIN + FLYWHEEL + PERFORMANCE (side by side) ===== */}
      <div className="grid grid-cols-12 gap-4">
        {/* ML Brain & Flywheel - Left 6 cols */}
        <div className="col-span-6">
          <ConfigPanel
            title="ML Brain & Flywheel"
            icon="\u{1F9E0}"
            collapsed={panels.mlInsights}
            onToggle={() => togglePanel('mlInsights')}
            badge={`Accuracy: ${mlData.modelAccuracy}% ${mlData.accuracyTrend}`}
            maxHeight="350px"
            headerActions={
              <Link to="/ml-brain" className="text-xs text-cyan-500 hover:text-cyan-300 mr-2">Full ML</Link>
            }
          >
            <div className="p-3 space-y-3">
              {/* Key ML metrics */}
              <div className="grid grid-cols-4 gap-2">
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Accuracy</p>
                  <p className="text-lg font-bold text-emerald-400">{mlData.modelAccuracy}%</p>
                  <p className="text-[10px] text-emerald-400">{mlData.accuracyTrend}</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Predictions</p>
                  <p className="text-sm font-bold text-white">{mlData.correctPredictions}/{mlData.totalPredictions}</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Flywheel Cycles</p>
                  <p className="text-sm font-bold text-cyan-400">{mlData.flywheelCycles}</p>
                  <p className="text-[10px] text-gray-500">+{mlData.improvementRate}%/cycle</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">YouTube Concepts</p>
                  <p className="text-sm font-bold text-purple-400">{mlData.conceptsFromYouTube}</p>
                  <p className="text-[10px] text-gray-500">{mlData.newFeaturesAdded} new features</p>
                </div>
              </div>
              {/* Top features - GRANULAR: shows what ML thinks is important */}
              <div>
                <p className="text-[10px] text-gray-500 mb-2">Top Feature Importance (live from model)</p>
                {mlData.topFeatures.map((feat, i) => (
                  <div key={i} className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] text-gray-400 w-28 font-mono">{feat.name}</span>
                    <div className="flex-1 bg-gray-700 rounded-full h-2">
                      <div className="bg-cyan-500 h-2 rounded-full" style={{ width: `${feat.importance * 500}%` }} />
                    </div>
                    <span className="text-[10px] text-gray-400 w-10">{(feat.importance * 100).toFixed(0)}%</span>
                    <span className={`text-[10px] ${feat.trend === 'up' ? 'text-emerald-400' : feat.trend === 'down' ? 'text-red-400' : 'text-gray-500'}`}>
                      {feat.trend === 'up' ? '\u2191' : feat.trend === 'down' ? '\u2193' : '\u2192'}
                    </span>
                  </div>
                ))}
              </div>
              {/* Training schedule */}
              <div className="bg-gray-800 rounded p-2 flex justify-between items-center">
                <div>
                  <p className="text-[10px] text-gray-500">Next Retrain</p>
                  <p className="text-xs text-white">{mlData.nextTrainDate}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Last Train</p>
                  <p className="text-xs text-gray-400">{mlData.lastTrainDate}</p>
                </div>
                <button className="px-3 py-1 bg-cyan-900 text-cyan-300 rounded text-xs hover:bg-cyan-800">Retrain Now</button>
              </div>
            </div>
          </ConfigPanel>
        </div>

        {/* Performance - Right 6 cols */}
        <div className="col-span-6">
          <ConfigPanel
            title="Performance Analytics"
            icon="\u{1F4C8}"
            collapsed={panels.performance}
            onToggle={() => togglePanel('performance')}
            badge={`Win: ${perfData.winRate}% | PF: ${perfData.profitFactor}`}
            maxHeight="350px"
            headerActions={
              <Link to="/performance" className="text-xs text-cyan-500 hover:text-cyan-300 mr-2">Full Stats</Link>
            }
          >
            <div className="p-3 space-y-3">
              {/* P&L grid */}
              <div className="grid grid-cols-4 gap-2">
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Today</p>
                  <p className={`text-lg font-bold ${perfData.todayPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${perfData.todayPnl >= 0 ? '+' : ''}{perfData.todayPnl}</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Week</p>
                  <p className={`text-lg font-bold ${perfData.weekPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${perfData.weekPnl >= 0 ? '+' : ''}{perfData.weekPnl.toLocaleString()}</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Month</p>
                  <p className={`text-lg font-bold ${perfData.monthPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${perfData.monthPnl >= 0 ? '+' : ''}{perfData.monthPnl.toLocaleString()}</p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">YTD</p>
                  <p className={`text-lg font-bold ${perfData.ytdPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>${perfData.ytdPnl >= 0 ? '+' : ''}{perfData.ytdPnl.toLocaleString()}</p>
                </div>
              </div>
              {/* Trading stats */}
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Win Rate</p>
                  <p className="text-sm font-bold text-white">{perfData.winRate}%</p>
                  <div className="w-full bg-gray-700 rounded-full h-1.5 mt-1">
                    <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: `${perfData.winRate}%` }} />
                  </div>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Avg Win / Loss</p>
                  <p className="text-xs">
                    <span className="text-emerald-400">${perfData.avgWin}</span>
                    {' / '}
                    <span className="text-red-400">${Math.abs(perfData.avgLoss)}</span>
                  </p>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <p className="text-[10px] text-gray-500">Trades</p>
                  <p className="text-sm font-bold text-white">{perfData.tradesTotal} total</p>
                  <p className="text-[10px] text-gray-500">{perfData.tradesToday} today</p>
                </div>
              </div>
              {/* Best / Worst */}
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-emerald-900/20 border border-emerald-800/30 rounded p-2">
                  <p className="text-[10px] text-emerald-500">Best Trade</p>
                  <p className="text-xs text-white">{perfData.bestTrade.symbol} +${perfData.bestTrade.pnl}</p>
                  <p className="text-[10px] text-gray-500">{perfData.bestTrade.date}</p>
                </div>
                <div className="bg-red-900/20 border border-red-800/30 rounded p-2">
                  <p className="text-[10px] text-red-500">Worst Trade</p>
                  <p className="text-xs text-white">{perfData.worstTrade.symbol} ${perfData.worstTrade.pnl}</p>
                  <p className="text-[10px] text-gray-500">{perfData.worstTrade.date}</p>
                </div>
              </div>
            </div>
          </ConfigPanel>
        </div>
      </div>

      {/* ===== ROW 7: ACTIVITY LOG - scrollable real-time feed of ALL agent actions ===== */}
      <ConfigPanel
        title="Live Activity Log (All Agents)"
        icon="\u{1F4DD}"
        collapsed={panels.activityLog}
        onToggle={() => togglePanel('activityLog')}
        badge={`${activityLog.length} Events`}
        maxHeight="300px"
        headerActions={
          <div className="flex items-center gap-2 mr-2">
            <label className="flex items-center gap-1 text-[10px] text-gray-400">
              <input type="checkbox" checked={config.autoScrollLog}
                onChange={(e) => { e.stopPropagation(); setConfig(prev => ({ ...prev, autoScrollLog: e.target.checked })); }}
                className="accent-cyan-500" />
              Auto-scroll
            </label>
            <Link to="/operator-console" className="text-xs text-cyan-500 hover:text-cyan-300">Console</Link>
          </div>
        }
      >
        <div>
          {activityLog.map((entry, i) => {
            const typeColors = {
              signal: 'text-emerald-400 bg-emerald-900/20',
              scan: 'text-blue-400 bg-blue-900/20',
              alert: 'text-yellow-400 bg-yellow-900/20',
              training: 'text-purple-400 bg-purple-900/20',
              data: 'text-gray-400 bg-gray-800/50',
              flywheel: 'text-cyan-400 bg-cyan-900/20',
              knowledge: 'text-pink-400 bg-pink-900/20',
            };
            return (
              <div key={i} className={`flex items-start gap-3 px-4 py-2 border-b border-gray-800/50 hover:bg-gray-800/30 ${typeColors[entry.type] || ''}`}>
                <span className="text-[10px] text-gray-500 w-16 shrink-0 font-mono">{entry.time}</span>
                <span className={`text-[10px] w-20 shrink-0 px-1.5 py-0.5 rounded ${typeColors[entry.type] || 'text-gray-400'}`}>{entry.agent}</span>
                <span className="text-xs text-gray-300 flex-1">{entry.msg}</span>
              </div>
            );
          })}
        </div>
      </ConfigPanel>

    </div>
  );
}
