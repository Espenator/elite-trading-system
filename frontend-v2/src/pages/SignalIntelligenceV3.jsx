import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useApi } from '../hooks/useApi';
import { getApiUrl, getAuthHeaders, getWsUrl, WS_CHANNELS } from '../config/api';
import log from "@/utils/logger";
import { createChart, CrosshairMode, LineStyle } from 'lightweight-charts';
import {
  Activity, AlertTriangle, Cpu, Network, Zap, TrendingUp, TrendingDown,
  Clock, Shield, Database, GitMerge, Radio, Server, Layers, BarChart2,
  Eye, Sliders, Globe, MessageSquare, Play, Square, RefreshCw, CheckCircle,
  XCircle, Rocket, FileText, Download, Share2, Search, Crosshair, Lock,
  Unlock, Save, Power, Wifi, HardDrive, Filter, Target, Maximize2
} from 'lucide-react';
import ReactFlow, { Background, Controls, MarkerType, Handle } from 'reactflow';
import 'reactflow/dist/style.css';
import ws from '../services/websocket';
// ============================================================================
// CONSTANTS & INITIAL DATA (fallbacks when API is unavailable)
// ============================================================================

const FALLBACK_CORE_AGENTS = [
  { id: 'apex', name: 'Apex Orchestrator', type: 'Core', defaultWeight: 100 },
  { id: 'rel_weak', name: 'Relative Weakness', type: 'Core', defaultWeight: 85 },
  { id: 'short_basket', name: 'Short Basket', type: 'Core', defaultWeight: 75 },
  { id: 'meta_arch', name: 'Meta Architect', type: 'Core', defaultWeight: 90 },
  { id: 'meta_alch', name: 'Meta Alchemist', type: 'Core', defaultWeight: 80 },
  { id: 'risk_gov', name: 'Risk Governor', type: 'Risk', defaultWeight: 100 },
  { id: 'sig_engine', name: 'Signal Engine', type: 'Engine', defaultWeight: 95 }
];

const FALLBACK_EXTENDED_AGENTS = Array.from({ length: 93 }, (_, i) => ({
  id: `agent_${i + 8}`, name: `Agent #${i + 8} (Swarm)`, type: 'Swarm', defaultWeight: 25
}));

const FALLBACK_ALL_AGENTS = [...FALLBACK_CORE_AGENTS, ...FALLBACK_EXTENDED_AGENTS];

/** Parse API agents response into { core, extended, all } using fallbacks */
function parseAgentsFromApi(apiData) {
  if (!apiData) return null;
  const list = Array.isArray(apiData) ? apiData
    : apiData?.agents ? apiData.agents
    : apiData?.data ? apiData.data
    : null;
  if (!list || list.length === 0) return null;
  const normalize = (a) => ({
    id: a.id || a.agent_id || a.name?.toLowerCase().replace(/\s+/g, '_'),
    name: a.name || a.label || a.id,
    type: a.type || a.role || 'Swarm',
    defaultWeight: a.weight ?? a.defaultWeight ?? a.default_weight ?? 50,
    status: a.status || a.state || null,
  });
  const all = list.map(normalize);
  const coreTypes = new Set(['Core', 'Risk', 'Engine', 'Orchestrator']);
  const core = all.filter(a => coreTypes.has(a.type));
  const extended = all.filter(a => !coreTypes.has(a.type));
  return { core, extended, all };
}

const SCANNERS = [
  { id: 'scan_daily', name: 'Daily Scanner', defaultWeight: 100 },
  { id: 'scan_finviz', name: 'Finviz Screener', defaultWeight: 70 },
  { id: 'scan_amd', name: 'AMD Detector', defaultWeight: 85 },
  { id: 'scan_pullback', name: 'Pullback Detector', defaultWeight: 90 },
  { id: 'scan_rebound', name: 'Rebound Detector', defaultWeight: 80 },
  { id: 'scan_squeeze', name: 'Short Squeeze', defaultWeight: 65 },
  { id: 'scan_tech', name: 'Technical Checker', defaultWeight: 75 },
  { id: 'scan_earnings', name: 'Earnings Calendar', defaultWeight: 50 },
  { id: 'scan_fomc', name: 'FOMC Expected', defaultWeight: 100 },
  { id: 'scan_sector', name: 'Sector Rotation', defaultWeight: 85 },
  { id: 'scan_whale', name: 'Whale Flow', defaultWeight: 95 },
  { id: 'scan_uw', name: 'UW Agents', defaultWeight: 90 },
  { id: 'scan_tv_watch', name: 'TV Watchlist', defaultWeight: 60 },
  { id: 'scan_tv_sess', name: 'TV Session Refresh', defaultWeight: 40 }
];

const INTEL_MODULES = [
  { id: 'intel_hmm', name: 'HMM Regime', defaultWeight: 100 },
  { id: 'intel_llm', name: 'LLM Client', defaultWeight: 85 },
  { id: 'intel_lora', name: 'LoRA Trainer', defaultWeight: 70 },
  { id: 'intel_macro', name: 'Macro Context', defaultWeight: 95 },
  { id: 'intel_mem1', name: 'Memory v1', defaultWeight: 60 },
  { id: 'intel_mem3', name: 'Memory v3', defaultWeight: 90 },
  { id: 'intel_mtf', name: 'MTF Alignment', defaultWeight: 85 },
  { id: 'intel_perf', name: 'Perf Tracker', defaultWeight: 100 },
  { id: 'intel_regime', name: 'Regime Detector', defaultWeight: 100 }
];

const ML_MODELS = [
  { id: 'ml_lstm', name: 'LSTM Daily', version: 'v4.2.1', defaultStatus: 'Ready' },
  { id: 'ml_xgb', name: 'XGBoost GPU', version: 'v2.8.0', defaultStatus: 'Ready' },
  { id: 'ml_river', name: 'River Online', version: 'v1.1.5', defaultStatus: 'Training' },
  { id: 'ml_infer', name: 'Inference Engine', version: 'v3.0.0', defaultStatus: 'Ready' },
  { id: 'ml_wfv', name: 'Walk-Forward Val', version: 'v1.0.2', defaultStatus: 'Idle' },
  { id: 'ml_pipe', name: 'ML Pipeline', version: 'v5.1.0', defaultStatus: 'Ready' }
];

const DATA_SOURCES = [
  { id: 'ds_twitter', name: 'Twitter/X API' },
  { id: 'ds_reddit', name: 'Reddit API' },
  { id: 'ds_news', name: 'NewsAPI' },
  { id: 'ds_benzinga', name: 'Benzinga Pro' },
  { id: 'ds_rss', name: 'RSS Aggregator' }
];

const API_ENDPOINTS = [
  'agents','alerts','backtest','data_sources','flywheel','logs',
  'market','ml_brain','openclaw','orders','patterns','performance',
  'portfolio','quotes','risk','risk_shield','sentiment','settings',
  'signals','status','stocks','strategy','system','training',
  'youtube_knowledge','websocket','auth_bridge','ext_webhooks'
];

const SHAP_FACTORS = [
  'UW Options Flow','Velez Score','Volume Surge','Whale Flow',
  'RSI Divergence','HTF Structure','Compression','Sector Momentum'
];
// ============================================================================
// REUSABLE UI COMPONENTS
// ============================================================================

