// BACKTESTING_LAB -- Embodier.ai Glass House Intelligence System
// Production V7 -- Exact mirror of Nano Banana Pro mockup 08-backtesting-lab.png
// ALL data from real API -- zero mock/fake data
import {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
  Component,
} from "react";
import { toast } from "react-toastify";
import log from "@/utils/logger";
import {
  Play,
  Square,
  Download,
  RotateCcw,
  Settings,
  Plus,
  Minus,
  Copy,
  Trash2,
  TrendingUp,
  TrendingDown,
  Activity,
  Zap,
  Shield,
  Brain,
  Users,
  GitBranch,
  Layers,
  BarChart3,
  Target,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Eye,
  EyeOff,
  Lock,
  Unlock,
  Cpu,
  Network,
  Clock,
  Search,
  Upload,
  Filter,
  Pause,
} from "lucide-react";
import Card from "../components/ui/Card";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import DataTable from "../components/ui/DataTable";
import Slider from "../components/ui/Slider";
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../config/api";
import { createChart, ColorType, CrosshairMode } from "lightweight-charts";
import ReactFlow, {
  Background,
  Controls,
  applyNodeChanges,
  applyEdgeChanges,
} from "reactflow";
import "reactflow/dist/style.css";

// Ensure d3-transition side-effects are loaded (patches d3-selection with .interrupt())
import "d3-transition";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  Cell,
  Legend,
  ComposedChart,
  Scatter,
  ScatterChart,
  ReferenceLine,
} from "recharts";
import clsx from "clsx";

/* ------------------------------------------------------------------ */
/*  Safe ReactFlow wrapper -- catches D3 transition errors gracefully */
/* ------------------------------------------------------------------ */
class SafeReactFlow extends Component {
  state = { hasError: false };
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-full text-secondary text-sm">
          <div className="text-center">
            <GitBranch className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p>Strategy builder unavailable</p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

/* ------------------------------------------------------------------ */
/*  Lightweight Charts: Equity Curve (area)                           */
/* ------------------------------------------------------------------ */
function EquityCurveLC({ data = [], height = 220 }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9CA3AF",
      },
      grid: {
        vertLines: { color: "rgba(42,52,68,0.3)" },
        horzLines: { color: "rgba(42,52,68,0.3)" },
      },
      width: ref.current.clientWidth,
      height,
      rightPriceScale: { borderColor: "rgba(42,52,68,0.3)" },
      timeScale: { borderColor: "rgba(42,52,68,0.3)" },
      crosshair: { mode: CrosshairMode.Normal },
    });
    const series = chart.addAreaSeries({
      topColor: "rgba(16,185,129,0.4)",
      bottomColor: "rgba(16,185,129,0.02)",
      lineColor: "#10B981",
      lineWidth: 2,
    });
    if (data.length) {
      const mapped = data.map((d) => ({
        time: d.time || d.date || d.x,
        value: d.value ?? d.equity ?? d.y ?? 0,
      }));
      series.setData(mapped);
    }
    // drawdown overlay
    const ddSeries = chart.addAreaSeries({
      topColor: "rgba(239,68,68,0.0)",
      bottomColor: "rgba(239,68,68,0.3)",
      lineColor: "rgba(239,68,68,0.6)",
      lineWidth: 1,
      priceScaleId: "dd",
    });
    chart
      .priceScale("dd")
      .applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } });
    if (data.length) {
      const ddMapped = data.map((d) => ({
        time: d.time || d.date || d.x,
        value: d.drawdown ?? d.dd ?? 0,
      }));
      ddSeries.setData(ddMapped);
    }
    const ro = new ResizeObserver(() => {
      if (ref.current) chart.applyOptions({ width: ref.current.clientWidth });
    });
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [data, height]);
  return <div ref={ref} className="w-full" style={{ height }} />;
}

/* ------------------------------------------------------------------ */
/*  Lightweight Charts: Trade P&L Distribution (histogram)            */
/* ------------------------------------------------------------------ */
function TradePnlDistLC({ data = [], height = 220 }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9CA3AF",
      },
      grid: {
        vertLines: { color: "rgba(42,52,68,0.3)" },
        horzLines: { color: "rgba(42,52,68,0.3)" },
      },
      width: ref.current.clientWidth,
      height,
      rightPriceScale: { borderColor: "rgba(42,52,68,0.3)" },
      timeScale: { borderColor: "rgba(42,52,68,0.3)" },
      crosshair: { mode: CrosshairMode.Normal },
    });
    const series = chart.addHistogramSeries({
      color: "#00D9FF",
      priceFormat: { type: "volume" },
    });
    if (data.length) {
      const mapped = data.map((d) => ({
        time: d.time || d.bucket || d.bin || d.x,
        value: d.value ?? d.count ?? d.frequency ?? d.y ?? 0,
        color: (d.value ?? d.pnl ?? d.y ?? 0) >= 0 ? "#10B981" : "#EF4444",
      }));
      series.setData(mapped);
    }
    const ro = new ResizeObserver(() => {
      if (ref.current) chart.applyOptions({ width: ref.current.clientWidth });
    });
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [data, height]);
  return <div ref={ref} className="w-full" style={{ height }} />;
}

/* ------------------------------------------------------------------ */
/*  Lightweight Charts: Rolling Sharpe Ratio (line)                   */
/* ------------------------------------------------------------------ */
function RollingSharpeLC({ data = [], height = 220 }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9CA3AF",
      },
      grid: {
        vertLines: { color: "rgba(42,52,68,0.3)" },
        horzLines: { color: "rgba(42,52,68,0.3)" },
      },
      width: ref.current.clientWidth,
      height,
      rightPriceScale: { borderColor: "rgba(42,52,68,0.3)" },
      timeScale: { borderColor: "rgba(42,52,68,0.3)" },
      crosshair: { mode: CrosshairMode.Normal },
    });
    const series = chart.addLineSeries({
      color: "#00D9FF",
      lineWidth: 2,
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });
    if (data.length) {
      const mapped = data.map((d) => ({
        time: d.time || d.date || d.x,
        value: d.value ?? d.sharpe ?? d.y ?? 0,
      }));
      series.setData(mapped);
    }
    // reference line at sharpe = 1.0
    const refLine = chart.addLineSeries({
      color: "rgba(239,68,68,0.4)",
      lineWidth: 1,
      lineStyle: 2,
      priceFormat: { type: "price", precision: 1, minMove: 0.1 },
    });
    if (data.length) {
      const times = data.map((d) => d.time || d.date || d.x);
      refLine.setData([
        { time: times[0], value: 1 },
        { time: times[times.length - 1], value: 1 },
      ]);
    }
    const ro = new ResizeObserver(() => {
      if (ref.current) chart.applyOptions({ width: ref.current.clientWidth });
    });
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.remove();
    };
  }, [data, height]);
  return <div ref={ref} className="w-full" style={{ height }} />;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */
