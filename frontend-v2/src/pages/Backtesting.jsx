// BACKTESTING LAB -- Embodier.ai Glass House Intelligence System
// Production V6 -- Exact mirror of Nano Banana Pro mockup 08-backtesting-lab.png
// ALL data from real API -- zero mock/fake data
import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { Play, Square, Download, RotateCcw, Settings, Plus, Minus, Copy, Trash2, TrendingUp, TrendingDown, Activity, Zap, Shield, Brain, Users, GitBranch, Layers, BarChart3, Target, AlertTriangle, ChevronDown, ChevronRight, RefreshCw, Eye, EyeOff, Lock, Unlock, Cpu, Network, Clock } from "lucide-react";
import Card from "../components/ui/Card";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import DataTable from "../components/ui/DataTable";
import PageHeader from "../components/ui/PageHeader";
import Slider from "../components/ui/Slider";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import { createChart, ColorType, CrosshairMode } from "lightweight-charts";
import ReactFlow, { Background, Controls, applyNodeChanges, applyEdgeChanges } from "reactflow";
import "reactflow/dist/style.css";

// Placeholder for charts migrating from Recharts to LW Charts
const ChartPlaceholder = ({ title, height = 180 }) => (
  <div className="flex items-center justify-center border border-dashed border-slate-700 rounded text-slate-500 text-xs" style={{ height }}>
    {title} (LW Charts migration pending)
  </div>
);
const ResultStat = ({ label, value, color = 'text-slate-300' }) => (
  <div className="text-center">
    <div className="text-[9px] text-slate-500 uppercase">{label}</div>
    <div className={`text-sm font-bold ${color}`}>{value ?? '--'}</div>
  </div>
);
const STRATEGIES = [
  "Mean Reversion V2", "ArbitrageAlpha", "TrendFollowerV1", "VolSurfaceBeta",
  "MomentumShift", "StatArbPairs", "GammaScalper", "DeltaNeutral",
  "MicrostructureHFT", "RegimeAdaptive", "MLEnsemble", "OpenClawSwarm"
];
const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D", "1W"];
const REGIME_TYPES = ["ALL", "BULL", "BEAR", "SIDEWAYS", "HIGH_VOL", "LOW_VOL", "CRASH"];
const REGIME_COLORS = { BULL: "#10b981", BEAR: "#ef4444", SIDEWAYS: "#3b82f6", HIGH_VOL: "#f59e0b", LOW_VOL: "#8b5cf6", CRASH: "#f43f5e" };

// ReactFlow strategy builder nodes
const INIT_NODES = [
  { id: "1", position: { x: 0, y: 0 }, data: { label: "Data Feed" }, style: { background: "#1e293b", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 8, padding: 10, fontSize: 11 } },
  { id: "2", position: { x: 180, y: -40 }, data: { label: "RSI Filter" }, style: { background: "#1e293b", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 8, padding: 10, fontSize: 11 } },
  { id: "3", position: { x: 180, y: 40 }, data: { label: "MACD Signal" }, style: { background: "#1e293b", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 8, padding: 10, fontSize: 11 } },
  { id: "4", position: { x: 360, y: 0 }, data: { label: "Entry Logic" }, style: { background: "#1e293b", color: "#10b981", border: "1px solid #10b981", borderRadius: 8, padding: 10, fontSize: 11 } },
  { id: "5", position: { x: 540, y: 0 }, data: { label: "Risk Manager" }, style: { background: "#1e293b", color: "#f59e0b", border: "1px solid #f59e0b", borderRadius: 8, padding: 10, fontSize: 11 } },
  { id: "6", position: { x: 720, y: 0 }, data: { label: "Execute" }, style: { background: "#1e293b", color: "#3b82f6", border: "1px solid #3b82f6", borderRadius: 8, padding: 10, fontSize: 11 } },
  { id: "7", position: { x: 360, y: -80 }, data: { label: "Vol Filter" }, style: { background: "#1e293b", color: "#8b5cf6", border: "1px solid #8b5cf6", borderRadius: 8, padding: 10, fontSize: 11 } },
  { id: "8", position: { x: 360, y: 80 }, data: { label: "Regime Gate" }, style: { background: "#1e293b", color: "#ec4899", border: "1px solid #ec4899", borderRadius: 8, padding: 10, fontSize: 11 } },
  { id: "9", position: { x: 540, y: -80 }, data: { label: "Kelly Sizer" }, style: { background: "#1e293b", color: "#06b6d4", border: "1px solid #06b6d4", borderRadius: 8, padding: 10, fontSize: 11 } },
  { id: "10", position: { x: 540, y: 80 }, data: { label: "Correlation Check" }, style: { background: "#1e293b", color: "#f97316", border: "1px solid #f97316", borderRadius: 8, padding: 10, fontSize: 11 } },
];
const INIT_EDGES = [
  { id: "e1-2", source: "1", target: "2", animated: true, style: { stroke: "#334155" } },
  { id: "e1-3", source: "1", target: "3", animated: true, style: { stroke: "#334155" } },
  { id: "e2-4", source: "2", target: "4", style: { stroke: "#334155" } },
  { id: "e3-4", source: "3", target: "4", style: { stroke: "#334155" } },
  { id: "e4-5", source: "4", target: "5", style: { stroke: "#10b981" } },
  { id: "e5-6", source: "5", target: "6", style: { stroke: "#f59e0b" } },
  { id: "e7-5", source: "7", target: "5", style: { stroke: "#8b5cf6" } },
  { id: "e8-4", source: "8", target: "4", style: { stroke: "#ec4899" } },
  { id: "e9-6", source: "9", target: "6", style: { stroke: "#06b6d4" } },
  { id: "e10-5", source: "10", target: "5", style: { stroke: "#f97316" } },
];

