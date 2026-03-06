import { useState, useRef, useEffect } from 'react';
import { createChart } from 'lightweight-charts';
import { useApi } from '../hooks/useApi';
import { getApiUrl, getAuthHeaders } from '../config/api';
import log from "@/utils/logger";
import { Brain, Activity, Zap, RotateCcw, Server, ChevronRight, TrendingUp, BarChart3, Radio } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import PageHeader from '../components/ui/PageHeader';

// --- FALLBACK DATA (N/A indicators when API unavailable) ---
const FALLBACK_KPIS = {
  activeModels: 0, activeModelsSub: "N/A",
  walkForwardAcc: 0, walkForwardSub: "N/A",
  stage3Ignitions: 0, stage3Sub: "N/A",
  flywheelCycles: 0, flywheelSub: "N/A",
  featureStore: "N/A", featureStoreSub: "Not Connected",
  winRateThresh: "N/A", winRateSub: "N/A"
};

const FALLBACK_PERFORMANCE = [];

const FALLBACK_SIGNALS = [];

const FALLBACK_MODELS = [];

const FALLBACK_LOGS = [
];

const FALLBACK_FEATURES = [];

// --- FLYWHEEL CYCLE STAGES ---
const FLYWHEEL_STAGES = [
  'Data', 'Features', 'Train', 'Validate', 'Deploy', 'Infer', 'Feedback'
];

// --- Flywheel Cycle SVG Component ---
function FlywheelCycleSVG() {
  const stageCount = FLYWHEEL_STAGES.length;
  const nodeW = 80;
  const nodeH = 28;
  const arrowGap = 24;
  const totalW = stageCount * nodeW + (stageCount - 1) * arrowGap;
  const svgW = totalW + 60; // padding for loop-back arrow
  const svgH = 60;
  const yCenter = svgH / 2;
  const xStart = 30;

  return (
    <div className="w-full shrink-0 overflow-hidden">
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        className="w-full"
        style={{ height: 60 }}
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <marker
            id="flywheel-arrow"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L8,3 L0,6 Z" fill="#00D9FF" />
          </marker>
          <marker
            id="flywheel-arrow-loop"
            markerWidth="8"
            markerHeight="6"
            refX="8"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L8,3 L0,6 Z" fill="#00D9FF" opacity="0.6" />
          </marker>
        </defs>

        {/* Nodes and arrows */}
        {FLYWHEEL_STAGES.map((stage, i) => {
          const x = xStart + i * (nodeW + arrowGap);
          const rx = x + nodeW / 2;
          const ry = yCenter;

          return (
            <g key={stage}>
              {/* Rounded rect node */}
              <rect
                x={x}
                y={ry - nodeH / 2}
                width={nodeW}
                height={nodeH}
                rx={6}
                fill="#111827"
                stroke="#00D9FF"
                strokeWidth={1}
                opacity={0.9}
              />
              <text
                x={rx}
                y={ry + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#F9FAFB"
                fontSize={10}
                fontFamily="monospace"
                fontWeight="bold"
              >
                {stage}
              </text>

              {/* Arrow to next node */}
              {i < stageCount - 1 && (
                <line
                  x1={x + nodeW + 2}
                  y1={yCenter}
                  x2={x + nodeW + arrowGap - 2}
                  y2={yCenter}
                  stroke="#00D9FF"
                  strokeWidth={1.5}
                  markerEnd="url(#flywheel-arrow)"
                />
              )}
            </g>
          );
        })}

        {/* Loop-back arrow: from last node back to first */}
        {(() => {
          const lastX = xStart + (stageCount - 1) * (nodeW + arrowGap) + nodeW / 2;
          const firstX = xStart + nodeW / 2;
          const loopY = yCenter + nodeH / 2 + 8;
          return (
            <path
              d={`M${lastX},${yCenter + nodeH / 2} L${lastX},${loopY} L${firstX},${loopY} L${firstX},${yCenter + nodeH / 2 + 2}`}
              fill="none"
              stroke="#00D9FF"
              strokeWidth={1.2}
              strokeDasharray="4,3"
              opacity={0.5}
              markerEnd="url(#flywheel-arrow-loop)"
            />
          );
        })()}
      </svg>
    </div>
  );
}

// --- Model Performance Lightweight Chart Component ---
function ModelPerformanceLC({ data }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#9CA3AF',
        fontFamily: 'monospace',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: 'rgba(42,52,68,0.3)' },
        horzLines: { color: 'rgba(42,52,68,0.3)' },
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      rightPriceScale: {
        borderColor: 'rgba(42,52,68,0.3)',
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

    const areaSeries = chart.addAreaSeries({
      lineColor: '#00D9FF',
      lineWidth: 2,
      topColor: 'rgba(0,217,255,0.25)',
      bottomColor: 'rgba(0,217,255,0.02)',
      crosshairMarkerBackgroundColor: '#00D9FF',
      priceFormat: {
        type: 'custom',
        formatter: (val) => `${val.toFixed(1)}%`,
      },
    });

    chartRef.current = chart;
    seriesRef.current = areaSeries;

    // Responsive resize
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
      seriesRef.current = null;
    };
  }, []);

  // Update data when it changes
  useEffect(() => {
    if (!seriesRef.current || !data || !Array.isArray(data) || data.length === 0) return;

    // Expect data as array of { time, value } or { date, accuracy } etc.
    // Normalize to { time, value } format
    const chartData = data
      .map((d) => {
        const time = d.time || d.date || d.timestamp;
        const value = d.value ?? d.accuracy ?? d.score;
        if (!time || value == null) return null;
        return { time, value: Number(value) };
      })
      .filter(Boolean)
      .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));

    if (chartData.length > 0) {
      seriesRef.current.setData(chartData);
      chartRef.current?.timeScale().fitContent();
    }
  }, [data]);

  return (
    <div ref={containerRef} className="w-full h-full min-h-[200px]" />
  );
}