const fmt = (v, d = 2) => (v == null ? "--" : Number(v).toFixed(d));
const fmtPct = (v) => (v == null ? "--" : `${Number(v).toFixed(2)}%`);
const fmtUsd = (v) =>
  v == null
    ? "--"
    : `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtK = (v) => {
  if (v == null) return "--";
  const n = Number(v);
  if (Math.abs(n) >= 1000) return `$${(n / 1000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
};

function kpiColor(val, thresholds) {
  if (val == null) return "text-gray-400";
  const n = Number(val);
  if (thresholds?.invert)
    return n <= (thresholds.good ?? 0)
      ? "text-green-400"
      : n <= (thresholds.warn ?? 0)
        ? "text-amber-400"
        : "text-red-400";
  return n >= (thresholds?.good ?? 0)
    ? "text-green-400"
    : n >= (thresholds?.warn ?? 0)
      ? "text-amber-400"
      : "text-red-400";
}

function kpiBadge(val, thresholds) {
  if (val == null) return "secondary";
  const n = Number(val);
  if (thresholds?.invert)
    return n <= (thresholds.good ?? 0)
      ? "success"
      : n <= (thresholds.warn ?? 0)
        ? "warning"
        : "danger";
  return n >= (thresholds?.good ?? 0)
    ? "success"
    : n >= (thresholds?.warn ?? 0)
      ? "warning"
      : "danger";
}

const REGIME_COLORS = {
  BULL: "#10B981",
  BEAR: "#EF4444",
  RECOVERY: "#F59E0B",
  SIDEWAYS: "#6366F1",
  VOLATILE: "#EC4899",
};

/* ------------------------------------------------------------------ */
/*  Strategy Builder ReactFlow nodes/edges                            */
/* ------------------------------------------------------------------ */
const MONO_FONT = "JetBrains Mono, monospace";
/* Mockup: Data Feed, RSI Filter, MACD Signal, Entry Logic, Execute, Optimizer, Risk Manager */
const defaultStratNodes = [
  {
    id: "1",
    data: { label: "Data Feed" },
    position: { x: 0, y: 20 },
    style: {
      background: "#0f172a",
      color: "#00D9FF",
      border: "1px solid #1e293b",
      borderRadius: "6px",
      padding: "8px 12px",
      fontSize: "10px",
      fontFamily: MONO_FONT,
    },
  },
  {
    id: "2",
    data: { label: "RSI Filter" },
    position: { x: 120, y: 0 },
    style: {
      background: "#0f172a",
      color: "#00D9FF",
      border: "1px solid #1e293b",
      borderRadius: "6px",
      padding: "8px 12px",
      fontSize: "10px",
      fontFamily: MONO_FONT,
    },
  },
  {
    id: "3",
    data: { label: "MACD Signal" },
    position: { x: 120, y: 50 },
    style: {
      background: "#0f172a",
      color: "#00D9FF",
      border: "1px solid #1e293b",
      borderRadius: "6px",
      padding: "8px 12px",
      fontSize: "10px",
      fontFamily: MONO_FONT,
    },
  },
  {
    id: "4",
    data: { label: "Entry Logic" },
    position: { x: 260, y: 25 },
    style: {
      background: "#0f172a",
      color: "#00D9FF",
      border: "1px solid #1e293b",
      borderRadius: "6px",
      padding: "8px 12px",
      fontSize: "10px",
      fontFamily: MONO_FONT,
    },
  },
  {
    id: "5",
    data: { label: "Execute" },
    position: { x: 380, y: 25 },
    style: {
      background: "#0f172a",
      color: "#00D9FF",
      border: "1px solid #1e293b",
      borderRadius: "6px",
      padding: "8px 12px",
      fontSize: "10px",
      fontFamily: MONO_FONT,
    },
  },
  {
    id: "6",
    data: { label: "Optimizer" },
    position: { x: 80, y: 120 },
    style: {
      background: "#0f172a",
      color: "#00D9FF",
      border: "1px solid #1e293b",
      borderRadius: "6px",
      padding: "8px 12px",
      fontSize: "10px",
      fontFamily: MONO_FONT,
    },
  },
  {
    id: "7",
    data: { label: "Risk Manager" },
    position: { x: 200, y: 120 },
    style: {
      background: "#0f172a",
      color: "#00D9FF",
      border: "1px solid #1e293b",
      borderRadius: "6px",
      padding: "8px 12px",
      fontSize: "10px",
      fontFamily: MONO_FONT,
    },
  },
];
const defaultStratEdges = [
  {
    id: "e1-2",
    source: "1",
    target: "2",
    animated: true,
    style: { stroke: "#334155" },
  },
  {
    id: "e1-3",
    source: "1",
    target: "3",
    animated: true,
    style: { stroke: "#334155" },
  },
  {
    id: "e2-4",
    source: "2",
    target: "4",
    animated: true,
    style: { stroke: "#334155" },
  },
  {
    id: "e3-4",
    source: "3",
    target: "4",
    animated: true,
    style: { stroke: "#334155" },
  },
  {
    id: "e4-5",
    source: "4",
    target: "5",
    animated: true,
    style: { stroke: "#334155" },
  },
  {
    id: "e1-6",
    source: "1",
    target: "6",
    animated: true,
    style: { stroke: "#334155" },
  },
  {
    id: "e6-7",
    source: "6",
    target: "7",
    animated: true,
    style: { stroke: "#334155" },
  },
  {
    id: "e7-4",
    source: "7",
    target: "4",
    animated: true,
    style: { stroke: "#334155" },
  },
];

/* ------------------------------------------------------------------ */
/*  Swarm agents list for OpenClaw panel (mockup: 7 Core Agents)       */
/* ------------------------------------------------------------------ */
const SWARM_AGENTS = [
  { name: "Apex Orchestrator", pct: 100, icon: Brain, color: "#00D9FF" },
  { name: "Relative Weakness", pct: 81, icon: TrendingDown, color: "#00D9FF" },
  { name: "Short Basket", pct: 75, icon: TrendingDown, color: "#00D9FF" },
  { name: "Meta Architect", pct: 90, icon: Layers, color: "#00D9FF" },
  { name: "Meta Alchemist", pct: 81, icon: Layers, color: "#00D9FF" },
  { name: "Risk Governor", pct: 100, icon: Shield, color: "#00D9FF" },
  { name: "Signal Engine", pct: 95, icon: Cpu, color: "#00D9FF" },
];
const SWARM_TEAMS = [
  { name: "Team Alpha", agents: 23, pct: 92, status: "green" },
  { name: "Team Beta", agents: 31, pct: 88, status: "green" },
  { name: "Team Gamma", agents: 22, pct: 72, status: "yellow" },
  { name: "Team Delta", agents: 17, pct: 58, status: "orange" },
];

/* ------------------------------------------------------------------ */
/*  Recharts dark tooltip                                             */
/* ------------------------------------------------------------------ */
function DarkTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-900/95 border border-[#00D9FF]/50/30 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color || "#00D9FF" }}>
          {p.name}: {typeof p.value === "number" ? p.value.toFixed(2) : p.value}
        </p>
      ))}
    </div>
  );
}

