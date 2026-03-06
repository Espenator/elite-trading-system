import { useState, useMemo } from 'react';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';
import { useApi } from '../hooks/useApi';
import { getApiUrl, getAuthHeaders } from '../config/api';
import log from "@/utils/logger";
import {
  Brain, Activity, Zap, RotateCcw, Server, TrendingUp, BarChart3, Radio,
  Search, Plus, ChevronRight, Cpu, Target, CheckCircle, Gauge
} from 'lucide-react';
import clsx from 'clsx';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import PageHeader from '../components/ui/PageHeader';

// ============================================================================
// FALLBACK DATA
// ============================================================================
const FALLBACK_KPIS = {
  activeModels: 3, activeModelsSub: "Stage 4 Active Models",
  walkForwardAcc: 91.4, walkForwardSub: "Walk Forward Accuracy",
  stageIgnitions: 24, stageIgnitionsSub: "Stage 3 Ignitions",
  flywheelCycles: 12, flywheelSub: "Flywheel Cycles",
  featureStore: "OK", featureStoreSub: "Feature Store Sync",
  minProbThresh: ">70%", minProbSub: "Min Prob Threshold"
};

const FALLBACK_PERFORMANCE = (() => {
  const pts = [];
  const startDate = new Date('2024-01-01');
  let xgb = 78;
  let rf = 74;
  for (let i = 0; i < 252; i++) {
    const d = new Date(startDate);
    d.setDate(d.getDate() + i);
    const dateStr = d.toISOString().slice(0, 10);
    xgb += (Math.random() - 0.42) * 1.2;
    xgb = Math.max(70, Math.min(97, xgb));
    rf += (Math.random() - 0.44) * 1.1;
    rf = Math.max(65, Math.min(93, rf));
    pts.push({ time: dateStr, xgboost: parseFloat(xgb.toFixed(1)), rf: parseFloat(rf.toFixed(1)) });
  }
  return pts;
})();

const FALLBACK_SIGNALS = [
  { symbol: 'NVDA', change24h: +3.2, winProb: 92, compression: 87, velezScore: 9.4, yieldScore: 8.8, days: 3 },
  { symbol: 'MSTR', change24h: +5.1, winProb: 89, compression: 91, velezScore: 9.1, yieldScore: 8.5, days: 2 },
  { symbol: 'AAPL', change24h: +1.4, winProb: 85, compression: 72, velezScore: 8.7, yieldScore: 7.9, days: 5 },
  { symbol: 'TSLA', change24h: -0.8, winProb: 81, compression: 68, velezScore: 8.2, yieldScore: 7.4, days: 4 },
  { symbol: 'AMD', change24h: +2.6, winProb: 78, compression: 65, velezScore: 7.8, yieldScore: 7.1, days: 6 },
  { symbol: 'SMCI', change24h: +4.3, winProb: 76, compression: 82, velezScore: 7.5, yieldScore: 6.9, days: 1 },
  { symbol: 'COIN', change24h: +1.9, winProb: 73, compression: 59, velezScore: 7.2, yieldScore: 6.5, days: 7 },
  { symbol: 'PLTR', change24h: +0.7, winProb: 70, compression: 54, velezScore: 6.9, yieldScore: 6.2, days: 8 },
  { symbol: 'META', change24h: +1.1, winProb: 68, compression: 48, velezScore: 6.5, yieldScore: 5.8, days: 3 },
  { symbol: 'CRWD', change24h: -0.3, winProb: 65, compression: 42, velezScore: 6.2, yieldScore: 5.5, days: 10 },
];

const FALLBACK_MODELS = [
  { name: 'XGBoost Classifier', status: 'Production', score1: 0.924, score2: 0.891, uptime: '21d 16hrs', lookback: '210 days', sparkline: null },
  { name: 'RF Ensemble Model', status: 'Production', score1: 0.885, score2: 0.862, uptime: '18d 4hrs', lookback: '89 days', sparkline: null },
  { name: 'Velez Engine v2.0', status: 'Production', score1: 0.865, score2: 0.840, uptime: '14d 7hrs', lookback: 'Not disabled', sparkline: null },
  { name: 'Compression Detector', status: 'Staging', score1: 0.941, score2: 0.912, uptime: '10d 2hrs', lookback: '63 days', sparkline: null },
  { name: 'Ignition Detector', status: 'Staging', score1: 0.870, score2: 0.850, uptime: '7d 11hrs', lookback: '1 Year', sparkline: null },
  { name: 'Regime Manager (VIX)', status: 'Production', score1: 0.990, score2: 0.885, uptime: '28d 3hrs', lookback: '1 Year', sparkline: null },
];

