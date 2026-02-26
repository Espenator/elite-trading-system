import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useApi } from '../hooks/useApi';
import { getApiUrl, getWsUrl, WS_CHANNELS } from '../config/api';
import { createChart, CrosshairMode, LineStyle } from 'lightweight-charts';
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  BarChart, Bar, Cell, RadarChart, PolarGrid, PolarAngleAxis, 
  PolarRadiusAxis, Radar, ScatterChart, Scatter, CartesianGrid 
} from 'recharts';
import { 
  Activity, AlertTriangle, Cpu, Network, Zap, TrendingUp, TrendingDown, 
  Clock, Shield, Database, GitMerge, Radio, Server, Layers, BarChart2, 
  Eye, Sliders, Globe, MessageSquare, Play, Square, RefreshCw, CheckCircle, 
  XCircle, Rocket, FileText, Download, Share2, Search, Crosshair, Lock, 
  Unlock, Save, Power, Wifi, HardDrive, Filter, Target, Maximize2
} from 'lucide-react';
import ReactFlow, { Background, Controls, MarkerType, Handle } from 'reactflow';
import 'reactflow/dist/style.css';

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
  id: `agent_${i + 8}`, name: `Agent #${i + 8} (Swarm)`, type: 'Swarm', defaultWeight: Math.floor(Math.random() * 40 + 10)
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
  { id: 'ml_lstm', name: 'LSTM Daily', version: 'v4.2.1', status: 'Ready' },
  { id: 'ml_xgb', name: 'XGBoost GPU', version: 'v2.8.0', status: 'Ready' },
  { id: 'ml_river', name: 'River Online', version: 'v1.1.5', status: 'Training' },
  { id: 'ml_infer', name: 'Inference Engine', version: 'v3.0.0', status: 'Ready' },
  { id: 'ml_wfv', name: 'Walk-Forward Val', version: 'v1.0.2', status: 'Idle' },
  { id: 'ml_pipe', name: 'ML Pipeline', version: 'v5.1.0', status: 'Ready' }
];

const DATA_SOURCES = [
  { id: 'ds_twitter', name: 'Twitter/X API' },
  { id: 'ds_reddit', name: 'Reddit API' },
  { id: 'ds_news', name: 'NewsAPI' },
  { id: 'ds_benzinga', name: 'Benzinga Pro' },
  { id: 'ds_rss', name: 'RSS Aggregator' }
];

const API_ENDPOINTS = [
  'agents', 'alerts', 'backtest_routes', 'data_sources', 'flywheel', 'logs', 
  'market', 'ml_brain', 'openclaw', 'orders', 'patterns', 'performance', 
  'portfolio', 'quotes', 'risk', 'risk_shield_api', 'sentiment', 'settings_routes', 
  'signals', 'status', 'stocks', 'strategy', 'system', 'training', 'youtube_knowledge',
  'websocket_stream', 'auth_bridge', 'external_webhooks'
];

const SHAP_FACTORS = [
  'UW Options Flow', 'Velez Score', 'Volume Surge', 'Whale Flow', 
  'RSI Divergence', 'HTF Structure', 'Compression', 'Sector Momentum'
];

// ============================================================================
// REUSABLE UI COMPONENTS
// ============================================================================

const Panel = ({ title, icon: Icon, children, className = '', headerAction = null }) => (
  <div className={`bg-[#13131a] border border-[#1a1a2f] rounded-lg overflow-hidden flex flex-col ${className}`}>
    <div className="px-3 py-2 border-b border-[#1a1a2f] flex justify-between items-center bg-[#0d0d14]">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-3.5 h-3.5 text-cyan-500" />}
        <h3 className="text-[11px] font-bold font-mono text-gray-300 uppercase tracking-widest">{title}</h3>
      </div>
      {headerAction && <div>{headerAction}</div>}
    </div>
    <div className="p-3 flex-1 flex flex-col overflow-y-auto custom-scrollbar">
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
    <button 
      type="button"
      onClick={() => onChange(!checked)}
      className={`${w} ${h} rounded-full relative transition-colors duration-200 focus:outline-none ${checked ? 'bg-cyan-500' : 'bg-[#2a2a4a]'}`}
    >
      <span className={`absolute top-0.5 left-0.5 bg-white rounded-full transition-transform duration-200 ${dot} ${checked ? translate : 'translate-x-0'}`} />
    </button>
  );
};

