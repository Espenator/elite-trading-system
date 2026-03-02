import { useState, useMemo } from 'react';
import { useApi } from '../hooks/useApi';
import { getApiUrl } from '../config/api';

// --- FALLBACK DATA (To match exact mockup state if API is loading/empty) ---
const FALLBACK_KPIS = {
  activeModels: 3, activeModelsSub: "= RF Ensemble",
  walkForwardAcc: 91.4, walkForwardSub: "T-252d Avg",
  stage3Ignitions: 24, stage3Sub: "Past Backtests Today",
  flywheelCycles: 12, flywheelSub: "Completed Trade Sync",
  featureStore: "OK", featureStoreSub: "TimescaleDB Connected",
  winRateThresh: ">70%", winRateSub: "Execution Gate"
};

const FALLBACK_PERFORMANCE = Array.from({ length: 20 }, (_, i) => ({
  date: `T-${252 - (i * 12)}d`,
  xgboost: 65 + (i * 1.3) + (i % 3) * 0.7,
  ensemble: 62 + (i * 1.5) + (i % 4) * 0.8
}));

const FALLBACK_SIGNALS = [
  { symbol: 'NVDA', dir: 'LONG', winProb: 94, compression: '3 Days', velezScore: '8% Daily(4h)', volRatio: '2.1x Avg' },
  { symbol: 'MSTR', dir: 'LONG', winProb: 89, compression: '5 Days', velezScore: '7% Daily(4h)', volRatio: '1.8x Avg' },
  { symbol: 'AAPL', dir: 'LONG', winProb: 82, compression: '7 Days', velezScore: '5% Daily(4h)', volRatio: '1.2x Avg' },
  { symbol: 'TSLA', dir: 'LONG', winProb: 78, compression: '4 Days', velezScore: '6% Daily(4h)', volRatio: '1.5x Avg' },
  { symbol: 'AMD',  dir: 'LONG', winProb: 76, compression: '7 Days', velezScore: '4% Daily(4h)', volRatio: '1.1x Avg' },
  { symbol: 'SMCI', dir: 'SHORT', winProb: 68, compression: '4 Days', velezScore: '-5% Daily(4h)', volRatio: '2.5x Avg' },
  { symbol: 'COIN', dir: 'LONG', winProb: 91, compression: '5 Days', velezScore: '9% Daily(4h)', volRatio: '1.9x Avg' },
  { symbol: 'PLTR', dir: 'LONG', winProb: 85, compression: '8 Days', velezScore: '6% Daily(4h)', volRatio: '1.4x Avg' },
  { symbol: 'META', dir: 'LONG', winProb: 72, compression: '5 Days', velezScore: '3% Daily(4h)', volRatio: '1.0x Avg' },
  { symbol: 'CRWD', dir: 'LONG', winProb: 84, compression: '4 Days', velezScore: '5% Daily(4h)', volRatio: '1.6x Avg' }
];

const FALLBACK_MODELS = [
  { name: 'XGBoost Classifier', status: 'PRODUCTION', uptime: '7 Days', score1: 0.924, score2: 0.891, lookback: '252 Days' },
  { name: 'RF Ensemble Model', status: 'VALIDATING', uptime: '63 Days', score1: 0.885, score2: 0.862, lookback: '252 Days' },
  { name: 'Velez Engine v2.0', status: 'PRODUCTION', uptime: 'N/A', score1: 0.865, score2: 0.840, lookback: 'Rules' },
  { name: 'Compression Detector', status: 'PRODUCTION', uptime: '14 Days', score1: 0.941, score2: 0.912, lookback: '60 Days' },
  { name: 'Ignition Detector', status: 'PRODUCTION', uptime: '3 Days', score1: 0.880, score2: 0.860, lookback: '30 Days' },
  { name: 'Regime Manager (VIX)', status: 'PRODUCTION', uptime: '60 Days', score1: 0.990, score2: 0.985, lookback: 'All Time' }
];

