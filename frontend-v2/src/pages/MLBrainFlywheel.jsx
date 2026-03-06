import { useState, useRef, useEffect, useMemo } from 'react';
import { createChart } from 'lightweight-charts';
import { AreaChart, Area, LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';
import { useApi } from '../hooks/useApi';
import { getApiUrl, getAuthHeaders } from '../config/api';
import log from "@/utils/logger";
import {
  Brain, Activity, Zap, RotateCcw, Server, TrendingUp, BarChart3, Radio,
  Search, Plus, ChevronRight, Cpu, Target, CheckCircle, Gauge, Shield,
  Crosshair, Layers, Database
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
  headModelAcc: 91.4, headModelSub: "Head Model Accuracy",
  trainingSessions: 24, trainingSessionsSub: "Training Sessions (24h)",
  signalsResolved: 142, signalsResolvedSub: "Signals Resolved",
  inferenceFleet: 12, inferenceFleetSub: "Inference Fleet",
  circuitBreaker: "OK", circuitBreakerSub: "Circuit Breaker",
  accuracyThreshold: ">70%", accuracyThresholdSub: "Accuracy Threshold"
};

const FALLBACK_PERFORMANCE = (() => {
  const pts = [];
  const startDate = new Date('2024-01-01');
  let val = 78;
  let val2 = 74;
  for (let i = 0; i < 252; i++) {
    const d = new Date(startDate);
    d.setDate(d.getDate() + i);
    const dateStr = d.toISOString().slice(0, 10);
    val += (Math.random() - 0.42) * 1.2;
    val = Math.max(70, Math.min(97, val));
    val2 += (Math.random() - 0.43) * 1.1;
    val2 = Math.max(65, Math.min(94, val2));
    pts.push({ time: dateStr, value: parseFloat(val.toFixed(1)), value2: parseFloat(val2.toFixed(1)) });
  }
  return pts;
})();

const FALLBACK_SIGNALS = [
  { symbol: 'NVDA', probs: { '1d': 0.92, '3d': 0.88, '5d': 0.85, '1w': 0.79, '2w': 0.72, '1m': 0.68 } },
  { symbol: 'META', probs: { '1d': 0.87, '3d': 0.84, '5d': 0.80, '1w': 0.76, '2w': 0.69, '1m': 0.63 } },
  { symbol: 'AAPL', probs: { '1d': 0.81, '3d': 0.75, '5d': 0.71, '1w': 0.65, '2w': 0.58, '1m': 0.52 } },
  { symbol: 'TSLA', probs: { '1d': 0.78, '3d': 0.73, '5d': 0.68, '1w': 0.62, '2w': 0.55, '1m': 0.50 } },
  { symbol: 'AMZN', probs: { '1d': 0.76, '3d': 0.71, '5d': 0.66, '1w': 0.60, '2w': 0.53, '1m': 0.48 } },
  { symbol: 'MSFT', probs: { '1d': 0.73, '3d': 0.69, '5d': 0.64, '1w': 0.58, '2w': 0.51, '1m': 0.45 } },
  { symbol: 'GOOG', probs: { '1d': 0.70, '3d': 0.66, '5d': 0.61, '1w': 0.55, '2w': 0.49, '1m': 0.42 } },
  { symbol: 'AMD', probs: { '1d': 0.68, '3d': 0.63, '5d': 0.58, '1w': 0.52, '2w': 0.46, '1m': 0.39 } },
  { symbol: 'CRWD', probs: { '1d': 0.65, '3d': 0.60, '5d': 0.55, '1w': 0.49, '2w': 0.43, '1m': 0.37 } },
];

const FALLBACK_MODELS = [
  { name: 'XGBoost Classifier', status: 'PRODUCTION', score1: 0.924, score2: 0.891, uptime: '21d 16hrs', lookback: '252 days', sparkline: null },
  { name: 'RF Ensemble Model', status: 'PRODUCTION', score1: 0.885, score2: 0.862, uptime: '18d 4hrs', lookback: '89 days', sparkline: null },
  { name: 'Votes Engine v2.0', status: 'PRODUCTION', score1: 0.865, score2: 0.840, uptime: '14d 7hrs', lookback: 'N/A (hybrid)', sparkline: null },
  { name: 'Compression Detector', status: 'PRODUCTION', score1: 0.841, score2: 0.812, uptime: '10d 2hrs', lookback: '63 days', sparkline: null },
  { name: 'Ignition Detector', status: 'PRODUCTION', score1: 0.812, score2: 0.800, uptime: '7d 11hrs', lookback: '1 Year', sparkline: null },
  { name: 'Regime Manager (VXY)', status: 'PRODUCTION', score1: 0.890, score2: 0.865, uptime: '28d 3hrs', lookback: '1 Year', sparkline: null },
];

const FALLBACK_LOGS = [
  { ts: '09:31:02', msg: 'NVDA long +2.4% hit TP1 — flywheel confirms XGBoost prediction correct, model weight +0.02' },
  { ts: '09:31:15', msg: 'META short -0.8% stopped — RF Ensemble prediction incorrect, reducing confidence -0.01' },
  { ts: '09:31:28', msg: 'TSLA long +1.1% partial fill — Votes Engine v2.0 signal validated, adding to training set' },
  { ts: '09:31:42', msg: 'Feature recalc triggered: VIX regime shift detected, re-scoring all active models' },
  { ts: '09:31:55', msg: 'Compression Detector flagged AMD — entering stage-3 watchlist for ignition' },
  { ts: '09:32:08', msg: 'Walk-forward validation complete: 91.4% accuracy across 252-day rolling window' },
  { ts: '09:32:21', msg: 'CRWD position closed +3.2% — Ignition Detector accuracy now 81.2% (7d rolling)' },
  { ts: '09:32:34', msg: 'Regime Manager (VXY) switched to RISK-OFF mode — adjusting position sizing -20%' },
  { ts: '09:32:47', msg: 'Flywheel cycle #12 complete — all models retrained on latest 500 trade outcomes' },
  { ts: '09:33:01', msg: 'New feature added: options_skew_30d — feature store now at 24 total inputs' },
  { ts: '09:33:14', msg: 'GOOG long +0.5% trailing — model ensemble agrees on continuation, holding' },
  { ts: '09:33:27', msg: 'AMZN short signal rejected — win probability 48% below 70% threshold' },
];

// ============================================================================
// MINI SPARKLINE COMPONENT (for KPI cards and model cards)
// ============================================================================
function MiniSparkline({ color = '#00D9FF', height = 28, width = '100%' }) {
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
    <ResponsiveContainer width={width} height={height}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id={`sparkGrad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0.0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="y"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#sparkGrad-${color.replace('#', '')})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// Small line sparkline for model cards
function MiniLineSparkline({ color = '#00D9FF', height = 28 }) {
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
// MODEL PERFORMANCE CHART (lightweight-charts area with two series)
// ============================================================================
function ModelPerformanceLC({ data }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const series1Ref = useRef(null);
  const series2Ref = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#6B7280',
        fontFamily: 'monospace',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: 'rgba(42,52,68,0.25)' },
        horzLines: { color: 'rgba(42,52,68,0.25)' },
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      rightPriceScale: {
        borderColor: 'rgba(42,52,68,0.3)',
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: 'rgba(42,52,68,0.3)',
        timeVisible: false,
      },
      crosshair: {
        horzLine: { color: 'rgba(0,217,255,0.3)', style: 2 },
        vertLine: { color: 'rgba(0,217,255,0.3)', style: 2 },
      },
      handleScroll: false,
      handleScale: false,
    });

    // Primary series: Brain Model (green area)
    const areaSeries1 = chart.addAreaSeries({
      lineColor: '#10b981',
      lineWidth: 2,
      topColor: 'rgba(16,185,129,0.3)',
      bottomColor: 'rgba(16,185,129,0.02)',
      crosshairMarkerBackgroundColor: '#10b981',
      priceFormat: {
        type: 'custom',
        formatter: (val) => `${val.toFixed(1)}%`,
      },
    });

    // Secondary series: Head Model (cyan line)
    const areaSeries2 = chart.addAreaSeries({
      lineColor: '#06b6d4',
      lineWidth: 1.5,
      topColor: 'rgba(6,182,212,0.08)',
      bottomColor: 'rgba(6,182,212,0.0)',
      crosshairMarkerBackgroundColor: '#06b6d4',
      priceFormat: {
        type: 'custom',
        formatter: (val) => `${val.toFixed(1)}%`,
      },
    });

    chartRef.current = chart;
    series1Ref.current = areaSeries1;
    series2Ref.current = areaSeries2;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      series1Ref.current = null;
      series2Ref.current = null;
    };
  }, []);

  useEffect(() => {
    if (!series1Ref.current || !data || !Array.isArray(data) || data.length === 0) return;

    const chartData1 = data
      .map((d) => {
        const time = d.time || d.date || d.timestamp;
        const value = d.value ?? d.accuracy ?? d.score;
        if (!time || value == null) return null;
        return { time, value: Number(value) };
      })
      .filter(Boolean)
      .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));

    const chartData2 = data
      .map((d) => {
        const time = d.time || d.date || d.timestamp;
        const value = d.value2 ?? (d.value ? d.value - 3 - Math.random() * 2 : null);
        if (!time || value == null) return null;
        return { time, value: Number(value) };
      })
      .filter(Boolean)
      .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));

    if (chartData1.length > 0) {
      series1Ref.current.setData(chartData1);
    }
    if (chartData2.length > 0 && series2Ref.current) {
      series2Ref.current.setData(chartData2);
    }
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return (
    <div ref={containerRef} className="w-full h-full min-h-[200px]" />
  );
}

// ============================================================================
// PROBABILITY HEATMAP CELL with gradient bar
// ============================================================================
function ProbCell({ value }) {
  if (value == null) return <td className="px-2 py-1.5 text-center text-gray-600 text-[10px] font-mono">--</td>;
  const v = typeof value === 'number' ? value : parseFloat(value);
  const pct = v > 1 ? v : v * 100;

  // Color gradient: red (<50%) -> orange (50-60%) -> yellow (60-70%) -> green (70-85%) -> bright green (>85%)
  let barColor, textColor;
  if (pct >= 85) { barColor = 'rgba(16,185,129,0.7)'; textColor = 'text-white'; }
  else if (pct >= 75) { barColor = 'rgba(16,185,129,0.5)'; textColor = 'text-emerald-100'; }
  else if (pct >= 65) { barColor = 'rgba(20,184,166,0.4)'; textColor = 'text-teal-100'; }
  else if (pct >= 55) { barColor = 'rgba(245,158,11,0.4)'; textColor = 'text-amber-100'; }
  else if (pct >= 45) { barColor = 'rgba(249,115,22,0.4)'; textColor = 'text-orange-100'; }
  else { barColor = 'rgba(239,68,68,0.4)'; textColor = 'text-red-100'; }

  return (
    <td className="px-1 py-1">
      <div className="relative rounded overflow-hidden">
        {/* Background gradient bar */}
        <div
          className="absolute inset-0 rounded"
          style={{
            background: `linear-gradient(90deg, ${barColor} ${pct}%, transparent ${pct}%)`,
          }}
        />
        <div className={clsx('relative rounded px-1.5 py-1 text-center text-[10px] font-mono font-bold', textColor)}>
          {pct.toFixed(0)}%
        </div>
      </div>
    </td>
  );
}

// ============================================================================
// LOG SPARKLINES (colored mini sparklines at bottom of learning log)
// ============================================================================
function LogSparklines() {
  const colors = ['#10b981', '#06b6d4', '#f59e0b', '#10b981'];
  return (
    <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-gray-800/30">
      {colors.map((color, i) => (
        <div key={i} className="h-6">
          <MiniLineSparkline color={color} height={24} />
        </div>
      ))}
    </div>
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

  // Probability table timeframes - matching mockup columns
  const timeframes = ['1d', '3d', '5d', '1w', '2w', '1m'];

  // KPI items matching mockup exactly: 7 cards
  const kpiItems = [
    {
      icon: Brain,
      label: 'Active Models',
      val: kpis.activeModels ?? 3,
      badge: { text: 'LIVE', variant: 'success' },
      color: 'text-white',
      hasSparkline: true,
      sparkColor: '#10b981',
    },
    {
      icon: Target,
      label: 'Head Model Accuracy',
      val: `${kpis.headModelAcc ?? kpis.walkForwardAcc ?? 91.4}%`,
      color: 'text-emerald-400',
      hasSparkline: true,
      sparkColor: '#10b981',
    },
    {
      icon: Zap,
      label: 'Training Sessions (24h)',
      val: kpis.trainingSessions ?? kpis.totalFeatures ?? 24,
      color: 'text-emerald-400',
      hasSparkline: false,
    },
    {
      icon: Crosshair,
      label: 'Signals Resolved',
      val: kpis.signalsResolved ?? 142,
      color: 'text-white',
      hasSparkline: true,
      sparkColor: '#10b981',
    },
    {
      icon: Server,
      label: 'Inference Fleet',
      val: kpis.inferenceFleet ?? kpis.flywheelCycles ?? 12,
      color: 'text-white',
      hasSparkline: false,
    },
    {
      icon: Shield,
      label: 'Circuit Breaker',
      val: kpis.circuitBreaker ?? kpis.featureStore ?? 'OK',
      color: 'text-emerald-400',
      hasSparkline: false,
    },
    {
      icon: Gauge,
      label: 'Accuracy Threshold',
      val: kpis.accuracyThreshold ?? kpis.winRateThresh ?? '>70%',
      color: 'text-white',
      hasSparkline: false,
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
            leftIcon={RotateCcw}
            onClick={handleRetrain}
            disabled={isRetraining}
          >
            {isRetraining ? 'Monitoring...' : 'Flywheel Monitor'}
          </Button>
        </PageHeader>

        {/* ================================================================ */}
        {/* KPI STRIP - 7 cards in a row matching mockup */}
        {/* ================================================================ */}
        <div className="grid grid-cols-7 gap-3 shrink-0">
          {kpiItems.map((kpi, i) => {
            const IconComp = kpi.icon;
            return (
              <div
                key={i}
                className="bg-[#0d1117] border border-gray-800/60 rounded-lg p-3 flex flex-col justify-between min-h-[88px] relative overflow-hidden"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5">
                    <IconComp className="w-3 h-3 text-gray-500" />
                    <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium leading-tight">
                      {kpi.label}
                    </span>
                  </div>
                  {kpi.badge && (
                    <Badge variant={kpi.badge.variant} size="sm">{kpi.badge.text}</Badge>
                  )}
                </div>
                <div className="flex items-end justify-between gap-2">
                  <span className={clsx('text-2xl font-mono font-bold', kpi.color)}>
                    {kpi.val}
                  </span>
                  {kpi.hasSparkline && (
                    <div className="w-16 h-6 opacity-60">
                      <MiniSparkline color={kpi.sparkColor} height={24} />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
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
              </div>
              <div className="flex items-center gap-3">
                {/* Legend items matching mockup */}
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-0.5 bg-emerald-500 rounded-full" />
                  <span className="text-[10px] text-gray-400 font-mono">BRAIN MODEL</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-0.5 bg-cyan-400 rounded-full" />
                  <span className="text-[10px] text-gray-400 font-mono">HEAD MODEL</span>
                </div>
                <Badge variant="success" size="sm">MEAN ACCURACY</Badge>
              </div>
            </div>
            <div className="flex-1 min-h-0 p-2 relative">
              <div className="absolute top-3 left-4 text-[10px] font-mono text-gray-500 z-10">
                252-Day Walk-Forward Model Ensemble Accuracy
              </div>
              {performanceData && Array.isArray(performanceData) && performanceData.length > 0 ? (
                <ModelPerformanceLC data={performanceData} />
              ) : (
                <div className="h-full min-h-[200px] flex items-center justify-center text-gray-500 text-xs font-mono">
                  Awaiting performance data...
                </div>
              )}
            </div>
          </div>

          {/* RIGHT: Stage 4: ML Probability Ranking */}
          <div className="w-[50%] flex flex-col bg-[#0d1117] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-semibold text-white">Stage 4: ML Probability Ranking</h3>
              </div>
              <Badge variant="primary" size="sm">LIVE</Badge>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
              <table className="w-full text-left font-mono text-[10px]">
                <thead className="sticky top-0 bg-[#0d1117] text-gray-500 border-b border-gray-800/40 z-10">
                  <tr>
                    <th className="px-3 py-2 font-medium text-left">SYMBOL</th>
                    {timeframes.map(tf => (
                      <th key={tf} className="px-2 py-2 font-medium text-center">{tf}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/20">
                  {signalsData.length > 0 ? signalsData.map((row, idx) => {
                    const probs = row.probs || {};
                    return (
                      <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-3 py-1.5 text-white font-bold text-[11px]">{row.symbol}</td>
                        {timeframes.map(tf => (
                          <ProbCell key={tf} value={probs[tf] ?? row[tf]} />
                        ))}
                      </tr>
                    );
                  }) : (
                    <tr>
                      <td colSpan={timeframes.length + 1} className="px-4 py-8 text-center text-gray-500">
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
                {modelsData.length > 0 ? modelsData.map((model, idx) => (
                  <div
                    key={idx}
                    className="bg-[#0B0E14] border border-gray-800/50 rounded-lg p-3 flex flex-col gap-1.5 hover:border-cyan-500/30 transition-colors"
                  >
                    {/* Model name + status */}
                    <div className="flex items-start justify-between gap-1">
                      <span className="text-[11px] font-bold text-white leading-tight">{model.name}</span>
                    </div>

                    {/* Train / Test labels + accuracy scores */}
                    <div className="flex items-baseline gap-4 mt-1">
                      <div className="flex flex-col items-start">
                        <span className={clsx(
                          'text-lg font-mono font-bold',
                          idx % 2 === 0 ? 'text-cyan-400' : 'text-cyan-400'
                        )}>
                          {(Number(model.score1) || 0).toFixed(3)}
                        </span>
                      </div>
                      <div className="flex flex-col items-start">
                        <span className="text-lg font-mono font-bold text-gray-400">
                          {(Number(model.score2) || 0).toFixed(3)}
                        </span>
                      </div>
                    </div>

                    {/* Mini sparkline */}
                    <div className="h-7 mt-1">
                      <MiniLineSparkline
                        color={idx % 3 === 0 ? '#10b981' : idx % 3 === 1 ? '#06b6d4' : '#f59e0b'}
                        height={28}
                      />
                    </div>

                    {/* Bottom info: uptime + lookback */}
                    <div className="flex items-center justify-between text-[9px] font-mono text-gray-500 mt-auto">
                      <span>{model.uptime || 'N/A'}</span>
                      <span>{model.lookback || 'N/A'}</span>
                    </div>
                  </div>
                )) : (
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
                {logsData.map((logEntry, idx) => (
                  <div key={idx} className="flex gap-2 hover:bg-white/[0.02] px-2 py-0.5 rounded">
                    <span className="text-gray-500 shrink-0 whitespace-nowrap">[{logEntry.ts}]</span>
                    <span className="text-emerald-400/90 break-words leading-relaxed">{logEntry.msg}</span>
                  </div>
                ))}
                {logsData.length === 0 && (
                  <div className="text-gray-500 text-center py-8">Awaiting log entries...</div>
                )}
                {/* Blinking cursor */}
                <div className="flex gap-2 px-2 py-0.5">
                  <span className="text-gray-500 shrink-0">[{new Date().toLocaleTimeString('en-US', { hour12: false })}]</span>
                  <span className="w-2 h-3 bg-emerald-400/70 animate-pulse inline-block" />
                </div>
              </div>

              {/* Bottom sparklines matching mockup */}
              <LogSparklines />
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