const Slider = ({ value, onChange, color = 'cyan', label = '' }) => (
  <div className="flex items-center gap-2 flex-1">
    {label && <span className="text-[9px] font-mono text-gray-500 w-8">{label}</span>}
    <input 
      type="range" min="0" max="100" value={value} 
      onChange={(e) => onChange(parseInt(e.target.value))}
      className={`w-full h-1 appearance-none bg-[#1a1a2f] rounded-full accent-${color}-500 cursor-pointer`}
      style={{
        background: `linear-gradient(to right, ${color === 'cyan' ? '#06b6d4' : color === 'emerald' ? '#10b981' : '#f59e0b'} ${value}%, #1a1a2f ${value}%)`
      }}
    />
    <span className="text-[9px] font-mono text-gray-400 w-6 text-right">{value}%</span>
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
    <div className="flex items-center justify-between gap-3 py-1.5 border-b border-[#1a1a2f] last:border-0 hover:bg-[#1a1a2f]/50 px-1 rounded transition-colors">
      <div className="flex items-center gap-2 w-1/3">
        <span className={`w-1.5 h-1.5 rounded-full ${isActive ? colors[statusColor] : colors.gray}`} />
        <span className="text-[10px] font-mono text-gray-300 truncate" title={title}>{title}</span>
      </div>
      <div className="w-10 flex justify-center">
        <Toggle checked={isActive} onChange={onToggle} size="sm" />
      </div>
      <div className="flex-1">
        <Slider value={weight} onChange={onWeightChange} />
      </div>
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
  return (
    <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono border ${colors[color]}`}>
      {children}
    </span>
  );
};

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

export default function SignalIntelligenceV3() {
  // --- REAL API HOOKS ---
  const { data: apiSignals, isLoading: sigLoading } = useApi('signals', { pollIntervalMs: 2000 });
  const { data: apiAgents } = useApi('agents');
  const { data: apiOpenclaw } = useApi('openclaw');
  const { data: apiDataSources } = useApi('dataSources');
  const { data: apiSentiment } = useApi('sentiment');
  const { data: apiYoutube } = useApi('youtubeKnowledge');
  const { data: apiTraining } = useApi('training');
  const { data: apiFlywheel } = useApi('flywheel');
  const { data: apiPatterns } = useApi('patterns');
  const { data: apiRisk } = useApi('risk');
  const { data: apiAlerts } = useApi('alerts');
  const { data: apiStatus } = useApi('status');
  const { data: apiPerf } = useApi('performance');
  const { data: apiMarket } = useApi('market');
  const { data: apiPortfolio } = useApi('portfolio');
  const { data: apiStrategy } = useApi('strategy');

  // --- LOCAL STATE (Optimistic UI & Control Mapping) ---
  
  // A. Agents
  const [agentStates, setAgentStates] = useState(() => 
    ALL_AGENTS.reduce((acc, agent) => ({
      ...acc, 
      [agent.id]: { active: true, weight: agent.defaultWeight, status: 'green' }
    }), {})
  );

  // B. Scanners
  const [scannerStates, setScannerStates] = useState(() =>
    SCANNERS.reduce((acc, scan) => ({
      ...acc,
      [scan.id]: { active: true, weight: scan.defaultWeight, status: 'green', runs: 0 }
    }), {})
  );

  // C. Intelligence
  const [intelStates, setIntelStates] = useState(() =>
    INTEL_MODULES.reduce((acc, mod) => ({
      ...acc,
      [mod.id]: { active: true, weight: mod.defaultWeight, status: 'green' }
    }), {})
  );

  // D. Scoring Weights
  const [scoringFormula, setScoringFormula] = useState({
    ocTaBlend: 60,
    tierSlamDunk: 90,
    tierStrongGo: 75,
    tierWatch: 60,
    regimeMultiplier: 1.2
  });

  const [shapWeights, setShapWeights] = useState(() =>
    SHAP_FACTORS.reduce((acc, factor) => ({ ...acc, [factor]: 50 }), {})
  );

  // E. ML Models
  const [mlStates, setMlStates] = useState(() =>
    ML_MODELS.reduce((acc, mod) => ({
      ...acc,
      [mod.id]: { active: true, confThreshold: 75, retrainRequested: false }
    }), {})
  );

  // F. Data Sources / Social
  const [dataSourceStates, setDataSourceStates] = useState(() =>
    DATA_SOURCES.reduce((acc, ds) => ({
      ...acc,
      [ds.id]: { active: true, weight: 100 }
    }), {})
  );

  // General State
  const [regimeLock, setRegimeLock] = useState(false);
  const [autoExecute, setAutoExecute] = useState(false);
  const [wsLatency, setWsLatency] = useState(42);
  const [signals, setSignals] = useState([]);

  // Chart References
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candlestickSeriesRef = useRef(null);

  // --- WEBSOCKET & EFFECTS ---

  useEffect(() => {
    // Connect WebSockets for Real-time
    const sigWsUrl = getWsUrl ? getWsUrl(WS_CHANNELS?.signals || 'signals') : 'wss://localhost/ws/signals';
    const sigSocket = new WebSocket(sigWsUrl);
    
    sigSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'signal') {
          setSignals(prev => [data.payload, ...prev].slice(0, 50));
        } else if (data.type === 'ping') {
          setWsLatency(data.latency);
        }
      } catch (e) { /* Ignore parsing errors in mock */ }
    };

    // Lightweight Charts Setup
    if (chartContainerRef.current && !chartRef.current) {
      const chart = createChart(chartContainerRef.current, {
        layout: { background: { color: 'transparent' }, textColor: '#9ca3af', fontFamily: 'JetBrains Mono' },
        grid: { vertLines: { color: '#1a1a2f', style: LineStyle.SparseDotted }, horzLines: { color: '#1a1a2f', style: LineStyle.SparseDotted } },
        crosshair: { mode: CrosshairMode.Normal },
        timeScale: { borderColor: '#2a2a4a', timeVisible: true, secondsVisible: false },
        rightPriceScale: { borderColor: '#2a2a4a' },
      });
      
      const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#10b981', downColor: '#ef4444', borderVisible: false,
        wickUpColor: '#10b981', wickDownColor: '#ef4444'
      });

      // Generate realistic mock OHLC data
      const generateData = () => {
        let data = [];
        let base = 450;
        let time = Math.floor(Date.now() / 1000) - 86400 * 100;
        for (let i = 0; i < 100; i++) {
          const open = base + (Math.random() - 0.5) * 10;
          const close = open + (Math.random() - 0.5) * 15 + (i > 50 ? 1 : -0.5); // Trend up later
          const high = Math.max(open, close) + Math.random() * 5;
          const low = Math.min(open, close) - Math.random() * 5;
          data.push({ time: time + i * 86400, open, high, low, close });
          base = close;
        }
        return data;
      };
      
      const chartData = generateData();
      candlestickSeries.setData(chartData);

      // Add Pattern Overlays (Section I)
      candlestickSeries.setMarkers([
        { time: chartData[30].time, position: 'aboveBar', color: '#ef4444', shape: 'arrowDown', text: 'H&S Top [92%]' },
        { time: chartData[60].time, position: 'belowBar', color: '#10b981', shape: 'arrowUp', text: 'Bull Flag [88%]' },
        { time: chartData[90].time, position: 'belowBar', color: '#06b6d4', shape: 'circle', text: 'Whale Entry' }
      ]);

      chartRef.current = chart;
      candlestickSeriesRef.current = candlestickSeries;
      
      const handleResize = () => {
        if (chartContainerRef.current) {
          chart.applyOptions({ width: chartContainerRef.current.clientWidth });
        }
      };
      window.addEventListener('resize', handleResize);
      return () => {
        window.removeEventListener('resize', handleResize);
        chart.remove();
        chartRef.current = null;
      };
    }

    return () => sigSocket.close();
  }, []);

  // Sync API signals to local state
  useEffect(() => {
    if (apiSignals && Array.isArray(apiSignals)) {
      setSignals(apiSignals.slice(0, 50));
    } else if (signals.length === 0) {
      // Mock data fallback if API fails
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

  const handleUpdateWeight = async (category, id, value) => {
    // Optimistic UI update
    if (category === 'agent') {
      setAgentStates(prev => ({ ...prev, [id]: { ...prev[id], weight: value } }));
    } else if (category === 'scanner') {
      setScannerStates(prev => ({ ...prev, [id]: { ...prev[id], weight: value } }));
    } else if (category === 'intel') {
      setIntelStates(prev => ({ ...prev, [id]: { ...prev[id], weight: value } }));
    } else if (category === 'shap') {
      setShapWeights(prev => ({ ...prev, [id]: value }));
      return; // SHAP weights saved differently
    }

    // Actual API Call
    try {
      const url = getApiUrl ? getApiUrl(`/api/v1/${category}s/${id}/weight`) : `/api/v1/${category}s/${id}/weight`;
      await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weight: value })
      });
    } catch (err) {
      console.error(`Failed to update ${category} weight:`, err);
    }
  };

  const handleToggleState = async (category, id, currentState) => {
    const newState = !currentState;
    
    // Optimistic UI update
    if (category === 'agent') {
      setAgentStates(prev => ({ ...prev, [id]: { ...prev[id], active: newState } }));
    } else if (category === 'scanner') {
      setScannerStates(prev => ({ ...prev, [id]: { ...prev[id], active: newState } }));
    } else if (category === 'intel') {
      setIntelStates(prev => ({ ...prev, [id]: { ...prev[id], active: newState } }));
    }

    // Actual API Call
    try {
      const url = getApiUrl ? getApiUrl(`/api/v1/${category}s/${id}/toggle`) : `/api/v1/${category}s/${id}/toggle`;
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: newState })
      });
    } catch (err) {
      console.error(`Failed to toggle ${category}:`, err);
    }
  };

  const triggerScan = async (id) => {
    try {
      setScannerStates(prev => ({ ...prev, [id]: { ...prev[id], status: 'yellow' } }));
      const url = getApiUrl ? getApiUrl(`/api/v1/openclaw/scan`) : `/api/v1/openclaw/scan`;
      await fetch(url, { method: 'POST', body: JSON.stringify({ scannerId: id }) });
      setTimeout(() => {
        setScannerStates(prev => ({ ...prev, [id]: { ...prev[id], status: 'green', runs: prev[id].runs + 1 } }));
      }, 1500);
    } catch (e) {
      setScannerStates(prev => ({ ...prev, [id]: { ...prev[id], status: 'red' } }));
    }
  };

  const triggerRetrain = async (id) => {
    try {
      setMlStates(prev => ({ ...prev, [id]: { ...prev[id], status: 'Training', retrainRequested: true } }));
      const url = getApiUrl ? getApiUrl(`/api/v1/training/retrain`) : `/api/v1/training/retrain`;
      await fetch(url, { method: 'POST', body: JSON.stringify({ modelId: id }) });
    } catch (e) {
      console.error(e);
    }
  };

  // --- RENDER ---

  const regimeData = apiOpenclaw?.regime || { state: 'BULL_TREND', conf: 87, color: 'emerald' };
  const bannerColor = regimeData.state.includes('BULL') ? 'emerald' : regimeData.state.includes('BEAR') ? 'red' : 'amber';

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-200 font-mono text-[11px] selection:bg-cyan-500/30 overflow-x-hidden pb-10">
      
      {/* TOP TOOLBAR */}
      <div className="flex justify-between items-center px-4 py-2 border-b border-[#1a1a2f] bg-[#0d0d14]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-cyan-500 font-bold text-sm tracking-widest">
            <Radio className="w-4 h-4" /> SIGNAL_INTELLIGENCE_V3
          </div>
          <div className="h-4 w-px bg-[#2a2a4a]"></div>
          <Badge color="cyan">OC_CORE_v5.2.1</Badge>
          <Badge color="emerald">WS_LATENCY: {wsLatency}ms</Badge>
          <Badge color="purple">SWARM_SIZE: {ALL_AGENTS.length}</Badge>
        </div>
        <div className="flex items-center gap-3">
          <button className="p-1.5 hover:bg-[#1a1a2f] rounded text-gray-400 hover:text-cyan-400 transition-colors"><Download className="w-4 h-4" /></button>
          <button className="p-1.5 hover:bg-[#1a1a2f] rounded text-gray-400 hover:text-cyan-400 transition-colors"><FileText className="w-4 h-4" /></button>
          <button className="p-1.5 hover:bg-[#1a1a2f] rounded text-gray-400 hover:text-purple-400 transition-colors"><Share2 className="w-4 h-4" /></button>
          <div className="h-4 w-px bg-[#2a2a4a]"></div>
          <button className="flex items-center gap-2 bg-[#1a1a2f] hover:bg-[#2a2a4a] px-3 py-1.5 rounded border border-[#2a2a4a] text-cyan-400 transition-colors">
            <Save className="w-3.5 h-3.5" /> Save Profile
          </button>
        </div>
      </div>

      {/* REGIME BANNER */}
      <div className={`mx-4 mt-4 border border-${bannerColor}-500/50 bg-${bannerColor}-500/10 shadow-[0_0_20px_rgba(16,185,129,0.15)] rounded-lg p-3 flex justify-between items-center`}>
        <div className="flex items-center gap-4">
          <Activity className={`w-6 h-6 text-${bannerColor}-400 animate-pulse`} />
          <div>
            <div className={`text-lg font-bold text-${bannerColor}-400 tracking-widest uppercase`}>{regimeData.state} REGIME</div>
            <div className="text-[10px] text-gray-400 uppercase">Hidden Markov Model (Layer 3) • Multi-Factor Agreement</div>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex flex-col items-end">
            <span className="text-[10px] text-gray-500">HMM Confidence</span>
            <span className={`text-xl font-bold text-${bannerColor}-400`}>{regimeData.conf}%</span>
          </div>
          <div className="h-8 w-px bg-white/10"></div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-gray-500 w-16">Override</span>
              <Toggle checked={regimeLock} onChange={setRegimeLock} size="sm" />
              {regimeLock ? <Lock className="w-3 h-3 text-amber-500" /> : <Unlock className="w-3 h-3 text-gray-500" />}
            </div>
          </div>
        </div>
      </div>

      {/* 4-COLUMN PANORAMIC GRID */}
      <div className="grid grid-cols-12 xl:grid-cols-20 gap-4 p-4 items-start">
        
        {/* ========================================================= */}
        {/* COLUMN 1: LEFT (20%) - AGENTS & SCANNERS                  */}
        {/* ========================================================= */}
        <div className="col-span-12 md:col-span-6 xl:col-span-4 flex flex-col gap-4">
          
          {/* SECTION B: SCANNER MODULES */}
          <Panel title="Scanner Modules (Layer 1)" icon={Search} className="h-[400px]">
            {SCANNERS.map(scan => (
              <div key={scan.id} className="flex flex-col gap-1 py-2 border-b border-[#1a1a2f] last:border-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${scannerStates[scan.id].status === 'green' ? 'bg-emerald-500' : scannerStates[scan.id].status === 'yellow' ? 'bg-amber-500 animate-pulse' : 'bg-red-500'}`} />
                    <span className="text-[10px] text-gray-300 w-28 truncate">{scan.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => triggerScan(scan.id)} className="text-gray-500 hover:text-cyan-400"><RefreshCw className="w-3 h-3" /></button>
                    <Toggle checked={scannerStates[scan.id].active} onChange={(v) => handleToggleState('scanner', scan.id, !v)} size="sm" />
                  </div>
                </div>
                <div className="flex items-center gap-2 pl-3">
                  <Slider value={scannerStates[scan.id].weight} onChange={(v) => handleUpdateWeight('scanner', scan.id, v)} />
                  <span className="text-[8px] text-gray-600 w-12 text-right">Runs: {scannerStates[scan.id].runs}</span>
                </div>
              </div>
            ))}
          </Panel>

          {/* SECTION A: OPENCLAW AGENT SWARM (100 Agents) */}
          <Panel title="OpenClaw Swarm (Layer 4)" icon={Network} className="h-[600px]">
            <div className="text-[9px] text-cyan-500 mb-2 pb-2 border-b border-cyan-500/20">CORE AGENTS (7)</div>
            {CORE_AGENTS.map(agent => (
              <ControlRow 
                key={agent.id} title={agent.name} 
                isActive={agentStates[agent.id].active} onToggle={(v) => handleToggleState('agent', agent.id, !v)}
                weight={agentStates[agent.id].weight} onWeightChange={(v) => handleUpdateWeight('agent', agent.id, v)}
              />
            ))}
            <div className="text-[9px] text-purple-500 mt-4 mb-2 pb-2 border-b border-purple-500/20 flex justify-between">
              <span>EXTENDED SWARM (93)</span>
              <span>SCROLL ▼</span>
            </div>
            {EXTENDED_AGENTS.map(agent => (
              <ControlRow 
                key={agent.id} title={agent.name} statusColor="gray"
                isActive={agentStates[agent.id].active} onToggle={(v) => handleToggleState('agent', agent.id, !v)}
                weight={agentStates[agent.id].weight} onWeightChange={(v) => handleUpdateWeight('agent', agent.id, v)}
              />
            ))}
          </Panel>

        </div>

        {/* ========================================================= */}
        {/* COLUMN 2: CENTER-LEFT (30%) - CHART & SIGNALS             */}
        {/* ========================================================= */}
        <div className="col-span-12 md:col-span-6 xl:col-span-6 flex flex-col gap-4">
          
          {/* SECTION I: CHART PATTERNS */}
          <Panel title="Market Action & Pattern Overlay" icon={TrendingUp} headerAction={
             <div className="flex gap-2">
               <Badge color="cyan">AAPL 15m</Badge>
               <Badge color="emerald">PATTERNS: ON</Badge>
             </div>
          } className="h-[400px]">
            <div ref={chartContainerRef} className="w-full h-full relative" />
          </Panel>

          {/* SIGNAL DATA TABLE */}
          <Panel title="Actionable Intelligence Stream" icon={Crosshair} className="h-[600px] !p-0">
            <div className="w-full text-left border-collapse">
              <div className="flex bg-[#0d0d14] border-b border-[#1a1a2f] p-2 text-[9px] text-gray-500 uppercase sticky top-0 z-10">
                <div className="w-16">Symbol</div>
                <div className="w-12">Score</div>
                <div className="w-14">Dir</div>
                <div className="w-16">Price</div>
                <div className="flex-1">Origin Agent</div>
                <div className="w-32 text-right">Actions</div>
              </div>
              <div className="flex flex-col">
                {signals.map((sig, idx) => (
                  <div key={idx} className="flex items-center p-2 border-b border-[#1a1a2f] hover:bg-[#1a1a2f]/50 transition-colors">
                    <div className={`w-16 font-bold ${sig.score > 80 ? 'text-cyan-400' : 'text-gray-300'}`}>{sig.symbol}</div>
                    <div className="w-12">
                      <span className={`px-1.5 py-0.5 rounded ${sig.score >= 90 ? 'bg-emerald-500/20 text-emerald-400' : sig.score <= 40 ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'}`}>
                        {sig.score}
                      </span>
                    </div>
                    <div className={`w-14 font-bold ${sig.dir === 'LONG' ? 'text-emerald-500' : 'text-red-500'}`}>{sig.dir}</div>
                    <div className="w-16 text-gray-400">{sig.price.toFixed(2)}</div>
                    <div className="flex-1 text-[10px] text-purple-400">{sig.agent}</div>
                    <div className="w-32 flex justify-end gap-1.5">
                      <button className="p-1 rounded bg-[#2a2a4a] hover:bg-emerald-500/20 hover:text-emerald-400 transition-colors" title="Accept"><CheckCircle className="w-3.5 h-3.5" /></button>
                      <button className="p-1 rounded bg-[#2a2a4a] hover:bg-red-500/20 hover:text-red-400 transition-colors" title="Reject"><XCircle className="w-3.5 h-3.5" /></button>
                      <button className="p-1 rounded bg-[#2a2a4a] hover:bg-cyan-500/20 hover:text-cyan-400 transition-colors" title="Watchlist"><Eye className="w-3.5 h-3.5" /></button>
                      <button className="p-1 rounded bg-cyan-600/20 text-cyan-500 hover:bg-cyan-500 hover:text-white transition-colors border border-cyan-500/30" title="Execute"><Rocket className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

        </div>

        {/* ========================================================= */}
        {/* COLUMN 3: CENTER-RIGHT (25%) - INTEL, SCORING, ML         */}
        {/* ========================================================= */}
        <div className="col-span-12 md:col-span-6 xl:col-span-5 flex flex-col gap-4">

          {/* SECTION D: SCORING ENGINE */}
          <Panel title="Global Scoring Engine (Layer 2)" icon={Sliders} className="h-auto">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1">
                <div className="flex justify-between text-[10px] text-gray-400">
                  <span>OpenClaw Core</span>
                  <span>Tech Analysis</span>
                </div>
                <input 
                  type="range" min="0" max="100" value={scoringFormula.ocTaBlend} 
                  onChange={(e) => setScoringFormula(prev => ({...prev, ocTaBlend: e.target.value}))}
                  className="w-full h-1.5 appearance-none bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full cursor-pointer"
                />
                <div className="text-center text-[10px] font-bold text-white">{scoringFormula.ocTaBlend} / {100 - scoringFormula.ocTaBlend}</div>
              </div>
              
              <div className="grid grid-cols-2 gap-2 mt-2">
                <div className="bg-[#1a1a2f] p-2 rounded border border-[#2a2a4a]">
                  <span className="text-[9px] text-gray-500 uppercase block mb-1">Regime Multiplier</span>
                  <input type="number" step="0.1" value={scoringFormula.regimeMultiplier} onChange={(e) => setScoringFormula(p => ({...p, regimeMultiplier: e.target.value}))} className="bg-transparent text-cyan-400 font-bold w-full outline-none" />
                </div>
                <div className="bg-[#1a1a2f] p-2 rounded border border-[#2a2a4a]">
                  <span className="text-[9px] text-gray-500 uppercase block mb-1">SLAM DUNK Tier</span>
                  <input type="number" value={scoringFormula.tierSlamDunk} onChange={(e) => setScoringFormula(p => ({...p, tierSlamDunk: e.target.value}))} className="bg-transparent text-emerald-400 font-bold w-full outline-none" />
                </div>
              </div>
              
              <div className="mt-2 text-[10px] text-cyan-500 pb-1 border-b border-[#2a2a4a]">PER-FACTOR SHAP WEIGHTS</div>
              <div className="flex flex-col gap-2">
                {SHAP_FACTORS.map(factor => (
                  <Slider key={factor} label={factor.substring(0,8)} value={shapWeights[factor]} onChange={(v) => handleUpdateWeight('shap', factor, v)} />
                ))}
              </div>
            </div>
          </Panel>

          {/* SECTION C: INTELLIGENCE LAYER */}
          <Panel title="Intelligence Modules (Layer 3)" icon={Cpu} className="h-auto max-h-[300px]">
            {INTEL_MODULES.map(mod => (
              <ControlRow 
                key={mod.id} title={mod.name} statusColor="cyan"
                isActive={intelStates[mod.id].active} onToggle={(v) => handleToggleState('intel', mod.id, !v)}
                weight={intelStates[mod.id].weight} onWeightChange={(v) => handleUpdateWeight('intel', mod.id, v)}
              />
            ))}
          </Panel>

          {/* SECTION E: ML/AI MODELS */}
          <Panel title="ML Model Control (Layer 5)" icon={Database} className="h-auto">
            <div className="flex flex-col gap-3">
              {ML_MODELS.map(model => (
                <div key={model.id} className="bg-[#1a1a2f] border border-[#2a2a4a] rounded p-2 flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <Toggle checked={mlStates[model.id].active} onChange={(v) => setMlStates(p => ({...p, [model.id]: { ...p[model.id], active: !p[model.id].active}}))} size="sm" />
                      <span className="font-bold text-gray-200">{model.name}</span>
                      <Badge color="gray">{model.version}</Badge>
                    </div>
                    <span className={`text-[9px] uppercase ${mlStates[model.id].status === 'Ready' ? 'text-emerald-500' : 'text-amber-500 animate-pulse'}`}>
                      {mlStates[model.id].status}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-gray-500 w-16">Conf Thresh</span>
                    <input 
                      type="range" min="0" max="100" value={mlStates[model.id].confThreshold}
                      onChange={(e) => setMlStates(p => ({...p, [model.id]: { ...p[model.id], confThreshold: parseInt(e.target.value)}}))}
                      className="flex-1 h-1 bg-[#0d0d14] rounded-full appearance-none accent-purple-500"
                    />
                    <span className="text-[9px] w-6">{mlStates[model.id].confThreshold}%</span>
                    <button onClick={() => triggerRetrain(model.id)} className="ml-2 px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded text-[9px] hover:bg-purple-500 hover:text-white transition-colors">
                      RETRAIN
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Panel>

        </div>

        {/* ========================================================= */}
        {/* COLUMN 4: RIGHT (25%) - SOCIAL, EXECUTION, APIS           */}
        {/* ========================================================= */}
        <div className="col-span-12 md:col-span-6 xl:col-span-5 flex flex-col gap-4">

          {/* SECTION F & G & H: SOCIAL, YOUTUBE, DISCORD */}
          <Panel title="External Sensors & Social" icon={Globe} className="h-auto">
            <div className="grid grid-cols-2 gap-2 mb-3">
              {DATA_SOURCES.map(ds => (
                <div key={ds.id} className="flex items-center justify-between bg-[#1a1a2f] p-1.5 rounded border border-[#2a2a4a]">
                  <span className="text-[9px] text-gray-300">{ds.name}</span>
                  <Toggle checked={dataSourceStates[ds.id].active} onChange={(v) => setDataSourceStates(p => ({...p, [ds.id]: {...p[ds.id], active: !p[ds.id].active}}))} size="sm" />
                </div>
              ))}
            </div>
            
            <div className="border-t border-[#1a1a2f] pt-2 mb-2 flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <span className="text-xs text-purple-400 font-bold flex items-center gap-1"><MessageSquare className="w-3 h-3"/> Discord Listener</span>
                <Badge color="purple">Connected</Badge>
              </div>
              <input type="text" placeholder="Watch Channels (comma sep)" className="w-full bg-[#1a1a2f] border border-[#2a2a4a] rounded p-1.5 text-xs text-gray-300 outline-none focus:border-purple-500" defaultValue="options-flow, alerts-pro" />
            </div>

            <div className="border-t border-[#1a1a2f] pt-2 flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <span className="text-xs text-red-400 font-bold flex items-center gap-1"><Play className="w-3 h-3"/> YouTube Agent</span>
                <Toggle checked={true} onChange={()=>{}} size="sm" />
              </div>
              <div className="flex gap-2">
                <Slider value={80} onChange={()=>{}} color="red" label="Weight" />
              </div>
            </div>
          </Panel>

          {/* SECTION M: EXECUTION CONTROLS */}
          <Panel title="Execution & Automation Engine" icon={Target} className="h-auto">
            <div className="flex items-center justify-between bg-[#1a1a2f] p-2 rounded border border-[#2a2a4a] mb-3">
              <span className="text-sm font-bold text-amber-500 flex items-center gap-2"><Zap className="w-4 h-4"/> AUTO EXECUTION</span>
              <Toggle checked={autoExecute} onChange={setAutoExecute} />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-gray-400">Trading Mode</span>
                <select className="bg-[#1a1a2f] border border-[#2a2a4a] rounded px-2 py-1 outline-none text-emerald-400 font-bold">
                  <option>PAPER TRADING</option>
                  <option>LIVE (ALPACA)</option>
                </select>
              </div>
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-gray-400">Position Sizer</span>
                <select className="bg-[#1a1a2f] border border-[#2a2a4a] rounded px-2 py-1 outline-none text-cyan-400">
                  <option>KELLY CRITERION</option>
                  <option>FIXED 2%</option>
                  <option>DYNAMIC VOL</option>
                </select>
              </div>
              <div className="flex flex-col gap-1 mt-2 border-t border-[#1a1a2f] pt-2">
                <span className="text-[9px] text-gray-500 uppercase">Max Portfolio Heat</span>
                <Slider value={25} onChange={()=>{}} color="amber" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[9px] text-gray-500 uppercase">Daily Loss Limit (%)</span>
                <Slider value={5} onChange={()=>{}} color="red" />
              </div>
            </div>
            
            <div className="mt-3 bg-[#0d0d14] border border-[#2a2a4a] p-2 rounded">
              <span className="text-[9px] text-gray-500 uppercase block mb-1">Active Rules (IF/THEN)</span>
              <div className="text-[9px] text-gray-300 flex items-center gap-2 mb-1">
                <Toggle checked={true} onChange={()=>{}} size="sm" />
                <span>IF <span className="text-cyan-400">comp > 90</span> AND <span className="text-emerald-400">regime=BULL</span> THEN stage</span>
              </div>
              <div className="text-[9px] text-gray-300 flex items-center gap-2">
                <Toggle checked={false} onChange={()=>{}} size="sm" />
                <span>IF <span className="text-red-400">VIX > 25</span> THEN halve pos size</span>
              </div>
            </div>
          </Panel>

          {/* SECTION P: 28 API ENDPOINTS HEALTH MATRIX */}
          <Panel title="System Telemetry & API Health" icon={Server} className="h-auto flex-1">
            <div className="grid grid-cols-4 sm:grid-cols-4 gap-1">
              {API_ENDPOINTS.map((ep, i) => {
                // Generate deterministic mock status
                const isWarning = i === 12 || i === 16;
                const isError = i === 22;
                const bg = isError ? 'bg-red-500 shadow-[0_0_5px_rgba(239,68,68,0.8)]' : 
                           isWarning ? 'bg-amber-500 shadow-[0_0_5px_rgba(245,158,11,0.8)] animate-pulse' : 
                           'bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]';
                return (
                  <div key={ep} className="flex flex-col items-center justify-center p-1.5 bg-[#1a1a2f] border border-[#2a2a4a] rounded overflow-hidden" title={`/api/v1/${ep}`}>
                    <span className={`w-1.5 h-1.5 rounded-full mb-1 ${bg}`} />
                    <span className="text-[7px] text-gray-500 w-full text-center truncate">{ep.substring(0,8)}</span>
                  </div>
                )
              })}
            </div>
            <div className="flex justify-between items-center mt-3 border-t border-[#1a1a2f] pt-2">
              <div className="flex items-center gap-1.5">
                <Wifi className="w-3.5 h-3.5 text-cyan-500" />
                <span className="text-[10px] text-gray-400">DB: 4.2ms</span>
              </div>
              <div className="flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-purple-500" />
                <span className="text-[10px] text-gray-400">MEM: 64%</span>
              </div>
            </div>
          </Panel>

        </div>
      </div>
    </div>
  );
}

// ============================================================================
// CONTINUED FROM PREVIOUS CODE (BOTTOM ROW COMPONENTS & IMPORTS)
// ============================================================================

import ReactFlow, { Background, Controls, MarkerType, Handle } from 'reactflow';
import 'reactflow/dist/style.css';

// --- REACT FLOW CUSTOM NODES ---
const CustomFlowNode = ({ data }) => {
  const colors = {
    green: 'border-emerald-500 bg-emerald-500/10 text-emerald-400',
    yellow: 'border-amber-500 bg-amber-500/10 text-amber-400 animate-pulse',
    red: 'border-red-500 bg-red-500/10 text-red-400'
  };
  return (
    <div className={`px-4 py-2 shadow-md rounded-md border border-l-4 ${colors[data.status]} font-mono text-[10px] w-40 text-center relative`}>
      <Handle type="target" position="top" className="w-2 h-2 bg-gray-500 border-none" />
      <div className="font-bold truncate">{data.label}</div>
      <div className="text-[8px] text-gray-400 mt-0.5 truncate">{data.subLabel}</div>
      <Handle type="source" position="bottom" className="w-2 h-2 bg-gray-500 border-none" />
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
    <div className="bg-[#13131a] border border-[#1a1a2f] rounded-lg overflow-hidden flex flex-col h-[500px] w-full mt-4">
      <div className="px-3 py-2 border-b border-[#1a1a2f] flex items-center gap-2 bg-[#0d0d14]">
        <Network className="w-3.5 h-3.5 text-cyan-500" />
        <h3 className="text-[11px] font-bold font-mono text-gray-300 uppercase tracking-widest">Agent Swarm Data Flow Pipeline</h3>
      </div>
      <div className="flex-1 w-full relative">
        <ReactFlow nodes={initialNodes} edges={initialEdges} nodeTypes={nodeTypes} fitView className="bg-[#0a0a0f]">
          <Background color="#1a1a2f" gap={16} />
          <Controls className="bg-[#13131a] border border-[#2a2a4a] fill-white" showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
};

// --- ADVANCED LIGHTWEIGHT CHART PANEL (Replaces Basic Chart) ---
export const LWChartPanel = () => {
  const chartContainerRef = useRef(null);
  const [tf, setTf] = useState('15m');
  const timeframes = ['1m', '5m', '15m', '1H', '4H', '1D', '1W'];

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: { background: { color: 'transparent' }, textColor: '#9ca3af', fontFamily: 'JetBrains Mono' },
      grid: { vertLines: { color: '#1a1a2f' }, horzLines: { color: '#1a1a2f' } },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { borderColor: '#2a2a4a', timeVisible: true },
      rightPriceScale: { borderColor: '#2a2a4a', autoScale: true },
    });

    // Main Candlestick Series
    const mainSeries = chart.addCandlestickSeries({
      upColor: '#10b981', downColor: '#ef4444', borderVisible: false,
      wickUpColor: '#10b981', wickDownColor: '#ef4444',
      priceFormat: { type: 'price', precision: 2, minMove: 0.01 }
    });

    // Volume Histogram
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a', priceFormat: { type: 'volume' },
      priceScaleId: '', // Overlay in main pane
      scaleMargins: { top: 0.8, bottom: 0 }
    });

    // Technical Indicators
    const sma20 = chart.addLineSeries({ color: '#06b6d4', lineWidth: 1, title: 'SMA 20' });
    const sma50 = chart.addLineSeries({ color: '#a855f7', lineWidth: 1, title: 'SMA 50' });
    const sma200 = chart.addLineSeries({ color: '#f59e0b', lineWidth: 2, title: 'SMA 200' });
    const vwap = chart.addLineSeries({ color: '#ffffff', lineWidth: 1, lineStyle: LineStyle.Dotted, title: 'VWAP' });

    // Generate Mock Data
    const generateData = () => {
      let data = []; let volData = []; let s20 = []; let s50 = []; let s200 = []; let vwapData = [];
      let base = 450; let time = Math.floor(Date.now() / 1000) - 86400 * 200;
      let cumulativeVol = 0, cumulativeVolPrice = 0;

      for (let i = 0; i < 200; i++) {
        const open = base + (Math.random() - 0.5) * 5;
        const close = open + (Math.random() - 0.5) * 8 + 0.2;
        const high = Math.max(open, close) + Math.random() * 4;
        const low = Math.min(open, close) - Math.random() * 4;
        const vol = Math.floor(Math.random() * 10000 + 1000);
        const typPrice = (high + low + close) / 3;
        
        cumulativeVol += vol;
        cumulativeVolPrice += typPrice * vol;

        const ts = time + i * 86400;
        data.push({ time: ts, open, high, low, close });
        volData.push({ time: ts, value: vol, color: close >= open ? '#10b98144' : '#ef444444' });
        vwapData.push({ time: ts, value: cumulativeVolPrice / cumulativeVol });
        
        if (i >= 20) s20.push({ time: ts, value: data.slice(i-20, i).reduce((a,b)=>a+b.close,0)/20 });
        if (i >= 50) s50.push({ time: ts, value: data.slice(i-50, i).reduce((a,b)=>a+b.close,0)/50 });
        if (i >= 200) s200.push({ time: ts, value: data.slice(i-200, i).reduce((a,b)=>a+b.close,0)/200 });

        base = close;
      }
      return { data, volData, s20, s50, s200, vwapData };
    };

    const d = generateData();
    mainSeries.setData(d.data);
    volumeSeries.setData(d.volData);
    sma20.setData(d.s20);
    sma50.setData(d.s50);
    sma200.setData(d.s200);
    vwap.setData(d.vwapData);

    // Entry / Target / Stop Lines
    const lastPrice = d.data[d.data.length - 1].close;
    mainSeries.createPriceLine({ price: lastPrice, color: '#06b6d4', lineWidth: 2, lineStyle: LineStyle.Solid, title: 'ENTRY' });
    mainSeries.createPriceLine({ price: lastPrice * 1.05, color: '#10b981', lineWidth: 2, lineStyle: LineStyle.Dashed, title: 'TARGET' });
    mainSeries.createPriceLine({ price: lastPrice * 0.98, color: '#ef4444', lineWidth: 2, lineStyle: LineStyle.Dotted, title: 'STOP' });

    // Pattern Annotations & Markers
    mainSeries.setMarkers([
      { time: d.data[50].time, position: 'aboveBar', color: '#ef4444', shape: 'arrowDown', text: 'H&S Top [94%]' },
      { time: d.data[120].time, position: 'belowBar', color: '#10b981', shape: 'arrowUp', text: 'Cup & Handle [88%]' },
      { time: d.data[180].time, position: 'belowBar', color: '#f59e0b', shape: 'circle', text: 'Bull Flag Break' }
    ]);

    const handleResize = () => chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [tf]);

  return (
    <div className="bg-[#13131a] border border-[#1a1a2f] rounded-lg overflow-hidden flex flex-col h-[600px] mt-4">
      <div className="px-3 py-2 border-b border-[#1a1a2f] flex justify-between items-center bg-[#0d0d14]">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-cyan-500" />
          <h3 className="text-[11px] font-bold font-mono text-gray-300 uppercase tracking-widest">Advanced Charting & Pattern Overlays</h3>
        </div>
        <div className="flex gap-1">
          {timeframes.map(t => (
            <button key={t} onClick={() => setTf(t)} className={`px-2 py-0.5 rounded text-[10px] font-mono border ${tf === t ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400' : 'bg-[#1a1a2f] border-[#2a2a4a] text-gray-500 hover:text-gray-300 transition-colors'}`}>
              {t}
            </button>
          ))}
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full flex-1 relative" />
    </div>
  );
};

