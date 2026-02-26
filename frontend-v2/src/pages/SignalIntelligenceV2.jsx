import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { createChart, CrosshairMode, LineStyle } from 'lightweight-charts';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, BarChart, Bar, Cell
} from 'recharts';
import {
  Activity, TrendingUp, TrendingDown, Zap, Target, Filter, RefreshCw,
  ChevronRight, Radio, AlertTriangle, ArrowUpRight, ArrowDownRight, Clock,
  Layers, Eye, EyeOff, Settings2, Cpu, Database, Brain, Shield, Gauge,
  BarChart3, GitBranch, Waves, FlaskConical, Crosshair, ScanLine,
  Power, Wifi, WifiOff, ChevronDown, ChevronUp, Sliders, Lock,
  Unlock, Volume2, DollarSign, Flame, Snowflake, Sun, Cloud, CloudRain,
  Thermometer, TrendingDown as TDown, Award, Hash, Percent, Timer
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════
// DESIGN TOKENS
// ═══════════════════════════════════════════════════════════════════════════
const T = {
  bgPrimary:    '#0a0a0f',
  bgCard:       '#13131a',
  bgCardHover:  '#1a1a24',
  bgPanel:      '#0e0e15',
  border:       'rgba(255,255,255,0.06)',
  borderActive: 'rgba(6,182,212,0.4)',
  borderWarn:   'rgba(245,158,11,0.4)',
  borderDanger: 'rgba(239,68,68,0.4)',
  cyan:    '#06b6d4',
  emerald: '#10b981',
  amber:   '#f59e0b',
  red:     '#ef4444',
  purple:  '#a855f7',
  blue:    '#3b82f6',
  pink:    '#ec4899',
  orange:  '#f97316',
  lime:    '#84cc16',
  textPri:  '#f1f5f9',
  textSec:  '#94a3b8',
  textMut:  '#64748b',
  textDim:  '#475569',
  mono: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
  sans: "'Inter', 'Segoe UI', sans-serif",
};

// ═══════════════════════════════════════════════════════════════════════════
// LAYER 1: SCANNER REGISTRY (15 scanner modules)
// ═══════════════════════════════════════════════════════════════════════════
const SCANNERS = [
  { id: 'daily_scanner',       name: 'Daily Scanner',       layer: 'scanner', icon: ScanLine,    color: T.cyan,   file: 'daily_scanner.py',       desc: 'Master orchestrator: 15-min pipeline' },
  { id: 'finviz_scanner',      name: 'Finviz Screener',     layer: 'scanner', icon: Filter,      color: T.blue,   file: 'finviz_scanner.py',      desc: 'Fundamental + technical filters' },
  { id: 'amd_detector',        name: 'After-Mkt Drop',      layer: 'scanner', icon: TDown,       color: T.red,    file: 'amd_detector.py',        desc: 'Gap-down setup detection' },
  { id: 'pullback_detector',   name: 'Pullback Detector',   layer: 'scanner', icon: TrendingDown,color: T.amber,  file: 'pullback_detector.py',   desc: 'Buy-the-dip signals' },
  { id: 'rebound_detector',    name: 'Rebound Detector',    layer: 'scanner', icon: TrendingUp,  color: T.emerald,file: 'rebound_detector.py',    desc: 'Bounce pattern detection' },
  { id: 'short_detector',      name: 'Short Squeeze',       layer: 'scanner', icon: Flame,       color: T.orange, file: 'short_detector.py',      desc: 'High SI + volume squeeze' },
  { id: 'technical_checker',   name: 'Technical Checker',   layer: 'scanner', icon: BarChart3,   color: T.purple, file: 'technical_checker.py',   desc: 'MA crossovers, RSI, MACD' },
  { id: 'earnings_calendar',   name: 'Earnings Calendar',   layer: 'scanner', icon: Clock,       color: T.pink,   file: 'earnings_calendar.py',   desc: 'Pre/post earnings plays' },
  { id: 'fomc_expected',       name: 'FOMC Expected',       layer: 'scanner', icon: Thermometer, color: T.amber,  file: 'fom_expected_moves.py',  desc: 'Macro event signals' },
  { id: 'sector_rotation',     name: 'Sector Rotation',     layer: 'scanner', icon: GitBranch,   color: T.lime,   file: 'sector_rotation.py',     desc: 'Money flow between sectors' },
  { id: 'whale_flow',          name: 'Whale Flow',          layer: 'scanner', icon: Waves,       color: T.cyan,   file: 'whale_flow.py',          desc: 'Dark pool/institutional flow' },
  { id: 'uw_agents',           name: 'UW Agents',           layer: 'scanner', icon: Eye,         color: T.blue,   file: 'uw_agents.py',           desc: 'Unusual Whales options flow' },
  { id: 'tv_watchlist',        name: 'TV Watchlist',        layer: 'scanner', icon: Crosshair,   color: T.purple, file: 'tradingview_watchlist.py',desc: 'TradingView integration' },
  { id: 'tv_session',          name: 'TV Session',          layer: 'scanner', icon: RefreshCw,   color: T.textMut,file: 'tv_session_refresh.py',  desc: 'TV session management' },
  { id: 'ml_lstm',             name: 'LSTM Predictions',    layer: 'ml',      icon: Brain,       color: T.purple, file: 'ml_training.py',         desc: 'PyTorch LSTM model' },
];

// LAYER 2-7 source modules
const SCORERS = [
  { id: 'composite_scorer',  name: 'Composite Scorer',  desc: '5-pillar scoring (0-100)', color: T.cyan },
  { id: 'dynamic_weights',   name: 'Dynamic Weights',   desc: 'Regime-adaptive weights',  color: T.amber },
  { id: 'ensemble_scorer',   name: 'Ensemble Scorer',   desc: 'Multi-model ensemble',     color: T.purple },
];

const INTEL_MODULES = [
  { id: 'regime',             name: 'Regime',          desc: 'GREEN/YELLOW/RED', color: T.emerald },
  { id: 'hmm_regime',         name: 'HMM 7-State',    desc: 'Hidden Markov Model', color: T.purple },
  { id: 'macro_context',      name: 'Macro Context',   desc: 'VIX, HY, yield, F&G', color: T.amber },
  { id: 'mtf_alignment',      name: 'MTF Alignment',   desc: 'Multi-timeframe', color: T.cyan },
  { id: 'perf_tracker',       name: 'Perf Tracker',    desc: 'Signal hit tracking', color: T.emerald },
  { id: 'signal_memory',      name: 'Signal Memory',   desc: 'Memory v3 learning', color: T.blue },
];

const AGENTS = [
  { id: 'apex_orchestrator',  name: 'Apex Orchestrator',  confidence: 87, color: T.cyan },
  { id: 'rel_weakness',       name: 'Relative Weakness',  confidence: 82, color: T.red },
  { id: 'short_basket',       name: 'Short Basket',       confidence: 79, color: T.orange },
  { id: 'meta_architect',     name: 'Meta Architect',     confidence: 91, color: T.purple },
  { id: 'meta_alchemist',     name: 'Meta Alchemist',     confidence: 88, color: T.pink },
  { id: 'risk_governor',      name: 'Risk Governor',      confidence: 95, color: T.emerald },
  { id: 'signal_engine',      name: 'Signal Engine',      confidence: 86, color: T.blue },
  { id: 'market_data_agent',  name: 'Market Data Agent',  confidence: 93, color: T.cyan },
  { id: 'xgboost_ensemble',   name: 'XGBoost Ensemble',   confidence: 84, color: T.amber },
  { id: 'lstm_predictor',     name: 'LSTM Predictor',     confidence: 81, color: T.purple },
];

const REGIME_MULTIPLIERS = {
  BULLISH: { mult: 1.10, color: T.emerald, icon: Sun },
  RISK_ON: { mult: 1.05, color: T.lime,    icon: TrendingUp },
  NEUTRAL: { mult: 1.00, color: T.textSec, icon: Cloud },
  RISK_OFF:{ mult: 0.90, color: T.amber,   icon: AlertTriangle },
  BEARISH: { mult: 0.80, color: T.orange,  icon: CloudRain },
  CRISIS:  { mult: 0.65, color: T.red,     icon: Snowflake },
};

const SIGNAL_TIERS = {
  SLAM_DUNK: { min: 90, color: T.emerald, label: 'SLAM DUNK', glow: 'rgba(16,185,129,0.2)' },
  STRONG_GO: { min: 75, color: T.cyan,    label: 'STRONG GO',  glow: 'rgba(6,182,212,0.15)' },
  WATCH:     { min: 60, color: T.amber,   label: 'WATCH',      glow: 'rgba(245,158,11,0.1)' },
  SKIP:      { min: 0,  color: T.textMut, label: 'SKIP',       glow: 'none' },
};

function getTier(score) {
  if (score >= 90) return SIGNAL_TIERS.SLAM_DUNK;
  if (score >= 75) return SIGNAL_TIERS.STRONG_GO;
  if (score >= 60) return SIGNAL_TIERS.WATCH;
  return SIGNAL_TIERS.SKIP;
}

// ═══════════════════════════════════════════════════════════════════════════
// MOCK DATA GENERATORS (replace with real API hooks in V3)
// ═══════════════════════════════════════════════════════════════════════════
const SYMBOLS = ['NVDA','TSLA','AAPL','AMD','MSFT','META','COIN','PLTR','CRWD','MSTR','SMCI','GOOGL','AMZN','NFLX','AVGO'];

function genSignals(count = 40) {
  const types = SCANNERS.map(s => s.id);
  const dirs = ['LONG','SHORT'];
  const hmmStates = ['BULL_RUN','BULL_TREND','RECOVERY','NEUTRAL','CAUTIOUS','BEARISH','CRASH'];
  return Array.from({ length: count }, (_, i) => {
    const dir = dirs[Math.floor(Math.random() * 2)];
    const composite = Math.floor(Math.random() * 40 + 55);
    const price = +(Math.random() * 400 + 50).toFixed(2);
    const entry = +(price + (dir === 'LONG' ? -2 : 2) + Math.random() * 2).toFixed(2);
    const stop  = +(entry + (dir === 'LONG' ? -8 : 8) + Math.random() * 3).toFixed(2);
    const target= +(entry + (dir === 'LONG' ? 16 : -16) + Math.random() * 6).toFixed(2);
    return {
      id: `sig-${Date.now()}-${i}`,
      symbol: SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)],
      direction: dir,
      sourceScanner: types[Math.floor(Math.random() * types.length)],
      composite,
      tier: getTier(composite).label,
      tierColor: getTier(composite).color,
      price, entry, stop, target,
      // 25+ factor columns
      velezScore:      Math.floor(Math.random() * 30 + 65),
      williamsR:       -(Math.random() * 80 + 10).toFixed(1),
      volumeSurge:     +(Math.random() * 300 + 50).toFixed(0),
      whaleFlowScore:  Math.floor(Math.random() * 40 + 50),
      optionsFlowBias: Math.random() > 0.5 ? 'BULLISH' : 'BEARISH',
      shortInterest:   +(Math.random() * 30 + 2).toFixed(1),
      rsi14:           +(Math.random() * 40 + 30).toFixed(1),
      macdSignal:      Math.random() > 0.5 ? 'BULL_CROSS' : 'BEAR_CROSS',
      hurst:           +(Math.random() * 0.5 + 0.3).toFixed(2),
      regimeState:     ['GREEN','YELLOW','RED'][Math.floor(Math.random() * 3)],
      hmmState:        hmmStates[Math.floor(Math.random() * hmmStates.length)],
      macroRisk:       Math.floor(Math.random() * 5 + 1),
      sectorScore:     Math.floor(Math.random() * 30 + 60),
      squeezeScore:    Math.floor(Math.random() * 100),
      mtfAlign:        ['ALIGNED','MIXED','COUNTER'][Math.floor(Math.random() * 3)],
      earningsProx:    Math.floor(Math.random() * 30),
      compressRatio:   +(Math.random() * 0.5 + 0.5).toFixed(2),
      atrPercent:      +(Math.random() * 5 + 1).toFixed(1),
      relStrength:     +(Math.random() * 2 - 0.5).toFixed(2),
      darkPoolVol:     +(Math.random() * 50000000).toFixed(0),
      putCallRatio:    +(Math.random() * 1.5 + 0.3).toFixed(2),
      impliedMove:     +(Math.random() * 8 + 1).toFixed(1),
      fearGreed:       Math.floor(Math.random() * 60 + 20),
      ta_score:        Math.floor(Math.random() * 40 + 50),
      oc_score:        Math.floor(Math.random() * 40 + 55),
      blendedScore:    0, // computed below
      confidenceAdj:   0,
      timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
      // Model agreement per horizon
      models: {
        '1H': { pred: dir, conf: Math.floor(Math.random() * 20 + 75) },
        '4H': { pred: dirs[Math.floor(Math.random()*2)], conf: Math.floor(Math.random() * 20 + 70) },
        '1D': { pred: dirs[Math.floor(Math.random()*2)], conf: Math.floor(Math.random() * 20 + 70) },
        '1W': { pred: dirs[Math.floor(Math.random()*2)], conf: Math.floor(Math.random() * 20 + 65) },
      },
      // SHAP-like factor importance
      shapFactors: [
        { name: 'UW Options Flow',  weight: +(Math.random()*0.25+0.05).toFixed(3) },
        { name: 'Velez Score',      weight: +(Math.random()*0.2+0.05).toFixed(3) },
        { name: 'Volume Surge',     weight: +(Math.random()*0.18+0.03).toFixed(3) },
        { name: 'Whale Flow',       weight: +(Math.random()*0.15+0.03).toFixed(3) },
        { name: 'RSI Divergence',   weight: +(Math.random()*0.12+0.02).toFixed(3) },
        { name: 'HTF Structure',    weight: +(Math.random()*0.1+0.02).toFixed(3) },
        { name: 'Compression',      weight: +(Math.random()*0.1+0.01).toFixed(3) },
        { name: 'Sector Momentum',  weight: +(Math.random()*0.08+0.01).toFixed(3) },
      ].sort((a,b) => b.weight - a.weight),
    };
  }).map(s => ({
    ...s,
    blendedScore: Math.floor(s.oc_score * 0.6 + s.ta_score * 0.4),
    confidenceAdj: Math.floor(s.composite * (REGIME_MULTIPLIERS[Object.keys(REGIME_MULTIPLIERS)[Math.floor(Math.random()*6)]]?.mult || 1)),
  }));
}