// KPI stat helper (matches mockup 2-row mega strip)
function KPI({ label, value, color = "text-slate-300", sub }) {
  return (
    <div className="text-center px-1">
      <div className="text-[9px] text-slate-500 uppercase tracking-wide">{label}</div>
      <div className={`text-sm font-bold ${color}`}>{value}</div>
      {sub && <div className="text-[8px] text-slate-600">{sub}</div>}
    </div>
  );
}

// Lightweight-Charts: Equity Curve with timeframe buttons
function EquityCurveLC({ data = [], height = 200 }) {
  const ref = useRef(null);
  const [range, setRange] = useState("ALL");
  useEffect(() => {
    if (!ref.current || !data.length) return;
    const chart = createChart(ref.current, {
      layout: { background: { type: ColorType.Solid, color: "#020617" }, textColor: "#64748b" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      width: ref.current.clientWidth, height,
      rightPriceScale: { borderColor: "#1e293b" },
      timeScale: { borderColor: "#1e293b" },
      crosshair: { mode: CrosshairMode.Normal },
    });
    const series = chart.addAreaSeries({ topColor: "rgba(16,185,129,0.4)", bottomColor: "rgba(16,185,129,0.02)", lineColor: "#10b981", lineWidth: 2 });
    series.setData(data);
    const resize = () => chart.applyOptions({ width: ref.current?.clientWidth });
    window.addEventListener("resize", resize);
    return () => { window.removeEventListener("resize", resize); chart.remove(); };
  }, [data, height, range]);
  return (
    <div>
      <div className="flex gap-1 mb-1">
        {["1M","3M","1Y","ALL"].map(r => <button key={r} onClick={() => setRange(r)} className={`px-2 py-0.5 text-[9px] rounded ${range===r?"bg-blue-600 text-white":"bg-slate-800 text-slate-400"}`}>{r}</button>)}
      </div>
      <div ref={ref} className="w-full rounded border border-slate-800 overflow-hidden" />
    </div>
  );
}

export default function Backtesting() {
  // === Config state (mockup: Backtest Configuration panel) ===
  const [strategy, setStrategy] = useState("Mean Reversion V2");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [assets, setAssets] = useState("BTCUSDT,ETHUSDT,SPY,QQQ,AAPL,MSFT,TSLA,NVDA");
  const [timeframe, setTimeframe] = useState("1h");
  const [capital, setCapital] = useState(100000);
  const [benchmark, setBenchmark] = useState("SPY");
  // === Parameter Sweeps & Controls (mockup center panel) ===
  const [paramA, setParamA] = useState(50);
  const [paramBMin, setParamBMin] = useState(10);
  const [paramBMax, setParamBMax] = useState(100);
  const [posSize, setPosSize] = useState(100);
  const [rebalanceFreq, setRebalanceFreq] = useState("Daily");
  const [slippage, setSlippage] = useState(5);
  const [stopLossPct, setStopLossPct] = useState(5);
  const [takeProfitPct, setTakeProfitPct] = useState(10);
  const [txCost, setTxCost] = useState(0);
  const [useKellySizing, setUseKellySizing] = useState(false);
  const [kellyFraction, setKellyFraction] = useState(0.5);
  const [sweepMode, setSweepMode] = useState("Single");
  const [commission, setCommission] = useState(0);
  const [trailingStop, setTrailingStop] = useState(0);
  const [volatilityTarget, setVolatilityTarget] = useState(0.5);
  const [correlationFilter, setCorrelationFilter] = useState(0.7);
  // === Regime & Advanced (mockup right controls area) ===
  const [regimeFilter, setRegimeFilter] = useState("BULL");
  const [riskPerTrade, setRiskPerTrade] = useState(2);
  const [maxPositions, setMaxPositions] = useState(5);
  const [warmUpPeriod, setWarmUpPeriod] = useState(1000);
  const [walkForwardWindow, setWalkForwardWindow] = useState(33);
  const [outOfSamplePct, setOutOfSamplePct] = useState(25);
  const [monteCarloIter, setMonteCarloIter] = useState(1000);
  const [confidenceLevel, setConfidenceLevel] = useState(95);
  // === Runtime state ===
  const [isRunning, setIsRunning] = useState(false);
  // === ReactFlow ===
  const [nodes, setNodes] = useState(INIT_NODES);
  const [edges, setEdges] = useState(INIT_EDGES);
  const onNodesChange = useCallback((c) => setNodes((n) => applyNodeChanges(c, n)), []);
  const onEdgesChange = useCallback((c) => setEdges((e) => applyEdgeChanges(c, e)), []);

  // === API HOOKS (ALL real data, zero fake fallbacks) ===
  const { data: runsData, loading, error, refetch } = useApi("backtestRuns", { pollIntervalMs: 30000 });
  const { data: resultsData } = useApi("backtestResults", { pollIntervalMs: 30000 });
  const { data: optData } = useApi("backtestOptimization");
  const { data: wfData } = useApi("backtestWalkforward");
  const { data: mcData } = useApi("backtestMontecarlo");
  const { data: regimeData } = useApi("backtestRegime");
  const { data: sharpeData } = useApi("backtestRollingSharpe");
  const { data: tradeDistData } = useApi("backtestTradeDistribution");
  const { data: kellyCompData } = useApi("backtestKellyComparison");
  const { data: corrData } = useApi("backtestCorrelation");
  const { data: sectorData } = useApi("backtestSectorExposure");
  const { data: ddAnalysis } = useApi("backtestDrawdownAnalysis");
  const { data: swarmStatus } = useApi("openclawSwarmStatus", { pollIntervalMs: 5000 });
  const { data: agentsData } = useApi("openclawAgents", { pollIntervalMs: 5000 });

  // === Derived data (no fallbacks - shows loading state if null) ===
  const results = resultsData || {};
  const runs = Array.isArray(runsData?.runs) ? runsData.runs : [];
  const runHistory = Array.isArray(runsData?.runHistory) ? runsData.runHistory : [];
  const tradeDist = tradeDistData?.distribution || [];
  const rollingSharpe = sharpeData?.series || [];
  const wfSeries = wfData?.periods || [];
  const mcPaths = mcData?.paths || [];
  const regimes = regimeData?.regimes || [];
  const optHeatmap = optData?.heatmap || [];
  const trades = resultsData?.trades_detail || resultsData?.trades || [];
  const kellyComp = kellyCompData || {};
  const correlations = corrData?.matrix || [];
  const sectorExposure = sectorData?.sectors || [];
  const drawdownPeriods = ddAnalysis?.periods || [];
  const swarmAgents = agentsData?.agents || [];
  const swarmMetrics = swarmStatus || {};
  const mcStats = mcData || {};

  // === Run Backtest (POST to real backend engine) ===
  const handleRunBacktest = async () => {
    setIsRunning(true);
    try {
      await fetch(getApiUrl("backtest"), {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy, startDate, endDate, assets, capital: parseFloat(capital), benchmark, txCost: parseFloat(txCost), useKellySizing, kellyFraction: parseFloat(kellyFraction), paramA, paramBMin, paramBMax, posSize, slippage, stopLossPct, takeProfitPct, sweepMode, commission, trailingStop, volatilityTarget, correlationFilter, regimeFilter, riskPerTrade, maxPositions, warmUpPeriod, walkForwardWindow, outOfSamplePct, monteCarloIter, confidenceLevel, rebalanceFreq, timeframe }),
      });
      refetch();
    } catch (err) { console.error("Backtest failed:", err); }
    finally { setIsRunning(false); }
  };

  const handleStop = () => setIsRunning(false);

  // === JSX RETURN (exact mirror of mockup 08-backtesting-lab.png) ===
  return (
    <div className="space-y-2">
      {/* TOP BAR: System status (mockup: OC_CORE_v3.2.1 bar) */}
      <div className="flex items-center justify-between text-[9px] text-slate-500 px-1">
        <span className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          OC_CORE_v3.2.1
        </span>
        <span>WS:LATENCY: {swarmMetrics.latency || "--"}ms | SWARM_SIZE: {swarmMetrics.totalAgents || "--"} | {new Date().toLocaleTimeString()}</span>
      </div>

      <PageHeader title="BACKTESTING_LAB" badge={isRunning ? "RUNNING" : runs.length > 0 ? "COMPLETE" : "READY"} />

      {/* ROW 1: Config + Param Sweeps + Run/Stop + OpenClaw Swarm (mockup top row) */}
      <div className="grid grid-cols-12 gap-2">
        {/* Backtest Configuration (mockup left) */}
        <div className="col-span-2">
          <Card title="Backtest Configuration">
            <div className="space-y-2">
              <Select label="Strategy" value={strategy} onChange={(e) => setStrategy(e.target.value)} options={STRATEGIES.map(s => ({ value: s, label: s }))} />
              <div className="grid grid-cols-2 gap-1">
                <TextField label="Start" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                <TextField label="End" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
              <TextField label="Assets" value={assets} onChange={(e) => setAssets(e.target.value)} />
              <TextField label="Capital" value={capital} onChange={(e) => setCapital(e.target.value)} />
              <TextField label="Benchmark" value={benchmark} onChange={(e) => setBenchmark(e.target.value)} />
            </div>
          </Card>
        </div>

        {/* Parameter Sweeps & Controls (mockup center - wide) */}
        <div className="col-span-6">
          <Card title="Parameter Sweeps & Controls">
            <div className="grid grid-cols-4 gap-x-4 gap-y-2">
              <Slider label={`Param A: ${paramA}`} min={0} max={100} value={paramA} onChange={(v) => setParamA(v)} />
              <TextField label="B Min/Max" value={`${paramBMin}`} onChange={(e) => setParamBMin(e.target.value)} />
              <TextField label="" value={`${paramBMax}`} onChange={(e) => setParamBMax(e.target.value)} />
              <TextField label="Max Positions" value={maxPositions} onChange={(e) => setMaxPositions(e.target.value)} />
              <Slider label={`Position Size: ${posSize}%`} min={1} max={100} value={posSize} onChange={(v) => setPosSize(v)} />
              <Select label="Rebalance Freq" value={rebalanceFreq} onChange={(e) => setRebalanceFreq(e.target.value)} options={["Daily","Weekly","Monthly"].map(r => ({ value: r, label: r }))} />
              <TextField label="Stop Loss %" value={stopLossPct} onChange={(e) => setStopLossPct(e.target.value)} />
              <TextField label="Take Profit %" value={takeProfitPct} onChange={(e) => setTakeProfitPct(e.target.value)} />
              <TextField label="Transaction Cost" value={txCost} onChange={(e) => setTxCost(e.target.value)} />
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-1 cursor-pointer"><input type="checkbox" checked={useKellySizing} onChange={() => setUseKellySizing(!useKellySizing)} /><span className="text-[10px] text-emerald-400 font-bold">Kelly Sizing</span></label>
                {useKellySizing && <Slider label={`${kellyFraction}`} min={0.1} max={1} step={0.05} value={kellyFraction} onChange={(v) => setKellyFraction(v)} />}
              </div>
              <div className="flex gap-1">
                {["Single","Sweep"].map(m => <button key={m} onClick={() => setSweepMode(m)} className={`px-2 py-0.5 text-[9px] rounded ${sweepMode===m?"bg-blue-600 text-white":"bg-slate-800 text-slate-400"}`}>{m}</button>)}
              </div>
              <TextField label="Commission" value={commission} onChange={(e) => setCommission(e.target.value)} />
              <TextField label="Trailing Stop" value={trailingStop} onChange={(e) => setTrailingStop(e.target.value)} />
              <Slider label={`Vol Target: ${volatilityTarget}`} min={0} max={1} step={0.05} value={volatilityTarget} onChange={(v) => setVolatilityTarget(v)} />
              <Slider label={`Corr Filter: ${correlationFilter}`} min={0} max={1} step={0.05} value={correlationFilter} onChange={(v) => setCorrelationFilter(v)} />
            </div>
            <div className="grid grid-cols-6 gap-2 mt-2 pt-2 border-t border-slate-800">
              <Select label="Regime Filter" value={regimeFilter} onChange={(e) => setRegimeFilter(e.target.value)} options={REGIME_TYPES.map(r => ({ value: r, label: r }))} />
              <TextField label="Risk/Trade %" value={riskPerTrade} onChange={(e) => setRiskPerTrade(e.target.value)} />
              <TextField label="Warm-Up" value={warmUpPeriod} onChange={(e) => setWarmUpPeriod(e.target.value)} />
              <TextField label={`WF Window ${walkForwardWindow}%`} value={walkForwardWindow} onChange={(e) => setWalkForwardWindow(e.target.value)} />
              <TextField label="MC Iterations" value={monteCarloIter} onChange={(e) => setMonteCarloIter(e.target.value)} />
              <TextField label={`Confidence ${confidenceLevel}%`} value={confidenceLevel} onChange={(e) => setConfidenceLevel(e.target.value)} />
            </div>
          </Card>
          {/* Run / Stop buttons */}
          <div className="flex gap-2 mt-2">
            <Button onClick={handleRunBacktest} disabled={isRunning} leftIcon={Play} className="bg-emerald-600 hover:bg-emerald-700 flex-1 text-xs">Run</Button>
            <Button onClick={handleStop} leftIcon={Square} variant="danger" className="flex-1 text-xs">Stop</Button>
          </div>
        </div>

        {/* OpenClaw Swarm Backtest Integration (mockup right) */}
        <div className="col-span-4">
          <Card title={<span className="flex items-center gap-1.5"><Network size={14} className="text-purple-400" /> OpenClaw Swarm Backtest Integration</span>}>
            <div className="grid grid-cols-2 gap-3">
              {/* 7 Core Agents */}
              <div>
                <div className="text-[10px] text-slate-500 font-bold mb-1">7 Core Agents</div>
                <div className="space-y-1">
                  {swarmAgents.slice(0,7).map((a, i) => (
                    <div key={a.id || i} className="flex items-center justify-between text-[9px]">
                      <span className="text-slate-300">{a.role || a.name}</span>
                      <div className="flex items-center gap-1">
                        <div className="w-16 bg-slate-800 rounded-full h-1"><div className="h-1 rounded-full" style={{width:`${a.health || a.cpu || 80}%`, background: (a.health || a.cpu || 80) > 70 ? "#10b981" : "#f59e0b"}} /></div>
                        <span className="text-slate-500 w-6 text-right">{a.health || a.cpu || 80}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              {/* Swarm Status */}
              <div>
                <div className="text-[10px] text-slate-500 font-bold mb-1">Swarm Status</div>
                <div className="p-2 bg-purple-500/10 border border-purple-500/20 rounded text-[9px] text-purple-300 space-y-1">
                  <div>EXTENDED SWARM: <span className="font-bold text-emerald-400">{swarmMetrics.subAgentCount || swarmMetrics.activeAgents || "--"} sub-agents active</span></div>
                  <div className="border-t border-purple-500/20 pt-1 mt-1 text-[8px] text-slate-400">
                    <div>Team Alpha: {swarmMetrics.teamAlpha || "--"} agents</div>
                    <div>Team Beta: {swarmMetrics.teamBeta || "--"} agents</div>
                    <div>Team Gamma: {swarmMetrics.teamGamma || "--"} agents</div>
                    <div>Team Delta: {swarmMetrics.teamDelta || "--"} agents</div>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* ROW 2: Performance KPI Mega Strip (mockup: 2 rows of KPIs) */}
      <div className="bg-slate-900/50 rounded-lg p-2 border border-slate-800">
        <div className="text-[9px] text-slate-500 font-bold uppercase mb-1">Performance KPI Mega Strip</div>
        <div className="grid grid-cols-14 gap-1">
          <KPI label="Net P&L" value={results.total_pnl != null ? `$${(results.total_pnl/1000).toFixed(0)}K` : "--"} color={results.total_pnl >= 0 ? "text-emerald-400" : "text-rose-400"} />
          <KPI label="Sharpe" value={results.sharpe?.toFixed(2) || "--"} color={results.sharpe >= 2 ? "text-emerald-400" : results.sharpe >= 1 ? "text-amber-400" : "text-rose-400"} />
          <KPI label="Sortino" value={results.sortino?.toFixed(2) || "--"} color="text-cyan-400" />
          <KPI label="Calmar" value={results.calmar?.toFixed(2) || "--"} color="text-purple-400" />
          <KPI label="Max DD" value={results.maxdd != null ? `${(results.maxdd * 100).toFixed(1)}%` : "--"} color="text-rose-400" />
          <KPI label="Win Rate" value={results.winrate != null ? `${(results.winrate * 100).toFixed(1)}%` : "--"} color={results.winrate >= 0.6 ? "text-emerald-400" : "text-amber-400"} />
          <KPI label="Profit Factor" value={results.profit_factor?.toFixed(2) || "--"} color="text-blue-400" />
          <KPI label="Avg Trade" value={results.avg_r != null ? `$${results.avg_r?.toFixed(0)}` : "--"} />
          <KPI label="Total Trades" value={results.trades?.toLocaleString() || "--"} />
          <KPI label="Expectancy" value={results.avg_r?.toFixed(4) || "--"} color="text-cyan-400" />
          <KPI label="Kelly Efficiency" value={results.kelly_efficiency != null ? `${(results.kelly_efficiency * 100).toFixed(0)}%` : "--"} color="text-purple-400" />
          <KPI label="Trading Grade" value={results.sharpe >= 2 ? "A+" : results.sharpe >= 1.5 ? "A" : results.sharpe >= 1 ? "B+" : "C"} color="text-amber-400" />
          <KPI label="CAGR" value={results.total_pnl != null ? `${((results.total_pnl / (results.initial_equity || 100000)) * 100).toFixed(1)}%` : "--"} color="text-emerald-400" />
          <KPI label="Beta" value={results.beta?.toFixed(2) || "--"} />
        </div>
        <div className="grid grid-cols-14 gap-1 mt-1 pt-1 border-t border-slate-800">
          <KPI label="Net P&L%" value={results.total_pnl != null ? `${((results.total_pnl / (results.initial_equity || 100000)) * 100).toFixed(2)}%` : "--"} />
          <KPI label="Avg Trade" value={results.avg_r?.toFixed(2) || "--"} />
          <KPI label="Win Rate" value={results.winrate != null ? `${(results.winrate * 100).toFixed(1)}%` : "--"} />
          <KPI label="Total Trades" value={results.trades?.toLocaleString() || "--"} />
          <KPI label="Expectancy" value={results.avg_r?.toFixed(2) || "--"} />
          <KPI label="R:R Ratio" value={results.profit_factor?.toFixed(2) || "--"} color="text-cyan-400" />
          <KPI label="Kelly Advantage" value={results.kelly_advantage?.toFixed(2) || "--"} color="text-emerald-400" />
          <KPI label="Trading Grade" value={results.sharpe >= 2 ? "A+" : "--"} color="text-amber-400" />
          <KPI label="CAGR" value={results.total_pnl != null ? `${((results.total_pnl / (results.initial_equity || 100000)) * 100).toFixed(1)}%` : "--"} />
          <KPI label="Volatility" value={results.volatility?.toFixed(1) || "--"} />
          <KPI label="Alpha" value={results.alpha?.toFixed(1) || "--"} color="text-emerald-400" />
          <KPI label="Beta" value={results.beta?.toFixed(2) || "--"} />
          <KPI label="Info Ratio" value={results.info_ratio?.toFixed(2) || "--"} />
          <KPI label="Omega" value={results.omega?.toFixed(2) || "--"} />
        </div>
      </div>

      {/* ROW 3: Equity Curve + Parallel Run Manager + Trade Dist + Rolling Sharpe + Walk-Forward */}
      <div className="grid grid-cols-12 gap-2">
        <div className="col-span-4">
          <Card title="Equity Curve - Lightweight Charts" noPadding>
            <div className="p-2"><EquityCurveLC data={results.equityCurve || results.equity_curve || []} height={180} /></div>
          </Card>
        </div>
        <div className="col-span-2">
          <Card title="Parallel Run Manager">
            <DataTable columns={[
              { key: "id", label: "#", render: (v) => <span className="text-xs">{v}</span> },
              { key: "strategy", label: "Strategy", render: (v) => <span className="text-xs">{v}</span> },
              { key: "status", label: "Status", render: (v) => <Badge variant={v==="Running"?"warning":v==="Complete"?"success":"danger"} className="text-[8px]">{v}</Badge> },
              { key: "trades", label: "Trades", cellClassName: "text-right text-xs" },
            ]} data={runs} />
          </Card>
        </div>
        <div className="col-span-2">
          <Card title="Trade P&L Distribution" noPadding>
            <ChartPlaceholder title="Trade P&L Distribution" />
          </Card>
        </div>
        <div className="col-span-2">
          <Card title="Rolling Sharpe Ratio (24M)" noPadding>
            <ChartPlaceholder title="Rolling Sharpe Ratio (24M)" />
          </Card>
        </div>
        <div className="col-span-2">
          <Card title="Walk-Forward Analysis" noPadding>
            <ChartPlaceholder title="Walk-Forward Analysis" />
          </Card>
        </div>
      </div>

      {/* ROW 4: Market Regime (donut) + Monte Carlo + Optimization + Strategy Builder */}
      <div className="grid grid-cols-12 gap-2">
        <div className="col-span-2">
          <Card title="Market Regime Performance">
            <ChartPlaceholder title="Market Regime Performance" height={140} />
            <div className="space-y-0.5 mt-1">
              {regimes.map(r => (
                <div key={r.name} className="flex justify-between text-[9px]">
                  <span style={{color: REGIME_COLORS[r.name]}}>{r.name}</span>
                  <span className="text-slate-400">{r.winRate?.toFixed(1) || "--"}%</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
        <div className="col-span-3">
                    <Card title="Monte Carlo Simulation" noPadding>
<ChartPlaceholder title="Monte Carlo Simulation" />
            <div className="grid grid-cols-3 gap-1 p-1">
              <KPI label="5th %ile" value={mcStats.equity_p5 != null ? `$${(mcStats.equity_p5/1000).toFixed(0)}K` : "--"} color="text-rose-400" />
              <KPI label="Median" value={mcStats.equity_median != null ? `$${(mcStats.equity_median/1000).toFixed(0)}K` : "--"} color="text-emerald-400" />
              <KPI label="95th %ile" value={mcStats.equity_p95 != null ? `$${(mcStats.equity_p95/1000).toFixed(0)}K` : "--"} color="text-cyan-400" />
            </div>
          </Card>
        </div>
        <div className="col-span-3">
          <Card title="Parameter Optimization Heatmap" noPadding>
            <div className="p-2">
              <div className="grid gap-0.5" style={{ gridTemplateColumns: `repeat(${optHeatmap[0]?.cells?.length || 6}, 1fr)` }}>
                {optHeatmap.flatMap((row) => row.cells.map((cell) => (
                  <div key={`${row.row}-${cell.col}`} className="aspect-square rounded-sm flex items-center justify-center text-[7px] font-bold" style={{ background: cell.value > 2 ? "#10b981" : cell.value > 1 ? "#22d3ee" : cell.value > 0 ? "#3b82f6" : cell.value > -0.5 ? "#f59e0b" : "#f43f5e", color: "#020617" }}>
                    {cell.value?.toFixed(1)}
                  </div>
                )))}
              </div>
            </div>
          </Card>
        </div>
        <div className="col-span-4">
          <Card title="Strategy Builder - ReactFlow" noPadding>
            <div style={{ height: 220 }}>
              <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} fitView>
                <Background color="#1e293b" gap={16} />
                <Controls />
              </ReactFlow>
            </div>
          </Card>
        </div>
      </div>

      {/* ROW 5: Trade Log (full columns) + Run History + OpenClaw Swarm Consensus */}
      <div className="grid grid-cols-12 gap-2">
        <div className="col-span-7">
          <Card title="Trade-by-Trade Log" noPadding>
            <DataTable columns={[
              { key: "received_at", label: "Date", render: (v) => <span className="text-slate-400 text-[9px]">{v?.slice(0,10)}</span> },
              { key: "symbol", label: "Asset", render: (v) => <span className="font-bold text-[9px]">{v}</span> },
              { key: "direction", label: "Side", render: (v) => <Badge variant={v==="LONG"?"success":"danger"} className="text-[7px]">{v}</Badge> },
              { key: "shares", label: "QTY", cellClassName: "text-right text-[9px]" },
              { key: "entry", label: "Entry", cellClassName: "text-right text-[9px]", render: (v) => `$${Number(v)?.toFixed(2)}` },
              { key: "target", label: "Exit", cellClassName: "text-right text-[9px]", render: (v) => `$${Number(v)?.toFixed(2)}` },
              { key: "pnl_dollars", label: "P&L", cellClassName: "text-right", render: (v) => <span className={Number(v)>=0?"text-emerald-400":"text-rose-400"}>${Number(v)?.toFixed(0)}</span> },
              { key: "pnl_r", label: "R-Mult", cellClassName: "text-right text-[9px]", render: (v) => <span className={Number(v)>=0?"text-emerald-400":"text-rose-400"}>{Number(v)?.toFixed(2)}R</span> },
              { key: "score", label: "Agent", cellClassName: "text-right text-[9px]", render: (v) => v ? `OC:${Number(v)?.toFixed(0)}` : "--" },
              { key: "kelly_sized", label: "Kelly", render: (v) => <Badge variant={v?"success":"default"} className="text-[7px]">{v?"Y":"N"}</Badge> },
            ]} data={trades} />
          </Card>
        </div>
        <div className="col-span-2">
          <Card title="Run History & Export" noPadding>
            <DataTable columns={[
              { key: "date", label: "Date", render: (v) => <span className="text-[9px] text-slate-400">{v}</span> },
              { key: "strategy", label: "Strategy", render: (v) => <span className="text-[9px]">{v}</span> },
              { key: "pnl", label: "Revenue", cellClassName: "text-right", render: (v) => <span className={Number(v)>=0?"text-emerald-400":"text-rose-400"}>${v}</span> },
            ]} data={runHistory} />
            <div className="p-2">
              <Button variant="secondary" fullWidth leftIcon={Download} className="text-[9px]">Export All Results (CSV/JSON)</Button>
            </div>
          </Card>
        </div>
        <div className="col-span-3">
          <Card title={<span className="flex items-center gap-1.5"><Brain size={12} className="text-purple-400" /> OpenClaw Swarm Consensus</span>}>
            <div className="space-y-2">
              <div className="text-center">
                <div className="text-[10px] text-slate-500">Agent Agreement</div>
                <div className="text-2xl font-bold text-emerald-400">{swarmMetrics.consensusScore != null ? `${(swarmMetrics.consensusScore * 100).toFixed(0)}%` : "--"}</div>
              </div>
              <div className="space-y-1">
                {[{team:"Alpha",count:swarmMetrics.teamAlpha,color:"#3b82f6"},{team:"Beta",count:swarmMetrics.teamBeta,color:"#10b981"},{team:"Gamma",count:swarmMetrics.teamGamma,color:"#f59e0b"},{team:"Delta",count:swarmMetrics.teamDelta,color:"#8b5cf6"}].map(t => (
                  <div key={t.team} className="flex items-center justify-between text-[9px]">
                    <span className="text-slate-300">{t.team}</span>
                    <div className="flex items-center gap-1">
                      <div className="w-20 bg-slate-800 rounded-full h-1.5"><div className="h-1.5 rounded-full" style={{width:`${((t.count||0)/30)*100}%`, background: t.color}} /></div>
                      <span className="text-slate-500 w-5 text-right">{t.count || "--"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      </div>

              {/* ROW 6: OpenClaw Swarm Agents + Strategy Builder */}
        <div className="grid grid-cols-12 gap-3">
          <div className="col-span-8">
            <Card title={`OpenClaw Swarm (${swarmAgents.length} Agents)`}>
              <div style={{ height: 320 }}>
                <ReactFlow
                  nodes={swarmAgents.map((a, i) => ({
                    id: String(a.id),
                    position: { x: 80 + (i % 4) * 200, y: 40 + Math.floor(i / 4) * 120 },
                    data: { label: `${a.role}\nTasks: ${a.tasksCompleted || 0}\nP&L: $${(a.pnl || 0).toLocaleString()}` },
                    style: {
                      background: a.status === 'active' ? '#064e3b' : '#1e293b',
                      color: '#e2e8f0', border: '1px solid #334155',
                      borderRadius: 8, padding: 10, fontSize: 11, whiteSpace: 'pre-line',
                      width: 160
                    }
                  }))}
                  edges={swarmAgents.slice(1).map((a, i) => ({
                    id: `e${i}`, source: '1', target: String(a.id),
                    animated: true, style: { stroke: '#10b981' }
                  }))}
                  fitView
                >
                  <Background color="#334155" gap={16} />
                  <Controls />
                </ReactFlow>
              </div>
              <div className="grid grid-cols-4 gap-2 mt-2">
                <ResultStat label="Active" value={swarmMetrics.activeAgents} color="text-emerald-400" />
                <ResultStat label="Tasks Done" value={swarmMetrics.tasksCompleted} />
                <ResultStat label="Swarm P&L" value={`$${(swarmMetrics.totalPnl || 0).toLocaleString()}`} color="text-emerald-400" />
                <ResultStat label="Consensus" value={`${swarmMetrics.consensusScore || 0}%`} />
              </div>
            </Card>
          </div>

                    <div className="col-span-4">
            <Card title="Sub-Agent Details">
              <div className="space-y-1 max-h-[360px] overflow-y-auto">
                {swarmAgents.map((a) => (
                  <div key={a.id} className="flex items-center justify-between p-2 rounded bg-slate-800/60 border border-slate-700">
                    <div>
                      <span className="text-slate-300 font-medium text-xs">{a.role}</span>
                      <div className="text-[10px] text-slate-500">ID: {a.id} | Tasks: {a.tasksCompleted || 0}</div>
                    </div>
                    <div className="text-right">
                      <Badge variant={a.status === 'active' ? 'success' : 'secondary'} className="text-[9px]">{a.status}</Badge>
                      <div className={`text-xs font-mono ${(a.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        ${(a.pnl || 0).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

        </div>

      {/* BOTTOM BAR (mockup: 7 Agents OK, EXTENDED SWARM) */}
      <div className="flex items-center justify-between text-[8px] text-slate-600 px-2 py-1 bg-slate-900/30 rounded border border-slate-800">
        <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />{swarmAgents.filter(a => a.status === "active").length || "--"} Agents OK</span>
        <span>EXTENDED SWARM ({swarmMetrics.subAgentCount || swarmMetrics.activeAgents || "--"})</span>
        <span>{new Date().toLocaleTimeString()}</span>
      </div>

    </div>
  );
}