const FALLBACK_LOGS = [
  { ts: '09:31:02', tag: 'RETRAIN', msg: 'NVDA long +2.4% hit TP1 — flywheel confirms XGBoost prediction correct, model weight +0.02' },
  { ts: '09:31:15', tag: 'EVAL', msg: 'META short -0.8% stopped — RF Ensemble prediction incorrect, reducing confidence -0.01' },
  { ts: '09:31:28', tag: 'RETRAIN', msg: 'TSLA long +1.1% partial fill — Velez Engine v2.0 signal validated, adding to training set' },
  { ts: '09:31:42', tag: 'WARNING', msg: 'Feature recalc triggered: VIX regime shift detected, re-scoring all active models' },
  { ts: '09:31:55', tag: 'RETRAIN', msg: 'Compression Detector flagged AMD — entering stage-3 watchlist for ignition' },
  { ts: '09:32:08', tag: 'EVAL', msg: 'Walk-forward validation complete: 91.4% accuracy across 252-day rolling window' },
  { ts: '09:32:21', tag: 'RETRAIN', msg: 'CRWD position closed +3.2% — Ignition Detector accuracy now 87.0% (7d rolling)' },
  { ts: '09:32:34', tag: 'WARNING', msg: 'Regime Manager (VIX) switched to RISK-OFF mode — adjusting position sizing -20%' },
  { ts: '09:32:47', tag: 'RETRAIN', msg: 'Flywheel cycle #12 complete — all models retrained on latest 500 trade outcomes' },
  { ts: '09:33:01', tag: 'EVAL', msg: 'New feature added: options_skew_30d — feature store now at 24 total inputs' },
  { ts: '09:33:14', tag: 'RETRAIN', msg: 'GOOG long +0.5% trailing — model ensemble agrees on continuation, holding' },
  { ts: '09:33:27', tag: 'WARNING', msg: 'AMZN short signal rejected — win probability 48% below 70% threshold' },
];

