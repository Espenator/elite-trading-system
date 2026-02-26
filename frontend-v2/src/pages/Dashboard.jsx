// DASHBOARD - Embodier.ai Intelligence Dashboard
// Production-ready: Real API wiring, LW Charts equity curve, OpenClaw regime, zero mock data
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
  PieChart,
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
    <div className="space-y-6">
      <PageHeader
        icon={LayoutDashboard}
        title="Intelligence Dashboard"
        description="Portfolio overview, market regime, agents status, and equity curve"
      />

      {/* === ROW 1: Top Stat Cards (6-col) === */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard
          title="Portfolio Value"
          icon={DollarSign}
          color="success"
          value={
            portfolioValue
              ? `$${Number(portfolioValue).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
              : "--"
          }
          change={
            dailyPnL != null
              ? `${dailyPnL >= 0 ? "+" : ""}$${Number(dailyPnL).toFixed(0)}`
              : null
          }
          changeType={dailyPnL >= 0 ? "up" : "down"}
        />
        <StatCard
          title="Daily P&L"
          icon={TrendingUp}
          color={dailyPnL >= 0 ? "success" : "danger"}
          value={
            dailyPnL != null
              ? `${dailyPnL >= 0 ? "+" : ""}$${Number(dailyPnL).toFixed(0)}`
              : "--"
          }
        />
        <StatCard
          title="Win Rate"
          icon={Target}
          color="primary"
          value={winRate ? `${Number(winRate).toFixed(1)}%` : "--"}
        />
        <StatCard
          title="Sharpe"
          icon={BarChart3}
          color="secondary"
          value={sharpe ? Number(sharpe).toFixed(2) : "--"}
        />
        <StatCard
          title="Market Regime"
          icon={Gauge}
          color="primary"
          value={openclawLoading ? "..." : regimeShort}
        />
        <StatCard
          title="Candidates"
          icon={Target}
          color="secondary"
          value={openclawLoading ? "..." : String(candidates.length)}
        />
      </div>

      {/* === ROW 2: KPI Micro Cards === */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-10 gap-2">
        <KpiMicroCard
          label="Total Return"
          value={`${totalPnLPct >= 0 ? "+" : ""}${Number(totalPnLPct).toFixed(1)}%`}
          color={totalPnLPct >= 0 ? "green" : "red"}
          icon={TrendingUp}
        />
        <KpiMicroCard
          label="Max Drawdown"
          value={`${Number(maxDrawdown).toFixed(1)}%`}
          color="red"
          icon={TrendingDown}
        />
        <KpiMicroCard
          label="Regime"
          value={regimeShort}
          sub={regime ?? "--"}
          color="cyan"
          icon={Gauge}
        />
        <KpiMicroCard
          label="Candidates"
          value={String(candidates.length)}
          sub="OpenClaw"
          color="green"
          icon={Target}
        />
        <KpiMicroCard
          label="Positions"
          value={String(positions.length)}
          sub="Active"
          color="cyan"
          icon={Briefcase}
        />
        <KpiMicroCard
          label="Signals"
          value={String(signals.length)}
          sub="Latest"
          color="purple"
          icon={Zap}
        />
        <KpiMicroCard
          label="Agents"
          value={String(agents.length)}
          sub="Running"
          color="cyan"
          icon={Bot}
        />
        <KpiMicroCard
          label="Win Rate"
          value={winRate ? `${Number(winRate).toFixed(0)}%` : "--"}
          color="green"
          icon={Target}
        />
        <KpiMicroCard
          label="Sharpe"
          value={sharpe ? Number(sharpe).toFixed(2) : "--"}
          color="amber"
          icon={BarChart3}
        />
        <KpiMicroCard
          label="System"
          value={statusData?.status === "ok" ? "Online" : "--"}
          sub={statusData?.latency ? `${statusData.latency}ms` : ""}
          color={statusData?.status === "ok" ? "green" : "red"}
          icon={Wifi}
        />
      </div>

      {/* === ROW 3: Equity Curve (LW Charts) + Market Regime === */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card
          title="Equity Curve"
          subtitle="Portfolio performance"
          className="lg:col-span-2"
        >
          <EquityCurveLW data={equityCurveData} />
        </Card>
        <Card
          title="Market Regime"
          subtitle={
            lastScanTs
              ? `Last scan: ${new Date(lastScanTs).toLocaleString()}`
              : null
          }
        >
          <div className="flex flex-wrap items-center gap-4 mb-4">
            <Badge
              variant={
                regime === "GREEN"
                  ? "success"
                  : regime === "RED"
                    ? "danger"
                    : "warning"
              }
              size="lg"
            >
              {regime ?? "--"}
            </Badge>
            {openclawHealth && (
              <span className="text-xs text-secondary">
                Bridge:{" "}
                {openclawHealth.connected ? "Connected" : "Disconnected"}
                {openclawHealth.candidate_count != null &&
                  ` | ${openclawHealth.candidate_count} candidates`}
              </span>
            )}
          </div>
          {regimeMarkdown && (
            <div className="openclaw-regime prose prose-invert prose-sm max-w-none text-secondary max-h-[200px] overflow-y-auto">
              <ReactMarkdown>{regimeMarkdown}</ReactMarkdown>
            </div>
          )}
          {!regimeMarkdown && !openclawLoading && (
            <p className="text-sm text-secondary">
              No regime readme available. OpenClaw scan may not have run yet.
            </p>
          )}
        </Card>
      </div>

      {/* === ROW 4: Candidates + Active Positions === */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card
          title="Top OpenClaw Candidates"
          subtitle={`Sorted by composite score | ${candidates.length} shown`}
          action={
            <Link
              to="/clawbot"
              className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1"
            >
              ClawBot Panel <ArrowUpRight className="w-3 h-3" />
            </Link>
          }
        >
          {openclawLoading ? (
            <p className="text-sm text-secondary py-4">Loading...</p>
          ) : candidates.length === 0 ? (
            <p className="text-sm text-secondary py-4">
              No candidates. Check OpenClaw bridge.
            </p>
          ) : (
            <ul className="space-y-2">
              {candidates.slice(0, 5).map((c, i) => (
                <li
                  key={c.symbol || c.ticker || i}
                  className="flex items-center justify-between py-2 px-3 rounded-lg bg-secondary/10 hover:bg-secondary/20"
                >
                  <span className="font-medium text-white">
                    {c.symbol || c.ticker}
                  </span>
                  <div className="flex items-center gap-2">
                    {c.sector && (
                      <span className="text-[10px] text-secondary">
                        {c.sector}
                      </span>
                    )}
                    <Badge variant="primary" size="sm">
                      {c.composite_score != null
                        ? Number(c.composite_score).toFixed(1)
                        : "--"}
                    </Badge>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card
          title="Active Positions"
          subtitle={`${positions.length} open`}
          action={
            <Link
              to="/trades"
              className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1"
            >
              Trade Execution <ArrowUpRight className="w-3 h-3" />
            </Link>
          }
        >
          <DataTable
            columns={[
              { key: "ticker", label: "Symbol" },
              { key: "side", label: "Side" },
              {
                key: "qty",
                label: "Qty",
                render: (v) => (v != null ? Number(v).toLocaleString() : "--"),
              },
              {
                key: "entry",
                label: "Entry",
                render: (v) => (v != null ? `$${Number(v).toFixed(2)}` : "--"),
              },
              {
                key: "current",
                label: "Current",
                render: (v) => (v != null ? `$${Number(v).toFixed(2)}` : "--"),
              },
              {
                key: "pnl",
                label: "P&L",
                render: (v) => {
                  const val = Number(v);
                  return (
                    <span className={val >= 0 ? "text-success" : "text-danger"}>
                      {val >= 0 ? "+" : ""}${val.toFixed(2)}
                    </span>
                  );
                },
              },
              {
                key: "pnlPct",
                label: "%",
                render: (v) => {
                  const val = Number(v);
                  return (
                    <span className={val >= 0 ? "text-success" : "text-danger"}>
                      {val >= 0 ? "+" : ""}
                      {val.toFixed(2)}%
                    </span>
                  );
                },
              },
            ]}
            data={positions}
            emptyMessage="No positions"
            rowKey={(row) => row.ticker}
          />
        </Card>
      </div>

      {/* === ROW 5: Signals + Agent Status === */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card
          title="Latest Signals"
          subtitle="ML signal feed"
          action={
            <Link
              to="/signals"
              className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1"
            >
              Signal Intelligence <ArrowUpRight className="w-3 h-3" />
            </Link>
          }
        >
          {signals.length === 0 ? (
            <p className="text-sm text-secondary py-4">No signals yet.</p>
          ) : (
            <ul className="space-y-2">
              {signals.map((s, i) => (
                <li
                  key={s.ticker || i}
                  className="flex items-center justify-between py-2 px-3 rounded-lg bg-secondary/10"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white">{s.ticker}</span>
                    <span className="text-[10px] text-secondary uppercase">
                      {s.type}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        s.score >= 70
                          ? "success"
                          : s.score >= 50
                            ? "warning"
                            : "danger"
                      }
                      size="sm"
                    >
                      {s.score}%
                    </Badge>
                    <span className="text-xs text-secondary">{s.time}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card
          title="Agent Status"
          subtitle={`${agents.filter((a) => a.status === "active").length}/${agents.length} active`}
          action={
            <Link
              to="/agents"
              className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1"
            >
              Agent Command Center <ArrowUpRight className="w-3 h-3" />
            </Link>
          }
        >
          {agents.length === 0 ? (
            <p className="text-sm text-secondary py-4">No agent data.</p>
          ) : (
            <ul className="space-y-2">
              {agents.map((a, i) => {
                const Icon = a.icon;
                return (
                  <li
                    key={a.name || i}
                    className="flex items-center justify-between py-2 px-3 rounded-lg bg-secondary/10"
                  >
                    <div className="flex items-center gap-2">
                      {Icon && <Icon className="w-4 h-4 text-primary" />}
                      <span className="text-sm text-white">{a.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {a.tasks !== "--" && (
                        <span className="text-[10px] text-secondary font-mono">
                          {a.tasks} tasks
                        </span>
                      )}
                      <Badge
                        variant={
                          a.status === "active"
                            ? "success"
                            : a.status === "error"
                              ? "danger"
                              : "secondary"
                        }
                        size="sm"
                      >
                        {a.status}
                      </Badge>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>

      {/* === ROW 6: Sector Heatmap + Quick Links === */}
      {sectors.length > 0 && (
        <Card title="Sector Heatmap" subtitle="Performance by sector">
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
            {sectors.map((s, i) => (
              <SectorCell
                key={s.name || i}
                name={s.name}
                value={s.change ?? s.value ?? 0}
                momentum={
                  s.momentum ||
                  (s.change > 0 ? "up" : s.change < 0 ? "down" : "flat")
                }
              />
            ))}
          </div>
        </Card>
      )}

      {/* === ROW 7: Quick Navigation === */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {[
          {
            to: "/signals",
            label: "Signals",
            icon: Zap,
            color: "text-purple-400",
          },
          {
            to: "/risk",
            label: "Risk Intel",
            icon: Shield,
            color: "text-red-400",
          },
          {
            to: "/performance",
            label: "Performance",
            icon: BarChart3,
            color: "text-cyan-400",
          },
          {
            to: "/ml-insights",
            label: "ML Brain",
            icon: Brain,
            color: "text-emerald-400",
          },
          {
            to: "/backtest",
            label: "Backtest Lab",
            icon: LineChart,
            color: "text-amber-400",
          },
          {
            to: "/market-regime",
            label: "Market Regime",
            icon: Gauge,
            color: "text-cyan-400",
          },
        ].map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className="flex items-center gap-2 p-3 bg-[#0B0E14] border border-secondary/20 rounded-xl hover:border-primary/40 hover:bg-primary/5 transition-all"
          >
            <link.icon className={`w-4 h-4 ${link.color}`} />
            <span className="text-xs font-medium text-white">{link.label}</span>
            <ArrowUpRight className="w-3 h-3 text-secondary ml-auto" />
          </Link>
        ))}
      </div>
    </div>
  );
}
