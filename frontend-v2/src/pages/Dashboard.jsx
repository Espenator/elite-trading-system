// DASHBOARD - Embodier.ai Intelligence Dashboard
// Layout: Top bar (indices + KPIs) → 4 charts → P&L dist → Candidates | Donut | Radar → Correlation | Agents | Signal accuracy
import { useMemo, useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import {
  TrendingUp,
  DollarSign,
  Activity,
  Zap,
  Brain,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Eye,
  Bot,
  Target,
  ShieldCheck,
  Clock,
  LayoutDashboard,
  Gauge,
  TrendingDown,
  Shield,
  Percent,
  Hash,
  Flame,
  RefreshCcw,
  AlertTriangle,
  Radio,
  Newspaper,
  Workflow,
  Users,
  ChevronUp,
  ChevronDown,
  ChevronRight,
  BarChart2,
  PieChart as PieChartIcon,
  Layers,
  Thermometer,
  CircleDot,
  ArrowUp,
  ArrowDown,
  Briefcase,
  LineChart,
  Cpu,
  Wifi,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  AreaChart,
  Area,
  ComposedChart,
  Line,
} from "recharts";
import Card from "../components/ui/Card";
import PageHeader from "../components/ui/PageHeader";
import DataTable from "../components/ui/DataTable";
import Badge from "../components/ui/Badge";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import { toast } from "react-toastify";
import { createChart, ColorType } from "lightweight-charts";

// === POLLING INTERVAL ===
const POLL_MS = 30000;
const OPENCLAW_POLL_MS = 30000;

// === Mock market indices (replace with real feed when available) ===
const MOCK_INDICES = [
  { id: "SPX", label: "SPX", value: "5800.10", change: 0.45 },
  { id: "NDAQ", label: "NDAQ", value: "17850.30", change: -0.12 },
  { id: "DOW", label: "DOW", value: "39120.55", change: 0.33 },
  { id: "BTC", label: "BTC", value: "$71500", change: 1.89 },
  { id: "ETH", label: "ETH", value: "$3850", change: -0.05 },
  { id: "OIL", label: "OIL", value: "$82.30", change: 0.67 },
];

// === StatCard: Gradient stat card ===
function StatCard({
  title,
  value,
  change,
  changeType,
  icon: Icon,
  color,
  onClick,
}) {
  const colors = {
    success: "from-success/20 to-success/5 border-success/30",
    primary: "from-primary/20 to-primary/5 border-primary/30",
    secondary: "from-secondary/20 to-secondary/5 border-secondary/30",
    warning: "from-warning/20 to-warning/5 border-warning/30",
    danger: "from-danger/20 to-danger/5 border-danger/30",
  };
  const iconColors = {
    success: "text-success",
    primary: "text-primary",
    secondary: "text-secondary",
    warning: "text-warning",
    danger: "text-danger",
  };
  return (
    <div
      className={`bg-gradient-to-br ${colors[color]} border rounded-2xl p-5 cursor-pointer hover:scale-[1.02] transition-all`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-secondary">{title}</span>
        {Icon && <Icon className={`w-5 h-5 ${iconColors[color]}`} />}
      </div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      {change && (
        <div
          className={`flex items-center gap-1 text-sm ${changeType === "up" ? "text-success" : "text-danger"}`}
        >
          {changeType === "up" ? (
            <ArrowUpRight className="w-4 h-4" />
          ) : (
            <ArrowDownRight className="w-4 h-4" />
          )}
          {change}
        </div>
      )}
    </div>
  );
}

// === KpiMicroCard: Ultra-dense micro KPI ===
function KpiMicroCard({ label, value, sub, color, icon: Icon, onClick }) {
  const borderMap = {
    cyan: "border-cyan-500/30 hover:border-cyan-500/60 shadow-[0_0_8px_rgba(6,182,212,0.08)]",
    amber:
      "border-amber-500/30 hover:border-amber-500/60 shadow-[0_0_8px_rgba(245,158,11,0.08)]",
    red: "border-red-500/30 hover:border-red-500/60 shadow-[0_0_8px_rgba(239,68,68,0.08)]",
    green:
      "border-emerald-500/30 hover:border-emerald-500/60 shadow-[0_0_8px_rgba(16,185,129,0.08)]",
    purple:
      "border-purple-500/30 hover:border-purple-500/60 shadow-[0_0_8px_rgba(168,85,247,0.08)]",
  };
  const textMap = {
    cyan: "text-cyan-400",
    amber: "text-amber-400",
    red: "text-red-400",
    green: "text-emerald-400",
    purple: "text-purple-400",
  };
  return (
    <div
      className={`bg-[#0B0E14] border rounded-xl p-2.5 cursor-pointer transition-all hover:scale-[1.03] ${borderMap[color] || borderMap.cyan}`}
      onClick={onClick || (() => toast.info(`Drilling into ${label}`))}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-[9px] text-secondary uppercase tracking-wider font-mono truncate">
          {label}
        </span>
        {Icon && (
          <Icon
            className={`w-3 h-3 ${textMap[color] || "text-cyan-400"} shrink-0`}
          />
        )}
      </div>
      <div
        className={`text-sm font-bold font-mono ${textMap[color] || "text-white"} truncate`}
      >
        {value}
      </div>
      {sub && (
        <div className="text-[8px] text-secondary/70 font-mono truncate mt-0.5">
          {sub}
        </div>
      )}
    </div>
  );
}

// === SectorCell: Heatmap cell with HSL-calculated bg ===
function SectorCell({ name, value, momentum }) {
  const pct = Math.min(100, Math.max(0, Math.abs(value)));
  const hue = value >= 0 ? 142 : 0;
  const sat = 60 + (pct / 100) * 30;
  const light = 20 + (pct / 100) * 15;
  return (
    <div
      className="rounded-lg p-2.5 text-center cursor-pointer hover:scale-105 transition-all border border-white/5 hover:border-white/20 shadow-sm"
      style={{ backgroundColor: `hsl(${hue}, ${sat}%, ${light}%)` }}
      onClick={() => toast.info(`Sector deep-dive: ${name}`)}
      title={`${name}: ${value >= 0 ? "+" : ""}${value.toFixed(1)}%`}
    >
      <div className="text-[10px] font-bold text-white/90 truncate">{name}</div>
      <div className="text-xs font-mono font-bold text-white mt-0.5">
        {value >= 0 ? "+" : ""}
        {value.toFixed(1)}%
      </div>
      <div className="text-[9px] mt-0.5">
        {momentum === "up" && (
          <ArrowUp className="w-3 h-3 text-emerald-300 inline" />
        )}
        {momentum === "down" && (
          <ArrowDown className="w-3 h-3 text-red-300 inline" />
        )}
        {momentum === "flat" && (
          <ChevronRight className="w-3 h-3 text-gray-400 inline" />
        )}
      </div>
    </div>
  );
}

// === EquityCurveLW: Lightweight Charts equity curve ===
function EquityCurveLW({ data }) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return;
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0B0E14" },
        textColor: "#9ca3af",
      },
      grid: {
        vertLines: { color: "#1f2937" },
        horzLines: { color: "#1f2937" },
      },
      width: chartContainerRef.current.clientWidth,
      height: 280,
      rightPriceScale: { borderColor: "#374151" },
      timeScale: { borderColor: "#374151", timeVisible: true },
      crosshair: { mode: 0 },
    });
    const areaSeries = chart.addAreaSeries({
      topColor: "rgba(6, 182, 212, 0.4)",
      bottomColor: "rgba(6, 182, 212, 0.0)",
      lineColor: "#06b6d4",
      lineWidth: 2,
    });
    areaSeries.setData(data);
    chart.timeScale().fitContent();
    chartRef.current = chart;
    const handleResize = () => {
      if (chartContainerRef.current)
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data]);
  if (!data || data.length === 0) {
    return (
      <div className="h-[280px] flex items-center justify-center text-secondary text-sm">
        No equity data available
      </div>
    );
  }
  return <div ref={chartContainerRef} className="w-full" />;
}

