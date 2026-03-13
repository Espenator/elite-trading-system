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
/*  Lightweight Charts: Equity Curve (area) + optional SPY benchmark   */
/* ------------------------------------------------------------------ */
function EquityCurveLC({ data = [], benchmarkData = [], height = 220 }) {
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
    if (Array.isArray(benchmarkData) && benchmarkData.length > 0) {
      const benchSeries = chart.addLineSeries({
        color: "#00D9FF",
        lineWidth: 1,
        lineStyle: 2,
        title: "SPY",
      });
      const benchMapped = benchmarkData.map((d) => ({
        time: d.time || d.date || d.x,
        value: d.value ?? d.equity ?? d.y ?? 0,
      }));
      benchSeries.setData(benchMapped);
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
  }, [data, benchmarkData, height]);
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
  const { data: corrRaw, loading: loadCorr } = useApi("backtestCorrelation", {
    pollIntervalMs: 60000,
  });
  const { data: sectorRaw, loading: loadSector } = useApi(
    "backtestSectorExposure",
    { pollIntervalMs: 60000 },
  );
  const { data: ddRaw, loading: loadDd } = useApi("backtestDrawdownAnalysis", {
    pollIntervalMs: 60000,
  });
  const { data: agentsRaw } = useApi("agents", { pollIntervalMs: 30000 });
  const { data: teamsRaw } = useApi("teams", { pollIntervalMs: 30000 });
  const { data: healthRaw } = useApi("system/health", { pollIntervalMs: 10000 });

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
  const swarmAgents = useMemo(() => {
    const list = agentsRaw?.data ?? agentsRaw?.agents ?? agentsRaw ?? [];
    return Array.isArray(list) ? list : [];
  }, [agentsRaw]);
  const swarmTeams = useMemo(() => {
    const list = teamsRaw?.data ?? teamsRaw?.teams ?? teamsRaw ?? [];
    return Array.isArray(list) ? list : [];
  }, [teamsRaw]);
  const benchmarkCurve = useMemo(
    () =>
      results?.benchmark_curve ??
      results?.benchmark_equity ??
      results?.spy_curve ??
      [],
    [results],
  );

  // --- Config state ---
  const [strategy, setStrategy] = useState("Mean Reversion V2");
  const [selectedAgentIds, setSelectedAgentIds] = useState(() => new Set());
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [tradeSortKey, setTradeSortKey] = useState("date");
  const [tradeSortDir, setTradeSortDir] = useState("asc");
  const [sweepPage, setSweepPage] = useState(0);
  const [sweepSortKey, setSweepSortKey] = useState("paramA");
  const [sweepSortDir, setSweepSortDir] = useState("asc");
  const runAbortRef = useRef(null);
  const [progress, setProgress] = useState({ pct: 0, elapsedMs: 0, etaMs: null });
  const progressIntervalRef = useRef(null);
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

  // --- Parallel run data (no fallback; empty when no API data) ---
  const parallelRuns = useMemo(() => {
    if (!Array.isArray(runs) || !runs.length) return [];
    return runs.slice(0, 5).map((r, i) => ({
      name: r.name ?? r.strategy ?? `Run ${i + 1}`,
      sharpe: r.sharpe ?? r.metrics?.sharpe ?? null,
      return: r.total_return ?? r.metrics?.total_return ?? null,
      maxDD: r.max_drawdown ?? r.metrics?.max_drawdown ?? null,
      status: r.status ?? r.state ?? null,
      color: ["#00D9FF", "#10B981", "#A78BFA", "#F59E0B", "#EC4899"][i % 5],
    }));
  }, [runs]);

  // --- Regime performance (no fallback; empty when no API data) ---
  const regimeChartData = useMemo(() => {
    if (!Array.isArray(regimeData) || !regimeData.length) return [];
    return regimeData.map((r) => {
      const pnl = r.avg_pnl ?? r.pnl ?? r.total_pnl ?? null;
      return {
        regime: r.regime ?? r.name ?? "UNKNOWN",
        winRate: r.win_rate ?? r.winRate ?? null,
        avgPnl: pnl,
      };
    });
  }, [regimeData]);

  // --- Flattened parameter sweep rows (for table, 25 per page, sortable) ---
  const SWEEP_PAGE_SIZE = 25;
  const sweepRows = useMemo(() => {
    if (!Array.isArray(heatmapGrid) || !heatmapGrid.length) return [];
    return heatmapGrid.flatMap((row, ri) =>
      (row.values ?? row).map((val, ci) => {
        const v =
          typeof val === "object"
            ? val.value ?? val.sharpe ?? null
            : Number(val) ?? null;
        return {
          paramA: row.row_label ?? row.param_a ?? ri,
          paramB: heatmapGrid[0]?.col_labels?.[ci] ?? ci,
          value: v,
        };
      }),
    );
  }, [heatmapGrid]);
  const sortedSweepRows = useMemo(() => {
    const sorted = [...sweepRows].sort((a, b) => {
      const aVal = a[sweepSortKey];
      const bVal = b[sweepSortKey];
      const cmp =
        typeof aVal === "number" && typeof bVal === "number"
          ? aVal - bVal
          : String(aVal ?? "").localeCompare(String(bVal ?? ""));
      return sweepSortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [sweepRows, sweepSortKey, sweepSortDir]);
  const paginatedSweepRows = useMemo(
    () =>
      sortedSweepRows.slice(
        sweepPage * SWEEP_PAGE_SIZE,
        (sweepPage + 1) * SWEEP_PAGE_SIZE,
      ),
    [sortedSweepRows, sweepPage],
  );
  const sweepTotalPages = Math.max(
    1,
    Math.ceil(sortedSweepRows.length / SWEEP_PAGE_SIZE),
  );

  // --- Sorted trades for table ---
  const sortedTrades = useMemo(() => {
    const list = Array.isArray(trades) ? [...trades] : [];
    list.sort((a, b) => {
      const aVal = a[tradeSortKey] ?? "";
      const bVal = b[tradeSortKey] ?? "";
      const cmp =
        typeof aVal === "number" && typeof bVal === "number"
          ? aVal - bVal
          : String(aVal).localeCompare(String(bVal));
      return tradeSortDir === "asc" ? cmp : -cmp;
    });
    return list;
  }, [trades, tradeSortKey, tradeSortDir]);

  // --- Run backtest handler (POST with params, progress, abort on Cancel) ---
  const handleRun = useCallback(async () => {
    runAbortRef.current = new AbortController();
    const signal = runAbortRef.current.signal;
    setRunning(true);
    setProgress({ pct: 0, elapsedMs: 0, etaMs: null });
    const startTs = Date.now();
    progressIntervalRef.current = setInterval(() => {
      setProgress((p) => ({
        ...p,
        elapsedMs: Date.now() - startTs,
        pct: Math.min(p.pct + 2, 95),
      }));
    }, 800);
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
          agent_ids:
            selectedAgentIds.size > 0
              ? Array.from(selectedAgentIds)
              : undefined,
          param_a: paramA,
          b_min_max: bMinMax,
          position_size_pct: positionSizePct,
          stop_loss_pct: stopLossPct,
          take_profit_pct: takeProfit,
          kelly_sizing: kellySizing,
          warm_up_period: warmUpPeriod,
          walk_forward_window: walkForwardWindow,
          monte_carlo_iterations: monteCarloIter,
        }),
        signal,
      });
      if (signal.aborted) return;
      clearInterval(progressIntervalRef.current);
      setProgress({ pct: 100, elapsedMs: Date.now() - startTs, etaMs: 0 });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      toast.success("Backtest started");
      setTimeout(() => refetchResults(), 2000);
    } catch (err) {
      if (err.name === "AbortError") {
        toast.info("Backtest cancelled");
      } else {
        log.error("Backtest run failed", err);
        toast.error(`Backtest failed: ${err.message}`);
      }
    } finally {
      clearInterval(progressIntervalRef.current);
      setRunning(false);
      setProgress({ pct: 0, elapsedMs: 0, etaMs: null });
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
    selectedAgentIds,
    paramA,
    bMinMax,
    positionSizePct,
    stopLossPct,
    takeProfit,
    kellySizing,
    warmUpPeriod,
    walkForwardWindow,
    monteCarloIter,
    refetchResults,
  ]);

  const handleCancel = useCallback(() => {
    if (runAbortRef.current) runAbortRef.current.abort();
    setRunning(false);
    setProgress({ pct: 0, elapsedMs: 0, etaMs: null });
    clearInterval(progressIntervalRef.current);
  }, []);

  const toggleAgent = useCallback((idOrName) => {
    setSelectedAgentIds((prev) => {
      const next = new Set(prev);
      if (next.has(idOrName)) next.delete(idOrName);
      else next.add(idOrName);
      return next;
    });
  }, []);

  // --- KPI definitions (no fallback numbers; null → "--") ---
  const kpiItems = useMemo(
    () => [
      {
        label: "Net P&L",
        value: fmtUsd(kpis.net_pnl ?? kpis.netPnl),
        sub: fmtPct(kpis.net_pnl_pct),
        raw: kpis.net_pnl ?? kpis.netPnl ?? null,
        thresholds: { good: 0, warn: -1000 },
      },
      {
        label: "Sharpe",
        value: fmt(kpis.sharpe ?? kpis.sharpe_ratio, 2),
        sub: fmtPct(kpis.sharpe_sub),
        raw: kpis.sharpe ?? kpis.sharpe_ratio ?? null,
        thresholds: { good: 1.5, warn: 1.0 },
      },
      {
        label: "Sortino",
        value: fmt(kpis.sortino ?? kpis.sortino_ratio, 2),
        sub: fmt(kpis.sortino_sub, 2),
        raw: kpis.sortino ?? kpis.sortino_ratio ?? null,
        thresholds: { good: 2.0, warn: 1.0 },
      },
      {
        label: "Calmar",
        value: fmt(kpis.calmar, 2),
        sub: fmt(kpis.calmar_sub, 2),
        raw: kpis.calmar ?? null,
        thresholds: { good: 1.5, warn: 1.0 },
      },
      {
        label: "Max DD",
        value: fmtPct(kpis.max_drawdown ?? kpis.maxDrawdown),
        sub: fmt(kpis.maxdd_sub, 1),
        raw: kpis.max_drawdown ?? kpis.maxDrawdown ?? null,
        thresholds: { good: -5, warn: -15, invert: true },
      },
      {
        label: "Win Rate",
        value: fmtPct(kpis.win_rate ?? kpis.winRate),
        sub: fmt(kpis.winrate_sub, 2),
        raw: kpis.win_rate ?? kpis.winRate ?? null,
        thresholds: { good: 55, warn: 45 },
      },
      {
        label: "Profit Factor",
        value: fmt(kpis.profit_factor ?? kpis.profitFactor, 2),
        sub: fmt(kpis.pf_sub, 2),
        raw: kpis.profit_factor ?? kpis.profitFactor ?? null,
        thresholds: { good: 1.5, warn: 1.0 },
      },
      {
        label: "Avg Trade",
        value: fmtUsd(kpis.avg_trade ?? kpis.avgTrade),
        sub: kpis.avg_grade ?? null,
        raw: kpis.avg_trade ?? kpis.avgTrade ?? null,
        thresholds: { good: 0, warn: -50 },
      },
      {
        label: "Total Trades",
        value:
          kpis.total_trades != null || kpis.totalTrades != null
            ? String(kpis.total_trades ?? kpis.totalTrades).replace(
                /\B(?=(\d{3})+(?!\d))/g,
                ",",
              )
            : "--",
        sub: fmtPct(kpis.trades_sub),
        raw: kpis.total_trades ?? kpis.totalTrades ?? null,
        thresholds: { good: 50, warn: 20 },
      },
      {
        label: "Expectancy",
        value: fmt(kpis.expectancy, 4),
        sub: fmtPct(kpis.exp_sub),
        raw: kpis.expectancy ?? null,
        thresholds: { good: 0.5, warn: 0 },
      },
      {
        label: "Kelly Efficiency",
        value: fmtPct(kpis.kelly_efficiency ?? kpis.kellyEfficiency),
        sub: fmtPct(kpis.kelly_sub),
        raw: kpis.kelly_efficiency ?? kpis.kellyEfficiency ?? null,
        thresholds: { good: 30, warn: 15 },
      },
      {
        label: "Trading Grade",
        value: kpis.trading_grade ?? kpis.tradingGrade ?? kpis.grade ?? "--",
        sub: fmt(kpis.grade_sub, 2),
        raw: null,
        thresholds: null,
      },
      {
        label: "CAGR",
        value: fmtPct(kpis.cagr ?? kpis.total_return),
        sub: fmt(kpis.cagr_sub, 2),
        raw: kpis.cagr ?? kpis.total_return ?? null,
        thresholds: { good: 10, warn: 0 },
      },
      {
        label: "Beta",
        value: fmt(kpis.beta, 2),
        sub: fmt(kpis.beta_sub, 2),
        raw: kpis.beta ?? null,
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
  const swarmSize =
    Array.isArray(swarmAgents) && swarmAgents.length > 0
      ? swarmAgents.length
      : "--";
  const wsLatency =
    healthRaw?.latency_ms ?? healthRaw?.ws_latency ?? healthRaw?.latency ?? "--";

  return (
    <div className="space-y-4 p-4 min-h-screen bg-[#0a0e1a]">
      {/* ------- TOP HEADER BAR ------- */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#111827] border-b border-[rgba(42,52,68,0.5)] shrink-0 rounded-lg">
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
            WS LATENCY: {typeof wsLatency === "number" ? `${wsLatency}ms` : wsLatency}
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
          {running && (
            <div className="flex items-center gap-2 px-2 py-1 rounded bg-[#0a0e1a] border border-[#00D9FF]/30 min-w-[140px]">
              <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#00D9FF] rounded-full transition-all duration-300"
                  style={{ width: `${progress.pct}%` }}
                />
              </div>
              <span className="text-[10px] text-[#00D9FF] font-mono">
                {progress.pct}%
              </span>
              <span className="text-[10px] text-gray-500">
                {Math.round(progress.elapsedMs / 1000)}s
              </span>
            </div>
          )}
          <Button
            size="sm"
            variant="primary"
            leftIcon={Play}
            loading={running}
            onClick={handleRun}
            className="!bg-emerald-600 !border-emerald-500/50"
          >
            Run Backtest
          </Button>
          <Button
            size="sm"
            variant="danger"
            leftIcon={Square}
            onClick={handleCancel}
            disabled={!running}
          >
            Cancel
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
      {/*  2-COL LAYOUT: LEFT 35% (params) | RIGHT 65% (results)        */}
      {/* ============================================================ */}
      <div className="grid grid-cols-1 lg:grid-cols-[35fr_65fr] gap-4">
        {/* --- LEFT COLUMN: Parameter panels --- */}
        <div className="space-y-3">
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
                "Breakout",
                "Trend Following",
                "Mean Reversion V1",
                "Volatility Breakout",
                "Sector Rotation",
                "Multi-Timeframe",
                "Hybrid ML",
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
            {swarmAgents.length > 0 && (
              <div>
                <label className="text-xs text-secondary font-medium mb-1 block">
                  Agent participants
                </label>
                <div className="max-h-24 overflow-y-auto space-y-1 rounded border border-secondary/30 p-1.5 bg-[#0a0e1a]">
                  {swarmAgents.slice(0, 20).map((a) => {
                    const id = a.id ?? a.name ?? a.agent_id ?? String(a);
                    const name = typeof a === "object" ? a.name ?? a.id ?? "--" : String(a);
                    const checked = selectedAgentIds.has(id);
                    return (
                      <label
                        key={id}
                        className="flex items-center gap-2 cursor-pointer hover:bg-[#00D9FF]/5 rounded px-1 py-0.5"
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleAgent(id)}
                          className="rounded border-secondary/50 text-[#00D9FF]"
                        />
                        <span className="text-[11px] text-white truncate">
                          {name}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </div>
            )}
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
                onClick={handleCancel}
                disabled={!running}
              >
                Cancel
              </Button>
            </div>
          }
        >
          <div className="space-y-2">
            {sortedSweepRows.length > 0 && (
              <div className="mb-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-secondary uppercase">
                    Sweep table ({sortedSweepRows.length} rows)
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => {
                        setSweepSortKey("paramA");
                        setSweepSortDir((d) => (d === "asc" ? "desc" : "asc"));
                      }}
                      className="px-1 py-0.5 text-[10px] rounded border border-secondary/30 hover:bg-[#00D9FF]/10"
                    >
                      Param A {sweepSortKey === "paramA" ? (sweepSortDir === "asc" ? "↑" : "↓") : ""}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setSweepSortKey("paramB");
                        setSweepSortDir((d) => (d === "asc" ? "desc" : "asc"));
                      }}
                      className="px-1 py-0.5 text-[10px] rounded border border-secondary/30 hover:bg-[#00D9FF]/10"
                    >
                      Param B {sweepSortKey === "paramB" ? (sweepSortDir === "asc" ? "↑" : "↓") : ""}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setSweepSortKey("value");
                        setSweepSortDir((d) => (d === "asc" ? "desc" : "asc"));
                      }}
                      className="px-1 py-0.5 text-[10px] rounded border border-secondary/30 hover:bg-[#00D9FF]/10"
                    >
                      Value {sweepSortKey === "value" ? (sweepSortDir === "asc" ? "↑" : "↓") : ""}
                    </button>
                  </div>
                </div>
                <div className="max-h-32 overflow-auto rounded border border-secondary/20 text-[10px]">
                  <table className="w-full">
                    <thead className="bg-[#111827] sticky top-0">
                      <tr>
                        <th className="text-left px-1 py-0.5">Param A</th>
                        <th className="text-left px-1 py-0.5">Param B</th>
                        <th className="text-right px-1 py-0.5">Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedSweepRows.map((row, i) => (
                        <tr key={i} className="border-t border-secondary/10">
                          <td className="px-1 py-0.5 text-white">{row.paramA}</td>
                          <td className="px-1 py-0.5 text-white">{row.paramB}</td>
                          <td className="px-1 py-0.5 text-right text-[#00D9FF]">
                            {row.value != null ? Number(row.value).toFixed(2) : "--"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-[9px] text-secondary">
                    Page {sweepPage + 1} of {sweepTotalPages}
                  </span>
                  <div className="flex gap-0.5">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="!min-w-0 !px-1 !py-0 text-[10px]"
                      onClick={() => setSweepPage((p) => Math.max(0, p - 1))}
                      disabled={sweepPage === 0}
                    >
                      Prev
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="!min-w-0 !px-1 !py-0 text-[10px]"
                      onClick={() =>
                        setSweepPage((p) =>
                          Math.min(sweepTotalPages - 1, p + 1),
                        )
                      }
                      disabled={sweepPage >= sweepTotalPages - 1}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </div>
            )}
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
                    type="button"
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

        {/* --- OpenClaw Swarm Backtest Integration (from API) --- */}
        <Card
          title="OpenClaw Swarm Backtest Integration"
          action={
            <span className="text-[10px] text-secondary">Swarm Status</span>
          }
        >
          <div className="space-y-2">
            <div className="text-[10px] text-secondary font-medium uppercase tracking-wider mb-1">
              Agent participants
            </div>
            {swarmAgents.length === 0 ? (
              <div className="text-[11px] text-secondary py-2">
                No agents loaded. Run from Agent Command Center or refresh.
              </div>
            ) : (
              <div className="space-y-1">
                {swarmAgents.slice(0, 12).map((agent) => {
                  const id = agent.id ?? agent.name ?? agent.agent_id ?? String(agent);
                  const name = typeof agent === "object" ? agent.name ?? agent.id ?? "--" : String(agent);
                  const pct = typeof agent === "object" ? (agent.weight ?? agent.pct ?? agent.confidence ?? null) : null;
                  return (
                    <div
                      key={id}
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelectedAgent(agent)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setSelectedAgent(agent);
                        }
                      }}
                      className="flex items-center justify-between gap-2 bg-[#0a0e1a]/50 rounded px-2 py-1 cursor-pointer hover:bg-[#00D9FF]/10 border border-transparent hover:border-[#00D9FF]/30"
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                        <span className="text-[11px] text-white truncate">
                          {name}
                        </span>
                      </div>
                      {pct != null && (
                        <div className="flex items-center gap-1.5 shrink-0">
                          <div className="w-12 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-500 rounded-full"
                              style={{ width: `${Math.min(100, Number(pct) * 100)}%` }}
                            />
                          </div>
                          <span className="text-[10px] text-emerald-400 w-8 text-right">
                            {typeof pct === "number" ? `${(pct * 100).toFixed(0)}%` : pct}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
            {swarmTeams.length > 0 && (
              <div className="pt-2 border-t border-secondary/20 space-y-1">
                <div className="text-[10px] text-secondary">
                  Teams: {swarmTeams.length} active
                </div>
                <div className="grid grid-cols-2 gap-1">
                  {swarmTeams.slice(0, 4).map((t, i) => (
                    <div
                      key={t.id ?? t.name ?? i}
                      className="flex items-center justify-between text-[10px]"
                    >
                      <span className="text-white truncate">{t.name ?? t.id ?? "--"}:</span>
                      <span className="flex items-center gap-1 shrink-0">
                        <span
                          className={clsx(
                            "w-1.5 h-1.5 rounded-full shrink-0",
                            (t.status ?? t.health) === "green" || t.status === "active"
                              ? "bg-emerald-500"
                              : (t.status ?? t.health) === "yellow"
                                ? "bg-amber-500"
                                : "bg-orange-500",
                          )}
                        />
                        <span className="text-secondary">
                          {t.agents ?? t.agent_count ?? 0} agents
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {selectedAgent && (
              <div className="pt-2 border-t border-secondary/20 rounded bg-[#111827] p-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-medium text-[#00D9FF]">
                    Agent metrics
                  </span>
                  <button
                    type="button"
                    onClick={() => setSelectedAgent(null)}
                    className="text-[10px] text-secondary hover:text-white"
                  >
                    Close
                  </button>
                </div>
                <div className="text-[10px] text-secondary space-y-0.5">
                  <p>
                    {typeof selectedAgent === "object"
                      ? selectedAgent.name ?? selectedAgent.id ?? "--"
                      : String(selectedAgent)}
                  </p>
                  {typeof selectedAgent === "object" &&
                    ["weight", "confidence", "pct", "status"].map(
                      (k) =>
                        selectedAgent[k] != null && (
                          <p key={k}>
                            {k}: {String(selectedAgent[k])}
                          </p>
                        ),
                    )}
                </div>
              </div>
            )}
          </div>
        </Card>
        </div>

        {/* --- RIGHT COLUMN: Results --- */}
        <div className="space-y-3">

      {/* ============================================================ */}
      {/*  KPI MEGA STRIP                                               */}
      {/* ============================================================ */}
      <Card
        title={
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            PERFORMANCE KPI MEGA STRIP
          </span>
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
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              EQUITY CURVE - LIGHTWEIGHT CHARTS
            </span>
          }
          action={
            <div className="flex gap-0.5">
              {["1M", "3M", "6M", "1Y", "ALL"].map((tf) => (
                <button
                  type="button"
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
            benchmarkData={Array.isArray(benchmarkCurve) ? benchmarkCurve : []}
            height={220}
          />
        </Card>

        {/* Parallel Run Manager (mockup: Run | Strategy Name | Status table) */}
        <Card
          title={
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              PARALLEL RUN MANAGER
            </span>
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
                {parallelRuns.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="py-2 px-1 text-secondary text-[10px]">
                      No runs — run a backtest
                    </td>
                  </tr>
                ) : (
                  parallelRuns.map((r, i) => (
                    <tr key={i} className="border-b border-secondary/10">
                      <td className="py-1 px-1 text-white">{i + 1}</td>
                      <td className="py-1 px-1 text-white">{r.name}</td>
                      <td className="py-1 px-1">
                        <span
                          className={
                            r.status === "completed" || r.status === "done"
                              ? "text-emerald-400"
                              : r.status === "running"
                                ? "text-amber-400"
                                : "text-secondary"
                          }
                        >
                          {r.status ?? "—"}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {parallelRuns.length > 0 && (
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
          )}
        </Card>

        {/* Trade P&L Distribution */}
        <Card
          title={
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              TRADE P&L DISTRIBUTION
            </span>
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
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              ROLLING SHARPE RATIO (24M)
            </span>
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
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              WALK FORWARD ANALYSIS
            </span>
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
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              MARKET REGIME PERFORMANCE
            </span>
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
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              MONTE CARLO SIMULATION (50 PATHS)
            </span>
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
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              PARAMETER OPTIMIZATION HEATMAP
            </span>
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
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              STRATEGY BUILDER - REACTFLOW
            </span>
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
                  showZoom
                  showFitView
                  showInteractive
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
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            TRADE-BY-TRADE LOG
          </span>
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
        <div className="max-h-[240px] overflow-auto rounded-md border border-secondary/30 bg-surface">
          <table className="w-full text-sm text-left">
            <thead className="bg-surface border-b border-secondary/30 sticky top-0 z-10">
              <tr>
                {tradeColumns.map((col) => (
                  <th
                    key={col.key}
                    className="px-4 py-3 text-left text-xs font-medium text-cyan-400 uppercase whitespace-nowrap cursor-pointer hover:bg-[#00D9FF]/10 select-none"
                    onClick={() => {
                      setTradeSortKey(col.key);
                      setTradeSortDir((d) => (d === "asc" ? "desc" : "asc"));
                    }}
                  >
                    {col.label}
                    {tradeSortKey === col.key && (
                      <span className="ml-0.5">{tradeSortDir === "asc" ? " ↑" : " ↓"}</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-cyan-500/10">
              {loadResults ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={`skel-${i}`}>
                    {tradeColumns.map((col) => (
                      <td key={col.key} className="px-4 py-3">
                        <div className="h-4 bg-secondary/20 rounded animate-pulse" style={{ width: "60%" }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : sortedTrades.length === 0 ? (
                <tr>
                  <td colSpan={tradeColumns.length} className="px-4 py-8 text-center text-sm text-secondary">
                    No trades — run a backtest first
                  </td>
                </tr>
              ) : (
                sortedTrades.slice(0, 50).map((row, rowIndex) => (
                  <tr key={`${row.date}-${row.asset ?? row.symbol}-${rowIndex}`} className="hover:bg-cyan-500/5">
                    {tradeColumns.map((col) => (
                      <td key={col.key} className="px-4 py-3 text-white/70">
                        {typeof col.render === "function"
                          ? col.render(row[col.key], row, rowIndex)
                          : row[col.key]}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ============================================================ */}
      {/*  BOTTOM ROW: Run History & Export | OpenClaw Swarm Consensus  */}
      {/* ============================================================ */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
        <Card
          title={
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              RUN HISTORY & EXPORT
            </span>
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
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              OPENCLAW SWARM CONSENSUS
            </span>
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
                {swarmTeams.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="py-2 px-1 text-secondary text-[10px]">
                      No team data — load from API
                    </td>
                  </tr>
                ) : (
                  swarmTeams.slice(0, 6).map((t, i) => {
                    const n = t.agents ?? t.agent_count ?? 0;
                    const pct = t.pct ?? t.agreement ?? null;
                    const status = t.status ?? t.health ?? "green";
                    return (
                      <tr key={t.id ?? t.name ?? i} className="border-b border-secondary/10">
                        <td className="py-1 px-1 text-white truncate">{t.name ?? t.id ?? "--"}</td>
                        <td className="py-1 px-1 text-white">{pct != null ? `${pct}%` : "--"}</td>
                        <td className="py-1 px-1">
                          <div className="flex gap-0.5">
                            {Array.from({ length: Math.min(Number(n) || 0, 20) }, (_, j) => (
                              <div
                                key={j}
                                className={clsx(
                                  "w-1.5 h-3 rounded-sm shrink-0",
                                  status === "green" || status === "active"
                                    ? "bg-emerald-500"
                                    : status === "yellow"
                                      ? "bg-amber-500"
                                      : "bg-orange-500",
                                )}
                              />
                            ))}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
      </div>
      </div>

      {/* Footer: Agent status bar (from API) */}
      <div className="flex items-center justify-between bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-md px-4 py-2">
        <div className="flex items-center gap-3 text-xs text-secondary">
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/40">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-emerald-400 font-medium">
              {swarmAgents.length > 0 ? `${swarmAgents.length} Agents` : "Agents"} OK
            </span>
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/40">
            <span className="text-emerald-400 font-medium">
              EXTENDED SWARM ({swarmTeams.length > 0 ? swarmTeams.reduce((acc, t) => acc + (t.agents ?? t.agent_count ?? 0), 0) : "--"})
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