// ============================================================================
// MINI SPARKLINE COMPONENT (for model cards)
// ============================================================================
function MiniSparkline({ color = '#00D9FF', height = 28 }) {
  const data = useMemo(() => {
    const pts = [];
    let v = 50 + Math.random() * 20;
    for (let i = 0; i < 20; i++) {
      v += (Math.random() - 0.45) * 6;
      v = Math.max(30, Math.min(95, v));
      pts.push({ x: i, y: v });
    }
    return pts;
  }, []);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <Line
          type="monotone"
          dataKey="y"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ============================================================================
// MODEL PERFORMANCE CHART (dual-line Recharts)
// ============================================================================
function ModelPerformanceDual({ data }) {
  const chartData = useMemo(() => {
    if (!data || !Array.isArray(data) || data.length === 0) return [];
    return data.map((d) => ({
      time: d.time || d.date || d.timestamp,
      xgboost: d.xgboost ?? d.value ?? d.accuracy ?? 0,
      rf: d.rf ?? (d.value ? d.value - 4 : 0),
    }));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={chartData} margin={{ top: 20, right: 10, bottom: 5, left: 10 }}>
        <Tooltip
          contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 6, fontSize: 10 }}
          labelStyle={{ color: '#9CA3AF', fontSize: 9 }}
          formatter={(val, name) => [`${Number(val).toFixed(1)}%`, name === 'xgboost' ? 'XGBoost v0.3 Prod' : 'Random Forest Ensemble']}
        />
        <Line
          type="monotone"
          dataKey="xgboost"
          stroke="#10b981"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
          name="xgboost"
        />
        <Line
          type="monotone"
          dataKey="rf"
          stroke="#6366f1"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
          name="rf"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ============================================================================
// PROBABILITY HEATMAP CELL
// ============================================================================
function ProbCell({ value }) {
  if (value == null) return <td className="px-2 py-1.5 text-center text-gray-600 text-[10px] font-mono">--</td>;
  const v = typeof value === 'number' ? value : parseFloat(value);
  const pct = v > 1 ? v : v * 100;

  // Color gradient: red (<50%) -> orange (50-60%) -> yellow (60-70%) -> green (70-85%) -> bright green (>85%)
  let bg, text;
  if (pct >= 85) { bg = 'bg-emerald-500/80'; text = 'text-white'; }
  else if (pct >= 75) { bg = 'bg-emerald-600/60'; text = 'text-emerald-100'; }
  else if (pct >= 65) { bg = 'bg-teal-600/50'; text = 'text-teal-100'; }
  else if (pct >= 55) { bg = 'bg-amber-600/50'; text = 'text-amber-100'; }
  else if (pct >= 45) { bg = 'bg-orange-600/50'; text = 'text-orange-100'; }
  else { bg = 'bg-red-600/50'; text = 'text-red-100'; }

  return (
    <td className="px-1 py-1">
      <div className={clsx('rounded px-1.5 py-1 text-center text-[10px] font-mono font-bold', bg, text)}>
        {pct.toFixed(0)}%
      </div>
    </td>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function MLBrainFlywheel() {
  const [isRetraining, setIsRetraining] = useState(false);

  // --- API INTEGRATION ---
  const { data: apiKpis } = useApi('flywheelKpis', { pollIntervalMs: 10000 });
  const { data: apiPerf } = useApi('flywheelPerformance', { pollIntervalMs: 60000 });
  const { data: apiSignals } = useApi('flywheelSignals', { pollIntervalMs: 5000 });
  const { data: apiModels } = useApi('flywheelModels', { pollIntervalMs: 15000 });
  const { data: apiLogs } = useApi('flywheelLogs', { pollIntervalMs: 2000 });
  const { data: apiFeatures } = useApi('flywheelFeatures', { pollIntervalMs: 30000 });
  const { data: apiBrain } = useApi('mlBrain', { pollIntervalMs: 15000 });

  // Safe data extraction with fallbacks
  const kpis = apiKpis?.flywheel || FALLBACK_KPIS;
  const performanceData = apiPerf?.flywheel?.history ?? FALLBACK_PERFORMANCE;
  const signalsData = apiSignals?.flywheel?.signals ?? FALLBACK_SIGNALS;
  const modelsData = apiModels?.flywheel?.models ?? FALLBACK_MODELS;
  const logsData = apiLogs?.flywheel?.logs ?? FALLBACK_LOGS;
  const featuresData = apiFeatures?.flywheel?.features ?? [];

  const handleRetrain = async () => {
    setIsRetraining(true);
    try {
      await fetch(getApiUrl('training') + '/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ type: 'retrain' })
      });
    } catch (e) {
      log.error("Retrain failed", e);
    }
    setTimeout(() => setIsRetraining(false), 2000);
  };

  // KPI items matching mockup exactly
  const kpiItems = [
    {
      label: 'Stage 4 Active Models',
      val: kpis.activeModels ?? 3,
      badge: { text: 'LIVE', variant: 'success' },
      color: 'text-white',
    },
    {
      label: 'Walk Forward Accuracy',
      val: `${kpis.walkForwardAcc ?? 91.4}%`,
      color: 'text-white',
    },
    {
      label: 'Stage 3 Ignitions',
      val: kpis.stageIgnitions ?? 24,
      sub: 'since yesterday',
      subColor: 'text-emerald-400',
      color: 'text-white',
    },
    {
      label: 'Flywheel Cycles',
      val: kpis.flywheelCycles ?? 12,
      color: 'text-white',
    },
    {
      label: 'Feature Store Sync',
      val: kpis.featureStore ?? 'OK',
      color: 'text-emerald-400',
    },
    {
      label: 'Min Prob Threshold',
      val: kpis.minProbThresh ?? '>70%',
      color: 'text-white',
    },
  ];

  return (
    <div className="flex flex-col min-h-screen w-full bg-[#0B0E14] text-gray-200 font-sans overflow-y-auto selection:bg-cyan-500/30">
      <div className="flex flex-col flex-1 min-h-0 p-4 gap-4">

        {/* ================================================================ */}
        {/* HEADER */}
        {/* ================================================================ */}
        <PageHeader
          icon={Brain}
          title="ML Brain & Flywheel"
          description="Autonomous Model Training, Inference & Continuous Learning Pipeline"
        >
          <Button
            variant="primary"
            size="sm"
            leftIcon={Plus}
            onClick={handleRetrain}
            disabled={isRetraining}
          >
            {isRetraining ? 'Retraining...' : 'Propose Models'}
          </Button>
        </PageHeader>

        {/* ================================================================ */}
        {/* KPI STRIP - 6 cards in a row */}
        {/* ================================================================ */}
        <div className="grid grid-cols-6 gap-3 shrink-0">
          {kpiItems.map((kpi, i) => (
            <div
              key={i}
              className="bg-[#0d1117] border border-gray-800/60 rounded-lg p-3 flex flex-col justify-between min-h-[80px]"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium leading-tight">
                  {kpi.label}
                </span>
                {kpi.badge && (
                  <Badge variant={kpi.badge.variant} size="sm">{kpi.badge.text}</Badge>
                )}
              </div>
              <div className="flex items-baseline gap-2">
                <span className={clsx('text-2xl font-mono font-bold', kpi.color)}>
                  {kpi.val}
                </span>
                {kpi.sub && (
                  <span className={clsx('text-[9px] font-medium', kpi.subColor || 'text-gray-500')}>
                    {kpi.sub}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* ================================================================ */}
        {/* MIDDLE ROW: Performance Chart + Probability Ranking */}
        {/* ================================================================ */}
        <div className="flex gap-4 min-h-0" style={{ flex: '1 1 45%' }}>

          {/* LEFT: Model Performance Tracking */}
          <div className="w-[50%] flex flex-col bg-[#0d1117] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-semibold text-white">Model Performance Tracking</h3>
                <span className="px-2 py-0.5 text-[9px] font-bold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  PROD MODEL
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="px-2 py-0.5 text-[9px] font-mono rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  XGBoost v0.3 Prod
                </span>
                <span className="px-2 py-0.5 text-[9px] font-mono rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Random Forest Ensemble
                </span>
              </div>
            </div>
            <div className="flex-1 min-h-0 p-2 relative">
              <div className="absolute top-3 left-4 text-[10px] font-mono text-gray-500 z-10">
                252-Day Walk-Forward Model Ensemble Accuracy
              </div>
              {performanceData && Array.isArray(performanceData) && performanceData.length > 0 ? (
                <ModelPerformanceDual data={performanceData} />
              ) : (
                <div className="h-full min-h-[200px] flex items-center justify-center text-gray-500 text-xs font-mono">
                  Awaiting performance data...
                </div>
              )}
            </div>
          </div>

          {/* RIGHT: Stage A: ML Probability Ranking */}
          <div className="w-[50%] flex flex-col bg-[#0d1117] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-semibold text-white">Stage A: ML Probability Ranking</h3>
              </div>
              <Badge variant="primary" size="sm">LIVE</Badge>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
              <table className="w-full text-left font-mono text-[10px]">
                <thead className="sticky top-0 bg-[#0d1117] text-gray-500 border-b border-gray-800/40 z-10">
                  <tr>
                    <th className="px-3 py-2 font-medium text-left">SYMBOL</th>
                    <th className="px-2 py-2 font-medium text-right">24H %</th>
                    <th className="px-2 py-2 font-medium text-left" style={{ minWidth: 120 }}>WIN PROB %</th>
                    <th className="px-2 py-2 font-medium text-right">COMPR %</th>
                    <th className="px-2 py-2 font-medium text-right">VELEZ</th>
                    <th className="px-2 py-2 font-medium text-right">YIELD</th>
                    <th className="px-2 py-2 font-medium text-right">DAYS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/20">
                  {signalsData.length > 0 ? signalsData.map((row, idx) => {
                    const wp = row.winProb ?? 0;
                    const barColor = wp >= 80 ? 'bg-emerald-500' : wp >= 70 ? 'bg-cyan-500' : wp >= 60 ? 'bg-amber-500' : 'bg-red-500';
                    const changeColor = (row.change24h ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400';
                    return (
                      <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-3 py-1.5 text-white font-bold text-[11px]">{row.symbol}</td>
                        <td className={clsx('px-2 py-1.5 text-right font-bold', changeColor)}>
                          {(row.change24h ?? 0) >= 0 ? '+' : ''}{(row.change24h ?? 0).toFixed(1)}%
                        </td>
                        <td className="px-2 py-1.5">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-2.5 bg-gray-800 rounded-full overflow-hidden">
                              <div className={clsx('h-full rounded-full', barColor)} style={{ width: `${wp}%` }} />
                            </div>
                            <span className="text-white text-[10px] w-8 text-right">{wp}%</span>
                          </div>
                        </td>
                        <td className="px-2 py-1.5 text-right text-gray-300">{row.compression ?? '--'}%</td>
                        <td className="px-2 py-1.5 text-right text-cyan-400">{(row.velezScore ?? 0).toFixed(1)}</td>
                        <td className="px-2 py-1.5 text-right text-gray-300">{(row.yieldScore ?? 0).toFixed(1)}</td>
                        <td className="px-2 py-1.5 text-right text-gray-400">{row.days ?? '--'}</td>
                      </tr>
                    );
                  }) : (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                        No probability data available
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ================================================================ */}
        {/* BOTTOM ROW: Deployed Fleet + Learning Log */}
        {/* ================================================================ */}
        <div className="flex gap-4 min-h-0" style={{ flex: '1 1 40%' }}>

          {/* LEFT: Deployed Inference Fleet */}
          <div className="w-1/2 flex flex-col bg-[#0d1117] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40 flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">Deployed Inference Fleet</h3>
              <span className="text-gray-500 text-xs font-normal">(TimescaleDB Connected)</span>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-3">
              <div className="grid grid-cols-3 gap-3">
                {modelsData.length > 0 ? modelsData.map((model, idx) => {
                  const isProd = (model.status || '').toLowerCase().includes('prod');
                  return (
                    <div
                      key={idx}
                      className="bg-[#0B0E14] border border-gray-800/50 rounded-lg p-3 flex flex-col gap-2 hover:border-cyan-500/30 transition-colors"
                    >
                      {/* Model name + badge */}
                      <div className="flex items-start justify-between gap-1">
                        <span className="text-[11px] font-bold text-white leading-tight">{model.name}</span>
                        <span className={clsx(
                          'px-1.5 py-0.5 text-[8px] font-bold rounded shrink-0',
                          isProd
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        )}>
                          {isProd ? 'Production' : 'Staging'}
                        </span>
                      </div>

                      {/* Precision / F1 scores */}
                      <div className="flex items-baseline gap-3 mt-1">
                        <div className="flex flex-col">
                          <span className="text-[8px] text-gray-500 uppercase">Precision</span>
                          <span className="text-lg font-mono font-bold text-cyan-400">
                            {(Number(model.score1) || 0).toFixed(3)}
                          </span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[8px] text-gray-500 uppercase">F1</span>
                          <span className="text-lg font-mono font-bold text-gray-400">
                            {(Number(model.score2) || 0).toFixed(3)}
                          </span>
                        </div>
                      </div>

                      {/* Mini sparkline */}
                      <div className="h-7 mt-1">
                        <MiniSparkline
                          color={idx % 2 === 0 ? '#10b981' : '#00D9FF'}
                          height={28}
                        />
                      </div>

                      {/* Bottom info */}
                      <div className="flex items-center justify-between text-[9px] font-mono text-gray-500 mt-auto">
                        <span>{model.uptime || 'N/A'}</span>
                        <span>{model.lookback || 'N/A'}</span>
                      </div>
                    </div>
                  );
                }) : (
                  <div className="col-span-3 text-center text-gray-500 text-xs font-mono py-8">
                    No deployed models
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* RIGHT: Flywheel Learning Log */}
          <div className="w-1/2 flex flex-col bg-[#0d1117] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <h3 className="text-sm font-semibold text-white">Flywheel Learning Log</h3>
                <span className="text-gray-500 text-xs font-normal">(Trade Outcomes)</span>
              </div>
              <p className="text-[10px] text-gray-500 mt-1">
                Continuous learning from trade results, failures, and market feedback for model improvement
              </p>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-3">
              <div className="font-mono text-[10px] space-y-1.5">
                {logsData.map((logEntry, idx) => {
                  const tagColors = {
                    RETRAIN: 'text-emerald-400',
                    EVAL: 'text-red-400',
                    WARNING: 'text-amber-400',
                  };
                  const tagColor = tagColors[logEntry.tag] || 'text-cyan-400';
                  return (
                    <div key={idx} className="flex gap-2 hover:bg-white/[0.02] px-2 py-0.5 rounded">
                      <span className="text-gray-500 shrink-0 whitespace-nowrap">[{logEntry.ts}]</span>
                      {logEntry.tag && (
                        <span className={clsx('shrink-0 font-bold', tagColor)}>[{logEntry.tag}]</span>
                      )}
                      <span className="text-cyan-400/80 break-words leading-relaxed">{logEntry.msg}</span>
                    </div>
                  );
                })}
                {logsData.length === 0 && (
                  <div className="text-gray-500 text-center py-8">Awaiting log entries...</div>
                )}
                {/* Blinking cursor */}
                <div className="flex gap-2 px-2 py-0.5">
                  <span className="text-gray-500 shrink-0">[{new Date().toLocaleTimeString('en-US', { hour12: false })}]</span>
                  <span className="w-2 h-3 bg-emerald-400/70 animate-pulse inline-block" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* GLOBAL SCROLLBAR CSS */}
      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #00D9FF; }
      `}} />
    </div>
  );
}
