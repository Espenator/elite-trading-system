import { useState, useEffect, useMemo, useCallback } from 'react';
import { useApi } from '../hooks/useApi';
import { getApiUrl } from '../config/api';

// --- ICONS ---
const HexagonLogo = () => (
  <svg className="w-5 h-5 text-[#00d4ff]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
  </svg>
);

// --- CONSTANTS ---
const SORT_PILLS = [
  "Composite Score", "Swarm Leader", "Technical Rank", "Momentum", "Breakout",
  "Rebound", "Mean Reversion", "Kelly Optimal", "SHAP Impact", "Risk-Reward",
  "ML Probability", "Sentiment", "Volume Surge", "Sector Rotation", "Options Flow"
];

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D", "1W"];

export default function Dashboard() {
  // --- STATE ---
  const [activeSortKey, setActiveSortKey] = useState('Composite Score');
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [activeTimeframe, setActiveTimeframe] = useState("1h");
  const [autoExec, setAutoExec] = useState(false);

  // --- API HOOKS (Real-time polling) ---
  const { data: signalsData, loading: sigLoading, error: sigErr } = useApi('signals', { pollIntervalMs: 3000 });
  const { data: kellyData } = useApi('kellyRanked', { pollIntervalMs: 5000 });
  const { data: portfolioData } = useApi('portfolio', { pollIntervalMs: 5000 });
  const { data: indicesData } = useApi('marketIndices', { pollIntervalMs: 5000 });
  const { data: openclawData } = useApi('openclaw', { pollIntervalMs: 10000 });
  const { data: performanceData } = useApi('performance', { pollIntervalMs: 15000 });
  const { data: agentsData } = useApi('agents', { pollIntervalMs: 10000 });
  const { data: riskScoreData } = useApi('riskScore', { pollIntervalMs: 15000 });
  const { data: alertsData } = useApi('systemAlerts', { pollIntervalMs: 10000 });
  const { data: flywheelData } = useApi('flywheel', { pollIntervalMs: 30000 });
  const { data: sentimentData } = useApi('sentiment', { pollIntervalMs: 15000 });

  // Right Panel specific APIs based on selectedSymbol
  const { data: techsData } = useApi('signals', { endpoint: `/signals/${selectedSymbol}/technicals`, enabled: !!selectedSymbol });
  const { data: swarmData } = useApi('swarmTopology', { endpoint: `/agents/swarm-topology/${selectedSymbol}`, enabled: !!selectedSymbol });
  const { data: dataSourcesData } = useApi('dataSources', { endpoint: `/data-sources/${selectedSymbol}`, enabled: !!selectedSymbol });
  const { data: riskData } = useApi('risk', { endpoint: `/risk/proposal/${selectedSymbol}`, enabled: !!selectedSymbol });
  const { data: quotesData } = useApi('quotes', { endpoint: `/quotes/${selectedSymbol}/book`, pollIntervalMs: 1000, enabled: !!selectedSymbol });

  // --- SORT MAP (all 15 pills) ---
  const SORT_MAP = useMemo(() => ({
    'Composite Score': (a, b) => (b.score || 0) - (a.score || 0),
    'Swarm Leader': (a, b) => (b.swarmVote || '').localeCompare(a.swarmVote || ''),
    'Technical Rank': (a, b) => (b.scores?.technical || 0) - (a.scores?.technical || 0),
    'Momentum': (a, b) => (b.momentum || 0) - (a.momentum || 0),
    'Breakout': (a, b) => (b.scores?.breakout || 0) - (a.scores?.breakout || 0),
    'Rebound': (a, b) => (b.scores?.rebound || 0) - (a.scores?.rebound || 0),
    'Mean Reversion': (a, b) => (b.scores?.meanReversion || 0) - (a.scores?.meanReversion || 0),
    'Kelly Optimal': (a, b) => (b.kellyPercent || 0) - (a.kellyPercent || 0),
    'SHAP Impact': (a, b) => Math.abs(b.shapFeatures?.[0]?.impact || 0) - Math.abs(a.shapFeatures?.[0]?.impact || 0),
    'Risk-Reward': (a, b) => (b.rMultiple || 0) - (a.rMultiple || 0),
    'ML Probability': (a, b) => (b.scores?.ml || 0) - (a.scores?.ml || 0),
    'Sentiment': (a, b) => (b.scores?.sentiment || 0) - (a.scores?.sentiment || 0),
    'Volume Surge': (a, b) => (b.volSpike || 0) - (a.volSpike || 0),
    'Sector Rotation': (a, b) => (b.scores?.sectorRotation || 0) - (a.scores?.sectorRotation || 0),
    'Options Flow': (a, b) => (b.scores?.optionsFlow || 0) - (a.scores?.optionsFlow || 0),
  }), []);

  // --- DATA PROCESSING ---
  const processedSignals = useMemo(() => {
    const signalsArray = signalsData?.signals || [];
    const kellyArray = kellyData?.kellyRanked || kellyData?.kelly || [];
    if (!signalsArray.length) return [];

    let merged = signalsArray.map(sig => {
      const kelly = kellyArray.find(k => k.symbol === sig.symbol);
      return { ...sig, kellyPercent: kelly?.optimalFraction || sig.kellyPercent || 0 };
    });

    const sortFn = SORT_MAP[activeSortKey] || SORT_MAP['Composite Score'];
    return merged.sort(sortFn);
  }, [signalsData, kellyData, activeSortKey, SORT_MAP]);

  // Auto-select first symbol on load
  useEffect(() => {
    if (processedSignals.length > 0 && !selectedSymbol) {
      setSelectedSymbol(processedSignals[0].symbol);
    }
  }, [processedSignals, selectedSymbol]);

  const selectedSignal = useMemo(() =>
    processedSignals.find(s => s.symbol === selectedSymbol) || processedSignals[0],
    [processedSignals, selectedSymbol]);

  // --- EXECUTION HANDLER ---
  const handleExecute = useCallback(async (action) => {
    try {
      const res = await fetch(getApiUrl('orders'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: selectedSymbol,
          action,
          size: riskData?.proposal?.proposedSize || 100,
          limitPrice: riskData?.proposal?.limitPrice,
          stopLoss: riskData?.proposal?.stopLoss
        })
      });
      if (res.ok) alert(`Execution successful: ${action} ${selectedSymbol}`);
    } catch (err) {
      console.error("Execution failed:", err);
    }
  }, [selectedSymbol, riskData]);

  // --- ACTION HANDLERS ---
  const handleRunScan = useCallback(async () => {
    try { await fetch(getApiUrl('signals'), { method: 'POST' }); } catch (e) { console.error(e); }
  }, []);

  const handleExecTop5 = useCallback(async () => {
    const top5 = processedSignals.slice(0, 5);
    for (const sig of top5) {
      try {
        await fetch(getApiUrl('orders'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol: sig.symbol, action: sig.direction === 'LONG' ? 'BUY' : 'SELL', size: 100 })
        });
      } catch (e) { console.error(e); }
    }
  }, [processedSignals]);

  const handleFlatten = useCallback(async () => {
    try { await fetch(getApiUrl('orders') + '/flatten-all', { method: 'POST' }); } catch (e) { console.error(e); }
  }, []);

  const handleEmergencyStop = useCallback(async () => {
    try { await fetch(getApiUrl('orders') + '/emergency-stop', { method: 'POST' }); } catch (e) { console.error(e); }
  }, []);

  // --- KEYBOARD SHORTCUTS ---
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'F5') { e.preventDefault(); handleRunScan(); }
      if (e.key === 'F7') { e.preventDefault(); /* export handled via browser */ }
      if (e.key === 'n' && !e.ctrlKey && !e.metaKey && document.activeElement?.tagName !== 'INPUT') { /* spawn agent */ }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleRunScan]);

  // Safe data extraction
  const portfolio = portfolioData?.portfolio || portfolioData || {};
  const indices = indicesData?.marketIndices || indicesData || {};
  const openclaw = openclawData?.openclaw || openclawData || {};
  const performance = performanceData?.performance || performanceData || {};
  const techs = techsData?.technicals || techsData || {};
  const swarm = swarmData?.swarmTopology || swarmData || {};
  const sources = dataSourcesData?.dataSources || dataSourcesData || {};
  const risk = riskData?.proposal || riskData || {};
  const quotes = quotesData?.book || quotesData || {};
  const agents = agentsData?.agents || agentsData || {};
  const riskScore = riskScoreData?.riskScore || riskScoreData || {};
  const alerts = alertsData?.alerts || alertsData?.systemAlerts || [];
  const flywheel = flywheelData?.flywheel || flywheelData || {};
  const globalSentiment = sentimentData?.sentiment || sentimentData || {};

  // --- LOADING / ERROR STATES ---
  if (sigLoading && !signalsData?.signals) return <div className="h-screen w-full bg-[#0a0e17] flex items-center justify-center text-[#00d4ff] font-mono text-xs">INITIALIZING EMBODIER NEURAL NET...</div>;
  if (sigErr) return <div className="h-screen w-full bg-[#0a0e17] text-red-500 p-4 font-mono text-xs">SYSTEM FAULT: {sigErr.message}</div>;

  return (
    <div className="flex flex-col h-screen w-full bg-[#0a0e17] text-[#e5e7eb] font-sans text-[9px] leading-tight overflow-hidden selection:bg-[#00d4ff]/30">

      {/* 1. TOP KPI BAR */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-[#1e3a5f] bg-[#111827] shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 pr-4 border-r border-[#1e3a5f]">
            <HexagonLogo />
            <h1 className="text-xs font-bold text-white tracking-widest">EMBODIER TRADER</h1>
          </div>

          {/* Regime Badges */}
          <div className={`px-2 py-0.5 rounded font-bold tracking-wider ${openclaw.regime === 'BEAR' ? 'bg-red-500/20 text-red-400 border border-red-500/50' : 'bg-green-500/20 text-green-400 border border-green-500/50 glow-green'}`}>
            {openclaw.regime || '\u2014'}
          </div>
          <div className="flex items-center gap-1">
            <span className="text-gray-400">SCORE</span>
            <div className="w-6 h-6 rounded-full border-2 border-green-400 flex items-center justify-center text-[10px] font-mono text-green-400 glow-green">
              {openclaw.compositeScore || '\u2014'}
            </div>
          </div>
          {/* Risk Score Badge */}
          <div className={`px-2 py-0.5 rounded font-bold ${(riskScore.score || 0) > 70 ? 'bg-red-500/20 text-red-400 border border-red-500/50' : (riskScore.score || 0) > 40 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/50' : 'bg-green-500/20 text-green-400 border border-green-500/50'}`}>
            RISK {riskScore.score || '\u2014'}
          </div>
          {/* Sentiment Badge */}
          <div className={`px-2 py-0.5 rounded font-bold ${(globalSentiment.score || 0) >= 60 ? 'bg-green-500/20 text-green-400' : (globalSentiment.score || 0) >= 40 ? 'bg-amber-500/20 text-amber-400' : 'bg-red-500/20 text-red-400'}`}>
            SENT {globalSentiment.score || '\u2014'}
          </div>
        </div>
        {/* KPIs */}
        <div className="flex items-center gap-4 font-mono text-[10px]">
          <div className="flex gap-3 text-gray-300">
            <span>SPX <span className="text-green-400">+{indices.SPX?.change || '\u2014'}%</span></span>
            <span>NDAQ <span className="text-red-400">{indices.NDAQ?.change || '\u2014'}%</span></span>
            <span>BTC <span className="text-green-400">+{indices.BTC?.change || '\u2014'}%</span></span>
          </div>
          <div className="w-px h-4 bg-[#1e3a5f]"></div>
          <div className="flex gap-4">
            <span>Equity <span className="text-white">${portfolio.totalEquity?.toLocaleString() || '\u2014'}</span></span>
            <span>P&L <span className="text-green-400">+${portfolio.dayPnL?.toLocaleString() || '\u2014'}</span></span>
            <span>Deployed <span className="text-cyan-400">{portfolio.deployedPercent || '\u2014'}%</span></span>
            <span>Sharpe <span className="text-cyan-400">{performance.sharpe || '\u2014'}</span></span>
            <span>Alpha <span className="text-green-400">+{performance.alpha || '\u2014'}%</span></span>
            <span>Win <span className="text-green-400">{performance.winRate || '\u2014'}%</span></span>
            <span>MaxDD <span className="text-red-400">{performance.maxDrawdown || '\u2014'}%</span></span>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT AREA */}
      <main className="flex flex-1 overflow-hidden">

        {/* CENTER COLUMN: SIGNAL TABLE (60%) */}
        <section className="flex flex-col w-[60%] border-r border-[#1e3a5f] bg-[#0a0e17]">

          {/* Filters & Sort Bar */}
          <div className="flex flex-col border-b border-[#1e3a5f] bg-[#111827] p-2 gap-2 shrink-0">
            {/* Row 1: Pills */}
            <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
              {SORT_PILLS.map(pill => (
                <button
                  key={pill}
                  onClick={() => setActiveSortKey(pill)}
                  className={`whitespace-nowrap px-2 py-1 rounded-sm border ${activeSortKey === pill ? 'bg-[#00d4ff]/20 text-[#00d4ff] border-[#00d4ff]/50' : 'bg-transparent text-gray-400 border-gray-700 hover:border-gray-500'} transition-colors`}
                >
                  {pill}
                </button>
              ))}
            </div>
            {/* Row 2: Timeframes & Controls */}
            <div className="flex items-center justify-between text-gray-400 font-mono">
              <div className="flex items-center gap-1">
                <span>TF:</span>
                {TIMEFRAMES.map(tf => (
                  <button key={tf} onClick={() => setActiveTimeframe(tf)} className={`px-1.5 py-0.5 rounded-sm ${activeTimeframe === tf ? 'bg-[#1e3a5f] text-white' : 'hover:bg-[#1e3a5f]/50'}`}>{tf}</button>
                ))}
              </div>
              <div className="flex items-center gap-3">
                <button onClick={() => setAutoExec(!autoExec)} className="flex items-center gap-1 cursor-pointer hover:text-white transition-colors">
                  <div className={`w-1.5 h-1.5 rounded-full ${autoExec ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                  Auto-Exec: {autoExec ? 'ON' : 'OFF'}
                </button>
                <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div> LIVE</span>
                <span>Flywheel: {flywheel.accuracy || '\u2014'}%</span>
              </div>
            </div>
          </div>

          {/* Table Container */}
          <div className="flex-1 overflow-auto bg-[#0a0e17]">
            <table className="w-full text-left font-mono whitespace-nowrap">
              <thead className="sticky top-0 bg-[#111827] text-gray-400 border-b border-[#1e3a5f] shadow-md z-10">
                <tr>
                  <th className="p-1.5 font-normal">Sym</th>
                  <th className="p-1.5 font-normal">Dir</th>
                  <th className="p-1.5 font-normal">Score</th>
                  <th className="p-1.5 font-normal">Regime</th>
                  <th className="p-1.5 font-normal">ML</th>
                  <th className="p-1.5 font-normal">Sent</th>
                  <th className="p-1.5 font-normal">Tech</th>
                  <th className="p-1.5 font-normal">Agent</th>
                  <th className="p-1.5 font-normal">Swarm</th>
                  <th className="p-1.5 font-normal">SHAP</th>
                  <th className="p-1.5 font-normal">Kelly</th>
                  <th className="p-1.5 font-normal">Entry</th>
                  <th className="p-1.5 font-normal">Tgt</th>
                  <th className="p-1.5 font-normal">Stop</th>
                  <th className="p-1.5 font-normal">R-Mult</th>
                  <th className="p-1.5 font-normal">P&L</th>
                  <th className="p-1.5 font-normal">Sec</th>
                  <th className="p-1.5 font-normal">Mom</th>
                  <th className="p-1.5 font-normal">Vol</th>
                  <th className="p-1.5 font-normal">News</th>
                  <th className="p-1.5 font-normal">Pat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e3a5f]/50">
                {processedSignals.map((sig, idx) => {
                  const isSelected = selectedSymbol === sig.symbol;
                  const isLong = sig.direction === 'LONG';
                  const dirColor = isLong ? 'text-green-400' : 'text-red-400';

                  return (
                    <tr
                      key={sig.symbol + idx}
                      onClick={() => setSelectedSymbol(sig.symbol)}
                      className={`cursor-pointer hover:bg-[#1e3a5f]/30 transition-colors ${isSelected ? 'bg-[#00d4ff]/10 border-l-2 border-[#00d4ff]' : 'border-l-2 border-transparent'}`}
                    >
                      <td className="p-1.5 text-white font-bold">{sig.symbol}</td>
                      <td className={`p-1.5 ${dirColor}`}>{isLong ? 'L' : 'S'}</td>
                      <td className="p-1.5">
                        <div className="flex items-center gap-1">
                          <span className={sig.score >= 90 ? 'text-green-400' : 'text-cyan-400'}>{sig.score}</span>
                          <div className="w-12 h-1.5 bg-[#1e3a5f] rounded-full overflow-hidden">
                            <div className="h-full bg-cyan-400" style={{ width: `${sig.score}%` }}></div>
                          </div>
                        </div>
                      </td>
                      <td className="p-1.5 text-gray-300">{sig.scores?.regime || '\u2014'}</td>
                      <td className="p-1.5 text-gray-300">{sig.scores?.ml || '\u2014'}</td>
                      <td className="p-1.5 text-gray-300">{sig.scores?.sentiment || '\u2014'}</td>
                      <td className="p-1.5 text-gray-300">{sig.scores?.technical || '\u2014'}</td>
                      <td className="p-1.5 text-cyan-400 truncate max-w-[80px]">{sig.leadAgent || '\u2014'}</td>
                      <td className="p-1.5 text-gray-300">{sig.swarmVote || '\u2014'}</td>
                      <td className="p-1.5 text-gray-400 truncate max-w-[60px]">{sig.topShap || '\u2014'}</td>
                      <td className="p-1.5 text-cyan-400">{sig.kellyPercent}%</td>
                      <td className="p-1.5 text-gray-300">${sig.entry?.toFixed(2)}</td>
                      <td className="p-1.5 text-green-400">${sig.target?.toFixed(2)}</td>
                      <td className="p-1.5 text-red-400">${sig.stop?.toFixed(2)}</td>
                      <td className="p-1.5 text-white">{sig.rMultiple?.toFixed(1)}:1</td>
                      <td className="p-1.5 text-green-400">+${sig.expPnL?.toLocaleString()}</td>
                      <td className="p-1.5 text-gray-400">{sig.sector?.substring(0,3) || '\u2014'}</td>
                      <td className="p-1.5 text-green-400">+{sig.momentum || '\u2014'}</td>
                      <td className="p-1.5 text-cyan-400">{sig.volSpike || '\u2014'}x</td>
                      <td className="p-1.5 text-gray-400 truncate max-w-[50px]">{sig.newsImpact || '\u2014'}</td>
                      <td className="p-1.5 text-cyan-500 truncate max-w-[60px]">{sig.pattern || '\u2014'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Alerts Bar */}
          {Array.isArray(alerts) && alerts.length > 0 && (
            <div className="bg-amber-900/30 border-t border-amber-500/50 px-3 py-1 shrink-0 overflow-x-auto no-scrollbar">
              <div className="flex items-center gap-4 text-[8px] font-mono text-amber-400">
                <span className="font-bold">ALERTS:</span>
                {alerts.slice(0, 5).map((a, i) => (
                  <span key={i} className="whitespace-nowrap">{a.message || a.msg || a}</span>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* RIGHT COLUMN: DETAIL DEEP DIVE (40%) */}
        <section className="flex flex-col w-[40%] bg-[#111827] overflow-y-auto custom-scrollbar p-3 space-y-3">

          {/* Header */}
          <div className="flex justify-between items-center pb-2 border-b border-[#1e3a5f]">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              {selectedSignal?.symbol}
              <span className={selectedSignal?.direction === 'LONG' ? 'text-green-400' : 'text-red-400'}>
                {selectedSignal?.direction || 'LONG'}
              </span>
            </h2>
            <div className="flex flex-col items-end">
              <span className="text-[8px] text-gray-400 uppercase">Composite Score</span>
              <span className="text-2xl font-mono font-bold text-[#00d4ff] glow-cyan">{selectedSignal?.score || '\u2014'}</span>
            </div>
          </div>

          {/* 1. COMPOSITE BREAKDOWN */}
          <div className="space-y-1.5">
            <h3 className="text-[9px] text-[#00d4ff] font-bold uppercase tracking-wider">Composite Breakdown</h3>
            <div className="bg-[#0a0e17] border border-[#1e3a5f] rounded p-2 space-y-1 font-mono text-[8px]">
              {[
                { label: 'Overall Score', val: `${selectedSignal?.score || 0}/100`, pct: selectedSignal?.score || 0 },
                { label: 'Technical Rank', val: `${selectedSignal?.scores?.technical || '\u2014'}`, pct: selectedSignal?.scores?.technical || 0 },
                { label: 'ML Probability', val: `${selectedSignal?.scores?.ml || '\u2014'}%`, pct: selectedSignal?.scores?.ml || 0 },
                { label: 'Sentiment Pulse', val: `${selectedSignal?.scores?.sentiment || '\u2014'}`, pct: selectedSignal?.scores?.sentiment || 0 },
                { label: 'Swarm Consensus', val: `${swarm.consensus || '\u2014'}%`, pct: swarm.consensus || 0 },
              ].map(item => (
                <div key={item.label} className="flex items-center justify-between">
                  <span className="text-gray-400 w-24">{item.label}</span>
                  <div className="flex-1 mx-2 h-1 bg-[#1e3a5f] rounded-full">
                    <div className="h-full bg-[#00d4ff] rounded-full" style={{ width: `${item.pct}%` }}></div>
                  </div>
                  <span className="text-white w-10 text-right">{item.val}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 2. TECHNICAL ANALYSIS */}
          <div className="space-y-1.5">
            <h3 className="text-[9px] text-[#00d4ff] font-bold uppercase tracking-wider">Technical Analysis</h3>
            <div className="grid grid-cols-2 gap-1.5 bg-[#0a0e17] border border-[#1e3a5f] rounded p-2 font-mono text-[8px]">
              <div><span className="text-gray-400">RSI:</span> <span className="text-green-400">{techs.rsi || '\u2014'}</span></div>
              <div><span className="text-gray-400">MACD:</span> <span className="text-green-400">{techs.macd || '\u2014'}</span></div>
              <div><span className="text-gray-400">BB:</span> <span className="text-white">{techs.bb || '\u2014'}</span></div>
              <div><span className="text-gray-400">VWAP:</span> <span className="text-cyan-400">{techs.vwap || '\u2014'}</span></div>
              <div><span className="text-gray-400">20 EMA:</span> <span className="text-white">{techs.ema20 || '\u2014'}</span></div>
              <div><span className="text-gray-400">50 SMA:</span> <span className="text-green-400">{techs.sma50 || '\u2014'}</span></div>
              <div><span className="text-gray-400">ADX:</span> <span className="text-white">{techs.adx || '\u2014'}</span></div>
              <div><span className="text-gray-400">Stoch:</span> <span className="text-green-400">{techs.stoch || '\u2014'}</span></div>
            </div>
          </div>

          {/* 3. ML ENGINE & SHAP */}
          <div className="space-y-1.5">
            <h3 className="text-[9px] text-[#00d4ff] font-bold uppercase tracking-wider">ML Engine & SHAP Drivers</h3>
            <div className="bg-[#0a0e17] border border-[#1e3a5f] rounded p-2 font-mono text-[8px]">
              <div className="flex justify-between mb-2 pb-2 border-b border-[#1e3a5f]/50">
                <span className="text-gray-400">Probability LONG: <span className="text-green-400 font-bold">{selectedSignal?.scores?.ml || '\u2014'}%</span></span>
                <span className="text-gray-400">Drift Score: <span className="text-green-400">{techs.driftScore || '\u2014'}</span></span>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-gray-400 mb-1"><span>Feature</span><span>Impact</span></div>
                {(techs.shapFeatures || selectedSignal?.shapFeatures || []).slice(0, 5).map(s => (
                  <div key={s.feature} className="flex items-center justify-between">
                    <span className="text-white truncate w-24">{s.feature}</span>
                    <div className="flex-1 flex items-center mx-2">
                      {s.impact < 0 ? (
                        <div className="w-1/2 flex justify-end"><div className="h-1.5 bg-red-500" style={{ width: `${Math.abs(s.impact) * 500}%` }}></div></div>
                      ) : (
                        <div className="w-1/2"></div>
                      )}
                      {s.impact > 0 && (
                        <div className="w-1/2"><div className="h-1.5 bg-green-500" style={{ width: `${Math.abs(s.impact) * 500}%` }}></div></div>
                      )}
                    </div>
                    <span className={s.impact > 0 ? 'text-green-400 w-8 text-right' : 'text-red-400 w-8 text-right'}>
                      {s.impact > 0 ? `+${s.impact.toFixed(2)}` : s.impact.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 4. AGENT SWARM */}
          <div className="space-y-1.5">
            <h3 className="text-[9px] text-[#00d4ff] font-bold uppercase tracking-wider">Swarm Consensus ({swarm.total || '\u2014'} Agents)</h3>
            <div className="flex gap-2 bg-[#0a0e17] border border-[#1e3a5f] rounded p-2 font-mono text-[8px]">
              <div className="w-1/3 flex flex-col items-center justify-center border-r border-[#1e3a5f]">
                <div className="text-xl font-bold text-green-400">{swarm.consensus || '\u2014'}%</div>
                <div className="text-gray-400">{swarm.signal || '\u2014'}</div>
                <div className="text-[7px] text-gray-500 mt-1">{swarm.buyCount || 0} Buy / {swarm.sellCount || 0} Sell / {swarm.holdCount || 0} Hold</div>
              </div>
              <div className="w-2/3 grid grid-cols-2 gap-x-2 gap-y-1">
                {(swarm.agents || []).slice(0, 6).map((agent, i) => (
                  <span key={i} className="text-gray-400">{agent.name}: <span className={agent.vote === 'BUY' ? 'text-green-400' : agent.vote === 'SELL' ? 'text-red-400' : 'text-gray-500'}>{agent.vote} {agent.confidence}%</span></span>
                ))}
              </div>
            </div>
          </div>

          {/* 5. DATA SOURCES */}
          <div className="space-y-1.5">
            <h3 className="text-[9px] text-[#00d4ff] font-bold uppercase tracking-wider">Real-Time Data Feeds</h3>
            <div className="bg-[#0a0e17] border border-[#1e3a5f] rounded p-2 space-y-1 font-mono text-[8px]">
              <div className="flex justify-between"><span className="text-gray-400">Market Data:</span> <span className="text-white">Price ${sources.price || '\u2014'} | Vol {sources.vol || '\u2014'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">NewsAPI:</span> <span className="text-green-400">{sources.news?.summary || '\u2014'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Social (Reddit/X):</span> <span className="text-green-400">{sources.social?.reddit || '\u2014'}% / {sources.social?.twitter || '\u2014'}%</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Options Flow:</span> <span className="text-cyan-400">P/C {sources.options?.putCallRatio || '\u2014'} ({sources.options?.bias || '\u2014'})</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Dark Pool:</span> <span className="text-white">{sources.darkPool?.buySidePct || '\u2014'}% Buy Side Executions</span></div>
            </div>
          </div>

          {/* 6. RISK & ORDER PROPOSAL */}
          <div className="space-y-1.5">
            <h3 className="text-[9px] text-[#00d4ff] font-bold uppercase tracking-wider">Risk & Order Proposal</h3>
            <div className="bg-[#0a0e17] border border-[#1e3a5f] rounded p-2 font-mono text-[8px]">
              <div className="text-[#00d4ff] mb-1 font-bold">PROPOSED ENTRY</div>
              <div className="grid grid-cols-2 gap-1 mb-2 pb-2 border-b border-[#1e3a5f]/50">
                <span className="text-gray-400">Action: <span className="text-white">Limit Buy {risk.limitPrice || '\u2014'}</span></span>
                <span className="text-gray-400">Size: <span className="text-white">{risk.shares || '\u2014'} shs (${risk.notional || '\u2014'})</span></span>
                <span className="text-gray-400">Stop Loss: <span className="text-red-400">{risk.stopLoss || '\u2014'}</span></span>
                <span className="text-gray-400">Target 1: <span className="text-green-400">{risk.target1 || '\u2014'}</span></span>
                <span className="text-gray-400">R:R Ratio: <span className="text-cyan-400">{risk.rr || '\u2014'}</span></span>
                <span className="text-gray-400">Sizing: <span className="text-white">Kelly {selectedSignal?.kellyPercent}%</span></span>
              </div>

              {/* L2 Order Book */}
              <div className="text-gray-400 mb-1">LIVE L2 ORDER BOOK (Spread: ${quotes.spread?.toFixed(2) || '\u2014'})</div>
              <div className="flex flex-col gap-[1px]">
                {quotes.asks?.slice(0,3).reverse().map((ask, i) => (
                  <div key={'ask'+i} className="flex items-center text-[7px]">
                    <span className="w-10 text-red-400">{ask.price}</span>
                    <span className="w-8 text-right mr-1">{ask.size}</span>
                    <div className="h-1.5 bg-red-500/30" style={{ width: `${(ask.size/1500)*100}%` }}></div>
                  </div>
                )) || <div className="text-gray-500 text-center py-1">Awaiting L2 data...</div>}
                <div className="h-px bg-[#1e3a5f] my-0.5"></div>
                {quotes.bids?.slice(0,3).map((bid, i) => (
                  <div key={'bid'+i} className="flex items-center text-[7px]">
                    <span className="w-10 text-green-400">{bid.price}</span>
                    <span className="w-8 text-right mr-1">{bid.size}</span>
                    <div className="h-1.5 bg-green-500/30" style={{ width: `${(bid.size/1500)*100}%` }}></div>
                  </div>
                )) || <div className="text-gray-500 text-center py-1">Awaiting L2 data...</div>}
              </div>
            </div>
          </div>

          {/* 7. EXECUTION CONTROLS */}
          <div className="pt-2">
            <div className="grid grid-cols-2 gap-1.5 mb-1.5">
              <button onClick={() => handleExecute('BUY')} className="bg-green-600 hover:bg-green-500 text-white font-bold py-1.5 rounded shadow-[0_0_8px_rgba(16,185,129,0.4)]">EXECUTE LONG</button>
              <button onClick={() => handleExecute('SELL')} className="bg-red-600 hover:bg-red-500 text-white font-bold py-1.5 rounded shadow-[0_0_8px_rgba(239,68,68,0.4)]">EXECUTE SHORT</button>
            </div>
            <div className="grid grid-cols-3 gap-1.5 mb-1.5">
              <button className="bg-[#1e3a5f] hover:bg-cyan-900 text-cyan-400 py-1 rounded">Limit Order</button>
              <button className="bg-[#1e3a5f] hover:bg-cyan-900 text-cyan-400 py-1 rounded">Stop Limit</button>
              <button className="bg-[#1e3a5f] hover:bg-amber-900 text-amber-400 py-1 rounded">Modify Setup</button>
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              <button className="bg-blue-900/50 hover:bg-blue-800 text-blue-300 py-1 rounded border border-blue-800">Paper Trade</button>
              <button className="bg-gray-800 hover:bg-gray-700 text-gray-300 py-1 rounded">Cancel / Reject</button>
            </div>
          </div>
        </section>
      </main>

      {/* BOTTOM ACTION BAR */}
      <footer className="flex items-center justify-between px-3 py-1.5 bg-[#0a0e17] border-t border-[#1e3a5f] shrink-0 font-mono text-[8px] text-gray-400">
        <div className="flex gap-2">
          <button onClick={handleRunScan} className="bg-[#1e3a5f] hover:bg-[#1e3a5f]/80 text-white px-2 py-0.5 rounded">Run Scan [F5]</button>
          <button className="bg-[#1e3a5f] hover:bg-[#1e3a5f]/80 text-white px-2 py-0.5 rounded">Spawn [N]</button>
          <button className="bg-[#1e3a5f] hover:bg-[#1e3a5f]/80 text-white px-2 py-0.5 rounded">Export [F7]</button>
          <button onClick={handleExecTop5} className="bg-cyan-900 text-cyan-400 px-2 py-0.5 rounded">Exec Top 5</button>
          <button onClick={handleFlatten} className="bg-amber-900 text-amber-400 px-2 py-0.5 rounded">Flatten</button>
          <button onClick={handleEmergencyStop} className="bg-red-900 text-red-400 px-2 py-0.5 rounded font-bold">EMERGENCY STOP</button>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-green-500"></div> WS</span>
          <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-green-500"></div> API</span>
          <span>{agents.total || swarm.total || '\u2014'} Agents</span>
          <span>CPU {performance.cpu || '\u2014'}%</span>
          <span>GPU {performance.gpu || '\u2014'}%</span>
          <span>Uptime {performance.uptime || '\u2014'}</span>
        </div>
      </footer>

      {/* Global CSS */}
      <style dangerouslySetInnerHTML={{__html: `
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #0a0e17; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e3a5f; border-radius: 2px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #00d4ff; }
        .glow-green { box-shadow: 0 0 8px rgba(16,185,129,0.3); }
        .glow-cyan { text-shadow: 0 0 8px rgba(0,212,255,0.6); }
      `}} />
    </div>
  );
}