// --- RECHARTS DASHBOARDS ROW ---
export const RechartsDashboards = () => {
  // Mock Data Generators
  const accData = Array.from({length: 30}, (_, i) => ({ day: `D-${30-i}`, acc: 60 + Math.random()*30, pnl: (Math.random()-0.3)*5 }));
  const agentConsensus = [
    { name: 'Apex', long: 85, short: 15 }, { name: 'RelWeak', long: 20, short: 80 },
    { name: 'MetaArch', long: 60, short: 40 }, { name: 'Whale', long: 95, short: 5 }
  ];
  const radarData = [
    { factor: 'Velez', score: 85 }, { factor: 'Whale', score: 92 }, { factor: 'RSI', score: 45 },
    { factor: 'Volume', score: 78 }, { factor: 'Hurst', score: 65 }, { factor: 'Compress', score: 88 },
    { factor: 'Sector', score: 72 }, { factor: 'Options', score: 95 }
  ];
  const corrData = Array.from({length: 50}, () => ({ x: Math.random()*100, y: Math.random()*100, z: Math.random()*400 }));

  return (
    <div className="grid grid-cols-12 gap-4 mt-4 h-[400px] mb-8 mx-4">
      
      {/* 1. AreaChart: Signal Accuracy */}
      <div className="bg-[#13131a] border border-[#1a1a2f] rounded-lg overflow-hidden flex flex-col col-span-12 xl:col-span-4 h-full">
        <div className="px-3 py-2 border-b border-[#1a1a2f] flex items-center gap-2 bg-[#0d0d14]">
          <TrendingUp className="w-3.5 h-3.5 text-cyan-500" />
          <h3 className="text-[11px] font-bold font-mono text-gray-300 uppercase tracking-widest">30-Day Signal Accuracy & PnL</h3>
        </div>
        <div className="flex-1 p-3">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={accData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorAcc" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2f" vertical={false} />
              <XAxis dataKey="day" tick={{fontSize: 9, fill: '#6b7280', fontFamily: 'monospace'}} tickLine={false} axisLine={false} />
              <YAxis tick={{fontSize: 9, fill: '#6b7280', fontFamily: 'monospace'}} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{backgroundColor: '#13131a', border: '1px solid #2a2a4a', fontSize: '10px', fontFamily: 'monospace'}} />
              <Area type="monotone" dataKey="acc" stroke="#10b981" fillOpacity={1} fill="url(#colorAcc)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. RadarChart: Multi-Factor Scoring */}
      <div className="bg-[#13131a] border border-[#1a1a2f] rounded-lg overflow-hidden flex flex-col col-span-12 md:col-span-6 xl:col-span-3 h-full">
        <div className="px-3 py-2 border-b border-[#1a1a2f] flex items-center gap-2 bg-[#0d0d14]">
          <Target className="w-3.5 h-3.5 text-cyan-500" />
          <h3 className="text-[11px] font-bold font-mono text-gray-300 uppercase tracking-widest">Multi-Factor Scoring Radar</h3>
        </div>
        <div className="flex-1 p-3">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
              <PolarGrid stroke="#2a2a4a" />
              <PolarAngleAxis dataKey="factor" tick={{ fill: '#9ca3af', fontSize: 9, fontFamily: 'monospace' }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
              <Radar name="Score" dataKey="score" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.3} />
              <Tooltip contentStyle={{backgroundColor: '#13131a', border: '1px solid #2a2a4a', fontSize: '10px', fontFamily: 'monospace'}} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. BarChart: Agent Consensus */}
      <div className="bg-[#13131a] border border-[#1a1a2f] rounded-lg overflow-hidden flex flex-col col-span-12 md:col-span-6 xl:col-span-3 h-full">
        <div className="px-3 py-2 border-b border-[#1a1a2f] flex items-center gap-2 bg-[#0d0d14]">
          <BarChart2 className="w-3.5 h-3.5 text-cyan-500" />
          <h3 className="text-[11px] font-bold font-mono text-gray-300 uppercase tracking-widest">Agent Swarm Consensus Matrix</h3>
        </div>
        <div className="flex-1 p-3">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={agentConsensus} layout="vertical" margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2f" horizontal={false} />
              <XAxis type="number" hide />
              <YAxis dataKey="name" type="category" tick={{fontSize: 9, fill: '#6b7280', fontFamily: 'monospace'}} width={60} axisLine={false} tickLine={false} />
              <Tooltip cursor={{fill: '#1a1a2f'}} contentStyle={{backgroundColor: '#13131a', border: '1px solid #2a2a4a', fontSize: '10px', fontFamily: 'monospace'}} />
              <Bar dataKey="long" stackId="a" fill="#10b981" radius={[0, 0, 0, 4]} barSize={16} />
              <Bar dataKey="short" stackId="a" fill="#ef4444" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4. ScatterChart: Signal Correlation */}
      <div className="bg-[#13131a] border border-[#1a1a2f] rounded-lg overflow-hidden flex flex-col col-span-12 xl:col-span-2 h-full">
        <div className="px-3 py-2 border-b border-[#1a1a2f] flex items-center gap-2 bg-[#0d0d14]">
          <Maximize2 className="w-3.5 h-3.5 text-cyan-500" />
          <h3 className="text-[11px] font-bold font-mono text-gray-300 uppercase tracking-widest">Scanner Correlation</h3>
        </div>
        <div className="flex-1 p-3">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2f" />
              <XAxis type="number" dataKey="x" name="Alpha" tick={false} axisLine={false} />
              <YAxis type="number" dataKey="y" name="Beta" tick={false} axisLine={false} />
              <Tooltip cursor={{strokeDasharray: '3 3'}} contentStyle={{backgroundColor: '#13131a', border: '1px solid #2a2a4a', fontSize: '10px', fontFamily: 'monospace'}} />
              <Scatter name="Signals" data={corrData} fill="#a855f7">
                {corrData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.z > 200 ? '#06b6d4' : '#a855f7'} opacity={entry.z / 400 + 0.2} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
};