// === OpenClaw Hooks (real API) ===
function useOpenClawTop(n = 5) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetchTop = useCallback(() => {
    fetch(`${getApiUrl("openclaw")}/top?n=${n}`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [n]);
  useEffect(() => {
    setLoading(true);
    fetchTop();
    const id = setInterval(fetchTop, OPENCLAW_POLL_MS);
    return () => clearInterval(id);
  }, [fetchTop]);
  return { data, loading };
}

function useOpenClawHealth() {
  const [data, setData] = useState(null);
  useEffect(() => {
    let cancelled = false;
    const fetchHealth = () => {
      fetch(`${getApiUrl("openclaw")}/health`, { cache: "no-store" })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => {
          if (!cancelled) setData(d);
        })
        .catch(() => {
          if (!cancelled) setData(null);
        });
    };
    fetchHealth();
    const id = setInterval(fetchHealth, OPENCLAW_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);
  return data;
}

// === MAIN DASHBOARD COMPONENT ===
export default function Dashboard() {
  // --- Real API hooks ---
  const { data: portfolioData, loading: portfolioLoading } = useApi(
    "portfolio",
    { pollIntervalMs: POLL_MS },
  );
  const { data: signalsData, loading: signalsLoading } = useApi("signals", {
    pollIntervalMs: POLL_MS,
  });
  const { data: agentsData, loading: agentsLoading } = useApi("agents", {
    pollIntervalMs: POLL_MS,
  });
  const { data: performanceData } = useApi("performance", {
    pollIntervalMs: POLL_MS,
  });
  const { data: riskData } = useApi("risk", { pollIntervalMs: 60000 });
  const { data: statusData } = useApi("status", { pollIntervalMs: POLL_MS });
  const { data: openclawTop, loading: openclawLoading } = useOpenClawTop();
  const openclawHealth = useOpenClawHealth();

  // --- OpenClaw derived data ---
  const regime = openclawTop?.regime ?? openclawHealth?.regime ?? null;
  const regimeReadme = openclawTop?.regime_readme ?? "";
  const candidates = openclawTop?.candidates ?? [];
  const lastScanTs = openclawHealth?.last_scan_timestamp ?? null;

  // --- Equity curve data for LW Charts ---
  const equityCurveData = useMemo(() => {
    const curve =
      portfolioData?.equityCurve || performanceData?.equityCurve || [];
    return curve
      .map((pt) => ({
        time:
          typeof pt.time === "string"
            ? Math.floor(new Date(pt.time).getTime() / 1000)
            : pt.time,
        value: pt.equity ?? pt.value ?? pt.close ?? 0,
      }))
      .sort((a, b) => a.time - b.time);
  }, [portfolioData, performanceData]);

  // --- Transform positions ---
  const positions = useMemo(() => {
    if (!portfolioData?.positions) return [];
    return portfolioData.positions.map((pos) => {
      const ticker = pos.symbol ?? pos.ticker ?? "--";
      const entry = pos.entryPrice ?? pos.entry ?? 0;
      const current = pos.currentPrice ?? pos.current ?? 0;
      const qty = pos.quantity ?? pos.qty ?? 0;
      const pnlDollars = pos.unrealizedPnL ?? pos.pnl ?? 0;
      let pnlPct = pos.pnlPct;
      if (pnlPct == null && entry && qty)
        pnlPct = (pnlDollars / (entry * qty)) * 100;
      return {
        ticker,
        side: pos.side || "Long",
        entry,
        current,
        qty,
        pnl: pnlDollars,
        pnlPct: pnlPct ?? 0,
      };
    });
  }, [portfolioData]);

  // --- Transform signals ---
  const signals = useMemo(() => {
    if (!signalsData?.signals) return [];
    return signalsData.signals.slice(0, 6).map((sig) => {
      const prob = sig.prob_up ?? sig.probUp ?? 0.5;
      return {
        ticker: sig.symbol,
        type: sig.action || sig.type || "Signal",
        score: Math.round(prob * 100),
        time: sig.timestamp
          ? new Date(sig.timestamp).toLocaleTimeString()
          : "now",
      };
    });
  }, [signalsData]);

  // --- Transform agents ---
  const agents = useMemo(() => {
    if (!agentsData?.agents) return [];
    const iconMap = {
      "Market Data Agent": Eye,
      "Signal Generation Agent": Brain,
      "ML Learning Agent": Cpu,
      "Sentiment Agent": Bot,
      "YouTube Knowledge Agent": Bot,
      "Risk Agent": Shield,
      "Execution Agent": Briefcase,
      "OpenClaw Agent": Target,
    };
    return agentsData.agents.map((agent) => ({
      name: agent.name,
      status: agent.status === "running" ? "active" : agent.status,
      tasks: agent.tasks_completed ?? "--",
      icon: iconMap[agent.name] || Bot,
      uptime: agent.uptime ?? null,
    }));
  }, [agentsData]);

  // --- Computed stats ---
  const portfolioValue =
    performanceData?.portfolioValue ?? portfolioData?.totalValue ?? 0;
  const dailyPnL = performanceData?.dailyPnL ?? portfolioData?.dailyPnL ?? 0;
  const totalPnLPct = performanceData?.totalReturnPct ?? 0;
  const winRate = performanceData?.winRate ?? 0;
  const sharpe = riskData?.sharpeRatio ?? performanceData?.sharpeRatio ?? 0;
  const maxDrawdown =
    riskData?.maxDrawdown ?? performanceData?.maxDrawdown ?? 0;
  const regimeShort =
    regime === "GREEN"
      ? "Bull"
      : regime === "RED"
        ? "Bear"
        : regime === "YELLOW"
          ? "Caution"
          : "--";
  const regimeMarkdown = typeof regimeReadme === "string" ? regimeReadme : "";

  // --- Sector data from API ---
  const sectors = useMemo(() => {
    if (performanceData?.sectors) return performanceData.sectors;
    return [];
  }, [performanceData]);

  return (
    <div className="space-y-4">
      <PageHeader
        icon={LayoutDashboard}
        title="Intelligence Dashboard"
        description="Portfolio overview, market regime, agents status, and equity curve"
      />

      {/* === TOP BAR: Market indices + KPIs (dense single row) === */}
      <div className="bg-[#0B0E14] border border-slate-800/60 rounded-xl px-4 py-2.5 flex flex-wrap items-center gap-x-6 gap-y-2 overflow-x-auto">
        <div className="flex items-center gap-x-5 shrink-0">
          {MOCK_INDICES.map((idx) => (
            <div key={idx.id} className="flex items-center gap-1.5">
              <span className="text-[10px] font-bold text-slate-500 uppercase">{idx.id}</span>
              <span className="text-xs font-mono text-white">{idx.value}</span>
              <span className={`text-[10px] font-mono font-bold ${idx.change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {idx.change >= 0 ? "+" : ""}{idx.change}%
              </span>
            </div>
          ))}
        </div>
        <div className="h-4 w-px bg-slate-700 shrink-0" />
        <div className="flex items-center gap-x-4 flex-wrap gap-y-1">
          <KpiMicroCard label="Total Equity" value={portfolioValue ? `$${Number(portfolioValue).toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "--"} color="green" icon={DollarSign} />
          <KpiMicroCard label="Day P&L" value={dailyPnL != null ? `${dailyPnL >= 0 ? "+" : ""}$${Number(dailyPnL).toFixed(0)}` : "--"} color={dailyPnL >= 0 ? "green" : "red"} icon={TrendingUp} />
          <KpiMicroCard label="Win Rate" value={winRate ? `${Number(winRate).toFixed(1)}%` : "--"} color="cyan" icon={Target} />
          <KpiMicroCard label="Open Risk" value={positions.length ? `$${(15000).toLocaleString()}` : "--"} color="amber" icon={Shield} />
          <KpiMicroCard label="Volatility" value="12.5%" color="purple" icon={Activity} />
          <KpiMicroCard label="Beta" value={sharpe ? Number(sharpe).toFixed(2) : "1.12"} color="cyan" icon={BarChart3} />
          <KpiMicroCard label="Alpha" value={totalPnLPct ? `${totalPnLPct >= 0 ? "+" : ""}${Number(totalPnLPct).toFixed(1)}%` : "+4.5%"} color="green" icon={TrendingUp} />
          <KpiMicroCard label="Correl" value="0.78" color="cyan" icon={Layers} />
          <KpiMicroCard label="Liquidity" value="$50M" color="green" icon={DollarSign} />
          <KpiMicroCard label="Margin" value="25%" color="amber" icon={Percent} />
        </div>
      </div>

      {/* === ROW 2: Four performance charts === */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <Card title="Equity Curve" subtitle="YTD +10.3% · SED -4.1%" className="flex flex-col">
          <div className="flex-1 min-h-[220px] h-[220px]">
            <EquityCurveLW data={equityCurveData} />
          </div>
        </Card>
        <Card title="Drawdown" subtitle="Max drawdown" className="flex flex-col">
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityCurveData.length ? equityCurveData.map((p, i) => ({ ...p, dd: -Math.min(0, (p.value || 0) - 240) })) : [{ time: 0, value: 0, dd: -10 }]} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="time" hide />
                <YAxis domain={["auto", 0]} tickFormatter={(v) => `$${v}`} stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }} />
                <Area type="monotone" dataKey="dd" stroke="#06b6d4" fill="url(#ddFill)" strokeWidth={1} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Win Rate Over Time" subtitle="Monthly" className="flex flex-col">
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].map((m, i) => ({ month: m, rate: 60 + Math.sin(i * 0.5) * 15 + Math.random() * 10 }))} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="month" stroke="#64748b" fontSize={10} />
                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={10} tickFormatter={(v) => `${v}%`} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }} />
                <Bar dataKey="rate" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Sector Performance" subtitle="By month" className="flex flex-col">
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].map((m, i) => ({ month: m, pct: i === 10 ? -120 : 80 + Math.random() * 80 }))} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="month" stroke="#64748b" fontSize={10} />
                <YAxis stroke="#64748b" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }} />
                <Bar dataKey="pct" fill="#06b6d4" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* === ROW 3: P&L Distribution (full width) === */}
      <Card title="P&L Distribution" subtitle="Realized P&L histogram">
        <div className="h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={[-50,-32,-22,-16,-10,-5,0,5,10,11,12,15,20,30,50].map((v, i) => ({ range: v, count: Math.round(500 + Math.sin(i) * 800 + Math.random() * 400) }))} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis dataKey="range" stroke="#64748b" fontSize={10} tickFormatter={(v) => `${v}K`} />
              <YAxis stroke="#64748b" fontSize={10} />
              <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }} />
              <Bar dataKey="count" fill="#06b6d4" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* === ROW 4: OpenClaw Candidates | Portfolio Allocation | Risk Radar === */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="OpenClaw Candidates" subtitle={`${candidates.length} shown · YTD -16.2%`} className="lg:col-span-1" action={<Link to="/agents" className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1">View all <ArrowUpRight className="w-3 h-3" /></Link>}>
          {openclawLoading ? (
            <p className="text-sm text-secondary py-4">Loading...</p>
          ) : candidates.length === 0 ? (
            <p className="text-sm text-secondary py-4">No candidates. Check OpenClaw bridge.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-slate-500 border-b border-slate-700/50">
                    <th className="py-2 pr-2">Shares</th>
                    <th className="py-2 pr-2">Equity</th>
                    <th className="py-2 pr-2">P&L</th>
                    <th className="py-2 pr-2">Alpha</th>
                    <th className="py-2 pr-2">Vol</th>
                    <th className="py-2 pr-2">Rex</th>
                    <th className="py-2 pr-2">Margin</th>
                  </tr>
                </thead>
                <tbody className="text-slate-300">
                  {candidates.slice(0, 6).map((c, i) => (
                    <tr key={c.symbol || c.ticker || i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                      <td className="py-1.5 font-mono">{c.shares ?? "—"}</td>
                      <td className="py-1.5 font-mono">{c.equity ?? "—"}</td>
                      <td className={`py-1.5 font-mono ${(c.pnl ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>{c.pnl != null ? `$${Number(c.pnl).toFixed(0)}` : "—"}</td>
                      <td className="py-1.5 font-mono">{c.alpha != null ? `${Number(c.alpha).toFixed(2)}%` : "—"}</td>
                      <td className="py-1.5 font-mono">{c.vol ?? "—"}</td>
                      <td className="py-1.5 font-mono">{c.rex ?? "—"}</td>
                      <td className="py-1.5 font-mono">{c.margin ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card title="Portfolio Allocation" subtitle="By position" className="lg:col-span-1">
          <div className="h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={positions.length ? positions.map((p, i) => ({ name: p.ticker, value: (p.current || p.entry) * (p.qty || 0) })) : [{ name: "Cash", value: 100 }]} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={2} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {positions.length ? positions.map((p, i) => <Cell key={p.ticker} fill={["#06b6d4","#10b981","#8b5cf6","#f59e0b","#ef4444"][i % 5]} />) : <Cell fill="#334155" />}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Risk Metrics" subtitle="Radar view" className="lg:col-span-1">
          <div className="h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={[{ metric: "Volatility", value: 72, fullMark: 100 }, { metric: "Bias", value: 85, fullMark: 100 }, { metric: "Risk", value: 45, fullMark: 100 }, { metric: "Back", value: 60, fullMark: 100 }, { metric: "Stealth", value: 90, fullMark: 100 }, { metric: "Firm", value: 78, fullMark: 100 }, { metric: "Hair", value: 55, fullMark: 100 }, { metric: "Bear", value: 40, fullMark: 100 }]}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 9 }} />
                <Radar name="Level" dataKey="value" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.3} strokeWidth={2} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* === ROW 5: Correlation Matrix | Agent Leaderboard | Signal Accuracy === */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Correlation Matrix" subtitle="Asset correlation" className="lg:col-span-1">
          <div className="overflow-x-auto">
            <div className="grid grid-cols-4 gap-1 text-[10px] font-mono min-w-[200px]">
              {(() => {
                const vals = [[1, 0.78, 0.65, 0.52], [0.78, 1, 0.72, 0.58], [0.65, 0.72, 1, 0.61], [0.52, 0.58, 0.61, 1]];
                return ["NVDA","TSLA","AMD","MSFT"].map((row, i) =>
                  ["NVDA","TSLA","AMD","MSFT"].map((col, j) => (
                    <div key={`${row}-${col}`} className={`p-1.5 rounded text-center ${i === j ? "bg-slate-700/50 text-slate-400" : vals[i][j] > 0.7 ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-800/50 text-slate-300"}`}>
                      {i === j ? "1.0" : vals[i][j].toFixed(2)}
                    </div>
                  ))
                );
              })()}
            </div>
          </div>
        </Card>
        <Card title="Agent Performance Leaderboard" subtitle="Day P&L · Rank" className="lg:col-span-1" action={<Link to="/agents" className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1">Command Center <ArrowUpRight className="w-3 h-3" /></Link>}>
          {agents.length === 0 ? (
            <p className="text-sm text-secondary py-4">No agent data.</p>
          ) : (
            <ul className="space-y-1.5">
              {agents.slice(0, 5).map((a, i) => {
                const Icon = a.icon || Bot;
                return (
                  <li key={a.name || i} className="flex items-center justify-between py-2 px-2 rounded-lg bg-slate-800/40">
                    <div className="flex items-center gap-2">
                      {Icon && <Icon className="w-3.5 h-3.5 text-cyan-400" />}
                      <span className="text-xs font-medium text-white truncate">{a.name}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[10px] text-slate-500">#{i + 1}</span>
                      <span className={`text-[10px] font-mono ${i === 0 ? "text-emerald-400" : "text-slate-400"}`}>{(2.5 - i * 0.5).toFixed(2)}%</span>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
        <Card title="Signal Accuracy Timeline" subtitle="Daily % correct" className="lg:col-span-1">
          <div className="h-[180px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={Array.from({ length: 30 }, (_, i) => ({ day: i + 1, correct: 70 + Math.random() * 25, wrong: 30 - Math.random() * 25 }))} margin={{ top: 4, right: 4, left: -20, bottom: 0 }} stackOffset="expand">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="day" stroke="#64748b" fontSize={9} />
                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={9} tickFormatter={(v) => `${v}%`} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155" }} />
                <Bar dataKey="correct" stackId="a" fill="#10b981" radius={[0, 0, 0, 0]} />
                <Bar dataKey="wrong" stackId="a" fill="#ef4444" radius={[0, 0, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* === ROW 6: Equity + Regime (original content, condensed) === */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Equity Curve (Detail)" subtitle="Portfolio performance" className="lg:col-span-2">
          <EquityCurveLW data={equityCurveData} />
        </Card>
        <Card title="Market Regime" subtitle={lastScanTs ? `Last scan: ${new Date(lastScanTs).toLocaleString()}` : null}>
          <div className="flex flex-wrap items-center gap-4 mb-4">
            <Badge variant={regime === "GREEN" ? "success" : regime === "RED" ? "danger" : "warning"} size="lg">{regime ?? "--"}</Badge>
            {openclawHealth && <span className="text-xs text-secondary">Bridge: {openclawHealth.connected ? "Connected" : "Disconnected"}{openclawHealth.candidate_count != null && ` | ${openclawHealth.candidate_count} candidates`}</span>}
          </div>
          {regimeMarkdown && <div className="prose prose-invert prose-sm max-w-none text-secondary max-h-[200px] overflow-y-auto"><ReactMarkdown>{regimeMarkdown}</ReactMarkdown></div>}
          {!regimeMarkdown && !openclawLoading && <p className="text-sm text-secondary">No regime readme available.</p>}
        </Card>
      </div>

      {/* === ROW 7: Active Positions + Quick Links === */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Active Positions" subtitle={`${positions.length} open`} action={<Link to="/trades" className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1">Trade Execution <ArrowUpRight className="w-3 h-3" /></Link>}>
          <DataTable
            columns={[{ key: "ticker", label: "Symbol" }, { key: "side", label: "Side" }, { key: "qty", label: "Qty", render: (v) => (v != null ? Number(v).toLocaleString() : "--") }, { key: "entry", label: "Entry", render: (v) => (v != null ? `$${Number(v).toFixed(2)}` : "--") }, { key: "current", label: "Current", render: (v) => (v != null ? `$${Number(v).toFixed(2)}` : "--") }, { key: "pnl", label: "P&L", render: (v) => { const val = Number(v); return <span className={val >= 0 ? "text-success" : "text-danger"}>{val >= 0 ? "+" : ""}${val.toFixed(2)}</span>; } }, { key: "pnlPct", label: "%", render: (v) => { const val = Number(v); return <span className={val >= 0 ? "text-success" : "text-danger"}>{val >= 0 ? "+" : ""}{val.toFixed(2)}%</span>; } }]}
            data={positions}
            emptyMessage="No positions"
            rowKey={(row) => row.ticker}
          />
        </Card>
        <Card title="Quick Navigation">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {[{ to: "/signals", label: "Signals", icon: Zap }, { to: "/risk", label: "Risk Intel", icon: Shield }, { to: "/performance", label: "Performance", icon: BarChart3 }, { to: "/ml-insights", label: "ML Brain", icon: Brain }, { to: "/backtest", label: "Backtest", icon: LineChart }, { to: "/market-regime", label: "Market Regime", icon: Gauge }].map((link) => (
              <Link key={link.to} to={link.to} className="flex items-center gap-2 p-2.5 bg-slate-800/40 border border-slate-700/50 rounded-lg hover:border-cyan-500/40 transition-all">
                <link.icon className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-medium text-white">{link.label}</span>
                <ArrowUpRight className="w-3 h-3 text-slate-500 ml-auto" />
              </Link>
            ))}
          </div>
        </Card>
      </div>

      {sectors.length > 0 && (
        <Card title="Sector Heatmap" subtitle="Performance by sector">
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
            {sectors.map((s, i) => <SectorCell key={s.name || i} name={s.name} value={s.change ?? s.value ?? 0} momentum={s.momentum || (s.change > 0 ? "up" : s.change < 0 ? "down" : "flat")} />)}
          </div>
        </Card>
      )}
    </div>
  );
}