function genOHLC(count = 200) {
  let p = 180;
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(Date.now() - (count - i) * 86400000);
    const o = p + (Math.random()-0.5)*4;
    const c = o + (Math.random()-0.5)*6;
    const h = Math.max(o,c) + Math.random()*3;
    const l = Math.min(o,c) - Math.random()*3;
    p = c;
    return { time: d.toISOString().split('T')[0], open: o, high: h, low: l, close: c, volume: Math.floor(Math.random()*5e7+1e7) };
  });
}

function genAccuracy(days=30) {
  return Array.from({ length: days }, (_,i) => ({
    day: `D-${30-i}`,
    compression: Math.floor(Math.random()*20+65),
    ignition: Math.floor(Math.random()*20+60),
    velez: Math.floor(Math.random()*15+72),
    whale: Math.floor(Math.random()*18+64),
    ensemble: Math.floor(Math.random()*12+74),
    overall: Math.floor(Math.random()*15+68),
  }));
}

function genCorrelation() {
  const ids = SCANNERS.slice(0,10).map(s=>s.id);
  return ids.map(row => {
    const obj = { scanner: row };
    ids.forEach(col => { obj[col] = row===col ? 1.0 : +(Math.random()*0.8-0.2).toFixed(2); });
    return obj;
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ═══════════════════════════════════════════════════════════════════════════
export default function SignalIntelligenceV2() {
  // ─── State ────────────────────────────────────────────
  const [signals, setSignals]             = useState([]);
  const [selectedSignal, setSelectedSignal] = useState(null);
  const [ohlcData]                        = useState(genOHLC);
  const [accuracyData]                    = useState(genAccuracy);
  const [correlationData]                 = useState(genCorrelation);
  const [isLive, setIsLive]               = useState(true);
  const [filterType, setFilterType]       = useState('all');
  const [filterDir, setFilterDir]         = useState('all');
  const [filterTier, setFilterTier]       = useState('all');
  const [rightPanel, setRightPanel]       = useState('controls'); // 'controls' | 'detail'
  const [scannerStates, setScannerStates] = useState(() =>
    Object.fromEntries(SCANNERS.map(s => [s.id, { enabled: true, weight: 50, lastRun: Date.now() - Math.random()*300000, errors: Math.floor(Math.random()*3), symbolsScanned: Math.floor(Math.random()*200+50), interval: 900 }]))
  );
  const [currentRegime, setCurrentRegime] = useState('NEUTRAL');

  useEffect(() => {
    const init = genSignals(40);
    setSignals(init);
    setSelectedSignal(init[0]);
  }, []);

  useEffect(() => {
    if (!isLive) return;
    const iv = setInterval(() => {
      const ns = genSignals(1)[0];
      setSignals(prev => [ns, ...prev.slice(0, 99)]);
    }, 5000);
    return () => clearInterval(iv);
  }, [isLive]);

  const filtered = useMemo(() => signals.filter(s => {
    if (filterType !== 'all' && s.sourceScanner !== filterType) return false;
    if (filterDir !== 'all' && s.direction !== filterDir) return false;
    if (filterTier !== 'all' && s.tier !== filterTier) return false;
    return true;
  }), [signals, filterType, filterDir, filterTier]);

  const toggleScanner = (id) => setScannerStates(prev => ({ ...prev, [id]: { ...prev[id], enabled: !prev[id].enabled } }));
  const setWeight = (id, w) => setScannerStates(prev => ({ ...prev, [id]: { ...prev[id], weight: w } }));

  // ─── KPI computations ────────────────────────────────
  const kpis = useMemo(() => {
    const active = signals.length;
    const longs = signals.filter(s=>s.direction==='LONG').length;
    const shorts = active - longs;
    const avgComposite = active ? Math.floor(signals.reduce((a,s)=>a+s.composite,0)/active) : 0;
    const slamDunks = signals.filter(s=>s.composite>=90).length;
    const avgRR = active ? +((signals.reduce((a,s)=>a+Math.abs(s.target-s.entry)/(Math.abs(s.entry-s.stop)||1),0))/active).toFixed(1) : 0;
    const enabledScanners = Object.values(scannerStates).filter(s=>s.enabled).length;
    const totalErrors = Object.values(scannerStates).reduce((a,s)=>a+s.errors,0);
    return { active, longs, shorts, avgComposite, slamDunks, avgRR, enabledScanners, totalErrors };
  }, [signals, scannerStates]);

  const regimeCfg = REGIME_MULTIPLIERS[currentRegime] || REGIME_MULTIPLIERS.NEUTRAL;
  const RegimeIcon = regimeCfg.icon;

  // ═══════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════
  return (
    <div className="flex flex-col h-full w-full overflow-hidden" style={{ background: T.bgPrimary, color: T.textPri, fontFamily: T.sans }}>

      {/* ═══ ROW 1: KPI STRIP (64px) ═══════════════════════ */}
      <div className="flex items-center gap-2 px-3 py-2 border-b overflow-x-auto" style={{ borderColor: T.border, background: T.bgPanel, minHeight: 64 }}>
        <KPI label="Active Signals" value={kpis.active} icon={Activity} color={T.cyan} />
        <KPI label="SLAM DUNKs" value={kpis.slamDunks} icon={Award} color={T.emerald} />
        <KPI label="Hit Rate 30d" value="71.4%" icon={Target} color={T.emerald} />
        <KPI label="Avg R-Multiple" value={`${kpis.avgRR}R`} icon={DollarSign} color={T.cyan} />
        <KPI label="Avg Composite" value={kpis.avgComposite} icon={Gauge} color={kpis.avgComposite>=75?T.emerald:kpis.avgComposite>=60?T.amber:T.red} />
        <KPI label="Regime" value={currentRegime} icon={RegimeIcon} color={regimeCfg.color} />
        <KPI label="Multiplier" value={`${regimeCfg.mult}x`} icon={Sliders} color={regimeCfg.color} />
        <KPI label="VIX" value="18.4" icon={Thermometer} color={T.amber} />
        <KPI label="Fear/Greed" value="62" icon={Gauge} color={T.emerald} />
        <KPI label="Scanners" value={`${kpis.enabledScanners}/${SCANNERS.length}`} icon={ScanLine} color={T.cyan} />
        <KPI label="Errors" value={kpis.totalErrors} icon={AlertTriangle} color={kpis.totalErrors>0?T.red:T.emerald} />
        <KPI label="Queue" value="24" icon={Layers} color={T.blue} />
        <KPI label="Whale Flow" value="78" icon={Waves} color={T.cyan} />
        <KPI label="Model Conf" value={`${kpis.avgComposite+5}%`} icon={Brain} color={T.purple} />

        {/* Live toggle + regime selector */}
        <div className="ml-auto flex items-center gap-2 flex-shrink-0">
          <select value={currentRegime} onChange={e=>setCurrentRegime(e.target.value)}
            className="text-[10px] px-2 py-1 rounded border outline-none"
            style={{ background: T.bgCard, borderColor: T.border, color: regimeCfg.color, fontFamily: T.mono }}>
            {Object.keys(REGIME_MULTIPLIERS).map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <button onClick={()=>setIsLive(!isLive)} className="flex items-center gap-1 text-[10px] px-2 py-1 rounded border"
            style={{ background: isLive?'rgba(16,185,129,0.1)':T.bgCard, borderColor: isLive?'rgba(16,185,129,0.3)':T.border, color: isLive?T.emerald:T.textMut }}>
            <Radio size={10}/>{isLive?'LIVE':'PAUSED'}
          </button>
        </div>
      </div>

      {/* ═══ ROW 2: FILTER BAR (36px) ═══════════════════════ */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b" style={{ borderColor: T.border, background: T.bgCard }}>
        <Filter size={12} style={{ color: T.textMut }}/>
        <span className="text-[10px] font-semibold" style={{ color: T.textMut }}>FILTERS:</span>
        <select value={filterType} onChange={e=>setFilterType(e.target.value)}
          className="text-[10px] px-2 py-0.5 rounded border outline-none" style={{ background: T.bgPrimary, borderColor: T.border, color: T.textSec }}>
          <option value="all">All Scanners</option>
          {SCANNERS.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        <select value={filterDir} onChange={e=>setFilterDir(e.target.value)}
          className="text-[10px] px-2 py-0.5 rounded border outline-none" style={{ background: T.bgPrimary, borderColor: T.border, color: T.textSec }}>
          <option value="all">All Dirs</option><option value="LONG">LONG</option><option value="SHORT">SHORT</option>
        </select>
        <select value={filterTier} onChange={e=>setFilterTier(e.target.value)}
          className="text-[10px] px-2 py-0.5 rounded border outline-none" style={{ background: T.bgPrimary, borderColor: T.border, color: T.textSec }}>
          <option value="all">All Tiers</option>
          {Object.values(SIGNAL_TIERS).map(t=><option key={t.label} value={t.label}>{t.label}</option>)}
        </select>
        <span className="text-[10px] ml-auto" style={{ color: T.textMut, fontFamily: T.mono }}>{filtered.length} signals · Blend: 60% OC + 40% TA</span>
      </div>

      {/* ═══ ROW 3: MAIN CONTENT (flex-1) ═══════════════════ */}
      <div className="flex-1 grid grid-cols-12 gap-0 overflow-hidden" style={{ minHeight: 0 }}>

        {/* ── LEFT: LW Charts (3 cols) ──────────────────── */}
        <div className="col-span-3 border-r flex flex-col" style={{ borderColor: T.border }}>
          <div className="px-3 py-2 flex items-center justify-between border-b" style={{ borderColor: T.border }}>
            <span className="text-xs font-semibold">{selectedSignal?.symbol||'—'}</span>
            <span className="text-[9px] font-mono" style={{ color: T.textMut }}>Daily · LW Charts</span>
          </div>
          <div className="flex-1 min-h-0">
            <LWChartPanel ohlcData={ohlcData} signals={filtered.filter(s=>s.symbol===selectedSignal?.symbol)} selected={selectedSignal} />
          </div>
        </div>

        {/* ── CENTER: Dense Signal Table (6 cols) ──────── */}
        <div className="col-span-6 flex flex-col overflow-hidden border-r" style={{ borderColor: T.border }}>
          <DenseSignalTable signals={filtered} selected={selectedSignal} onSelect={(s)=>{setSelectedSignal(s);setRightPanel('detail');}} />
        </div>

        {/* ── RIGHT: Control / Detail Panel (3 cols) ───── */}
        <div className="col-span-3 flex flex-col overflow-hidden">
          {/* Tab toggle */}
          <div className="flex border-b" style={{ borderColor: T.border }}>
            <button onClick={()=>setRightPanel('controls')} className="flex-1 text-[10px] py-2 font-semibold border-b-2 transition-colors"
              style={{ borderColor: rightPanel==='controls'?T.cyan:'transparent', color: rightPanel==='controls'?T.cyan:T.textMut, background: rightPanel==='controls'?'rgba(6,182,212,0.05)':'transparent' }}>
              <Settings2 size={10} className="inline mr-1"/>SCANNER CONTROLS
            </button>
            <button onClick={()=>setRightPanel('detail')} className="flex-1 text-[10px] py-2 font-semibold border-b-2 transition-colors"
              style={{ borderColor: rightPanel==='detail'?T.purple:'transparent', color: rightPanel==='detail'?T.purple:T.textMut, background: rightPanel==='detail'?'rgba(168,85,247,0.05)':'transparent' }}>
              <Brain size={10} className="inline mr-1"/>SIGNAL DETAIL
            </button>
          </div>
          <div className="flex-1 overflow-auto">
            {rightPanel === 'controls'
              ? <ScannerControlPanel scanners={SCANNERS} states={scannerStates} onToggle={toggleScanner} onWeight={setWeight} scorers={SCORERS} intel={INTEL_MODULES} regime={currentRegime} regimeMult={regimeCfg} />
              : selectedSignal ? <SignalDetailPanel signal={selectedSignal} agents={AGENTS} /> : <div className="flex items-center justify-center h-full text-xs" style={{color:T.textMut}}>Select a signal</div>
            }
          </div>
        </div>
      </div>

      {/* ═══ ROW 4: BOTTOM PANELS (220px) ═══════════════════ */}
      <div className="grid grid-cols-3 gap-0 border-t" style={{ borderColor: T.border, height: 220, background: T.bgPanel }}>
        {/* Bottom Left: Accuracy Timeline */}
        <div className="border-r px-3 py-2 overflow-hidden" style={{ borderColor: T.border }}>
          <span className="text-[10px] font-semibold" style={{ color: T.textMut }}>SIGNAL ACCURACY — 30-DAY ROLLING</span>
          <ResponsiveContainer width="100%" height="88%">
            <AreaChart data={accuracyData} margin={{top:8,right:4,left:0,bottom:0}}>
              <defs>
                <linearGradient id="gO" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={T.emerald} stopOpacity={0.25}/><stop offset="95%" stopColor={T.emerald} stopOpacity={0}/></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)"/>
              <XAxis dataKey="day" tick={{fill:T.textDim,fontSize:9}} axisLine={false} tickLine={false}/>
              <YAxis domain={[50,100]} tick={{fill:T.textDim,fontSize:9}} axisLine={false} tickLine={false} width={24}/>
              <Tooltip contentStyle={{background:T.bgCard,border:`1px solid ${T.border}`,borderRadius:4,fontSize:10}} labelStyle={{color:T.textSec}}/>
              <Area type="monotone" dataKey="overall" stroke={T.emerald} fill="url(#gO)" strokeWidth={2} dot={false}/>
              <Area type="monotone" dataKey="compression" stroke={T.amber} fill="none" strokeWidth={1} strokeDasharray="3 2" dot={false}/>
              <Area type="monotone" dataKey="ignition" stroke={T.red} fill="none" strokeWidth={1} strokeDasharray="3 2" dot={false}/>
              <Area type="monotone" dataKey="whale" stroke={T.cyan} fill="none" strokeWidth={1} strokeDasharray="3 2" dot={false}/>
              <Area type="monotone" dataKey="ensemble" stroke={T.purple} fill="none" strokeWidth={1} strokeDasharray="3 2" dot={false}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Bottom Center: Agent Consensus Matrix */}
        <div className="border-r px-3 py-2 overflow-auto" style={{ borderColor: T.border }}>
          <span className="text-[10px] font-semibold" style={{ color: T.textMut }}>AGENT CONSENSUS MATRIX — 10 AGENTS</span>
          <AgentConsensusMatrix agents={AGENTS} selected={selectedSignal} />
        </div>

        {/* Bottom Right: Correlation Heatmap */}
        <div className="px-3 py-2 overflow-auto">
          <span className="text-[10px] font-semibold" style={{ color: T.textMut }}>SCANNER CORRELATION HEATMAP</span>
          <CorrelationHeatmap data={correlationData} />
        </div>
      </div>

      {/* ═══ ROW 5: FOOTER STATUS STRIP (28px) ═══════════════ */}
      <div className="flex items-center gap-3 px-3 py-1 border-t overflow-x-auto" style={{ borderColor: T.border, background: T.bgCard, minHeight: 28 }}>
        {SCANNERS.slice(0,12).map(sc => {
          const st = scannerStates[sc.id];
          return (
            <div key={sc.id} className="flex items-center gap-1 flex-shrink-0">
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: st.enabled ? (st.errors>0?T.amber:T.emerald) : T.textMut }}/>
              <span className="text-[8px] font-mono" style={{ color: st.enabled?T.textSec:T.textDim }}>{sc.name.slice(0,12)}</span>
              <span className="text-[8px] font-mono" style={{ color: T.textDim }}>
                {Math.floor((Date.now()-st.lastRun)/1000)}s
              </span>
              <span className="text-[8px] font-mono" style={{ color: T.textDim }}>{st.symbolsScanned}sym</span>
              {st.errors>0 && <span className="text-[8px] font-mono" style={{ color: T.red }}>{st.errors}err</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// KPI CARD — compact stat chip for top strip
// ═══════════════════════════════════════════════════════════════════════════
function KPI({ label, value, icon: Icon, color }) {
  return (
    <div className="flex items-center gap-2 px-2.5 py-1.5 rounded border flex-shrink-0"
      style={{ background: `${color}08`, borderColor: `${color}20` }}>
      <Icon size={13} style={{ color }} />
      <div>
        <div className="text-[9px] uppercase tracking-wider" style={{ color: T.textMut }}>{label}</div>
        <div className="text-sm font-bold font-mono leading-tight" style={{ color, fontFamily: T.mono }}>{value}</div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// LW CHART PANEL — candlestick + volume + signal markers + price lines
// ═══════════════════════════════════════════════════════════════════════════
function LWChartPanel({ ohlcData, signals, selected }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      width: ref.current.clientWidth, height: ref.current.clientHeight,
      layout: { background: { color: T.bgPrimary }, textColor: T.textDim, fontFamily: T.mono, fontSize: 10 },
      grid: { vertLines: { color: 'rgba(255,255,255,0.02)' }, horzLines: { color: 'rgba(255,255,255,0.02)' } },
      crosshair: { mode: CrosshairMode.Normal,
        vertLine: { color: `${T.cyan}66`, width: 1, style: LineStyle.Dashed, labelBackgroundColor: T.cyan },
        horzLine: { color: `${T.cyan}66`, width: 1, style: LineStyle.Dashed, labelBackgroundColor: T.cyan },
      },
      rightPriceScale: { borderColor: T.border, scaleMargins: { top: 0.08, bottom: 0.18 } },
      timeScale: { borderColor: T.border, timeVisible: false },
    });
    const cs = chart.addCandlestickSeries({
      upColor: T.emerald, downColor: T.red,
      borderUpColor: T.emerald, borderDownColor: T.red,
      wickUpColor: `${T.emerald}99`, wickDownColor: `${T.red}99`,
    });
    cs.setData(ohlcData);
    // Volume
    const vs = chart.addHistogramSeries({ color: `${T.cyan}20`, priceFormat: { type: 'volume' }, priceScaleId: 'vol' });
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
    vs.setData(ohlcData.map(d => ({ time: d.time, value: d.volume, color: d.close >= d.open ? `${T.emerald}25` : `${T.red}25` })));
    // Markers
    if (signals.length) {
      const markers = signals.slice(0,15).map((s,i) => {
        const idx = Math.max(0, ohlcData.length - 1 - i * 4);
        return { time: ohlcData[idx]?.time, position: s.direction==='LONG'?'belowBar':'aboveBar', color: s.direction==='LONG'?T.emerald:T.red, shape: s.direction==='LONG'?'arrowUp':'arrowDown', text: `${s.sourceScanner?.slice(0,5)} ${s.composite}` };
      }).filter(m=>m.time).sort((a,b)=>a.time.localeCompare(b.time));
      if (markers.length) cs.setMarkers(markers);
    }
    // Price lines
    if (selected) {
      cs.createPriceLine({ price: +selected.entry, color: T.cyan, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: 'ENTRY' });
      cs.createPriceLine({ price: +selected.stop, color: T.red, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: 'STOP' });
      cs.createPriceLine({ price: +selected.target, color: T.emerald, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: 'TARGET' });
    }
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => { if (ref.current) chart.applyOptions({ width: ref.current.clientWidth, height: ref.current.clientHeight }); });
    ro.observe(ref.current);
    return () => { ro.disconnect(); chart.remove(); };
  }, [ohlcData, signals, selected]);
  return <div ref={ref} className="w-full h-full" />;
}

// ═══════════════════════════════════════════════════════════════════════════
// DENSE SIGNAL TABLE — 25+ columns, Bloomberg-density
// ═══════════════════════════════════════════════════════════════════════════
function DenseSignalTable({ signals, selected, onSelect }) {
  const [sortCol, setSortCol] = useState('composite');
  const [sortDir, setSortDir] = useState('desc');

  const sorted = useMemo(() => {
    return [...signals].sort((a,b) => {
      const va = a[sortCol], vb = b[sortCol];
      if (typeof va === 'number' && typeof vb === 'number') return sortDir==='desc' ? vb-va : va-vb;
      return sortDir==='desc' ? String(vb).localeCompare(String(va)) : String(va).localeCompare(String(vb));
    });
  }, [signals, sortCol, sortDir]);

  const handleSort = (col) => {
    if (sortCol === col) setSortDir(d => d==='desc'?'asc':'desc');
    else { setSortCol(col); setSortDir('desc'); }
  };

  const cols = [
    { key:'symbol',       label:'SYM',    w:54 },
    { key:'direction',    label:'DIR',    w:48 },
    { key:'tier',         label:'TIER',   w:72 },
    { key:'composite',    label:'COMP',   w:44 },
    { key:'blendedScore', label:'BLEND',  w:44 },
    { key:'velezScore',   label:'VELEZ',  w:42 },
    { key:'sourceScanner',label:'SCANNER',w:72 },
    { key:'price',        label:'PRICE',  w:56 },
    { key:'rsi14',        label:'RSI',    w:36 },
    { key:'williamsR',    label:'W%R',    w:42 },
    { key:'volumeSurge',  label:'VOL%',   w:42 },
    { key:'whaleFlowScore',label:'WHALE', w:42 },
    { key:'shortInterest',label:'SI%',    w:38 },
    { key:'hurst',        label:'HURST',  w:42 },
    { key:'compressRatio',label:'CMPR',   w:42 },
    { key:'squeezeScore', label:'SQUZ',   w:38 },
    { key:'sectorScore',  label:'SECT',   w:38 },
    { key:'regimeState',  label:'REG',    w:38 },
    { key:'hmmState',     label:'HMM',    w:72 },
    { key:'mtfAlign',     label:'MTF',    w:54 },
    { key:'macroRisk',    label:'MRSK',   w:36 },
    { key:'optionsFlowBias',label:'OPT',  w:52 },
    { key:'putCallRatio', label:'P/C',    w:36 },
    { key:'impliedMove',  label:'IV%',    w:38 },
    { key:'atrPercent',   label:'ATR%',   w:38 },
    { key:'relStrength',  label:'RS',     w:36 },
    { key:'fearGreed',    label:'F&G',    w:34 },
    { key:'earningsProx', label:'ERN',    w:34 },
    { key:'timestamp',    label:'TIME',   w:68 },
  ];

  const cellColor = (col, val) => {
    if (col==='direction') return val==='LONG' ? T.emerald : T.red;
    if (col==='regimeState') return val==='GREEN'?T.emerald:val==='YELLOW'?T.amber:T.red;
    if (col==='optionsFlowBias') return val==='BULLISH'?T.emerald:T.red;
    if (col==='mtfAlign') return val==='ALIGNED'?T.emerald:val==='MIXED'?T.amber:T.red;
    if (col==='hmmState') return val?.includes('BULL')?T.emerald:val==='NEUTRAL'?T.textSec:val==='CRASH'?T.red:T.amber;
    if (['composite','blendedScore','velezScore','whaleFlowScore','sectorScore','squeezeScore'].includes(col)) {
      const n = +val; return n>=80?T.emerald:n>=65?T.cyan:n>=50?T.amber:T.red;
    }
    if (col==='rsi14') { const n=+val; return n>70?T.red:n<30?T.emerald:T.textSec; }
    return T.textSec;
  };

  return (
    <div className="overflow-auto h-full" style={{ fontSize: 10, fontFamily: T.mono }}>
      <table className="w-max min-w-full">
        <thead className="sticky top-0 z-10" style={{ background: T.bgCard }}>
          <tr>
            {cols.map(c => (
              <th key={c.key} onClick={()=>handleSort(c.key)}
                className="px-1.5 py-2 text-left cursor-pointer select-none whitespace-nowrap"
                style={{ color: sortCol===c.key?T.cyan:T.textDim, width: c.w, minWidth: c.w, fontSize: 9, letterSpacing: '0.06em', borderBottom: `1px solid ${T.border}` }}>
                {c.label}{sortCol===c.key && (sortDir==='desc'?' ▼':' ▲')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map(sig => {
            const isSel = selected?.id === sig.id;
            const tier = getTier(sig.composite);
            return (
              <tr key={sig.id} onClick={()=>onSelect(sig)} className="cursor-pointer transition-colors"
                style={{
                  background: isSel ? `${T.cyan}12` : 'transparent',
                  borderBottom: `1px solid ${T.border}`,
                  borderLeft: isSel ? `2px solid ${T.cyan}` : '2px solid transparent',
                  boxShadow: isSel ? `inset 0 0 12px ${T.cyan}08` : 'none',
                }}
                onMouseEnter={e=>{if(!isSel) e.currentTarget.style.background=T.bgCardHover;}}
                onMouseLeave={e=>{if(!isSel) e.currentTarget.style.background='transparent';}}>
                {/* Symbol */}
                <td className="px-1.5 py-1.5 font-bold" style={{ color: T.textPri }}>{sig.symbol}</td>
                {/* Direction */}
                <td className="px-1.5 py-1.5">
                  <span className="px-1 py-0.5 rounded text-[9px] font-bold" style={{ background: `${sig.direction==='LONG'?T.emerald:T.red}18`, color: sig.direction==='LONG'?T.emerald:T.red }}>
                    {sig.direction==='LONG'?'▲ L':'▼ S'}
                  </span>
                </td>
                {/* Tier */}
                <td className="px-1.5 py-1.5">
                  <span className="px-1 py-0.5 rounded text-[9px] font-bold" style={{ background: `${tier.color}15`, color: tier.color }}>
                    {sig.tier}
                  </span>
                </td>
                {/* All numeric/text columns */}
                {cols.slice(3).map(c => {
                  let val = sig[c.key];
                  if (c.key==='timestamp') val = new Date(val).toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
                  const clr = cellColor(c.key, val);
                  return (
                    <td key={c.key} className="px-1.5 py-1.5 whitespace-nowrap" style={{ color: clr }}>
                      {val}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SCANNER CONTROL PANEL — ON/OFF toggles, weight sliders, status
// ═══════════════════════════════════════════════════════════════════════════
function ScannerControlPanel({ scanners, states, onToggle, onWeight, scorers, intel, regime, regimeMult }) {
  const [expanded, setExpanded] = useState(null);
  return (
    <div className="p-2 space-y-1" style={{ fontSize: 10 }}>
      {/* Layer 1: Scanners */}
      <div className="px-2 py-1 rounded" style={{ background: `${T.cyan}08` }}>
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: T.cyan }}>LAYER 1 — SCANNERS ({scanners.filter(s=>s.layer==='scanner').length})</span>
      </div>
      {scanners.filter(s=>s.layer==='scanner').map(sc => {
        const st = states[sc.id];
        const Icon = sc.icon;
        const isExp = expanded === sc.id;
        return (
          <div key={sc.id} className="rounded border transition-all" style={{ borderColor: st.enabled ? `${sc.color}30` : T.border, background: st.enabled ? `${sc.color}05` : 'transparent' }}>
            <div className="flex items-center gap-1.5 px-2 py-1.5 cursor-pointer" onClick={()=>setExpanded(isExp?null:sc.id)}>
              {/* Toggle */}
              <button onClick={e=>{e.stopPropagation();onToggle(sc.id);}}
                className="w-7 h-3.5 rounded-full flex items-center transition-colors"
                style={{ background: st.enabled ? T.emerald : T.textDim, padding: 2 }}>
                <div className="w-2.5 h-2.5 rounded-full bg-white transition-transform" style={{ transform: st.enabled?'translateX(12px)':'translateX(0)' }}/>
              </button>
              <Icon size={11} style={{ color: st.enabled ? sc.color : T.textDim }}/>
              <span className="flex-1 text-[10px] font-semibold" style={{ color: st.enabled ? T.textPri : T.textDim }}>{sc.name}</span>
              {/* Status dots */}
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: st.enabled ? (st.errors>0?T.amber:T.emerald) : T.textDim }}/>
              {isExp ? <ChevronUp size={10} style={{color:T.textMut}}/> : <ChevronDown size={10} style={{color:T.textMut}}/>}
            </div>
            {/* Expanded: weight slider + stats */}
            {isExp && (
              <div className="px-2 pb-2 space-y-1.5">
                <div className="text-[9px]" style={{ color: T.textMut }}>{sc.desc}</div>
                <div className="text-[9px]" style={{ color: T.textMut, fontFamily: T.mono }}>File: {sc.file}</div>
                {/* Weight Slider */}
                <div className="flex items-center gap-2">
                  <span className="text-[9px]" style={{ color: T.textMut }}>Weight</span>
                  <input type="range" min={0} max={100} value={st.weight} onChange={e=>onWeight(sc.id,+e.target.value)}
                    className="flex-1 h-1 appearance-none rounded" style={{ accentColor: sc.color }}/>
                  <span className="text-[10px] font-mono w-7 text-right" style={{ color: sc.color }}>{st.weight}</span>
                </div>
                {/* Stats */}
                <div className="grid grid-cols-3 gap-1 text-[9px]">
                  <div className="rounded px-1.5 py-1" style={{ background: T.bgCard }}>
                    <div style={{ color: T.textDim }}>Last Run</div>
                    <div style={{ color: T.textSec, fontFamily: T.mono }}>{Math.floor((Date.now()-st.lastRun)/1000)}s ago</div>
                  </div>
                  <div className="rounded px-1.5 py-1" style={{ background: T.bgCard }}>
                    <div style={{ color: T.textDim }}>Symbols</div>
                    <div style={{ color: T.cyan, fontFamily: T.mono }}>{st.symbolsScanned}</div>
                  </div>
                  <div className="rounded px-1.5 py-1" style={{ background: T.bgCard }}>
                    <div style={{ color: T.textDim }}>Errors</div>
                    <div style={{ color: st.errors>0?T.red:T.emerald, fontFamily: T.mono }}>{st.errors}</div>
                  </div>
                </div>
                {/* Interval control */}
                <div className="flex items-center gap-2">
                  <span className="text-[9px]" style={{ color: T.textMut }}>Interval</span>
                  <select className="text-[9px] px-1.5 py-0.5 rounded border outline-none" style={{ background: T.bgPrimary, borderColor: T.border, color: T.textSec }}>
                    <option>60s</option><option>300s</option><option selected>900s</option><option>1800s</option><option>3600s</option>
                  </select>
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Layer 2: Scorers */}
      <div className="px-2 py-1 rounded mt-2" style={{ background: `${T.purple}08` }}>
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: T.purple }}>LAYER 2 — SCORERS</span>
      </div>
      {scorers.map(s => (
        <div key={s.id} className="flex items-center gap-2 px-2 py-1 rounded" style={{ background: `${s.color}05` }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.color }}/>
          <span className="text-[10px]" style={{ color: T.textSec }}>{s.name}</span>
          <span className="text-[9px] ml-auto" style={{ color: T.textMut }}>{s.desc}</span>
        </div>
      ))}

      {/* Layer 3: Intelligence */}
      <div className="px-2 py-1 rounded mt-2" style={{ background: `${T.amber}08` }}>
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: T.amber }}>LAYER 3 — INTELLIGENCE</span>
      </div>
      {intel.map(m => (
        <div key={m.id} className="flex items-center gap-2 px-2 py-1 rounded" style={{ background: `${m.color}05` }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: m.color }}/>
          <span className="text-[10px]" style={{ color: T.textSec }}>{m.name}</span>
          <span className="text-[9px] ml-auto" style={{ color: T.textMut }}>{m.desc}</span>
        </div>
      ))}

      {/* Regime Multiplier Override */}
      <div className="px-2 py-1 rounded mt-2" style={{ background: `${regimeMult.color}08` }}>
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: regimeMult.color }}>REGIME: {regime} ({regimeMult.mult}x)</span>
      </div>
      <div className="grid grid-cols-3 gap-1">
        {Object.entries(REGIME_MULTIPLIERS).map(([k,v]) => {
          const RIcon = v.icon;
          return (
            <div key={k} className="flex items-center gap-1 px-1.5 py-1 rounded text-[9px]"
              style={{ background: regime===k?`${v.color}12`:T.bgCard, border: `1px solid ${regime===k?`${v.color}30`:T.border}`, color: v.color }}>
              <RIcon size={9}/>{k.slice(0,4)} <span className="font-mono">{v.mult}x</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SIGNAL DETAIL PANEL (right panel "detail" tab)
// ═══════════════════════════════════════════════════════════════════════════
function SignalDetailPanel({ signal, agents }) {
  const tier = getTier(signal.composite);
  const dirColor = signal.direction==='LONG' ? T.emerald : T.red;
  return (
    <div className="p-3 space-y-3 overflow-auto" style={{ fontSize: 10 }}>
      {/* Header */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-base font-bold" style={{ color: T.textPri }}>{signal.symbol}</span>
        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold" style={{ background: `${dirColor}18`, color: dirColor }}>{signal.direction}</span>
        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold" style={{ background: `${tier.color}15`, color: tier.color }}>{signal.tier}</span>
        <span className="text-[10px] font-mono" style={{ color: T.textMut }}>Composite: {signal.composite} · Blend: {signal.blendedScore}</span>
      </div>

      {/* Trade Levels */}
      <div className="grid grid-cols-4 gap-1">
        {[
          { l: 'Entry', v: signal.entry, c: T.cyan },
          { l: 'Stop', v: signal.stop, c: T.red },
          { l: 'Target', v: signal.target, c: T.emerald },
          { l: 'R:R', v: `1:${((Math.abs(signal.target-signal.entry))/(Math.abs(signal.entry-signal.stop)||1)).toFixed(1)}`, c: T.cyan },
        ].map(x => (
          <div key={x.l} className="rounded px-2 py-1.5 text-center" style={{ background: T.bgCard, border: `1px solid ${T.border}` }}>
            <div className="text-[8px] uppercase" style={{ color: T.textDim }}>{x.l}</div>
            <div className="text-xs font-bold font-mono" style={{ color: x.c, fontFamily: T.mono }}>${x.v}</div>
          </div>
        ))}
      </div>

      {/* SHAP Factor Importance */}
      <div>
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: T.textMut }}>SHAP FACTOR IMPORTANCE</span>
        <div className="mt-1 space-y-1">
          {signal.shapFactors.map((f,i) => (
            <div key={i} className="flex items-center gap-1.5">
              <span className="w-20 text-[9px] truncate" style={{ color: T.textSec }}>{f.name}</span>
              <div className="flex-1 h-2 rounded overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)' }}>
                <div className="h-full rounded transition-all" style={{ width: `${f.weight * 400}%`, background: `${T.cyan}cc`, maxWidth: '100%' }}/>
              </div>
              <span className="text-[9px] font-mono w-8 text-right" style={{ color: T.cyan }}>{(f.weight*100).toFixed(1)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Model Agreement */}
      <div>
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: T.textMut }}>MODEL AGREEMENT</span>
        <div className="grid grid-cols-4 gap-1 mt-1">
          {Object.entries(signal.models).map(([h,m]) => {
            const agrees = m.pred === signal.direction;
            return (
              <div key={h} className="rounded px-2 py-1.5 text-center" style={{ background: agrees?`${T.emerald}08`:`${T.red}08`, border: `1px solid ${agrees?`${T.emerald}20`:`${T.red}20`}` }}>
                <div className="text-[9px] font-bold" style={{ color: T.textPri }}>{h}</div>
                <div className="text-[9px]" style={{ color: agrees?T.emerald:T.red }}>{m.pred}</div>
                <div className="text-[10px] font-mono font-bold" style={{ color: agrees?T.emerald:T.red }}>{m.conf}%</div>
              </div>
            );
          })}
          <div className="rounded px-2 py-1.5 text-center" style={{ background: `${T.cyan}08`, border: `1px solid ${T.cyan}20` }}>
            <div className="text-[9px] font-bold" style={{ color: T.textPri }}>AGREE</div>
            <div className="text-base font-bold font-mono" style={{ color: T.cyan }}>
              {Object.values(signal.models).filter(m=>m.pred===signal.direction).length}/4
            </div>
          </div>
        </div>
      </div>

      {/* Key Factors Grid */}
      <div>
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: T.textMut }}>KEY FACTORS</span>
        <div className="grid grid-cols-3 gap-1 mt-1">
          {[
            { l:'Velez', v:signal.velezScore, c:signal.velezScore>=75?T.emerald:T.amber },
            { l:'Whale', v:signal.whaleFlowScore, c:signal.whaleFlowScore>=70?T.cyan:T.textSec },
            { l:'RSI', v:signal.rsi14, c:+signal.rsi14>70?T.red:+signal.rsi14<30?T.emerald:T.textSec },
            { l:'W%R', v:signal.williamsR, c:T.textSec },
            { l:'Vol%', v:`${signal.volumeSurge}%`, c:+signal.volumeSurge>200?T.emerald:T.textSec },
            { l:'SI%', v:`${signal.shortInterest}%`, c:+signal.shortInterest>15?T.orange:T.textSec },
            { l:'Hurst', v:signal.hurst, c:+signal.hurst>0.6?T.emerald:T.amber },
            { l:'ATR%', v:`${signal.atrPercent}%`, c:T.textSec },
            { l:'P/C', v:signal.putCallRatio, c:+signal.putCallRatio>1?T.red:T.emerald },
          ].map(x => (
            <div key={x.l} className="flex items-center justify-between px-1.5 py-1 rounded" style={{ background: T.bgCard }}>
              <span className="text-[9px]" style={{ color: T.textMut }}>{x.l}</span>
              <span className="text-[10px] font-mono font-bold" style={{ color: x.c }}>{x.v}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Execute Button */}
      <button className="w-full py-2 rounded text-xs font-bold"
        style={{ background: `linear-gradient(135deg, ${dirColor}, ${dirColor}cc)`, color: '#fff', boxShadow: `0 0 20px ${dirColor}33` }}>
        Stage {signal.direction} → Execution Deck
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// AGENT CONSENSUS MATRIX
// ═══════════════════════════════════════════════════════════════════════════
function AgentConsensusMatrix({ agents, selected }) {
  return (
    <div className="mt-1 space-y-0.5">
      {agents.map(a => {
        const agrees = Math.random() > 0.3; // replace with real consensus
        return (
          <div key={a.id} className="flex items-center gap-1.5 px-1.5 py-0.5 rounded" style={{ background: agrees?`${T.emerald}06`:`${T.red}06` }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: a.color }}/>
            <span className="w-24 text-[9px] truncate" style={{ color: T.textSec }}>{a.name}</span>
            <span className="text-[9px] font-mono" style={{ color: agrees?T.emerald:T.red }}>{agrees?'AGREE':'DISS'}</span>
            {/* Confidence bar */}
            <div className="flex-1 h-1.5 rounded overflow-hidden" style={{ background: 'rgba(255,255,255,0.04)' }}>
              <div className="h-full rounded" style={{ width: `${a.confidence}%`, background: agrees?`${T.emerald}88`:`${T.red}88` }}/>
            </div>
            <span className="text-[9px] font-mono w-6 text-right" style={{ color: agrees?T.emerald:T.red }}>{a.confidence}</span>
          </div>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// CORRELATION HEATMAP
// ═══════════════════════════════════════════════════════════════════════════
function CorrelationHeatmap({ data }) {
  const ids = data.length ? Object.keys(data[0]).filter(k=>k!=='scanner') : [];
  const getColor = (v) => {
    const n = +v;
    if (n >= 0.7) return T.emerald;
    if (n >= 0.4) return T.cyan;
    if (n >= 0) return T.blue;
    if (n >= -0.3) return T.amber;
    return T.red;
  };
  return (
    <div className="mt-1 overflow-auto" style={{ fontSize: 8, fontFamily: T.mono }}>
      <table>
        <thead>
          <tr>
            <th style={{ width: 60 }}></th>
            {ids.map(id => <th key={id} className="px-0.5 py-0.5 text-center" style={{ color: T.textDim, writingMode: 'vertical-rl', transform: 'rotate(180deg)', height: 52 }}>{id.slice(0,8)}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr key={row.scanner}>
              <td className="px-1 py-0.5 text-right" style={{ color: T.textMut }}>{row.scanner.slice(0,10)}</td>
              {ids.map(col => {
                const v = row[col];
                const c = getColor(v);
                return (
                  <td key={col} className="text-center px-0.5 py-0.5">
                    <div className="w-5 h-5 rounded-sm flex items-center justify-center" style={{ background: `${c}25`, color: c, fontSize: 7 }}>
                      {v}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