const Panel = ({ title, icon: Icon, children, className = '', headerAction = null }) => (
  <div className={`bg-[#111827] border border-[#1e293b] rounded-aurora overflow-hidden flex flex-col ${className}`}>
    <div className="px-3 py-1.5 border-b border-[#1e293b] flex justify-between items-center bg-[#111827] shrink-0">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-3.5 h-3.5 text-[#00D9FF] shrink-0" />}
        <h3 className="text-[10px] font-bold text-gray-300 uppercase tracking-widest">{title}</h3>
      </div>
      {headerAction && <div className="flex items-center gap-1">{headerAction}</div>}
    </div>
    <div className="p-2 flex-1 flex flex-col overflow-y-auto scrollbar-thin scrollbar-thumb-[#374151] scrollbar-track-transparent">
      {children}
    </div>
  </div>
);

const Toggle = ({ checked, onChange, size = 'md' }) => {
  const h = size === 'sm' ? 'h-3' : 'h-4';
  const w = size === 'sm' ? 'w-6' : 'w-8';
  const dot = size === 'sm' ? 'w-2 h-2' : 'w-3 h-3';
  const translate = size === 'sm' ? 'translate-x-3' : 'translate-x-4';
  return (
    <button type="button" onClick={() => onChange(!checked)}
      className={`${w} ${h} rounded-full relative transition-colors duration-200 focus:outline-none shrink-0 ${checked ? 'bg-cyan-500' : 'bg-[#374151]'}`}>
      <span className={`absolute top-0.5 left-0.5 bg-white rounded-full transition-transform duration-200 ${dot} ${checked ? translate : 'translate-x-0'}`} />
    </button>
  );
};

const Slider = ({ value, onChange, color = 'cyan', label = '' }) => (
  <div className="flex items-center gap-1.5 flex-1">
    {label && <span className="text-[8px] text-gray-500 w-10 shrink-0">{label}</span>}
    <div className="relative flex-1 h-1 bg-[#1e293b] rounded-full">
      <div className="absolute left-0 top-0 h-1 rounded-full transition-all"
        style={{ width: `${value}%`, background: color === 'cyan' ? '#06b6d4' : color === 'emerald' ? '#10b981' : color === 'amber' ? '#f59e0b' : color === 'red' ? '#ef4444' : '#a855f7' }} />
      <input type="range" min="0" max="100" value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="absolute inset-0 w-full opacity-0 cursor-pointer h-1" />
    </div>
    <span className="text-[9px] text-gray-400 w-6 text-right shrink-0">{value}%</span>
  </div>
);

const ControlRow = ({ title, isActive, onToggle, weight, onWeightChange, statusColor = 'green' }) => {
  const colors = {
    green: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]',
    yellow: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]',
    red: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]',
    gray: 'bg-gray-600'
  };
  return (
    <div className="flex items-center gap-2 py-1 border-b border-[#1e293b]/50 last:border-0 hover:bg-[#1e293b]/40 px-0.5 rounded group">
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isActive ? (colors[statusColor] || colors.gray) : colors.gray}`} />
      <span className="text-[9px] text-gray-300 truncate w-24 shrink-0" title={title}>{title}</span>
      <Toggle checked={isActive} onChange={onToggle} size="sm" />
      <Slider value={weight} onChange={onWeightChange} />
    </div>
  );
};

const Badge = ({ children, color = 'cyan' }) => {
  const colors = {
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    red: 'bg-red-500/10 text-red-400 border-red-500/30',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    gray: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
  };
  return (<span className={`px-1.5 py-0.5 rounded text-[9px] border font-mono ${colors[color] ?? colors.gray}`}>{children}</span>);
};

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================
export default function SignalIntelligenceV3() {
  // --- REAL API HOOKS (mapped to config/api.js endpoints) ---
  const { data: apiSignals, loading: sigLoading, refetch: refetchSignals } = useApi('signals', { pollIntervalMs: 5000 });
  const { data: apiAgents } = useApi('agents', { pollIntervalMs: 10000 });
  const { data: apiOpenclaw } = useApi('openclaw', { pollIntervalMs: 8000 });
  const { data: apiDataSources } = useApi('dataSources', { pollIntervalMs: 15000 });
  const { data: apiSentiment } = useApi('sentiment', { pollIntervalMs: 30000 });
  const { data: apiYoutube } = useApi('youtubeKnowledge', { pollIntervalMs: 60000 });
  const { data: apiTraining } = useApi('training', { pollIntervalMs: 30000 });
  const { data: apiMlBrain } = useApi('mlBrain', { pollIntervalMs: 15000 });
  // flywheel hook moved to derived data section with 15s polling for ML Controls
  const { data: apiPatterns } = useApi('patterns', { pollIntervalMs: 10000 });
  const { data: apiRisk } = useApi('risk', { pollIntervalMs: 10000 });
  const { data: apiAlerts } = useApi('alerts', { pollIntervalMs: 10000 });
  const { data: apiStatus } = useApi('status', { pollIntervalMs: 15000 });
  const { data: apiPerf } = useApi('performance', { pollIntervalMs: 30000 });
  const { data: apiMarket } = useApi('market', { pollIntervalMs: 5000 });
  const { data: apiPortfolio } = useApi('portfolio', { pollIntervalMs: 10000 });
  const { data: apiStrategy } = useApi('strategy', { pollIntervalMs: 30000 });

  // --- DERIVE AGENT LISTS FROM API (with hardcoded fallbacks) ---
  const parsedAgents = useMemo(() => parseAgentsFromApi(apiAgents), [apiAgents]);
  const CORE_AGENTS = useMemo(() => parsedAgents?.core ?? FALLBACK_CORE_AGENTS, [parsedAgents]);
  const EXTENDED_AGENTS = useMemo(() => parsedAgents?.extended ?? FALLBACK_EXTENDED_AGENTS, [parsedAgents]);
  const ALL_AGENTS = useMemo(() => parsedAgents?.all ?? FALLBACK_ALL_AGENTS, [parsedAgents]);

  // --- LOCAL STATE ---
  const [agentStates, setAgentStates] = useState(() =>
    FALLBACK_ALL_AGENTS.reduce((acc, agent) => ({ ...acc, [agent.id]: { active: true, weight: agent.defaultWeight, status: 'green' } }), {})
  );
  const [scannerStates, setScannerStates] = useState(() =>
    SCANNERS.reduce((acc, scan) => ({ ...acc, [scan.id]: { active: true, weight: scan.defaultWeight, status: 'green', runs: 0 } }), {})
  );
  const [intelStates, setIntelStates] = useState(() =>
    INTEL_MODULES.reduce((acc, mod) => ({ ...acc, [mod.id]: { active: true, weight: mod.defaultWeight, status: 'green' } }), {})
  );
  const [scoringFormula, setScoringFormula] = useState({
    ocTaBlend: 60, tierSlamDunk: 90, tierStrongGo: 75, tierWatch: 60, regimeMultiplier: 1.2
  });
  const [shapWeights, setShapWeights] = useState(() =>
    SHAP_FACTORS.reduce((acc, factor) => ({ ...acc, [factor]: 50 }), {})
  );
  const [shapActive, setShapActive] = useState(() =>
    SHAP_FACTORS.reduce((acc, factor) => ({ ...acc, [factor]: true }), {})
  );
  const [alertRules, setAlertRules] = useState({
    comp_regime_stage: true,
    vix_halve_pos: true,
  });
  const [mlStates, setMlStates] = useState(() =>
    ML_MODELS.reduce((acc, mod) => ({ ...acc, [mod.id]: { active: true, confThreshold: 75, status: mod.defaultStatus } }), {})
  );
  const [dataSourceStates, setDataSourceStates] = useState(() =>
    DATA_SOURCES.reduce((acc, ds) => ({ ...acc, [ds.id]: { active: true, weight: 100 } }), {})
  );
  const [regimeLock, setRegimeLock] = useState(false);
  const [autoExecute, setAutoExecute] = useState(false);
    const [maxHeat, setMaxHeat] = useState(25);
  const [lossLimit, setLossLimit] = useState(5);
  const [wsLatency, setWsLatency] = useState(42);
  const [signals, setSignals] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [chartTimeframe, setChartTimeframe] = useState('15m');

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  // --- WEBSOCKET CONNECTION (uses services/websocket.js singleton) ---
  useEffect(() => {
    ws.connect();
    const unsubSignals = ws.on('signals', (msg) => {
      if (msg?.type === 'signals_updated') refetchSignals();
      if (msg?.type === 'signal' && msg.payload) {
        setSignals(prev => [msg.payload, ...prev].slice(0, 50));
      }
    });
    const unsubLatency = ws.on('*', (msg) => {
      if (msg?.data?.type === 'ping' && msg.data.latency) setWsLatency(msg.data.latency);
    });
    return () => { unsubSignals(); unsubLatency(); };
  }, [refetchSignals]);

  // --- SYNC API AGENTS INTO LOCAL agentStates ---
  useEffect(() => {
    if (!ALL_AGENTS || ALL_AGENTS.length === 0) return;
    setAgentStates(prev => {
      const next = { ...prev };
      for (const agent of ALL_AGENTS) {
        const existing = prev[agent.id];
        const apiStatus = agent.status;
        const statusColor = apiStatus === 'active' || apiStatus === 'running' ? 'green'
          : apiStatus === 'degraded' || apiStatus === 'warming' ? 'yellow'
          : apiStatus === 'error' || apiStatus === 'stopped' ? 'red'
          : existing?.status || 'green';
        if (existing) {
          next[agent.id] = { ...existing, status: statusColor };
        } else {
          next[agent.id] = { active: true, weight: agent.defaultWeight, status: statusColor };
        }
      }
      return next;
    });
  }, [ALL_AGENTS]);

  // --- SYNC API DATA SOURCES INTO LOCAL dataSourceStates ---
  useEffect(() => {
    if (!apiDataSources) return;
    const sources = Array.isArray(apiDataSources) ? apiDataSources
      : apiDataSources?.sources || apiDataSources?.data || [];
    if (sources.length === 0) return;
    setDataSourceStates(prev => {
      const next = { ...prev };
      for (const src of sources) {
        const id = src.id || src.source_id;
        if (!id) continue;
        const isActive = src.active !== false && src.status !== 'down' && src.status !== 'error';
        next[id] = { active: isActive, weight: src.weight ?? prev[id]?.weight ?? 100 };
      }
      return next;
    });
  }, [apiDataSources]);

  // --- SYNC ML BRAIN / TRAINING STATUS INTO LOCAL mlStates ---
  useEffect(() => {
    const models = apiMlBrain?.models || apiTraining?.models || null;
    if (!models || !Array.isArray(models)) return;
    setMlStates(prev => {
      const next = { ...prev };
      for (const m of models) {
        const id = m.id || m.model_id;
        if (!id || !prev[id]) continue;
        next[id] = {
          ...prev[id],
          status: m.status || m.state || prev[id].status,
          confThreshold: m.confidence_threshold ?? m.confThreshold ?? prev[id].confThreshold,
        };
      }
      return next;
    });
  }, [apiMlBrain, apiTraining]);

  // --- LIGHTWEIGHT CHARTS SETUP ---
  useEffect(() => {
    if (!chartContainerRef.current || chartRef.current) return;
    const chart = createChart(chartContainerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: '#9ca3af', fontFamily: 'JetBrains Mono' },
      grid: { vertLines: { color: '#1e293b', style: LineStyle.SparseDotted }, horzLines: { color: '#1e293b', style: LineStyle.SparseDotted } },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { borderColor: '#374151', timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: '#374151' },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981', downColor: '#ef4444', borderVisible: false,
      wickUpColor: '#10b981', wickDownColor: '#ef4444'
    });
    const volSeries = chart.addHistogramSeries({
      color: '#26a69a', priceFormat: { type: 'volume' },
      priceScaleId: '', scaleMargins: { top: 0.8, bottom: 0 }
    });
    const sma20 = chart.addLineSeries({ color: '#06b6d4', lineWidth: 1, title: 'SMA20' });
    const sma50 = chart.addLineSeries({ color: '#a855f7', lineWidth: 1, title: 'SMA50' });
    const sma200 = chart.addLineSeries({ color: '#F97316', lineWidth: 1, lineStyle: LineStyle.Dashed, title: 'SMA200' });
    const vwap = chart.addLineSeries({ color: '#ffffff', lineWidth: 1, lineStyle: LineStyle.Dotted, title: 'VWAP' });
        // Fetch real OHLCV data from backend quotes API
    const fetchChart = async () => {
      try {
        const url = getApiUrl('quotes') + `/${selectedSymbol}?timeframe=${chartTimeframe}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Quote fetch failed');
        const json = await res.json();
        const bars = json.bars || json.data || json || [];
        if (bars.length === 0) return;
        const rawData = bars.map(b => {
          const t = b.timestamp ?? b.t ?? b.time;
          const ts = t != null ? Math.floor(new Date(t).getTime() / 1000) : NaN;
          const open = Number(b.open ?? b.o);
          const high = Number(b.high ?? b.h);
          const low = Number(b.low ?? b.l);
          const close = Number(b.close ?? b.c);
          const volume = Number(b.volume ?? b.v ?? 0);
          return { time: Number.isFinite(ts) ? ts : NaN, open, high, low, close, volume };
        });
        const sorted = rawData
          .filter(d => Number.isFinite(d.time) && Number.isFinite(d.close))
          .sort((a, b) => a.time - b.time);
        // De-duplicate by time (chart requires strictly ascending; keep last per timestamp)
        const data = [];
        let prevTime = -1;
        for (const d of sorted) {
          if (d.time > prevTime) {
            data.push(d);
            prevTime = d.time;
          } else if (d.time === prevTime && data.length > 0) {
            data[data.length - 1] = d;
          }
        }
        if (data.length === 0) return;
        const volData = data.map((d, i) => ({ time: d.time, value: d.volume, color: d.close >= d.open ? '#10b98144' : '#ef444444' }));
        // Compute SMA20, SMA50, SMA200, VWAP from real data
        const s20 = []; const s50 = []; const s200 = []; const vwapData = [];
        let cumVol = 0, cumVolPrice = 0;
        data.forEach((d, i) => {
          const vol = d.volume;
          const tp = (d.high + d.low + d.close) / 3;
          cumVol += vol; cumVolPrice += tp * vol;
          if (cumVol > 0) vwapData.push({ time: d.time, value: cumVolPrice / cumVol });
          if (i >= 19) s20.push({ time: d.time, value: data.slice(i - 19, i + 1).reduce((a, b) => a + b.close, 0) / 20 });
          if (i >= 49) s50.push({ time: d.time, value: data.slice(i - 49, i + 1).reduce((a, b) => a + b.close, 0) / 50 });
          if (i >= 199) s200.push({ time: d.time, value: data.slice(i - 199, i + 1).reduce((a, b) => a + b.close, 0) / 200 });
        });
        candleSeries.setData(data); volSeries.setData(volData);
        sma20.setData(s20); sma50.setData(s50); sma200.setData(s200); vwap.setData(vwapData);
        const lastPrice = data[data.length - 1].close;
        candleSeries.createPriceLine({ price: lastPrice, color: '#06b6d4', lineWidth: 2, lineStyle: LineStyle.Solid, title: 'ENTRY' });
        candleSeries.createPriceLine({ price: lastPrice * 1.05, color: '#10b981', lineWidth: 2, lineStyle: LineStyle.Dashed, title: 'TARGET' });
        candleSeries.createPriceLine({ price: lastPrice * 0.98, color: '#ef4444', lineWidth: 2, lineStyle: LineStyle.Dotted, title: 'STOP' });
      } catch (err) { log.warn('Chart data fetch (expected if no quotes endpoint):', err.message); }
    };
    fetchChart();
    chartRef.current = chart;
    const handleResize = () => { if (chartContainerRef.current) chart.applyOptions({ width: chartContainerRef.current.clientWidth }); };
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); chartRef.current = null; };
  }, [selectedSymbol, chartTimeframe]);

  // --- SYNC API SIGNALS TO LOCAL STATE ---
  useEffect(() => {
    if (apiSignals) {
      const list = Array.isArray(apiSignals) ? apiSignals
        : apiSignals?.signals ? apiSignals.signals
        : [];
      if (list.length > 0) { setSignals(list.slice(0, 50)); return; }
    }
    if (signals.length === 0) {
      setSignals([
        { id: 1, symbol: 'NVDA', score: 96, dir: 'LONG', price: 924.50, agent: 'Apex', status: 'Staged' },
        { id: 2, symbol: 'AMD', score: 88, dir: 'LONG', price: 174.20, agent: 'Finviz', status: 'Pending' },
        { id: 3, symbol: 'TSLA', score: 32, dir: 'SHORT', price: 168.45, agent: 'Rel_Weak', status: 'Active' },
        { id: 4, symbol: 'PLTR', score: 91, dir: 'LONG', price: 24.15, agent: 'Whale', status: 'Staged' },
        { id: 5, symbol: 'SMCI', score: 85, dir: 'LONG', price: 1045.2, agent: 'Squeeze', status: 'Watch' },
        { id: 6, symbol: 'META', score: 76, dir: 'LONG', price: 502.1, agent: 'Tech', status: 'Pending' },
        { id: 7, symbol: 'BA', score: 12, dir: 'SHORT', price: 184.2, agent: 'Short_B', status: 'Active' },
        { id: 8, symbol: 'AAPL', score: 65, dir: 'LONG', price: 172.5, agent: 'Daily', status: 'Watch' },
      ]);
    }
  }, [apiSignals]);

  // --- HANDLERS (Real API Mapped) ---
  const handleUpdateWeight = useCallback(async (category, id, value) => {
    if (category === 'agent') setAgentStates(p => ({ ...p, [id]: { ...p[id], weight: value } }));
    else if (category === 'scanner') setScannerStates(p => ({ ...p, [id]: { ...p[id], weight: value } }));
    else if (category === 'intel') setIntelStates(p => ({ ...p, [id]: { ...p[id], weight: value } }));
    else if (category === 'shap') { setShapWeights(p => ({ ...p, [id]: value })); return; }
    try {
      const url = getApiUrl(`${category}s`) + `/${id}/weight`;
      await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify({ weight: value }) });
    } catch (err) { log.error(`Failed to update ${category} weight:`, err); }
  }, []);

  const handleToggleState = useCallback(async (category, id, currentState) => {
    const newState = !currentState;
    if (category === 'agent') setAgentStates(p => ({ ...p, [id]: { ...p[id], active: newState } }));
    else if (category === 'scanner') setScannerStates(p => ({ ...p, [id]: { ...p[id], active: newState } }));
    else if (category === 'intel') setIntelStates(p => ({ ...p, [id]: { ...p[id], active: newState } }));
    try {
      const url = getApiUrl(`${category}s`) + `/${id}/toggle`;
      await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify({ active: newState }) });
    } catch (err) { log.error(`Failed to toggle ${category}:`, err); }
  }, []);

  const triggerScan = useCallback(async (id) => {
    try {
      setScannerStates(p => ({ ...p, [id]: { ...p[id], status: 'yellow' } }));
      const url = getApiUrl('openclaw/scan');
      await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify({ scannerId: id }) });
      setTimeout(() => { setScannerStates(p => ({ ...p, [id]: { ...p[id], status: 'green', runs: p[id].runs + 1 } })); }, 1500);
    } catch (e) { setScannerStates(p => ({ ...p, [id]: { ...p[id], status: 'red' } })); }
  }, []);

  const triggerRetrain = useCallback(async (id) => {
    try {
      setMlStates(p => ({ ...p, [id]: { ...p[id], status: 'Training' } }));
      const url = getApiUrl('training') + '/retrain';
      // POST to /api/v1/training/retrain with model ID
      await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify({ modelId: id }) });
    } catch (e) { log.error(e); }
  }, []);

  // --- SAVE PROFILE (persist all weights/toggles to backend settings) ---
  const handleSaveProfile = useCallback(async () => {
    try {
      const payload = {
        agentStates,
        scannerStates,
        intelStates,
        mlStates,
        dataSourceStates,
        scoringFormula,
        shapWeights,
        regimeLock,
        autoExecute,
        maxHeat,
        lossLimit,
      };
      const url = getApiUrl('settings');
      const res = await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ page: 'signal_intelligence_v3', profile: payload }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      log.info('Profile saved successfully');
    } catch (err) {
      log.error('Failed to save profile:', err);
    }
  }, [agentStates, scannerStates, intelStates, mlStates, dataSourceStates, scoringFormula, shapWeights, regimeLock, autoExecute, maxHeat, lossLimit]);

  // --- SIGNAL ACTIONS: Stage for execution via orders endpoint ---
  const handleStageSignal = useCallback(async (signal) => {
    try {
      const url = getApiUrl('orders');
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({
          symbol: signal.symbol || signal.ticker,
          side: (signal.dir === 'LONG' || signal.action === 'BUY') ? 'buy' : 'sell',
          type: 'limit',
          limit_price: signal.price,
          source: 'signal_intelligence_v3',
          signal_id: signal.id,
        }),
      });
    } catch (err) {
      log.error('Failed to stage signal:', err);
    }
  }, []);

  // --- ML Controls State ---
  const [mlConfidenceThreshold, setMlConfidenceThreshold] = useState(75);

  // --- DERIVED DATA ---
  const { data: regimeApiData } = useApi('openclawRegime', { pollIntervalMs: 10000 });
  const { data: flywheelData } = useApi('flywheel', { pollIntervalMs: 15000 });
  const regimeData = useMemo(() => regimeApiData || apiOpenclaw?.regime || { state: 'BULL_TREND', conf: 87, color: 'emerald', since: null }, [regimeApiData, apiOpenclaw]);

  // Regime banner color mapping: BULL=green, BEAR=red, SIDEWAYS=yellow, HIGH_VOL=orange
  const regimeBanner = useMemo(() => {
    const state = regimeData.state || '';
    if (state.includes('BULL')) return { color: '#10B981', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.3)', text: '#10B981', label: 'BULL', icon: 'trending-up' };
    if (state.includes('BEAR')) return { color: '#EF4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.3)', text: '#EF4444', label: 'BEAR', icon: 'trending-down' };
    if (state.includes('HIGH_VOL') || state.includes('VOLATILE')) return { color: '#F97316', bg: 'rgba(249,115,22,0.08)', border: 'rgba(249,115,22,0.3)', text: '#F97316', label: 'HIGH_VOL', icon: 'alert' };
    if (state.includes('SIDE') || state.includes('RANGE') || state.includes('CHOP')) return { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.3)', text: '#F59E0B', label: 'SIDEWAYS', icon: 'minus' };
    return { color: '#10B981', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.3)', text: '#10B981', label: 'BULL', icon: 'trending-up' };
  }, [regimeData]);

  const bannerColor = regimeData.state?.includes('BULL') ? 'emerald' : regimeData.state?.includes('BEAR') ? 'red' : 'amber';
  const timeframes = ['1m', '5m', '15m', '1H', '4H', '1D', '1W'];

  // Scanner metrics derived from real state
  const scannerMetrics = useMemo(() => {
    const activeScanners = Object.values(scannerStates).filter(s => s.active).length;
    const totalRuns = Object.values(scannerStates).reduce((sum, s) => sum + s.runs, 0);
    const sigs = Array.isArray(apiSignals) ? apiSignals : apiSignals?.signals || signals;
    const signalsToday = sigs.length;
    const highConfSignals = sigs.filter(s => (s.score || s.confidence || 0) >= 80).length;
    const hitRate = signalsToday > 0 ? Math.round((highConfSignals / signalsToday) * 100) : 0;
    const topSignal = sigs.length > 0 ? (sigs.reduce((best, s) => (s.score || s.confidence || 0) > (best.score || best.confidence || 0) ? s : best, sigs[0])) : null;
    return { activeScanners, totalRuns, signalsToday, hitRate, topSignal };
  }, [scannerStates, apiSignals, signals]);

  // ML Controls derived data (combines training + flywheel data)
  const mlControlsData = useMemo(() => {
    const activeModels = Object.values(mlStates).filter(m => m.active).length;
    const lastRetrain = flywheelData?.last_retrain || flywheelData?.lastRetrain || apiTraining?.last_retrain || apiTraining?.lastRetrain || null;
    const flywheelCycles = flywheelData?.cycles || flywheelData?.total_cycles || null;
    const flywheelAccuracy = flywheelData?.accuracy || flywheelData?.model_accuracy || null;
    const featureImportance = flywheelData?.feature_importance || flywheelData?.featureImportance || apiTraining?.feature_importance || apiTraining?.featureImportance || [
      { name: 'UW Options Flow', importance: 0.23 },
      { name: 'Velez Score', importance: 0.19 },
      { name: 'Volume Surge', importance: 0.15 },
      { name: 'RSI Divergence', importance: 0.12 },
      { name: 'HTF Structure', importance: 0.09 },
    ];
    return { activeModels, lastRetrain, flywheelCycles, flywheelAccuracy, featureImportance: (Array.isArray(featureImportance) ? featureImportance : []).slice(0, 5) };
  }, [mlStates, apiTraining, flywheelData]);

  // --- RENDER ---
  return (
    <div className="h-screen bg-[#0B0E14] text-gray-200 font-mono flex flex-col overflow-hidden">
      {/* ================================================================== */}
      {/* TOP TOOLBAR                                                        */}
      {/* ================================================================== */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#111827] border-b border-[#1e293b] shrink-0">
        <div className="flex items-center gap-3">
          <Activity className="w-4 h-4 text-[#00D9FF]" />
          <span className="text-sm font-bold text-[#00D9FF] tracking-wider font-mono">SIGNAL_INTELLIGENCE_V3</span>
        </div>
        <div className="flex items-center gap-3 text-[9px] text-gray-500">
          <Badge color="cyan">OC_CORE_v5.2.1</Badge>
          <Badge color={wsLatency < 100 ? 'emerald' : 'amber'}>WS_LATENCY: {wsLatency}ms</Badge>
          <Badge color="purple">SWARM_SIZE: {ALL_AGENTS?.length ?? 0}</Badge>
          <button onClick={handleSaveProfile} className="flex items-center gap-1 px-2 py-1 bg-[#00D9FF]/10 border border-[#00D9FF]/30 rounded-aurora text-[#00D9FF] hover:bg-[#00D9FF]/20 hover:shadow-glow transition-all duration-200">
            <Save className="w-3 h-3" /> Save Profile
          </button>
        </div>
      </div>

      {/* ================================================================== */}
      {/* REGIME BANNER                                                      */}
      {/* ================================================================== */}
      <div
        className="flex items-center justify-between px-3 py-1.5 border-b shrink-0"
        style={{
          background: `linear-gradient(90deg, ${regimeBanner.bg} 0%, rgba(11,14,20,0.95) 50%, ${regimeBanner.bg} 100%)`,
          borderColor: regimeBanner.border
        }}
      >
        <div className="flex items-center gap-3">
          <span className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: regimeBanner.color, boxShadow: `0 0 10px ${regimeBanner.color}` }} />
          {regimeBanner.label === 'BULL' && <TrendingUp className="w-3.5 h-3.5" style={{ color: regimeBanner.text }} />}
          {regimeBanner.label === 'BEAR' && <TrendingDown className="w-3.5 h-3.5" style={{ color: regimeBanner.text }} />}
          {regimeBanner.label === 'HIGH_VOL' && <AlertTriangle className="w-3.5 h-3.5" style={{ color: regimeBanner.text }} />}
          {regimeBanner.label === 'SIDEWAYS' && <Activity className="w-3.5 h-3.5" style={{ color: regimeBanner.text }} />}
          <span className="text-xs font-bold tracking-wider font-mono" style={{ color: regimeBanner.text }}>
            {regimeData.state || 'BULL_TREND REGIME'}
          </span>
          <span className="text-[9px] text-gray-600 font-mono">Hidden Markov Model (Layer 3)</span>
          <span className="text-[9px] text-gray-500 font-mono ml-2">Confidence: {regimeData.conf ?? '--'}%</span>
          <span className="text-[9px] text-gray-600 font-mono ml-1">Override</span>
          <Toggle checked={regimeLock} onChange={setRegimeLock} size="sm" />
          {regimeLock ? <Lock className="w-3 h-3 text-amber-500" /> : <Unlock className="w-3 h-3 text-gray-600" />}
        </div>
        <div className="flex items-center gap-2">
          <div className="w-20 h-1.5 bg-[#1e293b] rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${regimeData.conf ?? 0}%`, backgroundColor: regimeBanner.color }} />
          </div>
        </div>
      </div>

      {/* ================================================================== */}
      {/* MAIN 4-COLUMN GRID LAYOUT                                          */}
      {/* ================================================================== */}
      <div className="flex-1 grid grid-cols-[18%_34%_24%_24%] gap-1.5 p-1.5 overflow-hidden min-h-0">

        {/* ============================================================== */}
        {/* COLUMN 1: Scanner Modules + OpenClaw Agent Swarm               */}
        {/* ============================================================== */}
        <div className="flex flex-col gap-1.5 overflow-hidden min-h-0">
          {/* Scanner Modules (Layer 1) */}
          <Panel title="Scanner Modules (Layer 1)" icon={Search} className="flex-[4] min-h-0"
            headerAction={<span className="text-[8px] text-gray-500">{scannerMetrics.activeScanners} SCANNER TOGGLES</span>}>
            {SCANNERS.map(scan => (
              <div key={scan.id} className="flex items-center gap-1 py-0.5 border-b border-[#1e293b]/50 last:border-0 hover:bg-[#1e293b]/40 px-0.5 rounded">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                  scannerStates[scan.id].status === 'green' ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.7)]'
                  : scannerStates[scan.id].status === 'yellow' ? 'bg-amber-500 animate-pulse'
                  : 'bg-red-500'}`} />
                <span className="text-[9px] text-gray-300 truncate w-24 shrink-0">{scan.name}</span>
                <Toggle checked={scannerStates[scan.id].active} onChange={(v) => handleToggleState('scanner', scan.id, !v)} size="sm" />
                <Slider value={scannerStates[scan.id].weight} onChange={(v) => handleUpdateWeight('scanner', scan.id, v)} />
              </div>
            ))}
          </Panel>

          {/* OpenClaw Score (Layer 4) */}
          <Panel title="OpenClaw Score (Layer 4)" icon={Cpu} className="flex-[5] min-h-0"
            headerAction={<span className="text-[8px] text-gray-500">{CORE_AGENTS.length} CORE AGENTS</span>}>
            <div className="text-[8px] text-gray-500 mb-0.5 uppercase tracking-widest">CORE AGENTS</div>
            {CORE_AGENTS.map(agent => (
              <ControlRow key={agent.id} title={agent.name}
                isActive={agentStates[agent.id]?.active ?? true}
                onToggle={(v) => handleToggleState('agent', agent.id, !v)}
                weight={agentStates[agent.id]?.weight ?? agent.defaultWeight}
                onWeightChange={(v) => handleUpdateWeight('agent', agent.id, v)}
                statusColor={agentStates[agent.id]?.status || 'green'} />
            ))}
            <div className="flex items-center justify-between mt-1.5 mb-0.5">
              <span className="text-[8px] text-gray-500 uppercase tracking-widest">EXTENDED SWARM ({EXTENDED_AGENTS.length})</span>
              <span className="text-[8px] text-cyan-600">SCROLL</span>
            </div>
            <div className="flex-1 overflow-y-auto min-h-0">
              {EXTENDED_AGENTS.map(agent => (
                <ControlRow key={agent.id} title={agent.name}
                  isActive={agentStates[agent.id]?.active ?? true}
                  onToggle={(v) => handleToggleState('agent', agent.id, !v)}
                  weight={agentStates[agent.id]?.weight ?? agent.defaultWeight}
                  onWeightChange={(v) => handleUpdateWeight('agent', agent.id, v)}
                  statusColor={agentStates[agent.id]?.status || 'green'} />
              ))}
            </div>
          </Panel>
        </div>

        {/* ============================================================== */}
        {/* COLUMN 2: Chart + Signal Data Table                            */}
        {/* ============================================================== */}
        <div className="flex flex-col gap-1.5 overflow-hidden min-h-0">
          {/* Chart with symbol header */}
          <Panel title={`${selectedSymbol}`} icon={Crosshair} className="flex-[6] min-h-0"
            headerAction={
              <div className="flex items-center gap-1.5">
                <div className="flex items-center gap-0.5 mr-2">
                  <span className="text-[8px] text-cyan-400 font-mono">SMA20</span>
                  <span className="text-[8px] text-purple-400 font-mono ml-1">SMA50</span>
                  <span className="text-[8px] text-orange-400 font-mono ml-1">SMA200</span>
                  <span className="text-[8px] text-white font-mono ml-1">VWAP</span>
                </div>
                {timeframes.map(t => (
                  <button key={t} onClick={() => setChartTimeframe(t)}
                    className={`px-1.5 py-0.5 rounded-aurora text-[9px] font-mono border transition-all duration-200 ${chartTimeframe === t ? 'bg-[#00D9FF]/20 border-[#00D9FF]/50 text-[#00D9FF] shadow-glow' : 'bg-[#1e293b] border-[#374151] text-gray-500 hover:text-gray-300 hover:border-gray-500'}`}>{t}</button>
                ))}
              </div>
            }>
            <div ref={chartContainerRef} className="w-full flex-1 min-h-[180px]" />
          </Panel>

          {/* Signal Data Table */}
          <Panel title="Signal data table" icon={FileText} className="flex-[4] min-h-0"
            headerAction={
              <div className="flex items-center gap-2">
                <span className="text-[8px] text-gray-600 font-mono">{signals.length} signals</span>
                <button onClick={refetchSignals} className="text-gray-500 hover:text-[#00D9FF] transition-colors">
                  <RefreshCw className="w-3 h-3" />
                </button>
              </div>
            }>
            <div className="overflow-auto flex-1 min-h-0">
              <table className="w-full text-[9px]">
                <thead className="sticky top-0 bg-[#111827] z-10">
                  <tr className="text-gray-500 border-b border-[#1e293b] uppercase tracking-wider">
                    <th className="text-left py-1 px-1">Symbol</th>
                    <th className="text-left py-1 px-1">Score</th>
                    <th className="text-left py-1 px-1">Dir</th>
                    <th className="text-left py-1 px-1">Price</th>
                    <th className="text-left py-1 px-1">Origin Agent</th>
                    <th className="text-left py-1 px-1">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((sig, idx) => (
                    <tr key={sig.id || idx} className="border-b border-[#1e293b]/30 hover:bg-[#00D9FF]/5 cursor-pointer transition-colors"
                      onClick={() => setSelectedSymbol(sig.symbol || sig.ticker)}>
                      <td className="py-1 px-1 font-bold font-mono text-[#00D9FF]">
                        {sig.symbol || sig.ticker}
                      </td>
                      <td className="py-1 px-1">
                        <span className={`font-mono font-bold ${(sig.score || sig.confidence || 0) >= 80 ? 'text-emerald-400' : (sig.score || sig.confidence || 0) >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                          {sig.score || sig.confidence || '--'}
                        </span>
                      </td>
                      <td className="py-1 px-1">
                        <span className={`px-1 py-0.5 rounded text-[8px] font-bold ${(sig.dir === 'LONG' || sig.action === 'BUY') ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                          {sig.dir || sig.action || '--'}
                        </span>
                      </td>
                      <td className="py-1 px-1 font-mono text-gray-300">${typeof sig.price === 'number' ? sig.price.toFixed(2) : sig.price || '--'}</td>
                      <td className="py-1 px-1 text-gray-400 truncate max-w-[60px]">
                        <span className="text-cyan-400">{sig.agent || sig.source || '--'}</span>
                      </td>
                      <td className="py-1 px-1">
                        <div className="flex items-center gap-1">
                          <button onClick={(e) => { e.stopPropagation(); setSelectedSymbol(sig.symbol || sig.ticker); }}
                            className="text-[#00D9FF] hover:text-white transition-colors" title="View chart"><Eye className="w-2.5 h-2.5" /></button>
                          <button onClick={(e) => { e.stopPropagation(); handleStageSignal(sig); }}
                            className="text-emerald-400 hover:text-white transition-colors" title="Stage order"><Play className="w-2.5 h-2.5" /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        {/* ============================================================== */}
        {/* COLUMN 3: Global Scoring Engine + Intelligence Modules + Regime */}
        {/* ============================================================== */}
        <div className="flex flex-col gap-1.5 overflow-hidden min-h-0">
          {/* Global Scoring Engine (Layer 2) */}
          <Panel title="Global Scoring Engine (Layer 2)" icon={Target} className="flex-[5] min-h-0">
            <div className="flex items-center justify-between text-[9px] mb-1.5">
              <Badge color="cyan">OpenClaw Core</Badge>
              <span className="text-[8px] text-gray-500">vs</span>
              <Badge color="purple">Tech Analysis</Badge>
            </div>
            <input type="range" min="0" max="100" value={scoringFormula.ocTaBlend}
              onChange={(e) => setScoringFormula(p => ({...p, ocTaBlend: parseInt(e.target.value)}))}
              className="w-full h-1.5 appearance-none bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full cursor-pointer" />
            <div className="text-center text-[9px] text-gray-400 mt-0.5 mb-1.5">{scoringFormula.ocTaBlend} / {100 - scoringFormula.ocTaBlend}</div>

            <div className="flex items-center gap-2 py-0.5">
              <span className="text-[9px] text-gray-500 w-28">Regime Multiplier</span>
              <input type="number" step="0.1" value={scoringFormula.regimeMultiplier}
                onChange={(e) => setScoringFormula(p => ({...p, regimeMultiplier: parseFloat(e.target.value) || 1}))}
                className="bg-[#1e293b] border border-[#374151] rounded px-2 py-0.5 text-[9px] text-cyan-400 font-bold w-16 outline-none" />
            </div>
            <div className="flex items-center gap-2 py-0.5">
              <span className="text-[9px] text-gray-500 w-28">SLAM DUNK Tier</span>
              <input type="number" value={scoringFormula.tierSlamDunk}
                onChange={(e) => setScoringFormula(p => ({...p, tierSlamDunk: parseInt(e.target.value) || 90}))}
                className="bg-[#1e293b] border border-[#374151] rounded px-2 py-0.5 text-[9px] text-emerald-400 font-bold w-16 outline-none" />
            </div>

            <div className="mt-2 text-[8px] text-gray-500 uppercase tracking-widest mb-1">PER-FACTOR SHAP WEIGHTS</div>
            {SHAP_FACTORS.map(factor => (
              <ControlRow key={factor} title={factor}
                isActive={shapActive[factor]}
                onToggle={() => setShapActive(p => ({ ...p, [factor]: !p[factor] }))}
                weight={shapWeights[factor]}
                onWeightChange={(v) => handleUpdateWeight('shap', factor, v)} />
            ))}
          </Panel>

          {/* Intelligence Modules (Layer 3) */}
          <Panel title="Intelligence Modules (Layer 3)" icon={Shield} className="flex-[3] min-h-0">
            {INTEL_MODULES.map(mod => (
              <ControlRow key={mod.id} title={mod.name}
                isActive={intelStates[mod.id].active}
                onToggle={(v) => handleToggleState('intel', mod.id, !v)}
                weight={intelStates[mod.id].weight}
                onWeightChange={(v) => handleUpdateWeight('intel', mod.id, v)} />
            ))}
          </Panel>

          {/* Regime Detector */}
          <Panel title="Regime Detector" icon={BarChart2} className="flex-[2] min-h-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: regimeBanner.color, boxShadow: `0 0 8px ${regimeBanner.color}` }} />
              <span className="text-[10px] font-bold font-mono" style={{ color: regimeBanner.text }}>{regimeData.state || 'BULL_TREND'}</span>
              <Badge color={bannerColor}>{regimeData.conf ?? '--'}%</Badge>
            </div>
            <div className="flex items-center gap-2 text-[8px] text-gray-500">
              <span>Since: {regimeData.since ? new Date(regimeData.since).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '--'}</span>
              <span>|</span>
              <span>HMM Layer 3</span>
            </div>
            <div className="w-full h-1.5 bg-[#1e293b] rounded-full overflow-hidden mt-1.5">
              <div className="h-full rounded-full transition-all duration-500" style={{ width: `${regimeData.conf ?? 0}%`, backgroundColor: regimeBanner.color }} />
            </div>
          </Panel>
        </div>

        {/* ============================================================== */}
        {/* COLUMN 4: External Sensors + Execution + ML Model Control      */}
        {/* ============================================================== */}
        <div className="flex flex-col gap-1.5 overflow-hidden min-h-0">
          {/* External Sensors */}
          <Panel title="External Sensors" icon={Globe} className="flex-[3] min-h-0">
            {DATA_SOURCES.map(ds => (
              <div key={ds.id} className="flex items-center gap-2 py-0.5 border-b border-[#1e293b]/50 last:border-0">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dataSourceStates[ds.id].active ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)]' : 'bg-gray-600'}`} />
                <span className="text-[9px] text-gray-300 flex-1">{ds.name}</span>
                <Toggle checked={dataSourceStates[ds.id].active}
                  onChange={() => setDataSourceStates(p => ({...p, [ds.id]: {...p[ds.id], active: !p[ds.id].active}}))} size="sm" />
              </div>
            ))}
            <div className="flex items-center gap-2 py-0.5 border-b border-[#1e293b]/50">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-500 shrink-0" />
              <span className="text-[9px] text-gray-300 flex-1">Discord Listener</span>
              <Badge color="emerald">Connected</Badge>
            </div>
            <div className="flex items-center gap-2 py-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
              <span className="text-[9px] text-gray-300 flex-1">YouTube Agent</span>
              <Toggle checked={agentStates['youtube']?.active ?? true}
                onChange={() => handleToggleState('agent', 'youtube', agentStates['youtube']?.active ?? true)} size="sm" />
            </div>
          </Panel>

          {/* Execution & Automation Controls */}
          <Panel title="Execution & Automation Controls" icon={Rocket} className="flex-[4] min-h-0"
            headerAction={
              <Badge color={autoExecute ? 'emerald' : 'red'}>{autoExecute ? 'AUTO EXECUTION' : 'MANUAL'}</Badge>
            }>
            <div className="flex items-center gap-2 mb-1.5">
              <Toggle checked={autoExecute} onChange={setAutoExecute} />
              <span className={`text-[9px] font-bold ${autoExecute ? 'text-emerald-400' : 'text-gray-500'}`}>AUTO EXECUTION</span>
            </div>
            <div className="flex items-center gap-2 py-0.5">
              <span className="text-[9px] text-gray-500 w-24">Trading Mode</span>
              <select className="bg-[#1e293b] border border-[#374151] rounded px-2 py-0.5 text-[9px] outline-none text-red-400 font-bold flex-1" defaultValue="PAPER TRADING">
                <option>LIVE (ALPACA)</option><option>PAPER TRADING</option>
              </select>
            </div>
            <div className="flex items-center gap-2 py-0.5">
              <span className="text-[9px] text-gray-500 w-24">Position Sizer</span>
              <select className="bg-[#1e293b] border border-[#374151] rounded px-2 py-0.5 text-[9px] outline-none text-cyan-400 flex-1">
                <option>KELLY CRITERION</option><option>FIXED 2%</option><option>DYNAMIC VOL</option>
              </select>
            </div>
            <div className="mt-1.5">
              <Slider value={maxHeat} onChange={setMaxHeat} color="amber" label="Max Heat" />
            </div>
            <div className="mt-1">
              <Slider value={lossLimit} onChange={setLossLimit} color="red" label="Loss Lmt" />
            </div>
            <div className="text-[8px] text-gray-500 uppercase tracking-widest mt-2 mb-0.5">Active Rules (IF/THEN)</div>
            <div className="flex items-center gap-1 py-0.5">
              <Toggle checked={alertRules.comp_regime_stage} onChange={async (v) => {
                setAlertRules(p => ({ ...p, comp_regime_stage: v }));
                try {
                  await fetch(getApiUrl('settings/rules'), { method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify({ rule: 'comp_regime_stage', active: v }) });
                } catch (err) { log.error('Failed to update alert rule:', err); }
              }} size="sm" />
              <span className="text-[8px] text-gray-400">IF <Badge color="cyan">comp &gt; 90</Badge> AND <Badge color="emerald">regime=BULL</Badge> THEN stage</span>
            </div>
            <div className="flex items-center gap-1 py-0.5">
              <Toggle checked={alertRules.vix_halve_pos} onChange={async (v) => {
                setAlertRules(p => ({ ...p, vix_halve_pos: v }));
                try {
                  await fetch(getApiUrl('settings/rules'), { method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify({ rule: 'vix_halve_pos', active: v }) });
                } catch (err) { log.error('Failed to update alert rule:', err); }
              }} size="sm" />
              <span className="text-[8px] text-gray-400">IF <Badge color="red">VIX &gt; 25</Badge> THEN halve pos size</span>
            </div>
          </Panel>

          {/* ML Model Control (Layer 5) */}
          <Panel title="ML Model Control (Layer 5)" icon={Cpu} className="flex-[4] min-h-0"
            headerAction={
              <Badge color={flywheelData ? 'emerald' : 'gray'}>{flywheelData ? 'FLYWHEEL LIVE' : 'FLYWHEEL --'}</Badge>
            }>
            {ML_MODELS.map(model => (
              <div key={model.id} className="py-1 border-b border-[#1e293b]/50 last:border-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <Toggle checked={mlStates[model.id].active}
                    onChange={() => setMlStates(p => ({...p, [model.id]: {...p[model.id], active: !p[model.id].active}}))} size="sm" />
                  <span className="text-[9px] text-gray-300 font-bold">{model.name}</span>
                  <Badge color="gray">{model.version}</Badge>
                  <Badge color={mlStates[model.id].status === 'Ready' ? 'emerald' : mlStates[model.id].status === 'Training' ? 'amber' : 'gray'}>
                    {mlStates[model.id].status}
                  </Badge>
                  <button onClick={() => triggerRetrain(model.id)}
                    className="ml-auto px-1.5 py-0.5 bg-purple-500/20 text-purple-400 rounded text-[8px] hover:bg-purple-500 hover:text-white transition-colors">
                    RETRAIN
                  </button>
                </div>
              </div>
            ))}

            {/* System Telemetry */}
            <div className="mt-1.5 pt-1.5 border-t border-[#1e293b]">
              <div className="text-[8px] text-gray-500 uppercase tracking-widest mb-1">System Telemetry</div>
              <div className="grid grid-cols-2 gap-1">
                <div className="flex items-center justify-between">
                  <span className="text-[8px] text-gray-500">Active Models</span>
                  <span className="text-[9px] font-bold font-mono text-emerald-400">{mlControlsData.activeModels}/{ML_MODELS.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[8px] text-gray-500">Accuracy</span>
                  <span className="text-[9px] font-bold font-mono text-[#00D9FF]">
                    {mlControlsData.flywheelAccuracy != null ? `${(typeof mlControlsData.flywheelAccuracy === 'number' && mlControlsData.flywheelAccuracy <= 1 ? (mlControlsData.flywheelAccuracy * 100).toFixed(1) : mlControlsData.flywheelAccuracy)}%` : '--'}
                  </span>
                </div>
              </div>
            </div>

            {/* API Health minimap */}
            <div className="mt-1.5 pt-1.5 border-t border-[#1e293b]">
              <div className="text-[8px] text-gray-500 uppercase tracking-widest mb-1">API PRIORITY MAP ({API_ENDPOINTS.length})</div>
              <div className="grid grid-cols-7 gap-0.5">
                {API_ENDPOINTS.map((ep) => {
                  const health = apiStatus?.endpoints?.[ep];
                  const isWarn = health?.status === 'degraded' || health?.latency > 500;
                  const isErr = health?.status === 'down' || health?.error;
                  const bg = isErr ? 'bg-red-500 shadow-[0_0_3px_rgba(239,68,68,0.8)]'
                    : isWarn ? 'bg-amber-500 animate-pulse'
                    : 'bg-emerald-500 shadow-[0_0_3px_rgba(16,185,129,0.5)]';
                  return (
                    <div key={ep} className="flex flex-col items-center gap-0.5" title={ep}>
                      <span className={`w-2 h-2 rounded-full ${bg}`} />
                    </div>
                  );
                })}
              </div>
            </div>
          </Panel>
        </div>
      </div>

      {/* ================================================================== */}
      {/* BOTTOM STATUS BAR                                                  */}
      {/* ================================================================== */}
      <div className="flex items-center justify-between px-3 py-1 bg-[#111827] border-t border-[#1e293b] shrink-0 text-[8px] text-gray-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_4px_rgba(16,185,129,0.5)]" />
            {Object.values(agentStates).filter(a => a.active).length} Agents OK
          </span>
          <span className="flex items-center gap-1">
            <Database className="w-3 h-3 text-gray-600" />
            DB: {apiStatus?.db_latency_ms ?? '--'}ms
          </span>
          <span className="flex items-center gap-1">
            <HardDrive className="w-3 h-3 text-gray-600" />
            MEM: {apiStatus?.memory_pct ?? '--'}%
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span>Signals: {scannerMetrics.signalsToday}</span>
          <span>Hit Rate: {scannerMetrics.hitRate}%</span>
          <span>WS: {wsLatency}ms</span>
          <span className="text-gray-600">{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}


// ============================================================================
// EXPORTED SUB-COMPONENTS
// ============================================================================

// --- REACT FLOW CUSTOM NODES ---
const CustomFlowNode = ({ data }) => {
  const colors = {
    green: 'border-emerald-500 bg-emerald-500/10 text-emerald-400',
    yellow: 'border-amber-500 bg-amber-500/10 text-amber-400 animate-pulse',
    red: 'border-red-500 bg-red-500/10 text-red-400'
  };
  return (
    <div className={`px-3 py-2 rounded-lg border-2 ${colors[data.status] || colors.green} min-w-[140px] text-center`}>
      <Handle type="target" position="top" className="w-2 h-2" />
      <div className="text-[10px] font-bold">{data.label}</div>
      <div className="text-[8px] opacity-60">{data.subLabel}</div>
      <Handle type="source" position="bottom" className="w-2 h-2" />
    </div>
  );
};

const nodeTypes = { custom: CustomFlowNode };

export const AgentPipelineFlow = () => {
  const initialNodes = [
    { id: 'scan1', type: 'custom', position: { x: 50, y: 50 }, data: { label: 'Daily Scanner', subLabel: '15m Pipeline', status: 'green' } },
    { id: 'scan2', type: 'custom', position: { x: 250, y: 50 }, data: { label: 'Whale Flow', subLabel: 'UW Options', status: 'green' } },
    { id: 'intel1', type: 'custom', position: { x: 150, y: 150 }, data: { label: 'HMM Regime', subLabel: 'BULL_TREND', status: 'green' } },
    { id: 'agent1', type: 'custom', position: { x: 50, y: 250 }, data: { label: 'Relative Weakness', subLabel: 'Short Finding', status: 'yellow' } },
    { id: 'agent2', type: 'custom', position: { x: 250, y: 250 }, data: { label: 'Apex Orchestrator', subLabel: 'Master Coord', status: 'green' } },
    { id: 'score1', type: 'custom', position: { x: 150, y: 350 }, data: { label: 'Composite Scorer', subLabel: 'Pillar Weighting', status: 'green' } },
    { id: 'exec1', type: 'custom', position: { x: 150, y: 450 }, data: { label: 'Risk Governor', subLabel: 'Position Sizing', status: 'red' } }
  ];
  const initialEdges = [
    { id: 'e1', source: 'scan1', target: 'intel1', animated: true, style: { stroke: '#06b6d4' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#06b6d4' } },
    { id: 'e2', source: 'scan2', target: 'intel1', animated: true, style: { stroke: '#06b6d4' }, markerEnd: { type: MarkerType.ArrowClosed, color: '#06b6d4' } },
    { id: 'e3', source: 'intel1', target: 'agent1', animated: true, style: { stroke: '#10b981' } },
    { id: 'e4', source: 'intel1', target: 'agent2', animated: true, style: { stroke: '#10b981' } },
    { id: 'e5', source: 'agent1', target: 'score1', animated: true, style: { stroke: '#a855f7' } },
    { id: 'e6', source: 'agent2', target: 'score1', animated: true, style: { stroke: '#a855f7' } },
    { id: 'e7', source: 'score1', target: 'exec1', animated: true, style: { stroke: '#f59e0b' } }
  ];
  return (
    <div className="bg-[#111827] border border-[#1e293b] rounded-lg p-3">
      <h3 className="text-[10px] font-bold text-gray-300 uppercase tracking-widest mb-2">Agent Swarm Data Flow Pipeline</h3>
      <div style={{ height: 520 }}>
        <ReactFlow nodes={initialNodes} edges={initialEdges} nodeTypes={nodeTypes} fitView
          proOptions={{ hideAttribution: true }}>
          <Background color="#1e293b" gap={16} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
};

// --- ANALYTICS DASHBOARDS ROW (LW Charts - pending Step 7a) ---
export const AnalyticsDashboards = () => {
    const chartTitles = [
        '30-Day Signal Accuracy & PnL',
        'Multi-Factor Scoring Radar',
        'Agent Swarm Consensus Matrix',
        'Scanner Correlation'
    ];
    return (
        <div className="grid grid-cols-4 gap-2">
            {chartTitles.map((title, i) => (
                <div key={i} className="bg-[#111827] border border-[#1e293b] rounded-lg p-3">
                    <h3 className="text-[10px] font-bold text-gray-300 uppercase tracking-widest mb-2">{title}</h3>
                    <div className="h-[200px] flex items-center justify-center text-gray-500 text-xs border border-dashed border-[#1e293b] rounded">
                        <span>LW Charts pending</span>
                    </div>
                </div>
            ))}
        </div>
    );
};
