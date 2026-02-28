import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useApi } from '../hooks/useApi';
import { getApiUrl, getWsUrl, WS_CHANNELS } from '../config/api';
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
// CONSTANTS & INITIAL DATA
// ============================================================================

const CORE_AGENTS = [
  { id: 'apex', name: 'Apex Orchestrator', type: 'Core', defaultWeight: 100 },
  { id: 'rel_weak', name: 'Relative Weakness', type: 'Core', defaultWeight: 85 },
  { id: 'short_basket', name: 'Short Basket', type: 'Core', defaultWeight: 75 },
  { id: 'meta_arch', name: 'Meta Architect', type: 'Core', defaultWeight: 90 },
  { id: 'meta_alch', name: 'Meta Alchemist', type: 'Core', defaultWeight: 80 },
  { id: 'risk_gov', name: 'Risk Governor', type: 'Risk', defaultWeight: 100 },
  { id: 'sig_engine', name: 'Signal Engine', type: 'Engine', defaultWeight: 95 }
];

const EXTENDED_AGENTS = Array.from({ length: 93 }, (_, i) => ({
  id: `agent_${i + 8}`, name: `Agent #${i + 8} (Swarm)`, type: 'Swarm', defaultWeight: 25
}));

const ALL_AGENTS = [...CORE_AGENTS, ...EXTENDED_AGENTS];

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
  <div className={`bg-[#13131a] border border-[#1a1a2f] rounded-lg overflow-hidden flex flex-col ${className}`}>
    <div className="px-3 py-2 border-b border-[#1a1a2f] flex justify-between items-center bg-[#0d0d14] shrink-0">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-3.5 h-3.5 text-cyan-500 shrink-0" />}
        <h3 className="text-[10px] font-bold text-gray-300 uppercase tracking-widest">{title}</h3>
      </div>
      {headerAction && <div className="flex items-center gap-1">{headerAction}</div>}
    </div>
    <div className="p-2 flex-1 flex flex-col overflow-y-auto scrollbar-thin scrollbar-thumb-[#2a2a4a] scrollbar-track-transparent">
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
      className={`${w} ${h} rounded-full relative transition-colors duration-200 focus:outline-none shrink-0 ${checked ? 'bg-cyan-500' : 'bg-[#2a2a4a]'}`}>
      <span className={`absolute top-0.5 left-0.5 bg-white rounded-full transition-transform duration-200 ${dot} ${checked ? translate : 'translate-x-0'}`} />
    </button>
  );
};