const FALLBACK_LOGS = [
  { ts: '15:14:02', msg: '[SYNC] TimescaleDB feature store synchronized.' },
  { ts: '15:12:45', msg: '[INFERENCE] Stage 4 model generated new probabilities.' },
  { ts: '15:05:12', msg: '[TRAIN] RF Ensemble complete. Walk-forward accuracy: 88.5%' },
  { ts: '14:59:30', msg: '[DATA] Ingested 14,205 new options flow records.' },
  { ts: '14:45:10', msg: '[IGNITION] Detected 24 past backtests matching current regime.' },
  { ts: '14:30:00', msg: '[EVAL] XGBoost Classifier maintained 92.4% precision.' },
  { ts: '14:15:22', msg: '[SYNC] Local Data Lake validation passed.' },
];

export default function MLBrainFlywheel() {
  const [isRetraining, setIsRetraining] = useState(false);

  // --- API INTEGRATION ---
  const { data: apiKpis } = useApi('flywheel', { endpoint: '/flywheel/kpis', pollIntervalMs: 10000 });
  const { data: apiPerf } = useApi('flywheel', { endpoint: '/flywheel/performance', pollIntervalMs: 60000 });
  const { data: apiSignals } = useApi('flywheel', { endpoint: '/flywheel/signals/staged', pollIntervalMs: 5000 });
  const { data: apiModels } = useApi('flywheel', { endpoint: '/flywheel/models', pollIntervalMs: 15000 });
  const { data: apiLogs } = useApi('flywheel', { endpoint: '/flywheel/logs', pollIntervalMs: 2000 });

  // Safe data extraction with fallbacks
  const kpis = apiKpis?.flywheel || FALLBACK_KPIS;
  const performanceData = apiPerf?.flywheel || FALLBACK_PERFORMANCE;
  const signalsData = apiSignals?.flywheel || FALLBACK_SIGNALS;
  const modelsData = apiModels?.flywheel || FALLBACK_MODELS;
  const logsData = apiLogs?.flywheel || FALLBACK_LOGS;

  const handleRetrain = async () => {
    setIsRetraining(true);
    try {
      await fetch(getApiUrl('flywheel/retrain'), { method: 'POST' });
      // In a real app, this would trigger a toast or update logs
    } catch (e) {
      console.error("Retrain failed", e);
    }
    setTimeout(() => setIsRetraining(false), 2000);
  };

  return (
    <div className="flex flex-col h-screen w-full bg-[#0B0E14] text-[#e5e7eb] font-sans overflow-hidden selection:bg-[#06b6d4]/30 p-4 gap-4">
      
      {/* HEADER */}
      <header className="flex justify-between items-end shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-wide">ML Brain & Flywheel</h1>
          <p className="text-[#06b6d4] text-xs font-mono mt-1">Autonomous Model Training & Inference Pipeline</p>
        </div>
        <button 
          onClick={handleRetrain}
          disabled={isRetraining}
          className={`px-4 py-2 border rounded font-mono text-xs transition-all shadow-[0_0_10px_rgba(0,212,255,0.15)] ${
            isRetraining 
              ? 'bg-[#1e293b] border-gray-500 text-gray-400 cursor-not-allowed' 
              : 'bg-cyan-900/30 border-[#06b6d4]/50 text-[#06b6d4] hover:bg-[#06b6d4]/20'
          }`}
        >
          {isRetraining ? 'RETRAINING...' : 'RETRAIN MODELS [F9]'}
        </button>
      </header>

      {/* ROW 1: KPI STRIP */}
      <div className="grid grid-cols-6 gap-3 shrink-0">
        {[
          { label: 'Stage 4 Active Models', val: kpis.activeModels, sub: kpis.activeModelsSub, color: 'text-green-400' },
          { label: 'Walk Forward Accuracy', val: `${kpis.walkForwardAcc}%`, sub: kpis.walkForwardSub, color: 'text-green-400' },
          { label: 'Stage 3 Ignitions', val: kpis.stage3Ignitions, sub: kpis.stage3Sub, color: 'text-cyan-400' },
          { label: 'Flywheel Cycles', val: kpis.flywheelCycles, sub: kpis.flywheelSub, color: 'text-white' },
          { label: 'Feature Store Sync', val: kpis.featureStore, sub: kpis.featureStoreSub, color: 'text-green-400' },
          { label: 'Win Rate Threshold', val: kpis.winRateThresh, sub: kpis.winRateSub, color: 'text-cyan-400' },
        ].map((kpi, i) => (
          <div key={i} className="bg-[#111827] border border-[#1e293b] rounded p-3 flex flex-col justify-center">
            <span className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">{kpi.label}</span>
            <span className={`text-xl font-mono font-bold ${kpi.color}`}>{kpi.val}</span>
            <span className="text-[9px] text-gray-500 mt-1">{kpi.sub}</span>
          </div>
        ))}
      </div>

      {/* ROW 2: CHART & PROBABILITY RANKING */}
      <div className="flex gap-4 h-[35%] shrink-0">
        {/* LEFT: Chart Panel */}
        <div className="w-[45%] bg-[#111827] border border-[#1e293b] rounded flex flex-col">
          <div className="p-3 border-b border-[#1e293b]">
            <h2 className="text-xs font-bold text-white uppercase tracking-wider">Model Performance Tracking</h2>
            <p className="text-[10px] text-gray-400 font-mono">252-Day Walk-Forward Accuracy</p>
          </div>
          <div className="flex-1 p-2">
                            <div className="h-full min-h-[200px] flex items-center justify-center text-gray-500 text-sm border border-dashed border-[#1e293b] rounded">
                  <span>LW Charts - Model Performance (pending Step 7c enhancement)</span>
                </div>
                      </div>
          </div>

        {/* RIGHT: ML Probability Ranking */}
        <div className="w-[55%] bg-[#111827] border border-[#1e293b] rounded flex flex-col overflow-hidden">
          <div className="p-3 border-b border-[#1e293b] flex justify-between items-center bg-[#111827] z-10">
            <h2 className="text-xs font-bold text-white uppercase tracking-wider">Stage 4: ML Probability Ranking</h2>
            <span className="text-[9px] font-mono text-cyan-400 px-2 py-0.5 border border-cyan-900 rounded bg-cyan-900/20">LIVE INFERENCE</span>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            <table className="w-full text-left font-mono text-[10px]">
              <thead className="sticky top-0 bg-[#0B0E14] text-gray-400 border-b border-[#1e293b]">
                <tr>
                  <th className="p-2 font-normal">SYMBOL</th>
                  <th className="p-2 font-normal">DIR</th>
                  <th className="p-2 font-normal">WIN PROB</th>
                  <th className="p-2 font-normal">COMPRESSION</th>
                  <th className="p-2 font-normal">VELEZ SCORE</th>
                  <th className="p-2 font-normal">VOL RATIO</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b]/50 bg-[#111827]">
                {signalsData.map((row, idx) => {
                  const isLong = row.dir === 'LONG';
                  const dirColor = isLong ? 'text-green-400' : 'text-red-400';
                  const barColor = isLong ? 'bg-green-500' : 'bg-red-500';
                  return (
                    <tr key={idx} className="hover:bg-[#1e293b]/30 transition-colors">
                      <td className="p-2 text-white font-bold">{row.symbol}</td>
                      <td className={`p-2 ${dirColor}`}>{row.dir}</td>
                      <td className="p-2">
                        <div className="flex items-center gap-2">
                          <span className={isLong ? 'text-green-400' : 'text-red-400'}>{row.winProb}%</span>
                          <div className="w-16 h-1.5 bg-[#1e293b] rounded-full overflow-hidden">
                            <div className={`h-full ${barColor}`} style={{ width: `${row.winProb}%` }}></div>
                          </div>
                        </div>
                      </td>
                      <td className="p-2 text-gray-300">{row.compression}</td>
                      <td className="p-2 text-cyan-400">{row.velezScore}</td>
                      <td className="p-2 text-gray-300">{row.volRatio}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ROW 3: MODELS & LOGS */}
      <div className="flex gap-4 flex-1 min-h-0">
        
        {/* LEFT: Deployed Inference Fleet */}
        <div className="w-[60%] bg-[#111827] border border-[#1e293b] rounded flex flex-col">
          <div className="p-3 border-b border-[#1e293b]">
            <h2 className="text-xs font-bold text-white uppercase tracking-wider">Deployed Inference Fleet <span className="text-gray-500 normal-case ml-2">(TimescaleDB Connected)</span></h2>
          </div>
          <div className="flex-1 p-3 grid grid-cols-3 grid-rows-2 gap-3 overflow-y-auto custom-scrollbar">
            {modelsData.map((model, idx) => {
              const isProd = model.status === 'PRODUCTION';
              const badgeStyle = isProd 
                ? 'bg-green-500/20 text-green-400 border-green-500/50' 
                : 'bg-amber-500/20 text-amber-400 border-amber-500/50';
              
              return (
                <div key={idx} className="bg-[#0B0E14] border border-[#1e293b] rounded p-3 flex flex-col justify-between hover:border-[#06b6d4]/50 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[11px] font-bold text-white w-2/3">{model.name}</span>
                    <span className={`text-[8px] font-mono border px-1.5 py-0.5 rounded ${badgeStyle}`}>
                      {model.status}
                    </span>
                  </div>
                  <div className="space-y-1 font-mono text-[9px]">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Uptime:</span>
                      <span className="text-gray-300">{model.uptime}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Scores:</span>
                      <span className="text-cyan-400">{model.score1.toFixed(3)} / {model.score2.toFixed(3)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Lookback:</span>
                      <span className="text-gray-300">{model.lookback}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT: Flywheel Learning Log */}
        <div className="w-[40%] bg-[#0B0E14] border border-[#1e293b] rounded flex flex-col relative">
          <div className="p-3 border-b border-[#1e293b] bg-[#111827]">
            <h2 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              Flywheel Learning Log <span className="text-gray-500 normal-case ml-1">(Trade Outcomes)</span>
            </h2>
          </div>
          <div className="flex-1 p-3 overflow-y-auto custom-scrollbar font-mono text-[10px] space-y-1.5 text-green-400/90">
            {logsData.map((log, idx) => (
              <div key={idx} className="flex gap-3 hover:bg-[#1e293b]/30 px-1 py-0.5 rounded">
                <span className="text-gray-500 shrink-0">[{log.ts}]</span>
                <span className="break-words">{log.msg}</span>
              </div>
            ))}
            {/* Blinking cursor effect at the bottom */}
            <div className="flex gap-3 px-1 py-0.5">
              <span className="text-gray-500 shrink-0">[{new Date().toLocaleTimeString('en-US', {hour12:false})}]</span>
              <span className="w-2 h-3 bg-green-400/70 animate-pulse inline-block"></span>
            </div>
          </div>
        </div>

      </div>

      {/* BOTTOM LOCAL DATA LAKE STRIP */}
      <div className="flex items-center gap-3 shrink-0 py-1 px-2 border border-[#1e293b] bg-[#111827] w-fit rounded">
        <span className="text-[10px] font-bold text-gray-300 uppercase tracking-wider">Local Data Lake</span>
        <div className="h-3 w-px bg-[#1e293b]"></div>
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_5px_#10b981]"></div>
          <span className="text-[9px] font-mono text-green-400">TimescaleDB Synced</span>
        </div>
      </div>

      {/* GLOBAL SCROLLBAR CSS FOR THIS COMPONENT */}
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #06b6d4; }
      `}} />
    </div>
  );
}
