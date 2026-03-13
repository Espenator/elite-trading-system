import { useState, useRef, useEffect, useMemo } from 'react';
import { createChart } from 'lightweight-charts';
import { AreaChart, Area, LineChart, Line, ResponsiveContainer } from 'recharts';
import { useApi } from '../hooks/useApi';
import { getApiUrl, getAuthHeaders } from '../config/api';
import log from "@/utils/logger";
import {
  RotateCcw, ChevronDown, X, ChevronUp, ChevronRight
} from 'lucide-react';
import clsx from 'clsx';

// ============================================================================
// MINI SPARKLINE — real data array or flat gray when null
// ============================================================================
function MiniSparkline({ color = '#00D9FF', height = 28, width = '100%', data: rawData }) {
  const data = useMemo(() => {
    if (rawData && Array.isArray(rawData) && rawData.length > 0) {
      return rawData.map((v, i) => ({ x: i, y: typeof v === 'number' ? v : (v?.y ?? v?.value ?? 0) }));
    }
    return Array.from({ length: 20 }, (_, i) => ({ x: i, y: 50 }));
  }, [rawData]);

  const isPlaceholder = !rawData || !Array.isArray(rawData) || rawData.length === 0;
  const strokeColor = isPlaceholder ? '#4b5563' : color;

  return (
    <ResponsiveContainer width={width} height={height}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id={`sparkGrad-${strokeColor.replace('#', '')}-${height}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity={isPlaceholder ? 0.15 : 0.3} />
            <stop offset="100%" stopColor={strokeColor} stopOpacity={0.0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="y"
          stroke={strokeColor}
          strokeWidth={1.5}
          fill={`url(#sparkGrad-${strokeColor.replace('#', '')}-${height})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// Small line sparkline for model cards — real data or flat gray
function MiniLineSparkline({ color = '#00D9FF', height = 28, data: rawData }) {
  const data = useMemo(() => {
    if (rawData && Array.isArray(rawData) && rawData.length > 0) {
      return rawData.map((v, i) => ({ x: i, y: typeof v === 'number' ? v : (v?.y ?? v?.value ?? 0) }));
    }
    return Array.from({ length: 20 }, (_, i) => ({ x: i, y: 50 }));
  }, [rawData]);

  const isPlaceholder = !rawData || !Array.isArray(rawData) || rawData.length === 0;
  const strokeColor = isPlaceholder ? '#4b5563' : color;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <Line
          type="monotone"
          dataKey="y"
          stroke={strokeColor}
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
        const value = d.value2 ?? 0;
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
// WIN PROB BAR CELL — matching mockup's colored bar with percentage
// ============================================================================
function WinProbBar({ value, dir }) {
  if (value == null) return <td className="px-2 py-1.5 text-[#94a3b8] text-[10px] font-mono">—</td>;
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
// LOG SPARKLINES — real data arrays from logs or flat gray when null
// ============================================================================
function LogSparklines({ logSeries }) {
  const colors = ['#10b981', '#00D9FF', '#f59e0b', '#10b981'];
  const series = Array.isArray(logSeries) && logSeries.length >= 4 ? logSeries.slice(0, 4) : null;
  return (
    <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-gray-800/30">
      {colors.map((color, i) => (
        <div key={i} className="h-6">
          <MiniLineSparkline color={color} height={24} data={series?.[i]} />
        </div>
      ))}
    </div>
  );
}

// Score tier filter options for probability table
const SCORE_TIERS = [
  { id: 'all', label: 'All' },
  { id: 'slam', label: 'Slam Dunk (≥85%)' },
  { id: 'strong', label: 'Strong Go (70–84%)' },
  { id: 'watch', label: 'Watch (<70%)' },
];

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export default function MLBrainFlywheel() {
  const [isRetraining, setIsRetraining] = useState(false);
  const [modelMatrixOpen, setModelMatrixOpen] = useState(false);
  const [scoreTierFilter, setScoreTierFilter] = useState('all');
  const [filterDropdownOpen, setFilterDropdownOpen] = useState(false);
  const [sortKey, setSortKey] = useState('winProb');
  const [sortDir, setSortDir] = useState('desc');
  const [expandedModelId, setExpandedModelId] = useState(null);
  const [promotingId, setPromotingId] = useState(null);

  // --- API INTEGRATION (no mock fallbacks) ---
  const { data: apiKpis } = useApi('flywheelKpis', { pollIntervalMs: 15000 });
  const { data: apiPerf } = useApi('flywheelPerformance', { pollIntervalMs: 60000 });
  const { data: apiSignals } = useApi('flywheelSignals', { pollIntervalMs: 15000 });
  const { data: apiModels } = useApi('flywheelModels', { pollIntervalMs: 30000 });
  const { data: apiLogs } = useApi('flywheelLogs', { pollIntervalMs: 15000 });
  const { data: apiFeatures } = useApi('flywheelFeatures', { pollIntervalMs: 30000 });

  const kpis = apiKpis?.flywheel ?? {};
  const performanceData = apiPerf?.flywheel?.history ?? null;
  const signalsData = apiSignals?.flywheel?.signals ?? [];
  const modelsData = apiModels?.flywheel?.models ?? [];
  const logsData = apiLogs?.flywheel?.logs ?? [];

  // KPI sparkline data from performance history (accuracy series)
  const kpiSparklineData = useMemo(() => {
    if (!performanceData || !Array.isArray(performanceData) || performanceData.length === 0) return null;
    return performanceData.map((d) => (d.value ?? d.accuracy ?? d.score) != null ? Number(d.value ?? d.accuracy ?? d.score) : null).filter((v) => v != null);
  }, [performanceData]);

  const handleRetrain = async () => {
    setIsRetraining(true);
    try {
      const url = `${getApiUrl('training').replace(/\/?$/, '')}/retrain`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ type: 'retrain' }),
      });
      if (!res.ok) {
        const err = await res.text();
        log.error('Retrain failed', res.status, err);
      }
    } catch (e) {
      log.error('Retrain failed', e);
    }
    setTimeout(() => setIsRetraining(false), 2000);
  };

  const handlePromoteToChampion = async (model) => {
    const name = model?.name ?? model?.id;
    if (!name) return;
    setPromotingId(name);
    try {
      const url = `${getApiUrl('training').replace(/\/?$/, '')}/deploy`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ modelName: name, version: model?.version ?? undefined }),
      });
      if (!res.ok) {
        const err = await res.text();
        log.error('Promote failed', res.status, err);
      }
    } catch (e) {
      log.error('Promote failed', e);
    }
    setPromotingId(null);
  };

  // KPI items — show "—" when null (no mock values)
  const kpiItems = [
    {
      label: 'Stage 4 Active Models',
      val: (kpis.active_models ?? kpis.activeModels) != null ? String(kpis.active_models ?? kpis.activeModels) : '—',
      sub: 'XGBoost + RF Ensemble',
      color: 'text-white',
      iconColor: '#8B5CF6',
      sparkColor: '#8B5CF6',
      hasSparkline: true,
      sparkData: kpiSparklineData,
    },
    {
      label: 'Walk-Forward Accuracy',
      val: (kpis.walk_forward ?? kpis.walkForwardAcc ?? kpis.accuracy) != null
        ? `${Number(kpis.walk_forward ?? kpis.walkForwardAcc ?? kpis.accuracy)}%`
        : '—',
      sub: '252-day Rolling Window',
      color: 'text-emerald-400',
      iconColor: '#10b981',
      sparkColor: '#10b981',
      hasSparkline: true,
      sparkData: kpiSparklineData,
    },
    {
      label: 'Stage 3 Ignitions',
      val: (kpis.ignitions_total ?? kpis.trainingSessions ?? kpis.resolvedSignals) != null ? String(kpis.ignitions_total ?? kpis.trainingSessions ?? kpis.resolvedSignals) : '—',
      sub: 'Fresh Breakouts Today',
      color: 'text-amber-400',
      iconColor: '#f59e0b',
      hasSparkline: false,
    },
    {
      label: 'Flywheel Cycles',
      val: (kpis.flywheel_cycles ?? kpis.flywheelCycles) != null ? String(kpis.flywheel_cycles ?? kpis.flywheelCycles) : '—',
      sub: 'Continuous Trade Sync',
      color: 'text-white',
      iconColor: '#00D9FF',
      hasSparkline: false,
    },
    {
      label: 'Feature Store Sync',
      val: (kpis.feature_store_sync ?? kpis.featureStore) != null ? String(kpis.feature_store_sync ?? kpis.featureStore) : '—',
      sub: 'TimescaleDB Connected',
      color: 'text-emerald-400',
      iconColor: '#00D9FF',
      hasSparkline: false,
    },
    {
      label: 'Win Prob Threshold',
      val: (kpis.win_prob_threshold ?? kpis.winRateThresh) != null ? String(kpis.win_prob_threshold ?? kpis.winRateThresh) : '—',
      sub: 'High conviction only',
      color: 'text-white',
      iconColor: '#10b981',
      hasSparkline: false,
    },
  ];

  // Filter + sort signals (real API data only; no defaultSignals)
  const displaySignals = useMemo(() => {
    let list = [...signalsData].map((s) => ({
      symbol: s.symbol ?? s.ticker ?? '—',
      dir: s.dir ?? s.direction ?? s.side ?? 'LONG',
      winProb: s.winProb ?? s.win_prob ?? s.score ?? null,
      compression: s.compression ?? s.compression_days ?? '—',
      velezScore: s.velezScore ?? s.velez_score ?? '—',
      volRatio: s.volRatio ?? s.vol_ratio ?? '—',
    }));
    if (scoreTierFilter === 'slam') list = list.filter((s) => (s.winProb != null ? Number(s.winProb) >= 85 : false));
    else if (scoreTierFilter === 'strong') list = list.filter((s) => { const v = s.winProb != null ? Number(s.winProb) : null; return v != null && v >= 70 && v < 85; });
    else if (scoreTierFilter === 'watch') list = list.filter((s) => { const v = s.winProb != null ? Number(s.winProb) : null; return v != null && v < 70; });
    const key = sortKey === 'symbol' ? 'symbol' : sortKey === 'dir' ? 'dir' : sortKey === 'winProb' ? 'winProb' : sortKey === 'compression' ? 'compression' : sortKey === 'velezScore' ? 'velezScore' : 'volRatio';
    list.sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return sortDir === 'asc' ? -1 : 1;
      if (bVal == null) return sortDir === 'asc' ? 1 : -1;
      const cmp = typeof aVal === 'string' ? (aVal.localeCompare(bVal)) : (Number(aVal) - Number(bVal));
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return list;
  }, [signalsData, scoreTierFilter, sortKey, sortDir]);

  const handleSort = (key) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else setSortKey(key);
  };

  // Models from API only (no defaultModels)
  const displayModels = useMemo(() => {
    return (modelsData || []).map((m, idx) => ({
      id: m.id ?? m.name ?? `model-${idx}`,
      name: m.name ?? m.id ?? '—',
      status: m.status ?? null,
      uptime: m.uptime ?? m.latency_ms ?? null,
      precision: m.precision ?? m.score1 ?? m.accuracy ?? null,
      f1: m.f1 ?? m.score2 ?? null,
      lookback: m.lookback ?? null,
      sparkColor: m.sparkColor ?? (idx % 3 === 0 ? '#10b981' : idx % 3 === 1 ? '#00D9FF' : '#f59e0b'),
      history: m.history ?? null,
    }));
  }, [modelsData]);

  return (
    <div className="flex flex-col min-h-screen w-full bg-[#0a0e1a] text-[#e2e8f0] font-sans overflow-y-auto">
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
            className="flex items-center gap-2 px-4 py-2 bg-[#111827] border border-[#00D9FF]/40 rounded-lg text-[#00D9FF] text-sm font-bold hover:bg-[#00D9FF]/10 hover:shadow-[0_0_12px_rgba(0,217,255,0.3)] transition-all disabled:opacity-50"
          >
            <RotateCcw className={`w-4 h-4 ${isRetraining ? 'animate-spin' : ''}`} />
            {isRetraining ? 'Retraining...' : 'Retrain Models'}
          </button>
        </div>

        {/* ================================================================ */}
        {/* KPI STRIP — 6 cards, Aurora theme, real data or — */}
        {/* ================================================================ */}
        <div className="grid grid-cols-6 gap-3 shrink-0">
          {kpiItems.map((kpi, i) => (
            <div
              key={i}
              className="bg-[#111827] border border-gray-800/60 rounded-lg p-3 flex flex-col justify-between min-h-[90px] relative overflow-hidden hover:border-[#00D9FF]/30 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-[#94a3b8] uppercase tracking-wider font-medium leading-tight">
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
                  <div className="w-14 h-5 opacity-70">
                    <MiniSparkline color={kpi.sparkColor} height={20} data={kpi.sparkData} />
                  </div>
                )}
              </div>
              <div className="text-[9px] text-[#94a3b8] mt-1">{kpi.sub}</div>
            </div>
          ))}
        </div>

        {/* ================================================================ */}
        {/* MIDDLE ROW: Performance Chart + Probability Ranking */}
        {/* ================================================================ */}
        <div className="flex gap-4 min-h-0" style={{ flex: '1 1 45%', minHeight: 300 }}>

          {/* LEFT: Model Performance Tracking */}
          <div className="w-[50%] flex flex-col bg-[#111827] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-1 h-4 bg-[#00D9FF] rounded-full" />
                <h3 className="text-sm font-semibold text-white">Model Performance Tracking</h3>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <div className="w-8 h-0.5 bg-[#10b981] rounded-full" />
                  <span className="text-[10px] text-[#94a3b8] font-mono">XGBoost v3.2 (Prod)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-8 h-0.5 rounded-full" style={{ backgroundColor: '#8B5CF6' }} />
                  <span className="text-[10px] text-[#94a3b8] font-mono">Random Forest (Val)</span>
                </div>
                <button
                  onClick={() => setModelMatrixOpen(true)}
                  className="px-2 py-1 bg-[#00D9FF]/10 border border-[#00D9FF]/30 text-[#00D9FF] text-[9px] font-bold rounded hover:bg-[#00D9FF]/20 transition-colors"
                >
                  Model Matrix
                </button>
              </div>
            </div>
            <div className="flex-1 min-h-0 p-2 relative">
              <div className="absolute top-3 left-4 text-[9px] font-mono text-[#94a3b8] z-10 uppercase tracking-wider">
                252-Day Walk-Forward Accuracy • XGBoost vs Ensemble
              </div>
              {performanceData && Array.isArray(performanceData) && performanceData.length > 0 ? (
                <ModelPerformanceLC data={performanceData} />
              ) : (
                <div className="h-full min-h-[200px] flex items-center justify-center text-[#94a3b8] text-xs font-mono">
                  Awaiting performance data...
                </div>
              )}
            </div>
          </div>

          {/* RIGHT: Stage 4: ML Probability Ranking — sortable columns, Filter dropdown */}
          <div className="w-[50%] flex flex-col bg-[#111827] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-1 h-4 bg-amber-500 rounded-full" />
                <h3 className="text-sm font-semibold text-white">Stage 4: ML Probability Ranking</h3>
              </div>
              <div className="relative">
                <button
                  onClick={() => setFilterDropdownOpen((o) => !o)}
                  className="flex items-center gap-1 px-2 py-1 bg-gray-800 border border-gray-700 text-[#94a3b8] text-[9px] font-bold rounded hover:border-gray-600 transition-colors"
                >
                  Filter <ChevronDown className="w-3 h-3" />
                </button>
                {filterDropdownOpen && (
                  <>
                    <div className="fixed inset-0 z-20" onClick={() => setFilterDropdownOpen(false)} aria-hidden="true" />
                    <div className="absolute right-0 top-full mt-1 py-1 bg-[#111827] border border-gray-700 rounded-lg shadow-xl z-30 min-w-[160px]">
                      {SCORE_TIERS.map((t) => (
                        <button
                          key={t.id}
                          onClick={() => { setScoreTierFilter(t.id); setFilterDropdownOpen(false); }}
                          className={clsx('w-full text-left px-3 py-1.5 text-[10px] font-mono', scoreTierFilter === t.id ? 'bg-[#00D9FF]/20 text-[#00D9FF]' : 'text-[#e2e8f0] hover:bg-white/5')}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto">
              <table className="w-full text-left font-mono text-[10px]">
                <thead className="sticky top-0 bg-[#111827] text-[#94a3b8] border-b border-gray-800/40 z-10">
                  <tr>
                    {[
                      { key: 'symbol', label: 'SYMBOL' },
                      { key: 'dir', label: 'DIR' },
                      { key: 'winProb', label: 'WIN PROB' },
                      { key: 'compression', label: 'COMPRESSION' },
                      { key: 'velezScore', label: 'VELEZ SCORE' },
                      { key: 'volRatio', label: 'VOL RATIO', align: 'right' },
                    ].map(({ key, label, align }) => (
                      <th
                        key={key}
                        className={clsx('py-2 font-medium cursor-pointer hover:text-[#00D9FF] transition-colors select-none', key === 'symbol' ? 'px-3' : 'px-2', align === 'right' && 'text-right')}
                        onClick={() => handleSort(key)}
                      >
                        {label} {sortKey === key ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/20">
                  {displaySignals.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-3 py-6 text-center text-[#94a3b8] text-xs">
                        No staged signals. Data from flywheel API.
                      </td>
                    </tr>
                  ) : (
                    displaySignals.map((row, idx) => (
                      <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-3 py-1.5 text-white font-bold text-[11px]">{row.symbol}</td>
                        <td className="px-2 py-1.5">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${(row.dir === 'LONG' || row.dir === 'long') ? 'bg-[#10b981]/20 text-[#10b981]' : 'bg-red-500/20 text-red-400'}`}>
                            {row.dir?.toUpperCase()}
                          </span>
                        </td>
                        <WinProbBar value={row.winProb} dir={row.dir} />
                        <td className="px-2 py-1.5 text-[#e2e8f0]">{row.compression}</td>
                        <td className="px-2 py-1.5 text-[#e2e8f0]">{row.velezScore}</td>
                        <td className="px-2 py-1.5 text-right text-[#00D9FF]">{row.volRatio}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ================================================================ */}
        {/* BOTTOM ROW: Deployed Fleet + Learning Log */}
        {/* ================================================================ */}
        <div className="flex gap-4 min-h-0" style={{ flex: '1 1 40%', minHeight: 260 }}>

          {/* LEFT: Deployed Inference Fleet — click to expand, Promote to Champion */}
          <div className="w-1/2 flex flex-col bg-[#111827] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
              <h3 className="text-sm font-semibold text-white">Deployed Inference Fleet</h3>
              <span className="text-[#94a3b8] text-xs font-normal">(TimescaleDB Connected)</span>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-3">
              {displayModels.length === 0 ? (
                <div className="text-center py-6 text-[#94a3b8] text-xs font-mono">No models from API. Awaiting flywheel models.</div>
              ) : (
                <div className="grid grid-cols-3 gap-3">
                  {displayModels.map((model, idx) => {
                    const isExpanded = expandedModelId === model.id;
                    return (
                      <div
                        key={model.id}
                        className="bg-[#0a0e1a] border border-gray-800/50 rounded-lg overflow-hidden hover:border-[#00D9FF]/30 transition-colors"
                      >
                        <button
                          type="button"
                          className="w-full p-3 flex flex-col gap-1.5 text-left"
                          onClick={() => setExpandedModelId(isExpanded ? null : model.id)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="text-[11px] font-bold text-white leading-tight">{model.name}</div>
                            {isExpanded ? <ChevronUp className="w-4 h-4 text-[#94a3b8]" /> : <ChevronRight className="w-4 h-4 text-[#94a3b8]" />}
                          </div>
                          {model.status === 'PRODUCTION' ? (
                            <span className="self-start px-2 py-0.5 text-[8px] font-bold rounded-sm uppercase bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/30">PRODUCTION</span>
                          ) : model.status === 'VALIDATION' ? (
                            <span className="self-start px-2 py-0.5 text-[8px] font-bold rounded-sm uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">VALIDATION</span>
                          ) : model.status ? (
                            <span className="self-start px-2 py-0.5 text-[8px] font-bold rounded-sm uppercase bg-gray-500/20 text-[#94a3b8] border border-gray-500/30">{model.status}</span>
                          ) : null}
                          <div className="flex items-center gap-3 mt-1">
                            <div>
                              <div className="text-[8px] text-[#94a3b8] uppercase">Precision</div>
                              <div className="text-base font-mono font-bold text-[#00D9FF]">
                                {model.precision != null ? Number(model.precision).toFixed(3) : '—'}
                              </div>
                            </div>
                            <div>
                              <div className="text-[8px] text-[#94a3b8] uppercase">F1</div>
                              <div className="text-base font-mono font-bold text-[#e2e8f0]">
                                {model.f1 != null ? Number(model.f1).toFixed(3) : '—'}
                              </div>
                            </div>
                          </div>
                          <div className="h-7 mt-1">
                            <MiniLineSparkline color={model.sparkColor} height={28} data={model.history} />
                          </div>
                          <div className="flex items-center justify-between text-[9px] font-mono text-[#94a3b8] mt-1">
                            <span>Lookback</span>
                            <span>{model.uptime ?? model.lookback ?? '—'}</span>
                          </div>
                        </button>
                        {isExpanded && (
                          <div className="px-3 pb-3 pt-0 border-t border-gray-800/40">
                            <div className="text-[9px] font-mono text-[#94a3b8] mb-2">{model.lookback ?? '—'}</div>
                            <button
                              type="button"
                              disabled={!!promotingId}
                              onClick={(e) => { e.stopPropagation(); handlePromoteToChampion(model); }}
                              className="w-full py-1.5 px-2 rounded bg-[#10b981]/20 border border-[#10b981]/40 text-[#10b981] text-[9px] font-bold hover:bg-[#10b981]/30 disabled:opacity-50"
                            >
                              {promotingId === (model.name ?? model.id) ? 'Promoting…' : 'Promote to Champion'}
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* RIGHT: Flywheel Learning Log — real logs or empty state */}
          <div className="w-1/2 flex flex-col bg-[#111827] border border-gray-800/60 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-800/40">
              <div className="flex items-center gap-2">
                <div className="w-1 h-4 bg-[#00D9FF] rounded-full" />
                <h3 className="text-sm font-semibold text-white">Flywheel Learning Log</h3>
                <span className="text-[#94a3b8] text-xs font-normal">(Trade Outcomes)</span>
              </div>
              <p className="text-[10px] text-[#94a3b8] mt-1">
                Auto-retraining pipeline: reading exit reasons, R-multiples, and adjusting feature weights.
              </p>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-3">
              <div className="font-mono text-[10px] space-y-1.5">
                {logsData.length === 0 ? (
                  <div className="text-[#94a3b8] text-center py-4">Awaiting log entries. Data from flywheel API.</div>
                ) : (
                  logsData.map((logEntry, idx) => (
                    <div key={idx} className="flex gap-2 hover:bg-white/[0.02] px-2 py-0.5 rounded">
                      <span className="text-[#94a3b8] shrink-0 whitespace-nowrap font-mono">[{logEntry.ts ?? '—'}]</span>
                      <span
                        className={`font-mono text-[10px] break-words leading-relaxed ${
                          logEntry.msg?.includes('WIN') || logEntry.msg?.includes('PROFIT') ? 'text-[#10b981]' :
                          logEntry.msg?.includes('LOSS') ? 'text-red-400' :
                          logEntry.msg?.includes('ADJUST') || logEntry.msg?.includes('RETRAIN') ? 'text-amber-400' :
                          'text-[#e2e8f0]'
                        }`}
                      >
                        {logEntry.msg ?? '—'}
                      </span>
                    </div>
                  ))
                )}
                <div className="flex gap-2 px-2 py-0.5">
                  <span className="text-[#94a3b8] shrink-0">[{new Date().toLocaleTimeString('en-US', { hour12: false })}]</span>
                  <span className="w-2 h-3 bg-[#10b981]/70 animate-pulse inline-block" />
                </div>
              </div>
              <LogSparklines logSeries={null} />
            </div>
          </div>
        </div>
      </div>

      {/* Model Matrix modal — confusion matrix / model comparison */}
      {modelMatrixOpen && (
        <ModelMatrixModal onClose={() => setModelMatrixOpen(false)} />
      )}

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #00D9FF; }
      `}} />
    </div>
  );
}

// Modal: Model comparison from GET /training/models/compare
function ModelMatrixModal({ onClose }) {
  const [compareData, setCompareData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const url = `${getApiUrl('training').replace(/\/?$/, '')}/models/compare`;
        const res = await fetch(url, { headers: getAuthHeaders() });
        if (cancelled) return;
        const json = res.ok ? await res.json() : null;
        setCompareData(Array.isArray(json) ? json : []);
      } catch {
        if (!cancelled) setCompareData([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" onClick={onClose}>
      <div className="bg-[#111827] border border-gray-700 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <h3 className="text-sm font-semibold text-white">Model Matrix — Comparison</h3>
          <button type="button" onClick={onClose} className="p-1 rounded hover:bg-white/10 text-[#94a3b8]"><X className="w-5 h-5" /></button>
        </div>
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="text-[#94a3b8] text-sm">Loading…</div>
          ) : compareData && compareData.length > 0 ? (
            <table className="w-full text-left font-mono text-[10px]">
              <thead className="text-[#94a3b8] border-b border-gray-700">
                <tr>
                  <th className="py-2 pr-4">Model</th>
                  <th className="py-2 pr-4">Precision</th>
                  <th className="py-2 pr-4">Recall</th>
                  <th className="py-2 pr-4">F1</th>
                </tr>
              </thead>
              <tbody className="text-[#e2e8f0] divide-y divide-gray-800">
                {compareData.map((row, i) => (
                  <tr key={i}>
                    <td className="py-1.5">{row.modelName ?? row.name ?? '—'}</td>
                    <td className="py-1.5">{row.precision != null ? Number(row.precision).toFixed(3) : '—'}</td>
                    <td className="py-1.5">{row.recall != null ? Number(row.recall).toFixed(3) : '—'}</td>
                    <td className="py-1.5">{row.f1 != null ? Number(row.f1).toFixed(3) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-[#94a3b8] text-sm">No model comparison data available.</div>
          )}
        </div>
      </div>
    </div>
  );
}