const Slider = ({ value, onChange, color = 'cyan', label = '' }) => (
  <div className="flex items-center gap-1.5 flex-1">
    {label && <span className="text-[8px] text-gray-500 w-10 shrink-0">{label}</span>}
    <div className="relative flex-1 h-1 bg-[#1a1a2f] rounded-full">
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
    <div className="flex items-center gap-2 py-1 border-b border-[#1a1a2f]/50 last:border-0 hover:bg-[#1a1a2f]/40 px-0.5 rounded group">
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
  const { data: apiFlywheel } = useApi('flywheel', { pollIntervalMs: 30000 });
  const { data: apiPatterns } = useApi('patterns', { pollIntervalMs: 10000 });
  const { data: apiRisk } = useApi('risk', { pollIntervalMs: 10000 });
  const { data: apiAlerts } = useApi('alerts', { pollIntervalMs: 10000 });
  const { data: apiStatus } = useApi('status', { pollIntervalMs: 15000 });
  const { data: apiPerf } = useApi('performance', { pollIntervalMs: 30000 });
  const { data: apiMarket } = useApi('market', { pollIntervalMs: 5000 });
  const { data: apiPortfolio } = useApi('portfolio', { pollIntervalMs: 10000 });
  const { data: apiStrategy } = useApi('strategy', { pollIntervalMs: 30000 });

  // --- LOCAL STATE ---
  const [agentStates, setAgentStates] = useState(() =>
    ALL_AGENTS.reduce((acc, agent) => ({ ...acc, [agent.id]: { active: true, weight: agent.defaultWeight, status: 'green' } }), {})
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

  // --- LIGHTWEIGHT CHARTS SETUP ---
  useEffect(() => {
    if (!chartContainerRef.current || chartRef.current) return;
    const chart = createChart(chartContainerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: '#9ca3af', fontFamily: 'JetBrains Mono' },
      grid: { vertLines: { color: '#1a1a2f', style: LineStyle.SparseDotted }, horzLines: { color: '#1a1a2f', style: LineStyle.SparseDotted } },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { borderColor: '#2a2a4a', timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: '#2a2a4a' },
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
    const vwap = chart.addLineSeries({ color: '#ffffff', lineWidth: 1, lineStyle: LineStyle.Dotted, title: 'VWAP' });
        // Fetch real OHLCV data from backend quotes API
    const fetchChart = async () => {
      try {
        const url = getApiUrl ? getApiUrl('quotes') + `/${selectedSymbol}?timeframe=${chartTimeframe}` : `/api/v1/quotes/${selectedSymbol}?timeframe=${chartTimeframe}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Quote fetch failed');
        const json = await res.json();
        const bars = json.bars || json.data || json || [];
        if (bars.length === 0) return;
        const data = bars.map(b => ({ time: Math.floor(new Date(b.timestamp || b.t).getTime() / 1000), open: b.open || b.o, high: b.high || b.h, low: b.low || b.l, close: b.close || b.c }));
        const volData = bars.map((b, i) => ({ time: data[i].time, value: b.volume || b.v || 0, color: data[i].close >= data[i].open ? '#10b98144' : '#ef444444' }));
        // Compute SMA20, SMA50, VWAP from real data
        const s20 = []; const s50 = []; const vwapData = [];
        let cumVol = 0, cumVolPrice = 0;
        data.forEach((d, i) => {
          const vol = bars[i].volume || bars[i].v || 0;
          const tp = (d.high + d.low + d.close) / 3;
          cumVol += vol; cumVolPrice += tp * vol;
          if (cumVol > 0) vwapData.push({ time: d.time, value: cumVolPrice / cumVol });
          if (i >= 19) s20.push({ time: d.time, value: data.slice(i - 19, i + 1).reduce((a, b) => a + b.close, 0) / 20 });
          if (i >= 49) s50.push({ time: d.time, value: data.slice(i - 49, i + 1).reduce((a, b) => a + b.close, 0) / 50 });
        });
        candleSeries.setData(data); volSeries.setData(volData);
        sma20.setData(s20); sma50.setData(s50); vwap.setData(vwapData);
        const lastPrice = data[data.length - 1].close;
        candleSeries.createPriceLine({ price: lastPrice, color: '#06b6d4', lineWidth: 2, lineStyle: LineStyle.Solid, title: 'ENTRY' });
        candleSeries.createPriceLine({ price: lastPrice * 1.05, color: '#10b981', lineWidth: 2, lineStyle: LineStyle.Dashed, title: 'TARGET' });
        candleSeries.createPriceLine({ price: lastPrice * 0.98, color: '#ef4444', lineWidth: 2, lineStyle: LineStyle.Dotted, title: 'STOP' });
      } catch (err) { console.error('Chart data fetch error:', err); }
    };
    fetchChart();
    chartRef.current = chart;
    const handleResize = () => { if (chartContainerRef.current) chart.applyOptions({ width: chartContainerRef.current.clientWidth }); };
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); chartRef.current = null; };
  }, []);

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
      const url = getApiUrl ? getApiUrl(`/api/v1/${category}s/${id}/weight`) : `/api/v1/${category}s/${id}/weight`;
      await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ weight: value }) });
    } catch (err) { console.error(`Failed to update ${category} weight:`, err); }
  }, []);

  const handleToggleState = useCallback(async (category, id, currentState) => {
    const newState = !currentState;
    if (category === 'agent') setAgentStates(p => ({ ...p, [id]: { ...p[id], active: newState } }));
    else if (category === 'scanner') setScannerStates(p => ({ ...p, [id]: { ...p[id], active: newState } }));
    else if (category === 'intel') setIntelStates(p => ({ ...p, [id]: { ...p[id], active: newState } }));
    try {
      const url = getApiUrl ? getApiUrl(`/api/v1/${category}s/${id}/toggle`) : `/api/v1/${category}s/${id}/toggle`;
      await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ active: newState }) });
    } catch (err) { console.error(`Failed to toggle ${category}:`, err); }
  }, []);

  const triggerScan = useCallback(async (id) => {
    try {
      setScannerStates(p => ({ ...p, [id]: { ...p[id], status: 'yellow' } }));
      const url = getApiUrl ? getApiUrl('openclaw') + '/scan' : '/api/v1/openclaw/scan';
      await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scannerId: id }) });
      setTimeout(() => { setScannerStates(p => ({ ...p, [id]: { ...p[id], status: 'green', runs: p[id].runs + 1 } })); }, 1500);
    } catch (e) { setScannerStates(p => ({ ...p, [id]: { ...p[id], status: 'red' } })); }
  }, []);

  const triggerRetrain = useCallback(async (id) => {
    try {
      setMlStates(p => ({ ...p, [id]: { ...p[id], status: 'Training' } }));
      const url = getApiUrl ? getApiUrl('training') + '/retrain' : '/api/v1/training/retrain';
      await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ modelId: id }) });
    } catch (e) { console.error(e); }
  }, []);

  // --- DERIVED DATA ---
  const regimeData = useMemo(() => apiOpenclaw?.regime || { state: 'BULL_TREND', conf: 87, color: 'emerald' }, [apiOpenclaw]);
  const bannerColor = regimeData.state?.includes('BULL') ? 'emerald' : regimeData.state?.includes('BEAR') ? 'red' : 'amber';
  const timeframes = ['1m', '5m', '15m', '1H', '4H', '1D', '1W'];

  // --- RENDER ---
  return (
    <div className="min-h-screen bg-[#0a0a12] text-gray-200 font-mono">
      {/* TOP TOOLBAR */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#0d0d14] border-b border-[#1a1a2f] sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Activity className="w-4 h-4 text-cyan-500" />
          <span className="text-sm font-bold text-cyan-400 tracking-wider">SIGNAL_INTELLIGENCE_V3</span>
        </div>
        <div className="flex items-center gap-3 text-[9px] text-gray-500">
          <Badge color="cyan">OC_CORE_v5.2.1</Badge>
          <Badge color={wsLatency < 100 ? 'emerald' : 'amber'}>WS_LATENCY: {wsLatency}ms</Badge>
          <Badge color="purple">SWARM_SIZE: {ALL_AGENTS.length}</Badge>
          <button className="flex items-center gap-1 px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400 hover:bg-cyan-500/20 transition-colors">
            <Save className="w-3 h-3" /> Save Profile
          </button>
        </div>
      </div>

      {/* REGIME BANNER */}
      <div className={`flex items-center justify-between px-4 py-1.5 bg-${bannerColor}-500/5 border-b border-${bannerColor}-500/20`}>
        <div className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full bg-${bannerColor}-500 shadow-[0_0_8px] shadow-${bannerColor}-500/50 animate-pulse`} />
          <span className={`text-xs font-bold text-${bannerColor}-400 tracking-wider`}>{regimeData.state} REGIME</span>
          <span className="text-[9px] text-gray-600">Hidden Markov Model (Layer 3)</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-[9px] text-gray-500">HMM Confidence</span>
            <span className={`text-xs font-bold text-${bannerColor}-400`}>{regimeData.conf}%</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[9px] text-gray-500">Override</span>
            <Toggle checked={regimeLock} onChange={setRegimeLock} size="sm" />
            {regimeLock ? <Lock className="w-3 h-3 text-amber-500" /> : <Unlock className="w-3 h-3 text-gray-600" />}
          </div>
        </div>
      </div>

      {/* 4-COLUMN PANORAMIC GRID */}
      <div className="grid grid-cols-[20%_30%_25%_25%] gap-2 p-2 h-[calc(100vh-80px)]">

        {/* COL 1: AGENTS & SCANNERS (20%) */}
        <div className="flex flex-col gap-2 overflow-y-auto">
          <Panel title="Scanner Modules" icon={Search} className="max-h-[45%]">
            {SCANNERS.map(scan => (
              <div key={scan.id} className="flex items-center gap-1.5 py-1 border-b border-[#1a1a2f]/50 last:border-0 hover:bg-[#1a1a2f]/40 px-0.5 rounded">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                  scannerStates[scan.id].status === 'green' ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.7)]'
                  : scannerStates[scan.id].status === 'yellow' ? 'bg-amber-500 animate-pulse'
                  : 'bg-red-500'}`} />
                <span className="text-[9px] text-gray-300 truncate w-20 shrink-0">{scan.name}</span>
                <button onClick={() => triggerScan(scan.id)} className="text-gray-500 hover:text-cyan-400">
                  <Play className="w-2.5 h-2.5" />
                </button>
                <Toggle checked={scannerStates[scan.id].active} onChange={(v) => handleToggleState('scanner', scan.id, !v)} size="sm" />
                <Slider value={scannerStates[scan.id].weight} onChange={(v) => handleUpdateWeight('scanner', scan.id, v)} />
                <span className="text-[8px] text-gray-600">Runs: {scannerStates[scan.id].runs}</span>
              </div>
            ))}
          </Panel>

          <Panel title="OpenClaw Agent Swarm" icon={Cpu} className="flex-1">
            <div className="text-[8px] text-gray-500 mb-1 uppercase tracking-widest">CORE AGENTS (7)</div>
            {CORE_AGENTS.map(agent => (
              <ControlRow key={agent.id} title={agent.name}
                isActive={agentStates[agent.id].active}
                onToggle={(v) => handleToggleState('agent', agent.id, !v)}
                weight={agentStates[agent.id].weight}
                onWeightChange={(v) => handleUpdateWeight('agent', agent.id, v)} />
            ))}
            <div className="flex items-center justify-between mt-2 mb-1">
              <span className="text-[8px] text-gray-500 uppercase tracking-widest">EXTENDED SWARM (93)</span>
              <span className="text-[8px] text-cyan-600">SCROLL</span>
            </div>
            <div className="max-h-[200px] overflow-y-auto">
              {EXTENDED_AGENTS.map(agent => (
                <ControlRow key={agent.id} title={agent.name}
                  isActive={agentStates[agent.id].active}
                  onToggle={(v) => handleToggleState('agent', agent.id, !v)}
                  weight={agentStates[agent.id].weight}
                  onWeightChange={(v) => handleUpdateWeight('agent', agent.id, v)} />
              ))}
            </div>
          </Panel>
        </div>

        {/* COL 2: CHART & SIGNALS (30%) */}
        <div className="flex flex-col gap-2 overflow-y-auto">
          <Panel title={`${selectedSymbol} ${chartTimeframe} PATTERNS: ON`} icon={Crosshair} className="h-[55%]"
            headerAction={
              <div className="flex gap-1">
                {timeframes.map(t => (
                  <button key={t} onClick={() => setChartTimeframe(t)}
                    className={`px-1.5 py-0.5 rounded text-[9px] font-mono border ${chartTimeframe === t ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400' : 'bg-[#1a1a2f] border-[#2a2a4a] text-gray-500 hover:text-gray-300'}`}>{t}</button>
                ))}
              </div>
            }>
            <div ref={chartContainerRef} className="w-full h-full min-h-[300px]" />
          </Panel>

          <Panel title="Signal Data Table" icon={FileText} className="flex-1">
            <div className="overflow-x-auto">
              <table className="w-full text-[9px]">
                <thead>
                  <tr className="text-gray-500 border-b border-[#1a1a2f]">
                    <th className="text-left py-1 px-1">Symbol</th>
                    <th className="text-left py-1">Score</th>
                    <th className="text-left py-1">Dir</th>
                    <th className="text-left py-1">Price</th>
                    <th className="text-left py-1">Agent</th>
                                      <th className="text-left py-1 px-1">Kelly</th>
                  <th className="text-left py-1 px-1">Quality</th>
                    <th className="text-left py-1">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.map((sig, idx) => (
                    <tr key={sig.id || idx} className="border-b border-[#1a1a2f]/30 hover:bg-[#1a1a2f]/40 cursor-pointer"
                      onClick={() => setSelectedSymbol(sig.symbol)}>
                      <td className={`py-1 px-1 font-bold ${sig.score > 80 ? 'text-cyan-400' : 'text-gray-300'}`}>{sig.symbol}</td>
                      <td className="py-1">
                        <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${sig.score >= 90 ? 'bg-emerald-500/20 text-emerald-400' : sig.score <= 40 ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}`}>{sig.score}</span>
                      </td>
                      <td className={`py-1 font-bold ${sig.dir === 'LONG' ? 'text-emerald-400' : 'text-red-400'}`}>{sig.dir}</td>
                      <td className="py-1 text-gray-300">{typeof sig.price === 'number' ? sig.price.toFixed(2) : sig.price}</td>
                      <td className="py-1 text-gray-500">{sig.agent}</td>
                                      <td className="py-1 text-cyan-400">{sig.kelly_edge ? `${(sig.kelly_edge * 100).toFixed(1)}%` : '-'}</td>
                <td className="py-1">
                  {sig.signal_quality ? (
                    <span className={`px-1 rounded text-[8px] font-bold ${sig.signal_quality >= 0.7 ? 'bg-emerald-500/20 text-emerald-400' : sig.signal_quality >= 0.4 ? 'bg-amber-500/20 text-amber-400' : 'bg-red-500/20 text-red-400'}`}>
                      {(sig.signal_quality * 100).toFixed(0)}%
                    </span>
                  ) : '-'}
                </td>
                      <td className="py-1">
                        <button className="text-cyan-500 hover:text-cyan-300"><Eye className="w-2.5 h-2.5" /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        {/* COL 3: INTEL, SCORING, ML (25%) */}
        <div className="flex flex-col gap-2 overflow-y-auto">
          <Panel title="Scoring Engine" icon={Target}>
            <div className="flex items-center justify-between text-[9px] mb-2">
              <Badge color="cyan">OpenClaw Core</Badge>
              <Badge color="purple">Tech Analysis</Badge>
            </div>
            <input type="range" min="0" max="100" value={scoringFormula.ocTaBlend}
              onChange={(e) => setScoringFormula(p => ({...p, ocTaBlend: parseInt(e.target.value)}))}
              className="w-full h-1.5 appearance-none bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full cursor-pointer" />
            <div className="text-center text-[9px] text-gray-400 mt-1">{scoringFormula.ocTaBlend} / {100 - scoringFormula.ocTaBlend}</div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-[9px] text-gray-500 w-28">Regime Multiplier</span>
              <input type="number" step="0.1" value={scoringFormula.regimeMultiplier}
                onChange={(e) => setScoringFormula(p => ({...p, regimeMultiplier: parseFloat(e.target.value) || 1}))}
                className="bg-[#1a1a2f] border border-[#2a2a4a] rounded px-2 py-0.5 text-[9px] text-cyan-400 font-bold w-16 outline-none" />
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[9px] text-gray-500 w-28">SLAM DUNK Tier</span>
              <input type="number" value={scoringFormula.tierSlamDunk}
                onChange={(e) => setScoringFormula(p => ({...p, tierSlamDunk: parseInt(e.target.value) || 90}))}
                className="bg-[#1a1a2f] border border-[#2a2a4a] rounded px-2 py-0.5 text-[9px] text-emerald-400 font-bold w-16 outline-none" />
            </div>
            <div className="mt-3 text-[8px] text-gray-500 uppercase tracking-widest mb-1">PER-FACTOR SHAP WEIGHTS</div>
            {SHAP_FACTORS.map(factor => (
              <ControlRow key={factor} title={factor}
                isActive={true} onToggle={() => {}}
                weight={shapWeights[factor]}
                onWeightChange={(v) => handleUpdateWeight('shap', factor, v)} />
            ))}
          </Panel>

          <Panel title="Intelligence Layer" icon={Shield}>
            {INTEL_MODULES.map(mod => (
              <ControlRow key={mod.id} title={mod.name}
                isActive={intelStates[mod.id].active}
                onToggle={(v) => handleToggleState('intel', mod.id, !v)}
                weight={intelStates[mod.id].weight}
                onWeightChange={(v) => handleUpdateWeight('intel', mod.id, v)} />
            ))}
          </Panel>

          <Panel title="ML/AI Models" icon={Cpu}>
            {ML_MODELS.map(model => (
              <div key={model.id} className="py-1.5 border-b border-[#1a1a2f]/50 last:border-0">
                <div className="flex items-center gap-2 mb-1">
                  <Toggle checked={mlStates[model.id].active}
                    onChange={() => setMlStates(p => ({...p, [model.id]: {...p[model.id], active: !p[model.id].active}}))} size="sm" />
                  <span className="text-[9px] text-gray-300 font-bold">{model.name}</span>
                  <Badge color="gray">{model.version}</Badge>
                  <Badge color={mlStates[model.id].status === 'Ready' ? 'emerald' : mlStates[model.id].status === 'Training' ? 'amber' : 'gray'}>
                    {mlStates[model.id].status}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[8px] text-gray-600">Conf Thresh</span>
                  <input type="range" min="0" max="100" value={mlStates[model.id].confThreshold}
                    onChange={(e) => setMlStates(p => ({...p, [model.id]: {...p[model.id], confThreshold: parseInt(e.target.value)}}))}
                    className="flex-1 h-1 bg-[#0d0d14] rounded-full appearance-none accent-purple-500" />
                  <span className="text-[8px] text-gray-400">{mlStates[model.id].confThreshold}%</span>
                  <button onClick={() => triggerRetrain(model.id)}
                    className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-[8px] hover:bg-purple-500 hover:text-white transition-colors">
                    RETRAIN
                  </button>
                </div>
              </div>
            ))}
          </Panel>
        </div>

        {/* COL 4: SOCIAL, EXECUTION, APIS (25%) */}
        <div className="flex flex-col gap-2 overflow-y-auto">
          <Panel title="Social & Data Feeds" icon={Globe}>
            {DATA_SOURCES.map(ds => (
              <div key={ds.id} className="flex items-center gap-2 py-1 border-b border-[#1a1a2f]/50 last:border-0">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                <span className="text-[9px] text-gray-300 flex-1">{ds.name}</span>
                <Toggle checked={dataSourceStates[ds.id].active}
                  onChange={() => setDataSourceStates(p => ({...p, [ds.id]: {...p[ds.id], active: !p[ds.id].active}}))} size="sm" />
              </div>
            ))}
            <div className="flex items-center gap-2 py-1 border-b border-[#1a1a2f]/50">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-500 shrink-0" />
              <span className="text-[9px] text-gray-300 flex-1">Discord Listener</span>
              <Badge color="emerald">Connected</Badge>
            </div>
            <input type="text" placeholder="Watch Channels (comma sep)"
              className="w-full bg-[#1a1a2f] border border-[#2a2a4a] rounded p-1.5 text-[9px] text-gray-300 outline-none focus:border-purple-500 mt-1"
              defaultValue="options-flow, alerts-pro" />
            <div className="flex items-center gap-2 py-1 mt-1">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
              <span className="text-[9px] text-gray-300 flex-1">YouTube Agent</span>
              <Toggle checked={true} onChange={() => {}} size="sm" />
            </div>
          </Panel>

          <Panel title="Execution Controls" icon={Rocket}>
            <div className="flex items-center gap-2 mb-2">
              <Toggle checked={autoExecute} onChange={setAutoExecute} />
              <span className={`text-[9px] font-bold ${autoExecute ? 'text-emerald-400' : 'text-gray-500'}`}>AUTO EXECUTION</span>
            </div>
            <div className="flex items-center gap-2 py-1">
              <span className="text-[9px] text-gray-500 w-24">Trading Mode</span>
              <select className="bg-[#1a1a2f] border border-[#2a2a4a] rounded px-2 py-1 text-[9px] outline-none text-emerald-400 font-bold flex-1">
                <option>PAPER TRADING</option><option>LIVE (ALPACA)</option>
              </select>
            </div>
            <div className="flex items-center gap-2 py-1">
              <span className="text-[9px] text-gray-500 w-24">Position Sizer</span>
              <select className="bg-[#1a1a2f] border border-[#2a2a4a] rounded px-2 py-1 text-[9px] outline-none text-cyan-400 flex-1">
                <option>KELLY CRITERION</option><option>FIXED 2%</option><option>DYNAMIC VOL</option>
              </select>
            </div>
                      <Slider value={maxHeat} onChange={setMaxHeat} color="amber" label="Max Heat" />
            <Slider value={lossLimit} onChange={setLossLimit} color="red" label="Loss Lmt" />
            <div className="text-[8px] text-gray-500 uppercase tracking-widest mt-2 mb-1">Active Rules (IF/THEN)</div>
            <div className="flex items-center gap-1 py-0.5">
              <Toggle checked={true} onChange={() => {}} size="sm" />
              <span className="text-[8px] text-gray-400">IF <Badge color="cyan">comp &gt; 90</Badge> AND <Badge color="emerald">regime=BULL</Badge> THEN stage</span>
            </div>
            <div className="flex items-center gap-1 py-0.5">
              <Toggle checked={true} onChange={() => {}} size="sm" />
              <span className="text-[8px] text-gray-400">IF <Badge color="red">VIX &gt; 25</Badge> THEN halve pos size</span>
            </div>
          </Panel>

          <Panel title="API Health Matrix (28)" icon={Server}>
            <div className="grid grid-cols-7 gap-1">
              {API_ENDPOINTS.map((ep, i) => {
                              const health = apiStatus?.endpoints?.[ep];
              const isWarn = health?.status === 'degraded' || health?.latency > 500;
              const isErr = health?.status === 'down' || health?.error;
                            const bg = isErr ? 'bg-red-500 shadow-[0_0_5px_rgba(239,68,68,0.8)]'
                  : isWarn ? 'bg-amber-500 shadow-[0_0_5px_rgba(245,158,11,0.8)] animate-pulse'
                  : 'bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]';
                return (
                  <div key={ep} className="flex flex-col items-center gap-0.5" title={ep}>
                    <span className={`w-2.5 h-2.5 rounded-full ${bg}`} />
                    <span className="text-[7px] text-gray-600 truncate w-full text-center">{ep.substring(0,6)}</span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center gap-3 mt-2 pt-1 border-t border-[#1a1a2f]">
                            <Badge color="emerald">DB: {apiStatus?.db_latency_ms ?? '—'}ms</Badge>
              <Badge color="cyan">MEM: {apiStatus?.memory_pct ?? '—'}%</Badge>
            </div>
          </Panel>
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
    <div className="bg-[#13131a] border border-[#1a1a2f] rounded-lg p-3">
      <h3 className="text-[10px] font-bold text-gray-300 uppercase tracking-widest mb-2">Agent Swarm Data Flow Pipeline</h3>
      <div style={{ height: 520 }}>
        <ReactFlow nodes={initialNodes} edges={initialEdges} nodeTypes={nodeTypes} fitView
          proOptions={{ hideAttribution: true }}>
          <Background color="#1a1a2f" gap={16} />
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
                <div key={i} className="bg-[#13131a] border border-[#1a1a2f] rounded-lg p-3">
                    <h3 className="text-[10px] font-bold text-gray-300 uppercase tracking-widest mb-2">{title}</h3>
                    <div className="h-[200px] flex items-center justify-center text-gray-500 text-xs border border-dashed border-[#1e3a5f] rounded">
                        <span>LW Charts pending</span>
                    </div>
                </div>
            ))}
        </div>
    );
};