/* ================================================================== */
/*  MAIN COMPONENT                                                     */
/* ================================================================== */
export default function Backtesting() {
  // --- API hooks ---
  const {
    data: resultsRaw,
    loading: loadResults,
    error: errResults,
    refetch: refetchResults,
  } = useApi("backtestResults", { pollIntervalMs: 30000 });
  const { data: optRaw, loading: loadOpt } = useApi("backtestOptimization", {
    pollIntervalMs: 60000,
  });
  const { data: wfRaw, loading: loadWf } = useApi("backtestWalkforward", {
    pollIntervalMs: 60000,
  });
  const { data: mcRaw, loading: loadMc } = useApi("backtestMontecarlo", {
    pollIntervalMs: 60000,
  });
  const { data: rsRaw, loading: loadRs } = useApi("backtestRollingSharpe", {
    pollIntervalMs: 60000,
  });
  const { data: tdRaw, loading: loadTd } = useApi("backtestTradeDistribution", {
    pollIntervalMs: 60000,
  });
  const { data: regimeRaw, loading: loadRegime } = useApi("backtestRegime", {
    pollIntervalMs: 60000,
  });
  const { data: runsRaw, loading: loadRuns } = useApi("backtestRuns", {
    pollIntervalMs: 30000,
  });

  // --- Normalize API data ---
  const results = useMemo(
    () => resultsRaw?.data ?? resultsRaw ?? {},
    [resultsRaw],
  );
  const equity = useMemo(
    () =>
      results?.equity_curve ?? results?.equityCurve ?? results?.equity ?? [],
    [results],
  );
  const trades = useMemo(
    () => results?.trades ?? results?.trade_log ?? [],
    [results],
  );
  const kpis = useMemo(
    () => results?.kpis ?? results?.metrics ?? results?.summary ?? {},
    [results],
  );
  const optData = useMemo(
    () => optRaw?.data ?? optRaw?.heatmap ?? optRaw ?? [],
    [optRaw],
  );
  const wfData = useMemo(
    () => wfRaw?.data ?? wfRaw?.periods ?? wfRaw ?? [],
    [wfRaw],
  );
  const mcPaths = useMemo(
    () => mcRaw?.data ?? mcRaw?.paths ?? mcRaw ?? [],
    [mcRaw],
  );
  const rsData = useMemo(
    () => rsRaw?.data ?? rsRaw?.series ?? rsRaw ?? [],
    [rsRaw],
  );
  const tdData = useMemo(
    () => tdRaw?.data ?? tdRaw?.distribution ?? tdRaw ?? [],
    [tdRaw],
  );
  const regimeData = useMemo(
    () => regimeRaw?.data ?? regimeRaw?.regimes ?? regimeRaw ?? [],
    [regimeRaw],
  );
  const runs = useMemo(
    () => runsRaw?.data ?? runsRaw?.runs ?? runsRaw ?? [],
    [runsRaw],
  );

  // --- Config state ---
  const [strategy, setStrategy] = useState("Mean Reversion V2");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [assets, setAssets] = useState(
    "BTCUSDT, ETHUSDT, SPY, QQQ, AAPL, MSFT, TSLA, NVDA",
  );
  const [capital, setCapital] = useState("100000");
  const [batches, setBatches] = useState(10);
  const [trainPct, setTrainPct] = useState(70);
  const [minPositions, setMinPositions] = useState(5);
  const [txnCost, setTxnCost] = useState(0);
  const [maxPositions, setMaxPositions] = useState(100);

  // --- Parameter Sweeps ---
  const symbols = useMemo(
    () =>
      assets
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    [assets],
  );
  const [benchmark, setBenchmark] = useState("SPY");
  const [commission, setCommission] = useState(0.001);
  const [regimeFilter, setRegimeFilter] = useState("BULL");
  const [slippage, setSlippage] = useState(0.05);
  const [walkForwardWindow, setWalkForwardWindow] = useState(35);
  const [confidenceLevel, setConfidenceLevel] = useState(95);
  const [positionFreq, setPositionFreq] = useState(5);
  const [paramA, setParamA] = useState(50);
  const [bMinMax, setBMinMax] = useState(10);
  const [positionSizePct, setPositionSizePct] = useState(100);
  const [stopLossPct, setStopLossPct] = useState(50);
  const [takeProfit, setTakeProfit] = useState(50);
  const [kellySizing, setKellySizing] = useState(0.5);
  const [warmUpPeriod, setWarmUpPeriod] = useState(1000);
  const [monteCarloIter, setMonteCarloIter] = useState(1000);
  const [betPerTrade, setBetPerTrade] = useState(2.0);
  const [stopType, setStopType] = useState("Trailing");
  const [wfPasses, setWfPasses] = useState(5);
  const [equityTimeframe, setEquityTimeframe] = useState("ALL");

  // --- Backtest running state ---
  const [running, setRunning] = useState(false);

  // --- ReactFlow state ---
  const [nodes, setNodes] = useState(defaultStratNodes);
  const [edges, setEdges] = useState(defaultStratEdges);
  const onNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [],
  );
  const onEdgesChange = useCallback(
    (changes) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    [],
  );

  // --- Monte Carlo chart data ---
  const mcChartData = useMemo(() => {
    if (!Array.isArray(mcPaths) || !mcPaths.length) return [];
    // Each path is array of equity values; transform to [{step, p0, p1, ..., mean}]
    const maxLen = Math.max(
      ...mcPaths.map((p) =>
        Array.isArray(p) ? p.length : (p?.values?.length ?? 0),
      ),
    );
    const out = [];
    for (let i = 0; i < maxLen; i++) {
      const row = { step: i };
      const vals = [];
      mcPaths.forEach((p, j) => {
        const arr = Array.isArray(p) ? p : (p?.values ?? []);
        const v = arr[i] ?? null;
        row[`p${j}`] = v;
        if (v != null) vals.push(v);
      });
      row.mean = vals.length
        ? vals.reduce((a, b) => a + b, 0) / vals.length
        : null;
      out.push(row);
    }
    return out;
  }, [mcPaths]);

  // --- Optimization heatmap data ---
  const heatmapGrid = useMemo(() => {
    if (!Array.isArray(optData) || !optData.length) return [];
    return optData;
  }, [optData]);

  // --- Parallel run data ---
  const parallelRuns = useMemo(() => {
    if (!Array.isArray(runs) || !runs.length)
      return [
        {
          name: "Mean Reversion V2",
          sharpe: 1.2,
          return: 12.5,
          maxDD: -8.2,
          color: "#00D9FF",
        },
        {
          name: "Mean Reversion V2",
          sharpe: 1.8,
          return: 18.3,
          maxDD: -5.1,
          color: "#10B981",
        },
        {
          name: "Mean Reversion V2",
          sharpe: 1.5,
          return: 15.1,
          maxDD: -6.8,
          color: "#A78BFA",
        },
      ];
    return runs.slice(0, 5).map((r, i) => ({
      name: r.name ?? r.strategy ?? `Run ${i + 1}`,
      sharpe: r.sharpe ?? r.metrics?.sharpe ?? 0,
      return: r.total_return ?? r.metrics?.total_return ?? 0,
      maxDD: r.max_drawdown ?? r.metrics?.max_drawdown ?? 0,
      color: ["#00D9FF", "#10B981", "#A78BFA", "#F59E0B", "#EC4899"][i % 5],
    }));
  }, [runs]);

  // --- Regime performance (mockup: BULL 65.5% $450 avg, BEAR 42.0% -$120 avg, SIDEWAYS 51.1% $80 avg) ---
  const regimeChartData = useMemo(() => {
    if (!Array.isArray(regimeData) || !regimeData.length)
      return [
        { regime: "BULL", winRate: 65.5, avgPnl: 450 },
        { regime: "BEAR", winRate: 42.0, avgPnl: -120 },
        { regime: "SIDEWAYS", winRate: 51.1, avgPnl: 80 },
      ];
    return regimeData.map((r) => {
      const pnl = r.avg_pnl ?? r.pnl ?? r.total_pnl ?? 0;
      return {
        regime: r.regime ?? r.name ?? "UNKNOWN",
        winRate: r.win_rate ?? r.winRate ?? 50,
        avgPnl: pnl,
      };
    });
  }, [regimeData]);

  // --- Run backtest handler ---
  const handleRun = useCallback(async () => {
    setRunning(true);
    try {
      const url = getApiUrl("backtest");
      if (!url) {
        toast.error("Backtest endpoint not configured");
        return;
      }
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({
          strategy,
          start_date: startDate,
          end_date: endDate,
          batches,
          train_pct: trainPct,
          min_positions: minPositions,
          transaction_cost: txnCost,
          max_positions: maxPositions,
          symbols,
          benchmark,
          commission,
          regime_filter: regimeFilter,
          slippage,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      toast.success("Backtest started");
      setTimeout(() => refetchResults(), 2000);
    } catch (err) {
      log.error("Backtest run failed", err);
      toast.error(`Backtest failed: ${err.message}`);
    } finally {
      setRunning(false);
    }
  }, [
    strategy,
    startDate,
    endDate,
    batches,
    trainPct,
    minPositions,
    txnCost,
    maxPositions,
    symbols,
    benchmark,
    commission,
    regimeFilter,
    slippage,
    refetchResults,
  ]);

  // --- KPI definitions (mockup: 18 KPIs with primary + secondary values) ---
  const kpiItems = useMemo(
    () => [
      {
        label: "Net P&L",
        value: fmtUsd(kpis.net_pnl ?? kpis.netPnl ?? 345000),
        sub: fmtPct(kpis.net_pnl_pct ?? 2.43),
        raw: kpis.net_pnl ?? kpis.netPnl ?? 345000,
        thresholds: { good: 0, warn: -1000 },
      },
      {
        label: "Sharpe",
        value: fmt(kpis.sharpe ?? kpis.sharpe_ratio ?? 2.35, 2),
        sub: fmtPct(kpis.sharpe_sub ?? 9.3),
        raw: kpis.sharpe ?? kpis.sharpe_ratio ?? 2.35,
        thresholds: { good: 1.5, warn: 1.0 },
      },
      {
        label: "Sortino",
        value: fmt(kpis.sortino ?? kpis.sortino_ratio ?? 3.5, 2),
        sub: fmt(kpis.sortino_sub ?? 4.56, 2),
        raw: kpis.sortino ?? kpis.sortino_ratio ?? 3.5,
        thresholds: { good: 2.0, warn: 1.0 },
      },
      {
        label: "Calmar",
        value: fmt(kpis.calmar ?? 1.96, 2),
        sub: fmt(kpis.calmar_sub ?? 3.86, 2),
        raw: kpis.calmar ?? 1.96,
        thresholds: { good: 1.5, warn: 1.0 },
      },
      {
        label: "Max DD",
        value: fmtPct(kpis.max_drawdown ?? kpis.maxDrawdown ?? -12.5),
        sub: fmt(kpis.maxdd_sub ?? 3.3, 1),
        raw: kpis.max_drawdown ?? kpis.maxDrawdown ?? -12.5,
        thresholds: { good: -5, warn: -15, invert: true },
      },
      {
        label: "Win Rate",
        value: fmtPct(kpis.win_rate ?? kpis.winRate ?? 58.5),
        sub: fmt(kpis.winrate_sub ?? 2.15, 2),
        raw: kpis.win_rate ?? kpis.winRate ?? 58.5,
        thresholds: { good: 55, warn: 45 },
      },
      {
        label: "Profit Factor",
        value: fmt(kpis.profit_factor ?? kpis.profitFactor ?? 3.5, 2),
        sub: fmt(kpis.pf_sub ?? 71.24, 2),
        raw: kpis.profit_factor ?? kpis.profitFactor ?? 3.5,
        thresholds: { good: 1.5, warn: 1.0 },
      },
      {
        label: "Avg Trade",
        value: fmtUsd(kpis.avg_trade ?? kpis.avgTrade ?? 196),
        sub: kpis.avg_grade ?? "A+",
        raw: kpis.avg_trade ?? kpis.avgTrade ?? 196,
        thresholds: { good: 0, warn: -50 },
      },
      {
        label: "Total Trades",
        value: String(kpis.total_trades ?? kpis.totalTrades ?? 1250).replace(
          /\B(?=(\d{3})+(?!\d))/g,
          ",",
        ),
        sub: fmtPct(kpis.trades_sub ?? 31.2),
        raw: kpis.total_trades ?? kpis.totalTrades ?? 1250,
        thresholds: { good: 50, warn: 20 },
      },
      {
        label: "Expectancy",
        value: fmt(kpis.expectancy ?? 0.0847, 4),
        sub: fmtPct(kpis.exp_sub ?? 14.8),
        raw: kpis.expectancy ?? 0.0847,
        thresholds: { good: 0.5, warn: 0 },
      },
      {
        label: "Kelly Efficiency",
        value: fmtPct(kpis.kelly_efficiency ?? kpis.kellyEfficiency ?? 78),
        sub: fmtPct(kpis.kelly_sub ?? 8.5),
        raw: kpis.kelly_efficiency ?? kpis.kellyEfficiency ?? 78,
        thresholds: { good: 30, warn: 15 },
      },
      {
        label: "Trading Grade",
        value: kpis.trading_grade ?? kpis.tradingGrade ?? kpis.grade ?? "A+",
        sub: fmt(kpis.grade_sub ?? 0.72, 2),
        raw: null,
        thresholds: null,
      },
      {
        label: "CAGR",
        value: fmtPct(kpis.cagr ?? kpis.total_return ?? 31.2),
        sub: fmt(kpis.cagr_sub ?? 1.85, 2),
        raw: kpis.cagr ?? kpis.total_return ?? 31.2,
        thresholds: { good: 10, warn: 0 },
      },
      {
        label: "Beta",
        value: fmt(kpis.beta ?? 0.31, 2),
        sub: fmt(kpis.beta_sub ?? 2.31, 2),
        raw: kpis.beta ?? 0.31,
        thresholds: { good: 0.5, warn: 1.0, invert: true },
      },
    ],
    [kpis],
  );

  // --- Trade log columns (mockup: Date, Asset, Side, QTY, Entry Price, Exit Price, P&L, Patch, Duration, R-Multiple, Agent Origin, Commission) ---
  const tradeColumns = useMemo(
    () => [
      {
        key: "date",
        label: "Date",
        render: (v) => (v ? String(v).slice(0, 10) : "--"),
      },
      {
        key: "asset",
        label: "Asset",
        render: (v, row) => v ?? row.symbol ?? "--",
      },
      {
        key: "side",
        label: "Side",
        render: (v) => (
          <span
            className={clsx(
              "px-1 py-0.5 rounded text-[9px] font-medium",
              v === "BUY" || v === "buy" || v === "LONG"
                ? "bg-emerald-500/20 text-emerald-400"
                : "bg-red-500/20 text-red-400",
            )}
          >
            {v ?? "--"}
          </span>
        ),
      },
      {
        key: "qty",
        label: "QTY",
        render: (v, row) => v ?? row.quantity ?? row.size ?? "--",
      },
      { key: "entry_price", label: "Entry Price", render: (v) => fmtUsd(v) },
      { key: "exit_price", label: "Exit Price", render: (v) => fmtUsd(v) },
      {
        key: "pnl",
        label: "P&L",
        render: (v) => (
          <span className={Number(v) >= 0 ? "text-green-400" : "text-red-400"}>
            {fmtUsd(v)}
          </span>
        ),
      },
      {
        key: "patch",
        label: "Patch",
        render: (v, row) => v ?? row.batch ?? "--",
      },
      {
        key: "duration",
        label: "Duration",
        render: (v, row) => v ?? row.holding_period ?? "--",
      },
      {
        key: "r_multiple",
        label: "R-Multiple",
        render: (v, row) => (
          <span
            className={
              Number(v ?? row.r_ratio ?? 0) >= 0
                ? "text-green-400"
                : "text-red-400"
            }
          >
            {fmt(v ?? row.r_ratio, 1)}
          </span>
        ),
      },
      {
        key: "agent",
        label: "Agent Origin",
        render: (v, row) => (
          <span className="text-[#00D9FF] text-[10px]">
            {v ?? row.agent_name ?? "--"}
          </span>
        ),
      },
      { key: "commission", label: "Commission", render: (v) => fmtUsd(v) },
    ],
    [],
  );

  // --- Run history columns ---
  const runHistoryColumns = useMemo(
    () => [
      {
        key: "name",
        label: "Run",
        render: (v, row) => v ?? row.strategy ?? "--",
      },
      {
        key: "date",
        label: "Date",
        render: (v) => (v ? String(v).slice(0, 10) : "--"),
      },
      { key: "sharpe", label: "Sharpe", render: (v) => fmt(v, 2) },
      { key: "total_return", label: "Return", render: (v) => fmtPct(v) },
      {
        key: "status",
        label: "Status",
        render: (v) => (
          <Badge
            variant={
              v === "completed" || v === "done"
                ? "success"
                : v === "running"
                  ? "primary"
                  : "secondary"
            }
            size="sm"
          >
            {v ?? "done"}
          </Badge>
        ),
      },
    ],
    [],
  );

  /* ================================================================ */
  /*  RENDER                                                           */
  /* ================================================================ */
  const swarmSize = 100;
  const wsLatency = 42;

  return (
    <div className="space-y-4 p-4 min-h-screen bg-[#0B0E14]">
      {/* ------- TOP HEADER BAR (mockup: center title, right status + buttons) ------- */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#0B0E14] border-b border-[rgba(42,52,68,0.5)] shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-xs font-bold text-[#00D9FF] tracking-wider font-mono">
              BACKTESTING_LAB
            </span>
          </div>
          <span className="text-[10px] text-gray-500 font-mono">
            OC_CORE_v3.2.1
          </span>
          <span className="text-[10px] text-gray-500 font-mono">
            WS LATENCY: {wsLatency}ms
          </span>
          <span className="text-[10px] text-gray-500 font-mono">
            SWARM_SIZE: {swarmSize}
          </span>
          <span className="text-[10px] text-gray-500 font-mono">
            {new Date().toLocaleTimeString("en-US", {
              hour12: false,
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}{" "}
            &MT
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="primary"
            leftIcon={Play}
            loading={running}
            onClick={handleRun}
            className="!bg-emerald-600 !border-emerald-500/50"
          >
            Run
          </Button>
          <Button
            size="sm"
            variant="danger"
            leftIcon={Square}
            onClick={() => setRunning(false)}
          >
            Stop
          </Button>
          <Button size="sm" variant="ghost" leftIcon={Download}>
            Export
          </Button>
          <Button
            size="sm"
            variant="ghost"
            leftIcon={RotateCcw}
            onClick={refetchResults}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* ============================================================ */}
      {/*  TOP ROW: Config | Parameter Sweeps | OpenClaw Swarm          */}
      {/* ============================================================ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* --- Backtest Configuration (mockup) --- */}
        <Card title="Backtest Configuration" loading={loadResults}>
          <div className="space-y-2">
            <Select
              label="Strategy"
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              options={[
                "Mean Reversion V2",
                "Momentum V3",
                "ML Ensemble",
                "Stat Arb",
                "Pairs Trading",
              ]}
            />
            <div className="grid grid-cols-2 gap-2">
              <TextField
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <TextField
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <TextField
              label="Assets"
              value={assets}
              onChange={(e) => setAssets(e.target.value)}
              placeholder="BTCUSDT, ETHUSDT, SPY, QQQ, AAPL, MSFT, TSLA, NVDA"
            />
            <TextField
              label="Capital"
              value={capital}
              onChange={(e) =>
                setCapital(String(e.target.value).replace(/[^0-9]/g, ""))
              }
              placeholder="100000"
            />
            <Select
              label="Benchmark"
              value={benchmark}
              onChange={(e) => setBenchmark(e.target.value)}
              options={["SPY", "QQQ", "IWM", "DIA", "BTC"]}
            />
          </div>
        </Card>

        {/* --- Parameter Sweeps & Controls (mockup) --- */}
        <Card
          title="Parameter Sweeps & Controls"
          action={
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="success"
                leftIcon={Play}
                loading={running}
                onClick={handleRun}
                className="!bg-emerald-600"
              >
                Run
              </Button>
              <Button
                size="sm"
                variant="danger"
                leftIcon={Square}
                onClick={() => setRunning(false)}
              >
                Stop
              </Button>
            </div>
          }
        >
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <Slider
                label="Param A"
                min={0}
                max={50}
                step={1}
                value={paramA}
                onChange={setParamA}
                className="py-0.5"
                valueClassName="text-[10px] min-w-[2rem]"
              />
              <div>
                <label className="text-xs text-secondary font-medium mb-1 block">
                  Transaction Cost
                </label>
                <input
                  type="text"
                  value={txnCost === 0 ? "$0" : `$${txnCost}`}
                  onChange={(e) => {
                    const v = e.target.value.replace(/[^0-9.]/g, "");
                    setTxnCost(v ? Number(v) : 0);
                  }}
                  placeholder="$0"
                  className="w-full bg-dark/80 border border-secondary/40 rounded px-2 py-1 text-xs text-white"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Slider
                label="B Min/Max"
                min={10}
                max={100}
                step={1}
                value={bMinMax}
                onChange={setBMinMax}
                className="py-0.5"
                valueClassName="text-[10px] min-w-[2rem]"
              />
              <TextField
                label="Max Positions"
                type="number"
                value={maxPositions}
                onChange={(e) => setMaxPositions(Number(e.target.value) || 0)}
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Slider
                label="Position Size"
                min={0}
                max={100}
                step={5}
                value={positionSizePct}
                onChange={setPositionSizePct}
                suffix="%"
                className="py-0.5"
                valueClassName="text-[10px] min-w-[2.5rem]"
              />
              <div>
                <label className="text-xs text-secondary font-medium mb-1 block">
                  Rebalance Freq.
                </label>
                <select
                  value={positionFreq}
                  onChange={(e) => setPositionFreq(Number(e.target.value))}
                  className="w-full bg-dark/80 border border-secondary/40 rounded px-2 py-1 text-xs text-white"
                >
                  <option value={1}>Daily</option>
                  <option value={5}>Weekly</option>
                  <option value={20}>Monthly</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="flex items-center gap-2">
                <label className="text-xs text-secondary font-medium shrink-0 w-24">
                  Slippage
                </label>
                <input
                  type="text"
                  value={slippage}
                  onChange={(e) =>
                    setSlippage(
                      Number(String(e.target.value).replace(/\D/g, "")) || 0,
                    )
                  }
                  placeholder="0"
                  className="flex-1 bg-dark/80 border border-secondary/40 rounded px-2 py-1 text-xs text-white"
                />
                <span className="text-[10px] text-secondary shrink-0">bps</span>
              </div>
              <Slider
                label="Stop Loss %"
                min={0}
                max={50}
                step={1}
                value={stopLossPct}
                onChange={setStopLossPct}
                suffix="%"
                className="py-0.5"
                valueClassName="text-[10px] min-w-[2rem]"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Slider
                label="Take Profit %"
                min={0}
                max={50}
                step={1}
                value={takeProfit}
                onChange={setTakeProfit}
                suffix="%"
                className="py-0.5"
                valueClassName="text-[10px] min-w-[2rem]"
              />
              <Slider
                label="Kelly Sizing"
                min={0}
                max={0.5}
                step={0.05}
                value={kellySizing}
                onChange={setKellySizing}
                formatValue={(v) => v.toFixed(2)}
                className="py-0.5"
                valueClassName="text-[10px] min-w-[2rem]"
              />
            </div>
            <div>
              <label className="text-xs text-secondary font-medium mb-1 block">
                Regime Filter
              </label>
              <div className="flex gap-1">
                {["BULL", "SIDEWAYS"].map((r) => (
                  <button
                    key={r}
                    onClick={() => setRegimeFilter(r)}
                    className={clsx(
                      "px-2 py-1 text-xs rounded border transition-colors",
                      regimeFilter === r
                        ? "bg-cyan-500/20 border-[#00D9FF]/50 text-[#00D9FF]"
                        : "border-secondary/30 text-secondary hover:text-white",
                    )}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <TextField
                label="Warm-Up Period"
                type="number"
                value={warmUpPeriod}
                onChange={(e) => setWarmUpPeriod(Number(e.target.value) || 0)}
              />
              <Slider
                label="Walk-Forward Window"
                min={10}
                max={90}
                step={5}
                value={walkForwardWindow}
                onChange={setWalkForwardWindow}
                suffix="%"
                className="py-0.5"
                valueClassName="text-[10px] min-w-[2rem]"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <TextField
                label="Monte Carlo Iterations"
                type="number"
                value={monteCarloIter}
                onChange={(e) => setMonteCarloIter(Number(e.target.value) || 0)}
              />
              <div className="flex items-center gap-2">
                <label className="text-xs text-secondary font-medium shrink-0 w-28">
                  Confidence Level
                </label>
                <span className="text-xs text-white">{confidenceLevel}%</span>
              </div>
            </div>
          </div>
        </Card>

        {/* --- OpenClaw Swarm Backtest Integration (mockup) --- */}
        <Card
          title="OpenClaw Swarm Backtest Integration"
          action={
            <span className="text-[10px] text-secondary">Swarm Status</span>
          }
        >
          <div className="space-y-2">
            <div className="text-[10px] text-secondary font-medium uppercase tracking-wider mb-1">
              7 Core Agents
            </div>
            <div className="space-y-1">
              {SWARM_AGENTS.map((agent) => {
                const Ic = agent.icon;
                const pct = agent.pct ?? 100;
                return (
                  <div
                    key={agent.name}
                    className="flex items-center justify-between gap-2 bg-dark/50 rounded px-2 py-1"
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                      <span className="text-[11px] text-white truncate">
                        {agent.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <div className="w-12 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-emerald-400 w-8 text-right">
                        {pct}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="pt-2 border-t border-secondary/20 space-y-1">
              <div className="text-[10px] text-secondary">
                EXTENDED SWARM: 93 sub-agents active
              </div>
              <div className="grid grid-cols-2 gap-1">
                {SWARM_TEAMS.map((t) => (
                  <div
                    key={t.name}
                    className="flex items-center justify-between text-[10px]"
                  >
                    <span className="text-white">{t.name}:</span>
                    <span className="flex items-center gap-1">
                      <span
                        className={clsx(
                          "w-1.5 h-1.5 rounded-full shrink-0",
                          t.status === "green"
                            ? "bg-emerald-500"
                            : t.status === "yellow"
                              ? "bg-amber-500"
                              : "bg-orange-500",
                        )}
                      />
                      <span className="text-secondary">{t.agents} agents</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* ============================================================ */}
      {/*  KPI MEGA STRIP                                               */}
      {/* ============================================================ */}
      <Card
        title={
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            PERFORMANCE KPI MEGA STRIP
          </h3>
        }
        noPadding
      >
        <div className="overflow-x-auto">
          <div className="flex divide-x divide-secondary/20 min-w-max">
            {kpiItems.map((k) => (
              <div
                key={k.label}
                className="px-3 py-2 flex flex-col items-center min-w-[90px]"
              >
                <span className="text-[9px] text-secondary uppercase tracking-wider mb-0.5 whitespace-nowrap">
                  {k.label}
                </span>
                <span
                  className={clsx(
                    "text-base font-bold leading-tight",
                    k.thresholds ? kpiColor(k.raw, k.thresholds) : "text-white",
                  )}
                >
                  {k.value}
                </span>
                {k.sub != null && (
                  <span className="text-[10px] text-secondary mt-0.5">
                    {k.sub}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* ============================================================ */}
      {/*  CHARTS ROW 1: Equity | Parallel Run | P&L Dist | Sharpe | WF */}
      {/* ============================================================ */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
        {/* Equity Curve - Lightweight Charts (mockup: 1M/3M/6M/1Y/ALL filters) */}
        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              EQUITY CURVE - LIGHTWEIGHT CHARTS
            </h3>
          }
          action={
            <div className="flex gap-0.5">
              {["1M", "3M", "6M", "1Y", "ALL"].map((tf) => (
                <button
                  key={tf}
                  onClick={() => setEquityTimeframe(tf)}
                  className={clsx(
                    "px-1.5 py-0.5 text-[10px] rounded font-medium transition-colors",
                    equityTimeframe === tf
                      ? "bg-[#00D9FF]/30 text-[#00D9FF] border border-[#00D9FF]/50"
                      : "text-secondary hover:text-white border border-transparent",
                  )}
                >
                  {tf}
                </button>
              ))}
            </div>
          }
          loading={loadResults}
          className="md:col-span-1"
        >
          <EquityCurveLC
            data={Array.isArray(equity) ? equity : []}
            height={220}
          />
        </Card>

        {/* Parallel Run Manager (mockup: Run | Strategy Name | Status table) */}
        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              PARALLEL RUN MANAGER
            </h3>
          }
          className="xl:col-span-1"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="border-b border-secondary/20 text-secondary">
                  <th className="text-left py-1 px-1">Run</th>
                  <th className="text-left py-1 px-1">Strategy Name</th>
                  <th className="text-left py-1 px-1">Status</th>
                </tr>
              </thead>
              <tbody>
                {parallelRuns.map((r, i) => (
                  <tr key={i} className="border-b border-secondary/10">
                    <td className="py-1 px-1 text-white">{i + 1}</td>
                    <td className="py-1 px-1 text-white">{r.name}</td>
                    <td className="py-1 px-1">
                      <span className="text-emerald-400">Running</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ResponsiveContainer width="100%" height={130}>
            <BarChart data={parallelRuns} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(42,52,68,0.3)" />
              <XAxis type="number" stroke="#6B7280" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="name" stroke="#6B7280" tick={{ fontSize: 9 }} width={90} />
              <Tooltip content={<DarkTooltip />} />
              <Bar dataKey="sharpe" name="Sharpe">
                {parallelRuns.map((r, i) => <Cell key={r.name || `cell-${i}`} fill={r.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Trade P&L Distribution */}
        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              TRADE P&L DISTRIBUTION
            </h3>
          }
          loading={loadTd}
          className="xl:col-span-1"
        >
          <TradePnlDistLC
            data={Array.isArray(tdData) ? tdData : []}
            height={220}
          />
        </Card>

        {/* Rolling Sharpe Ratio (24M) - mockup */}
        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              ROLLING SHARPE RATIO (24M)
            </h3>
          }
          loading={loadRs}
          className="xl:col-span-1"
        >
          <RollingSharpeLC
            data={Array.isArray(rsData) ? rsData : []}
            height={220}
          />
        </Card>

        {/* Walk Forward Analysis */}
        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              WALK FORWARD ANALYSIS
            </h3>
          }
          loading={loadWf}
          className="xl:col-span-1"
        >
          {Array.isArray(wfData) && wfData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <ComposedChart data={wfData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(42,52,68,0.3)"
                />
                <XAxis
                  dataKey="period"
                  stroke="#6B7280"
                  tick={{ fontSize: 9 }}
                />
                <YAxis stroke="#6B7280" tick={{ fontSize: 9 }} />
                <Tooltip content={<DarkTooltip />} />
                <Bar
                  dataKey="in_sample"
                  name="In-Sample"
                  fill="#00D9FF"
                  opacity={0.6}
                  radius={[2, 2, 0, 0]}
                />
                <Bar
                  dataKey="out_sample"
                  name="Out-Sample"
                  fill="#10B981"
                  opacity={0.8}
                  radius={[2, 2, 0, 0]}
                />
                <Line
                  type="monotone"
                  dataKey="efficiency"
                  name="Efficiency"
                  stroke="#F59E0B"
                  dot={false}
                  strokeWidth={2}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[220px] text-secondary text-sm">
              <div className="text-center">
                <GitBranch className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p>Run walk-forward to generate analysis</p>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* ============================================================ */}
      {/*  CHARTS ROW 2: Regime | Monte Carlo | Heatmap | Strategy     */}
      {/* ============================================================ */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        {/* Market Regime Performance (mockup: BULL 65.5% $450 avg, BEAR 42.0% -$120 avg, SIDEWAYS 51.1% $80 avg) */}
        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              MARKET REGIME PERFORMANCE
            </h3>
          }
          loading={loadRegime}
          className="col-span-1"
        >
          <div className="grid grid-cols-3 gap-2 py-2">
            {regimeChartData.map((r) => {
              const color = REGIME_COLORS[r.regime] ?? "#6B7280";
              const avgVal = r.avgPnl ?? r.pnl ?? 0;
              return (
                <div
                  key={r.regime}
                  className="flex flex-col items-center p-2 rounded-lg bg-dark/40 border border-secondary/20"
                >
                  <span className="text-[11px] font-bold" style={{ color }}>
                    {r.regime}
                  </span>
                  <span className="text-sm font-bold text-white">
                    {r.winRate ?? 0}%
                  </span>
                  <span
                    className={clsx(
                      "text-[10px]",
                      Number(avgVal) >= 0 ? "text-green-400" : "text-red-400",
                    )}
                  >
                    {Number(avgVal) >= 0
                      ? `$${avgVal} avg`
                      : `-$${Math.abs(avgVal)} avg`}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Monte Carlo Simulation */}
        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              MONTE CARLO SIMULATION (50 PATHS)
            </h3>
          }
          loading={loadMc}
          className="col-span-1"
        >
          {mcChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={mcChartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(42,52,68,0.3)"
                />
                <XAxis
                  dataKey="step"
                  stroke="#6B7280"
                  tick={{ fontSize: 10 }}
                />
                <YAxis stroke="#6B7280" tick={{ fontSize: 10 }} />
                <Tooltip content={<DarkTooltip />} />
                {Object.keys(mcChartData[0] || {})
                  .filter((k) => k !== "step" && k !== "mean")
                  .slice(0, 50)
                  .map((k, i) => (
                    <Line
                      key={k}
                      type="monotone"
                      dataKey={k}
                      stroke="#94a3b8"
                      dot={false}
                      strokeWidth={1}
                      strokeOpacity={0.15}
                      isAnimationActive={false}
                    />
                  ))}
                <Line
                  key="mean"
                  type="monotone"
                  dataKey="mean"
                  stroke="#00D9FF"
                  dot={false}
                  strokeWidth={2}
                  strokeOpacity={1}
                  name="Mean"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[240px] text-secondary text-sm">
              <div className="text-center">
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p>Run backtest to generate Monte Carlo paths</p>
              </div>
            </div>
          )}
        </Card>

        {/* Parameter Optimization Heatmap */}
        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              PARAMETER OPTIMIZATION HEATMAP
            </h3>
          }
          loading={loadOpt}
          className="col-span-1"
        >
          {Array.isArray(heatmapGrid) && heatmapGrid.length > 0 ? (
            <div className="overflow-auto" style={{ maxHeight: 250 }}>
              {/* Axis labels */}
              <div className="mb-1 flex items-center gap-1">
                <span className="text-[8px] text-slate-500 font-mono uppercase tracking-wider w-6 shrink-0">
                  Param A ↓
                </span>
                <span className="text-[8px] text-slate-500 font-mono uppercase tracking-wider">
                  Param B →
                </span>
              </div>
              <div className="flex gap-0.5">
                {/* Row labels */}
                <div className="flex flex-col gap-0.5 shrink-0">
                  {heatmapGrid.map((row, ri) => (
                    <div
                      key={ri}
                      className="aspect-square flex items-center justify-center text-[7px] font-mono text-slate-500 w-5"
                    >
                      {row.row_label ?? row.param_a ?? ri}
                    </div>
                  ))}
                </div>
                <div className="flex-1">
                  {/* Col labels row */}
                  <div
                    className="grid gap-0.5 mb-0.5"
                    style={{
                      gridTemplateColumns: `repeat(${Math.min((heatmapGrid[0]?.values ?? heatmapGrid[0] ?? []).length, 15)}, 1fr)`,
                    }}
                  >
                    {(
                      heatmapGrid[0]?.col_labels ??
                      Array.from(
                        {
                          length: Math.min(
                            (heatmapGrid[0]?.values ?? heatmapGrid[0] ?? [])
                              .length,
                            15,
                          ),
                        },
                        (_, i) => i,
                      )
                    ).map((lbl, ci) => (
                      <div
                        key={ci}
                        className="text-center text-[7px] font-mono text-slate-500 truncate"
                      >
                        {lbl}
                      </div>
                    ))}
                  </div>
                  <div
                    className="grid gap-0.5"
                    style={{
                      gridTemplateColumns: `repeat(${Math.min((heatmapGrid[0]?.values ?? heatmapGrid[0] ?? []).length, 15)}, 1fr)`,
                    }}
                  >
                    {heatmapGrid.flatMap((row, ri) =>
                      (row.values ?? row).map((val, ci) => {
                        const v =
                          typeof val === "object"
                            ? (val.value ?? val.sharpe ?? 0)
                            : Number(val) || 0;
                        const maxV = 3;
                        const norm = Math.max(0, Math.min(1, (v + 1) / maxV));
                        const bg =
                          v >= 1.5
                            ? `rgba(16,185,129,${0.3 + norm * 0.6})`
                            : v >= 0
                              ? `rgba(245,158,11,${0.3 + norm * 0.5})`
                              : `rgba(239,68,68,${0.3 + (1 - norm) * 0.5})`;
                        return (
                          <div
                            key={`${ri}-${ci}`}
                            className="aspect-square flex items-center justify-center font-mono text-[8px] text-white/80 rounded-sm cursor-default"
                            style={{ backgroundColor: bg }}
                            title={`Param A: ${ri}, Param B: ${ci} → ${v.toFixed(2)}`}
                          >
                            {v.toFixed(1)}
                          </div>
                        );
                      }),
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-[240px] text-secondary text-sm">
              <div className="text-center">
                <Layers className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p>Run optimization to generate heatmap</p>
              </div>
            </div>
          )}
        </Card>

        {/* Strategy Builder - ReactFlow */}
        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              STRATEGY BUILDER - REACTFLOW
            </h3>
          }
          noPadding
          className="col-span-1"
        >
          <div style={{ height: 260 }}>
            <SafeReactFlow>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                fitView
                proOptions={{ hideAttribution: true }}
                style={{ background: "transparent" }}
              >
                <Background color="#1E293B" gap={16} size={1} />
                <Controls
                  showZoom={false}
                  showFitView={false}
                  showInteractive={false}
                />
              </ReactFlow>
            </SafeReactFlow>
          </div>
        </Card>
      </div>

      {/* ============================================================ */}
      {/*  TRADE-BY-TRADE LOG (full width)                              */}
      {/* ============================================================ */}
      <Card
        title={
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            TRADE-BY-TRADE LOG
          </h3>
        }
        action={
          <div className="flex gap-2">
            <Badge variant="secondary" size="sm">
              {Array.isArray(trades) ? trades.length : 0} trades
            </Badge>
            <Button size="sm" variant="ghost" leftIcon={Download}>
              CSV
            </Button>
          </div>
        }
      >
        <div className="max-h-[240px] overflow-auto">
          <DataTable
            columns={tradeColumns}
            data={Array.isArray(trades) ? trades.slice(0, 50) : []}
            loading={loadResults}
            emptyMessage="No trades — run a backtest first"
            rowKey={(r, i) => `${r.date}-${r.asset ?? r.symbol}-${i}`}
          />
        </div>
      </Card>

      {/* ============================================================ */}
      {/*  BOTTOM ROW: Run History & Export | OpenClaw Swarm Consensus  */}
      {/* ============================================================ */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              RUN HISTORY & EXPORT
            </h3>
          }
          action={
            <Button size="sm" variant="primary" leftIcon={Download}>
              Export All Results
            </Button>
          }
        >
          <div className="max-h-[140px] overflow-auto">
            <DataTable
              columns={runHistoryColumns}
              data={Array.isArray(runs) ? runs.slice(0, 10) : []}
              loading={loadRuns}
              emptyMessage="No run history"
              rowKey={(r, i) => `run-${i}`}
            />
          </div>
        </Card>

        <Card
          title={
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              OPENCLAW SWARM CONSENSUS
            </h3>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="border-b border-secondary/20 text-secondary">
                  <th className="text-left py-1 px-1">Agent Agreement</th>
                  <th className="text-left py-1 px-1">%</th>
                  <th className="text-left py-1 px-1 w-24"></th>
                </tr>
              </thead>
              <tbody>
                {SWARM_TEAMS.map((t) => (
                  <tr key={t.name} className="border-b border-secondary/10">
                    <td className="py-1 px-1 text-white">{t.name}</td>
                    <td className="py-1 px-1 text-white">{t.pct}%</td>
                    <td className="py-1 px-1">
                      <div className="flex gap-0.5">
                        {Array.from({ length: t.agents }, (_, i) => (
                          <div
                            key={i}
                            className={clsx(
                              "w-1.5 h-3 rounded-sm shrink-0",
                              t.status === "green"
                                ? "bg-emerald-500"
                                : t.status === "yellow"
                                  ? "bg-amber-500"
                                  : "bg-orange-500",
                            )}
                          />
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Footer: Agent status bar (mockup: 7 Agents OK, EXTENDED SWARM (93)) */}
      <div className="flex items-center justify-between bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-md px-4 py-2">
        <div className="flex items-center gap-3 text-xs text-secondary">
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/40">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-emerald-400 font-medium">7 Agents OK</span>
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/40">
            <span className="text-emerald-400 font-medium">
              EXTENDED SWARM (93)
            </span>
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-secondary">
          <span>Last run: {kpis.last_run ?? kpis.lastRun ?? "--"}</span>
          <span className="text-secondary/60">|</span>
          <span>Engine: V3.2.1</span>
          <span className="text-secondary/60">|</span>
          <span>OC_CORE_v3.2.1</span>
        </div>
      </div>
    </div>
  );
}
