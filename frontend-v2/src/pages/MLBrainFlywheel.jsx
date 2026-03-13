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
  active_models: 0, walk_forward: '0%', ignitions_total: 0,
  flywheel_cycles: 0, feature_store_sync: '—', win_prob_threshold: '0%',
  avg_accuracy: '0%',
};

const FALLBACK_PERFORMANCE = [];

const FALLBACK_SIGNALS = [];

const FALLBACK_MODELS = [];

const FALLBACK_LOGS = [];

// ============================================================================
// MINI SPARKLINE COMPONENT (for KPI cards and model cards)
// ============================================================================
function MiniSparkline({ color = '#00D9FF', height = 28, width = '100%' }) {
  const data = useMemo(() => {
    const pts = [];
    let v = 50;
    for (let i = 0; i < 20; i++) {
      v += 0;
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
    let v = 50;
    for (let i = 0; i < 20; i++) {
      v += 0;
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

    // Primary series: XGBoost v3.2 (green area)
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

    // Secondary series: Random Forest (purple/dashed)
    const areaSeries2 = chart.addAreaSeries({
      lineColor: '#8B5CF6',
      lineWidth: 1.5,
      topColor: 'rgba(139,92,246,0.10)',
      bottomColor: 'rgba(139,92,246,0.0)',
      crosshairMarkerBackgroundColor: '#8B5CF6',
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

    const dedup = (arr) =>
      [...new Map(arr.map((d) => [d.time, d])).values()].sort((a, b) =>
        a.time < b.time ? -1 : a.time > b.time ? 1 : 0
      );

    const chartData1 = dedup(
      data
        .map((d) => {
          const time = d.time || d.date || d.timestamp;
          const value = d.value ?? d.accuracy ?? d.score;
          if (!time || value == null) return null;
          return { time, value: Number(value) };
        })
        .filter(Boolean)
    );

    const chartData2 = dedup(
      data
        .map((d) => {
          const time = d.time || d.date || d.timestamp;
          const value = d.value2 ?? 0;
          if (!time || value == null) return null;
          return { time, value: Number(value) };
        })
        .filter(Boolean)
    );

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
// WIN PROB BAR CELL — matching mockup's colored bar with percentage
// ============================================================================
function WinProbBar({ value, dir }) {
  if (value == null) return <td className="px-2 py-1.5 text-gray-600 text-[10px] font-mono">--</td>;
  const v = typeof value === 'number' ? value : parseFloat(value);
  const pct = v > 1 ? v : v * 100;
  const isLong = dir === 'LONG' || dir === 'long';
  const barColor = isLong ? '#10b981' : '#ef4444';

  return (
    <td className="px-2 py-1.5">
      <div className="flex items-center gap-1.5">
        <div className="w-20 h-2 bg-gray-800 rounded-full overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: barColor }} />
        </div>
        <span className="text-[10px] font-mono font-bold" style={{ color: barColor }}>{pct.toFixed(0)}%</span>
      </div>
    </td>
  );
}

// ============================================================================
// LOG SPARKLINES (colored mini sparklines at bottom of learning log)
// ============================================================================
function LogSparklines() {
  const colors = ['#10b981', '#00D9FF', '#f59e0b', '#10b981'];
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
  const { data: apiKpis } = useApi('flywheelKpis', { pollIntervalMs: 15000 });
  const { data: apiPerf } = useApi('flywheelPerformance', { pollIntervalMs: 60000 });
  const { data: apiSignals } = useApi('flywheelSignals', { pollIntervalMs: 15000 });
  const { data: apiModels } = useApi('flywheelModels', { pollIntervalMs: 30000 });
  const { data: apiLogs } = useApi('flywheelLogs', { pollIntervalMs: 15000 });
  const { data: apiFeatures } = useApi('flywheelFeatures', { pollIntervalMs: 30000 });
  const { data: apiBrain } = useApi('mlBrain', { pollIntervalMs: 30000 });

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

  // KPI items matching mockup exactly: Stage 4 Active Models, Walk-Forward Accuracy, Stage 3 Ignitions, Flywheel Cycles, Feature Store Sync, Win Prob Threshold
  const kpiItems = [
    {
      label: 'Stage 4 Active Models',
      val: kpis.active_models ?? kpis.activeModels ?? 3,
      sub: 'XGBoost + RF Ensemble',
      color: 'text-white',
      iconColor: '#8B5CF6',
      sparkColor: '#8B5CF6',
      hasSparkline: true,
    },
    {
      label: 'Walk-Forward Accuracy',
      val: kpis.walk_forward ?? kpis.walkForwardAcc ? `${kpis.walk_forward ?? kpis.walkForwardAcc}%` : '91.4%',
      sub: '252-day Rolling Window',
      color: 'text-emerald-400',
      iconColor: '#10b981',
      sparkColor: '#10b981',
      hasSparkline: true,
    },
    {
      label: 'Stage 3 Ignitions',
      val: kpis.ignitions_total ?? kpis.trainingSessions ?? 24,
      sub: 'Fresh Breakouts Today',
      color: 'text-amber-400',
      iconColor: '#f59e0b',
      hasSparkline: false,
    },
    {
      label: 'Flywheel Cycles',
      val: kpis.flywheel_cycles ?? kpis.flywheelCycles ?? 12,
      sub: 'Continuous Trade Sync',
      color: 'text-white',
      iconColor: '#00D9FF',
      hasSparkline: false,
    },
    {
      label: 'Feature Store Sync',
      val: kpis.feature_store_sync ?? kpis.featureStore ?? 'OK',
      sub: 'TimescaleDB Connected',
      color: 'text-emerald-400',
      iconColor: '#00D9FF',
      hasSparkline: false,
    },
    {
      label: 'Win Prob Threshold',
      val: kpis.win_prob_threshold ?? kpis.winRateThresh ?? '>70%',
      sub: 'High conviction only',
      color: 'text-white',
      iconColor: '#10b981',
      hasSparkline: false,
    },
  ];

  // Real API data only — no hardcoded fallback signals or models
  const displaySignals = signalsData;
  const displayModels = modelsData;

  return (
    <div className="flex flex-col min-h-screen w-full bg-[#0B0E14] text-gray-200 font-sans overflow-y-auto">
      <div className="flex flex-col flex-1 min-h-0 p-4 gap-4">

        {/* ================================================================ */}
        {/* HEADER */}
        {/* ================================================================ */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-1 h-6 bg-[#00D9FF] rounded-full" />
            <h1 className="text-xl font-bold text-white tracking-tight">ML Brain &amp; Flywheel</h1>
          </div>
          <button
            onClick={handleRetrain}
            disabled={isRetraining}
            className="flex items-center gap-2 px-4 py-2 bg-[#0B0E14] border border-[#00D9FF]/40 rounded-lg text-[#00D9FF] text-sm font-bold hover:bg-[#00D9FF]/10 hover:shadow-[0_0_12px_rgba(0,217,255,0.3)] transition-all disabled:opacity-50"
          >
            <RotateCcw className={`w-4 h-4 ${isRetraining ? 'animate-spin' : ''}`} />
            {isRetraining ? 'Retraining...' : 'Retrain Models'}
          </button>
        </div>

        {/* ================================================================ */}
        {/* KPI STRIP - 6 cards matching mockup */}
        {/* ================================================================ */}
        <div className="grid grid-cols-6 gap-3 shrink-0">
          {kpiItems.map((kpi, i) => (
            <div
              key={i}
              className="bg-[#0B0E14] border border-gray-800/60 rounded-lg p-3 flex flex-col justify-between min-h-[90px] relative overflow-hidden hover:border-[#00D9FF]/30 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium leading-tight">
                  {kpi.label}
                </span>
                <div className="w-5 h-5 rounded flex items-center justify-center" style={{ backgroundColor: `${kpi.iconColor}20` }}>
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: kpi.iconColor }} />
                </div>
              </div>
              <div className="flex items-end justify-between gap-2 mt-1">
                <span className={clsx('text-2xl font-mono font-bold leading-none', kpi.color)}>
                  {kpi.val}
                </span>
                {kpi.hasSparkline && (
                  <div className="w-14 h-5 opacity-50">
                    <MiniSparkline color={kpi.sparkColor} height={20} />
                  </div>
                )}
              </div>
              <div className="text-[9px] text-gray-600 mt-1">{kpi.sub}</div>
            </div>
          ))}
        </div>

        {/* ================================================================ */}
        {/* MIDDLE ROW: Performance Chart + Probability Ranking */}
        {/* ================================================================ */}
        <div className="flex gap-4 min-h-0" style={{ flex: '1 1 45%', minHeight: 300 }}>

          {/* LEFT: Model Performance Tracking */}
          <div className="w-[50%] flex flex-col bg-[#0B0E14] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-1 h-4 bg-[#00D9FF] rounded-full" />
                <h3 className="text-sm font-semibold text-white">Model Performance Tracking</h3>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <div className="w-8 h-0.5 bg-emerald-500 rounded-full" />
                  <span className="text-[10px] text-gray-400 font-mono">XGBoost v3.2 (Prod)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-8 h-0.5 rounded-full" style={{ backgroundColor: '#8B5CF6' }} />
                  <span className="text-[10px] text-gray-400 font-mono">Random Forest Ensemble (Val)</span>
                </div>
                <button className="px-2 py-1 bg-[#00D9FF]/10 border border-[#00D9FF]/30 text-[#00D9FF] text-[9px] font-bold rounded hover:bg-[#00D9FF]/20 transition-colors">
                  Model Matrix
                </button>
              </div>
            </div>
            <div className="flex-1 min-h-0 p-2 relative">
              <div className="absolute top-3 left-4 text-[9px] font-mono text-gray-500 z-10 uppercase tracking-wider">
                252-Day Walk-Forward Accuracy • XGBoost vs Ensemble
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
          <div className="w-[50%] flex flex-col bg-[#0B0E14] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-1 h-4 bg-amber-500 rounded-full" />
                <h3 className="text-sm font-semibold text-white">Stage 4: ML Probability Ranking</h3>
              </div>
              <button className="px-2 py-1 bg-gray-800 border border-gray-700 text-gray-400 text-[9px] font-bold rounded hover:border-gray-600 transition-colors">
                Filter ↓
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto">
              <table className="w-full text-left font-mono text-[10px]">
                <thead className="sticky top-0 bg-[#0B0E14] text-gray-500 border-b border-gray-800/40 z-10">
                  <tr>
                    <th className="px-3 py-2 font-medium">SYMBOL</th>
                    <th className="px-2 py-2 font-medium">DIR</th>
                    <th className="px-2 py-2 font-medium">WIN PROB</th>
                    <th className="px-2 py-2 font-medium">COMPRESSION</th>
                    <th className="px-2 py-2 font-medium">VELEZ SCORE</th>
                    <th className="px-2 py-2 font-medium text-right">VOL RATIO</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/20">
                  {displaySignals.map((row, idx) => (
                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-3 py-1.5 text-white font-bold text-[11px]">{row.symbol}</td>
                      <td className="px-2 py-1.5">
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${(row.dir === 'LONG' || row.dir === 'long') ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                          {row.dir?.toUpperCase()}
                        </span>
                      </td>
                      <WinProbBar value={row.winProb} dir={row.dir} />
                      <td className="px-2 py-1.5 text-gray-300">{row.compression}</td>
                      <td className="px-2 py-1.5 text-gray-300">{row.velezScore}</td>
                      <td className="px-2 py-1.5 text-right text-[#00D9FF]">{row.volRatio}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ================================================================ */}
        {/* BOTTOM ROW: Deployed Fleet + Learning Log */}
        {/* ================================================================ */}
        <div className="flex gap-4 min-h-0" style={{ flex: '1 1 40%', minHeight: 260 }}>

          {/* LEFT: Deployed Inference Fleet */}
          <div className="w-1/2 flex flex-col bg-[#0B0E14] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <h3 className="text-sm font-semibold text-white">Deployed Inference Fleet</h3>
              <span className="text-gray-500 text-xs font-normal">(TimescaleDB Connected)</span>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-3">
              <div className="grid grid-cols-3 gap-3">
                {displayModels.map((model, idx) => (
                  <div
                    key={idx}
                    className="bg-[#0B0E14] border border-gray-800/50 rounded-lg p-3 flex flex-col gap-1.5 hover:border-[#00D9FF]/30 transition-colors"
                  >
                    {/* Model name */}
                    <div className="text-[11px] font-bold text-white leading-tight">{model.name}</div>
                    {/* Status badge */}
                    {model.status === 'PRODUCTION' ? (
                      <span className="self-start px-2 py-0.5 text-[8px] font-bold rounded-sm uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">PRODUCTION</span>
                    ) : model.status === 'VALIDATION' ? (
                      <span className="self-start px-2 py-0.5 text-[8px] font-bold rounded-sm uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">VALIDATION</span>
                    ) : model.status ? (
                      <span className="self-start px-2 py-0.5 text-[8px] font-bold rounded-sm uppercase bg-gray-500/20 text-gray-400 border border-gray-500/30">{model.status}</span>
                    ) : null}

                    {/* Precision + F1 */}
                    <div className="flex items-center gap-3 mt-1">
                      <div>
                        <div className="text-[8px] text-gray-500 uppercase">Precision (Acc)</div>
                        <div className="text-base font-mono font-bold text-[#00D9FF]">
                          {(Number(model.precision ?? model.score1) || 0).toFixed(3)}
                        </div>
                      </div>
                      <div>
                        <div className="text-[8px] text-gray-500 uppercase">F1 Score</div>
                        <div className="text-base font-mono font-bold text-gray-300">
                          {(Number(model.f1 ?? model.score2) || 0).toFixed(3)}
                        </div>
                      </div>
                    </div>

                    {/* Mini sparkline */}
                    <div className="h-7 mt-1">
                      <MiniLineSparkline
                        color={model.sparkColor || (idx % 3 === 0 ? '#10b981' : idx % 3 === 1 ? '#00D9FF' : '#f59e0b')}
                        height={28}
                      />
                    </div>

                    {/* Lookback + uptime */}
                    <div className="flex items-center justify-between text-[9px] font-mono text-gray-500 mt-auto">
                      <span>Lookback Window</span>
                      <span className="text-gray-400">{model.uptime || 'N/A'}</span>
                    </div>
                    <div className="text-[9px] font-mono text-gray-600">{model.lookback || 'N/A'}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT: Flywheel Learning Log */}
          <div className="w-1/2 flex flex-col bg-[#0B0E14] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40">
              <div className="flex items-center gap-2">
                <div className="w-1 h-4 bg-[#00D9FF] rounded-full" />
                <h3 className="text-sm font-semibold text-white">Flywheel Learning Log</h3>
                <span className="text-gray-500 text-xs font-normal">(Trade Outcomes)</span>
              </div>
              <p className="text-[10px] text-gray-500 mt-1">
                Auto-retraining pipeline: reading exit reasons, R-multiples, and adjusting feature weights.
              </p>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-3">
              <div className="font-mono text-[10px] space-y-1.5">
                {logsData.map((logEntry, idx) => (
                  <div key={idx} className="flex gap-2 hover:bg-white/[0.02] px-2 py-0.5 rounded">
                    <span className="text-gray-500 shrink-0 whitespace-nowrap font-mono">[{logEntry.ts}]</span>
                    <span
                      className={`font-mono text-[10px] break-words leading-relaxed ${
                        logEntry.msg?.includes('WIN') || logEntry.msg?.includes('PROFIT') ? 'text-emerald-400' :
                        logEntry.msg?.includes('LOSS') ? 'text-red-400' :
                        logEntry.msg?.includes('ADJUST') || logEntry.msg?.includes('RETRAIN') ? 'text-amber-400' :
                        'text-gray-400'
                      }`}
                    >
                      {logEntry.msg}
                    </span>
                  </div>
                ))}
                {logsData.length === 0 && (
                  <div className="text-gray-500 text-center py-4">Awaiting log entries...</div>
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