// --- Feature Importance Bar Chart Component ---
function FeatureImportanceChart({ features }) {
  if (!features || !Array.isArray(features) || features.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-xs font-mono">
        No feature importance data available
      </div>
    );
  }

  // Sort by importance descending, take top entries
  const sorted = [...features]
    .sort((a, b) => (b.importance ?? b.score ?? 0) - (a.importance ?? a.score ?? 0))
    .slice(0, 10);

  const maxVal = Math.max(...sorted.map((f) => f.importance ?? f.score ?? 0), 1);

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {sorted.map((feat, idx) => {
        const val = feat.importance ?? feat.score ?? 0;
        const pct = (val / maxVal) * 100;
        const name = feat.name || feat.feature || `Feature ${idx + 1}`;
        return (
          <div key={idx} className="flex items-center gap-2 group">
            <span className="text-[9px] font-mono text-gray-400 w-[120px] truncate shrink-0 text-right" title={name}>
              {name}
            </span>
            <div className="flex-1 h-4 bg-[#0B0E14] rounded-sm overflow-hidden relative">
              <div
                className="h-full rounded-sm transition-all duration-500"
                style={{
                  width: `${pct}%`,
                  background: 'linear-gradient(90deg, #10b981, #00D9FF)',
                }}
              />
            </div>
            <span className="text-[9px] font-mono text-cyan-400 w-[40px] shrink-0">
              {val.toFixed(3)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function MLBrainFlywheel() {
  const [isRetraining, setIsRetraining] = useState(false);

  // --- API INTEGRATION ---
  const { data: apiKpis } = useApi('flywheel', { endpoint: '/flywheel/kpis', pollIntervalMs: 10000 });
  const { data: apiPerf } = useApi('flywheel', { endpoint: '/flywheel/performance', pollIntervalMs: 60000 });
  const { data: apiSignals } = useApi('flywheel', { endpoint: '/flywheel/signals/staged', pollIntervalMs: 5000 });
  const { data: apiModels } = useApi('flywheel', { endpoint: '/flywheel/models', pollIntervalMs: 15000 });
  const { data: apiLogs } = useApi('flywheel', { endpoint: '/flywheel/logs', pollIntervalMs: 2000 });
  const { data: apiFeatures } = useApi('flywheel', { endpoint: '/flywheel/features', pollIntervalMs: 30000 });

  // Safe data extraction with fallbacks
  const kpis = apiKpis?.flywheel || FALLBACK_KPIS;
  const performanceData = apiPerf?.flywheel?.history ?? FALLBACK_PERFORMANCE;
  const signalsData = apiSignals?.flywheel?.signals ?? FALLBACK_SIGNALS;
  const modelsData = apiModels?.flywheel?.models ?? FALLBACK_MODELS;
  const logsData = apiLogs?.flywheel?.logs ?? FALLBACK_LOGS;
  const featuresData = apiFeatures?.flywheel?.features ?? FALLBACK_FEATURES;

  const handleRetrain = async () => {
    setIsRetraining(true);
    try {
      await fetch(getApiUrl('training') + '/runs', { method: 'POST', headers: { 'Content-Type': 'application/json', ...getAuthHeaders() }, body: JSON.stringify({ type: 'retrain' }) });
      // In a real app, this would trigger a toast or update logs
    } catch (e) {
      log.error("Retrain failed", e);
    }
    setTimeout(() => setIsRetraining(false), 2000);
  };

  const kpiItems = [
    { label: 'Stage 4 Active Models', val: kpis.activeModels, sub: kpis.activeModelsSub, color: 'text-emerald-400', icon: Activity },
    { label: 'Walk Forward Accuracy', val: `${kpis.walkForwardAcc}%`, sub: kpis.walkForwardSub, color: 'text-emerald-400', icon: TrendingUp },
    { label: 'Stage 3 Ignitions', val: kpis.stage3Ignitions, sub: kpis.stage3Sub, color: 'text-cyan-400', icon: Zap },
    { label: 'Flywheel Cycles', val: kpis.flywheelCycles, sub: kpis.flywheelSub, color: 'text-white', icon: RotateCcw },
    { label: 'Feature Store Sync', val: kpis.featureStore, sub: kpis.featureStoreSub, color: 'text-emerald-400', icon: Server },
    { label: 'Win Rate Threshold', val: kpis.winRateThresh, sub: kpis.winRateSub, color: 'text-cyan-400', icon: BarChart3 },
  ];

  return (
    <div className="flex flex-col h-screen w-full bg-[#0B0E14] text-gray-200 font-sans overflow-hidden selection:bg-cyan-500/30">
      <div className="flex flex-col flex-1 min-h-0 p-4 gap-4">

        {/* HEADER */}
        <PageHeader
          icon={Brain}
          title="ML Brain & Flywheel"
          description="Autonomous Model Training & Inference Pipeline"
        >
          <Button
            variant="primary"
            size="sm"
            leftIcon={RotateCcw}
            onClick={handleRetrain}
            disabled={isRetraining}
          >
            {isRetraining ? 'Retraining...' : 'Retrain Models'}
          </Button>
        </PageHeader>

        {/* KPI STRIP */}
        <div className="grid grid-cols-6 gap-3 shrink-0">
          {kpiItems.map((kpi, i) => (
            <div
              key={i}
              className="bg-surface border border-secondary/20 rounded-xl p-3 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">{kpi.label}</span>
                <kpi.icon className="w-3.5 h-3.5 text-gray-600" />
              </div>
              <span className={`text-2xl font-mono font-bold ${kpi.color}`}>{kpi.val}</span>
              <span className="text-[10px] text-gray-500 mt-1 font-mono">{kpi.sub}</span>
            </div>
          ))}
        </div>

        {/* MIDDLE ROW: Performance Chart + ML Probability Ranking */}
        <div className="flex gap-4 min-h-0" style={{ flex: '1 1 45%' }}>
          {/* LEFT: Model Performance Tracking */}
          <Card
            title={
              <span className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
                Model Performance Tracking
              </span>
            }
            subtitle="252-Day Walk-Forward Accuracy vs Random Baseline"
            action={<Badge variant="success" size="sm">ONLINE</Badge>}
            className="w-[45%] flex flex-col"
            bodyClassName="flex-1 min-h-0"
            noPadding
          >
            <div className="h-full p-2">
              {performanceData && Array.isArray(performanceData) && performanceData.length > 0 ? (
                <ModelPerformanceLC data={performanceData} />
              ) : (
                <div className="h-full min-h-[200px] flex items-center justify-center text-gray-500 text-xs font-mono">
                  Awaiting performance data...
                </div>
              )}
            </div>
          </Card>

          {/* RIGHT: Stage 4 ML Probability Ranking */}
          <Card
            title={
              <span className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-cyan-400" />
                Stage 4: ML Probability Ranking
              </span>
            }
            action={<Badge variant="primary" size="sm">LIVE INFERENCE</Badge>}
            className="w-[55%] flex flex-col"
            bodyClassName="flex-1 min-h-0 overflow-hidden"
            noPadding
          >
            <div className="h-full overflow-y-auto custom-scrollbar">
              <table className="w-full text-left font-mono text-[10px]">
                <thead className="sticky top-0 bg-[#0B0E14] text-gray-500 border-b border-secondary/20 z-10">
                  <tr>
                    <th className="px-4 py-2 font-medium">SYMBOL</th>
                    <th className="px-3 py-2 font-medium">DIR</th>
                    <th className="px-3 py-2 font-medium">WIN PROB</th>
                    <th className="px-3 py-2 font-medium">COMPRESSION</th>
                    <th className="px-3 py-2 font-medium">VELEZ SCORE</th>
                    <th className="px-3 py-2 font-medium">VOL RATIO</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary/10">
                  {signalsData.length > 0 ? signalsData.map((row, idx) => {
                    const isLong = row.dir === 'LONG';
                    const dirColor = isLong ? 'text-emerald-400' : 'text-red-400';
                    const barColor = isLong ? 'bg-emerald-500' : 'bg-red-500';
                    return (
                      <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-4 py-2 text-white font-bold">{row.symbol}</td>
                        <td className={`px-3 py-2 font-bold ${dirColor}`}>{row.dir}</td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <span className={dirColor}>{row.winProb}%</span>
                            <div className="w-14 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full ${barColor}`} style={{ width: `${row.winProb}%` }} />
                            </div>
                          </div>
                        </td>
                        <td className="px-3 py-2 text-gray-300">{row.compression}</td>
                        <td className="px-3 py-2 text-cyan-400">{row.velezScore}</td>
                        <td className="px-3 py-2 text-gray-300">{row.volRatio}</td>
                      </tr>
                    );
                  }) : (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        No staged signals available
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* BOTTOM ROW: Deployed Fleet + Flywheel Learning Log */}
        <div className="flex gap-4 min-h-0" style={{ flex: '1 1 40%' }}>
          {/* LEFT: Deployed Inference Fleet */}
          <Card
            title={
              <span className="flex items-center gap-2">
                <Server className="w-4 h-4 text-cyan-400" />
                Deployed Inference Fleet
                <span className="text-gray-500 text-xs font-normal">(TimescaleDB Connected)</span>
              </span>
            }
            className="w-1/2 flex flex-col"
            bodyClassName="flex-1 min-h-0 overflow-y-auto custom-scrollbar"
          >
            <div className="grid grid-cols-3 gap-3">
              {modelsData.length > 0 ? modelsData.map((model, idx) => {
                const isProd = model.status === 'PRODUCTION';
                return (
                  <div
                    key={idx}
                    className="bg-[#0B0E14] border border-secondary/20 rounded-lg p-3 flex flex-col gap-2 hover:border-cyan-500/40 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-1">
                      <span className="text-[11px] font-bold text-white leading-tight">{model.name}</span>
                      <Badge variant={isProd ? 'success' : 'warning'} size="sm">
                        {model.status}
                      </Badge>
                    </div>
                    <div className="flex items-baseline gap-3 mt-1">
                      <span className="text-lg font-mono font-bold text-cyan-400">
                        {(Number(model.score1) || 0).toFixed(3)}
                      </span>
                      <span className="text-lg font-mono font-bold text-gray-400">
                        {(Number(model.score2) || 0).toFixed(3)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[9px] font-mono text-gray-500 mt-auto">
                      <span>{model.uptime}</span>
                      <span>{model.lookback}</span>
                    </div>
                  </div>
                );
              }) : (
                <div className="col-span-3 text-center text-gray-500 text-xs font-mono py-8">
                  No deployed models
                </div>
              )}
            </div>
          </Card>

          {/* RIGHT: Flywheel Learning Log */}
          <Card
            title={
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Flywheel Learning Log
                <span className="text-gray-500 text-xs font-normal">(Trade Outcomes)</span>
              </span>
            }
            subtitle="Continuous learning from trade results, failures, and market feedback for model improvement"
            className="w-1/2 flex flex-col"
            bodyClassName="flex-1 min-h-0 overflow-y-auto custom-scrollbar"
            noPadding
          >
            <div className="p-3 font-mono text-[10px] space-y-1.5 text-emerald-400/90">
              {logsData.map((logEntry, idx) => (
                <div key={idx} className="flex gap-3 hover:bg-white/[0.02] px-2 py-0.5 rounded">
                  <span className="text-gray-500 shrink-0">[{logEntry.ts}]</span>
                  <span className="break-words">{logEntry.msg}</span>
                </div>
              ))}
              {logsData.length === 0 && (
                <div className="text-gray-500 text-center py-8">Awaiting log entries...</div>
              )}
              {/* Blinking cursor */}
              <div className="flex gap-3 px-2 py-0.5">
                <span className="text-gray-500 shrink-0">[{new Date().toLocaleTimeString('en-US', { hour12: false })}]</span>
                <span className="w-2 h-3 bg-emerald-400/70 animate-pulse inline-block" />
              </div>
            </div>
          </Card>
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
