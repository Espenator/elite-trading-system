import { useState, useRef, useEffect } from 'react';
import { createChart } from 'lightweight-charts';
import { useApi } from '../hooks/useApi';
import { getApiUrl } from '../config/api';
import log from "@/utils/logger";

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
  const performanceData = apiPerf?.flywheel || FALLBACK_PERFORMANCE;
  const signalsData = apiSignals?.flywheel || FALLBACK_SIGNALS;
  const modelsData = apiModels?.flywheel || FALLBACK_MODELS;
  const logsData = apiLogs?.flywheel || FALLBACK_LOGS;
  const featuresData = apiFeatures?.flywheel || FALLBACK_FEATURES;

  const handleRetrain = async () => {
    setIsRetraining(true);
    try {
      await fetch(getApiUrl('flywheel/retrain'), { method: 'POST' });
      // In a real app, this would trigger a toast or update logs
    } catch (e) {
      log.error("Retrain failed", e);
    }
    setTimeout(() => setIsRetraining(false), 2000);
  };

  return (
    <div className="flex flex-col h-screen w-full bg-[#0B0E14] text-[#e5e7eb] font-sans overflow-hidden selection:bg-[#00D9FF]/30 p-4 gap-4">

      {/* HEADER */}
      <header className="flex justify-between items-end shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-wide">ML Brain & Flywheel</h1>
          <p className="text-[#00D9FF] text-xs font-mono mt-1">Autonomous Model Training & Inference Pipeline</p>
        </div>
        <button
          onClick={handleRetrain}
          disabled={isRetraining}
          className={`px-4 py-2 border rounded font-mono text-xs transition-all shadow-[0_0_10px_rgba(0,217,255,0.15)] ${
            isRetraining
              ? 'bg-[#1e293b] border-gray-500 text-gray-400 cursor-not-allowed'
              : 'bg-cyan-900/30 border-[#00D9FF]/50 text-[#00D9FF] hover:bg-[#00D9FF]/20'
          }`}
        >
          {isRetraining ? 'RETRAINING...' : 'RETRAIN MODELS [F9]'}
        </button>
      </header>

      {/* FLYWHEEL CYCLE VISUALIZATION */}
      <FlywheelCycleSVG />

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
            {performanceData && Array.isArray(performanceData) && performanceData.length > 0 ? (
              <ModelPerformanceLC data={performanceData} />
            ) : (
              <div className="h-full min-h-[200px] flex items-center justify-center text-gray-500 text-xs font-mono">
                Awaiting performance data...
              </div>
            )}
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

      {/* ROW 3: MODELS, FEATURES & LOGS */}
      <div className="flex gap-4 flex-1 min-h-0">

        {/* LEFT: Deployed Inference Fleet */}
        <div className="w-[40%] bg-[#111827] border border-[#1e293b] rounded flex flex-col">
          <div className="p-3 border-b border-[#1e293b]">
            <h2 className="text-xs font-bold text-white uppercase tracking-wider">Deployed Inference Fleet <span className="text-gray-500 normal-case ml-2">(TimescaleDB Connected)</span></h2>
          </div>
          <div className="flex-1 p-3 grid grid-cols-2 grid-rows-2 gap-3 overflow-y-auto custom-scrollbar">
            {modelsData.map((model, idx) => {
              const isProd = model.status === 'PRODUCTION';
              const badgeStyle = isProd
                ? 'bg-green-500/20 text-green-400 border-green-500/50'
                : 'bg-amber-500/20 text-amber-400 border-amber-500/50';

              return (
                <div key={idx} className="bg-[#0B0E14] border border-[#1e293b] rounded p-3 flex flex-col justify-between hover:border-[#00D9FF]/50 transition-colors">
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

        {/* MIDDLE: Feature Importance */}
        <div className="w-[25%] bg-[#111827] border border-[#1e293b] rounded flex flex-col">
          <div className="p-3 border-b border-[#1e293b]">
            <h2 className="text-xs font-bold text-white uppercase tracking-wider">Feature Importance</h2>
            <p className="text-[10px] text-gray-400 font-mono">Top predictive features</p>
          </div>
          <div className="flex-1 p-3 overflow-y-auto custom-scrollbar">
            <FeatureImportanceChart features={featuresData} />
          </div>
        </div>

        {/* RIGHT: Flywheel Learning Log */}
        <div className="w-[35%] bg-[#0B0E14] border border-[#1e293b] rounded flex flex-col relative">
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
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #00D9FF; }
      `}} />
    </div>
  );
}
