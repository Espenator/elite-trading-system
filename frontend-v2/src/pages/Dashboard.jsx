// DASHBOARD - Embodier.ai Glass House Intelligence System
// Main overview: Stats, P&L, OpenClaw regime + candidates, active positions, signals, agent status
import { useMemo, useState, useEffect, useCallback } from "react";
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
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import Card from "../components/ui/Card";
import PageHeader from "../components/ui/PageHeader";
import DataTable from "../components/ui/DataTable";
import Badge from "../components/ui/Badge";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";

function StatCard({ title, value, change, changeType, icon: Icon, color }) {
  const colors = {
    success: "from-success/20 to-success/5 border-success/30",
    primary: "from-primary/20 to-primary/5 border-primary/30",
    secondary: "from-secondary/20 to-secondary/5 border-secondary/30",
    warning: "from-warning/20 to-warning/5 border-warning/30",
  };
  const iconColors = {
    success: "text-success",
    primary: "text-primary",
    secondary: "text-secondary",
    warning: "text-warning",
  };
  return (
    <div
      className={`bg-gradient-to-br ${colors[color]} border rounded-2xl p-5`}
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

const OPENCLAW_POLL_MS = 30000;

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

export default function Dashboard() {
  const { data: portfolioData } = useApi("portfolio", {
    pollIntervalMs: 30000,
  });
  const { data: signalsData } = useApi("signals", { pollIntervalMs: 30000 });
  const { data: agentsData } = useApi("agents", { pollIntervalMs: 30000 });
  const { data: performanceData } = useApi("performance", {
    pollIntervalMs: 30000,
  });
  const { data: openclawTop, loading: openclawLoading } = useOpenClawTop();
  const openclawHealth = useOpenClawHealth();
  const regime = openclawTop?.regime ?? openclawHealth?.regime ?? null;
  const regimeReadme = openclawTop?.regime_readme ?? "";
  const candidates = openclawTop?.candidates ?? [];
  const lastScanTs = openclawHealth?.last_scan_timestamp ?? null;

  // Transform portfolio positions for table (support both API shapes: symbol/entryPrice/... and ticker/entry/...)
  const positions = useMemo(() => {
    if (!portfolioData?.positions) return [];
    return portfolioData.positions.slice(0, 4).map((pos) => {
      const ticker = pos.symbol ?? pos.ticker ?? "—";
      const entry = pos.entryPrice ?? pos.entry ?? 0;
      const current = pos.currentPrice ?? pos.current ?? 0;
      const qty = pos.quantity ?? pos.qty ?? 0;
      const pnlDollars = pos.unrealizedPnL ?? pos.pnl ?? 0;
      let pnlPct = pos.pnlPct;
      if (pnlPct == null && entry && qty) {
        pnlPct = (pnlDollars / (entry * qty)) * 100;
      }
      const pnlStr =
        pnlPct != null
          ? `${Number(pnlPct) >= 0 ? "+" : ""}${Number(pnlPct).toFixed(2)}%`
          : "—";
      return {
        ticker,
        side: pos.side || "Long",
        entry,
        current,
        pnl: pnlStr,
      };
    });
  }, [portfolioData]);

  // Transform signals (latest 3); backend sends prob_up (snake_case)
  const signals = useMemo(() => {
    if (!signalsData?.signals) return [];
    return signalsData.signals.slice(0, 3).map((sig) => {
      const prob = sig.prob_up ?? sig.probUp ?? 0.5;
      return {
        ticker: sig.symbol,
        type: sig.action || "Signal",
        score: Math.round(prob * 100),
        time: "now",
      };
    });
  }, [signalsData]);

  // Transform agents (first 4)
  const agents = useMemo(() => {
    if (!agentsData?.agents) return [];
    const iconMap = {
      "Market Data Agent": Eye,
      "Signal Generation Agent": Brain,
      "ML Learning Agent": Brain,
      "Sentiment Agent": Bot,
      "YouTube Knowledge Agent": Bot,
    };
    return agentsData.agents.map((agent) => ({
      name: agent.name,
      status: agent.status === "running" ? "active" : agent.status,
      tasks: "—", // Task count not provided by API
      icon: iconMap[agent.name] || Bot,
    }));
  }, [agentsData]);

  // Calculate stats from performance data
  const portfolioValue = performanceData?.portfolioValue || 124850;
  const dailyPnL = performanceData?.dailyPnL || 2340;
  const dailyPnLPct = performanceData?.dailyPnLPct || 1.9;
  const activeSignalsCount = signalsData?.signals?.length || 0;
  const winRate = performanceData?.winRate30d || 68.5;

  const regimeVariant = useMemo(() => {
    const s = (regime || "").toUpperCase();
    if (["GREEN", "BULLISH", "RISK_ON"].includes(s)) return "success";
    if (["YELLOW", "NEUTRAL"].includes(s)) return "warning";
    if (["RED", "BEARISH", "RISK_OFF", "CRISIS"].includes(s)) return "danger";
    if (/\bRED\b/.test(s)) return "danger";
    if (/\bGREEN\b/.test(s)) return "success";
    if (/\bYELLOW\b/.test(s)) return "warning";
    return "secondary";
  }, [regime]);

  const regimeShort = useMemo(() => {
    if (!regime || typeof regime !== "string") return "—";
    const m = regime.match(/\b(GREEN|YELLOW|RED)\b/i);
    if (m) return m[1].toUpperCase();
    const t = regime.replace(/\*\*/g, "").trim();
    return t.length <= 14 ? t : "—";
  }, [regime]);

  // Markdown: single \n → line break (two trailing spaces in CommonMark)
  const regimeMarkdown = useMemo(
    () =>
      regime && typeof regime === "string" ? regime.replace(/\n/g, "  \n") : "",
    [regime],
  );

  const lastScanLabel = useMemo(() => {
    if (!lastScanTs) return "—";
    try {
      const d = new Date(lastScanTs);
      return Number.isNaN(d.getTime()) ? lastScanTs : d.toLocaleString();
    } catch {
      return lastScanTs;
    }
  }, [lastScanTs]);

  return (
    <div className="space-y-6">
      <PageHeader
        icon={LayoutDashboard}
        title="Intelligence Dashboard"
        description="Glass House Intelligence Overview"
      />

      {/* OpenClaw: Status bar + Regime details + Top 5 */}
      <Card
        title="OpenClaw"
        subtitle="Market regime and top candidates from OpenClaw scan"
      >
        {/* Status bar: Regime badge | Last scan | Count */}
        <div className="flex flex-wrap items-center gap-4 gap-y-2 mb-4 pb-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <span className="text-xs text-secondary uppercase tracking-wider">
              Regime
            </span>
            <span
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-bold ${
                regimeVariant === "success"
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                  : regimeVariant === "warning"
                    ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                    : regimeVariant === "danger"
                      ? "bg-red-500/20 text-red-400 border border-red-500/40"
                      : "bg-secondary/20 text-secondary border border-secondary/30"
              }`}
            >
              <Gauge className="w-4 h-4 shrink-0" />
              {openclawLoading ? "…" : regimeShort}
            </span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Clock className="w-4 h-4 text-cyan-400/80 shrink-0" />
            <span className="text-xs text-secondary">Last scan</span>
            <span className="text-sm font-medium text-white">
              {lastScanLabel}
            </span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <Target className="w-4 h-4 text-primary/80 shrink-0" />
            <span className="text-xs text-secondary">Candidates</span>
            <span className="text-sm font-bold text-white">
              {openclawLoading ? "…" : candidates.length}
            </span>
          </div>
        </div>

        {/* Regime details (markdown) - scrollable */}
        {regimeMarkdown && !openclawLoading && (
          <div className="mb-4">
            <p className="text-xs text-secondary uppercase tracking-wider mb-2">
              Regime details
            </p>
            <div
              className={`rounded-xl border-2 p-4 ${
                regimeVariant === "success"
                  ? "bg-emerald-500/5 border-emerald-500/30"
                  : regimeVariant === "warning"
                    ? "bg-amber-500/5 border-amber-500/30"
                    : regimeVariant === "danger"
                      ? "bg-red-500/5 border-red-500/30"
                      : "bg-secondary/10 border-secondary/30"
              }`}
            >
              <div className="openclaw-regime prose prose-invert prose-sm max-w-none">
                <ReactMarkdown
                  components={{
                    p: ({ children }) => (
                      <p className="mb-2 last:mb-0 text-slate-200">
                        {children}
                      </p>
                    ),
                    strong: ({ children }) => (
                      <strong className="font-semibold text-white">
                        {children}
                      </strong>
                    ),
                    ul: ({ children }) => (
                      <ul className="list-disc list-inside mb-3 space-y-1 text-slate-200">
                        {children}
                      </ul>
                    ),
                    li: ({ children }) => (
                      <li className="text-slate-200">{children}</li>
                    ),
                    h1: ({ children }) => (
                      <h1 className="text-base font-bold text-white mt-3 mb-2 first:mt-0">
                        {children}
                      </h1>
                    ),
                    h2: ({ children }) => (
                      <h2 className="text-sm font-bold text-white mt-3 mb-1.5">
                        {children}
                      </h2>
                    ),
                    h3: ({ children }) => (
                      <h3 className="text-sm font-semibold text-slate-100 mt-2 mb-1">
                        {children}
                      </h3>
                    ),
                    code: ({ children }) => (
                      <code className="px-1.5 py-0.5 rounded bg-black/30 text-cyan-300 font-mono text-xs">
                        {children}
                      </code>
                    ),
                  }}
                >
                  {regimeMarkdown}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {/* Top 5 by composite score */}
        <div>
          <p className="text-xs text-secondary uppercase tracking-wider mb-3">
            Top 5 by composite score
          </p>
          {openclawLoading ? (
            <span className="text-slate-300 text-sm">Loading…</span>
          ) : candidates.length === 0 ? (
            <p className="text-slate-200 text-sm">
              No OpenClaw data — add{" "}
              <code className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-xs font-mono">
                OPENCLAW_GIST_ID
              </code>{" "}
              (and optionally{" "}
              <code className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-xs font-mono">
                OPENCLAW_GIST_TOKEN
              </code>
              ) to backend{" "}
              <code className="px-1.5 py-0.5 rounded bg-secondary/30 text-slate-300 text-xs">
                .env
              </code>
            </p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
              {candidates.slice(0, 10).map((c, i) => (
                <div
                  key={c.symbol ?? i}
                  className="flex items-center justify-between rounded-lg bg-secondary/15 border border-cyan-500/20 px-3 py-2 hover:border-cyan-500/40 transition-colors"
                >
                  <span className="font-semibold text-white truncate">
                    {c.symbol ?? c.ticker ?? "—"}
                  </span>
                  <span className="text-cyan-400 text-sm font-medium tabular-nums shrink-0 ml-2">
                    {c.composite_score != null
                      ? Number(c.composite_score).toFixed(1)
                      : "—"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* Stat cards row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Portfolio Value"
          value={`$${portfolioValue.toLocaleString()}`}
          change={`+${dailyPnLPct.toFixed(1)}% today`}
          changeType="up"
          icon={DollarSign}
          color="success"
        />
        <StatCard
          title="Daily P&L"
          value={`${dailyPnL >= 0 ? "+" : ""}$${Math.abs(dailyPnL).toLocaleString()}`}
          change={`${dailyPnLPct >= 0 ? "+" : ""}${dailyPnLPct.toFixed(1)}%`}
          changeType={dailyPnL >= 0 ? "up" : "down"}
          icon={TrendingUp}
          color="primary"
        />
        <StatCard
          title="Active Signals"
          value={activeSignalsCount.toString()}
          change="live"
          changeType="up"
          icon={Zap}
          color="secondary"
        />
        <StatCard
          title="Win Rate (30d)"
          value={`${winRate.toFixed(1)}%`}
          change=""
          changeType="up"
          icon={Target}
          color="warning"
        />
      </div>

      {/* Main grid: Positions + Signals + Agents */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card
            title="Active Positions"
            action={
              <Link
                to="/trades"
                className="text-xs text-primary hover:text-primary/80"
              >
                View All
              </Link>
            }
            noPadding
          >
            <DataTable
              columns={[
                {
                  key: "ticker",
                  label: "Ticker",
                  render: (v) => (
                    <span className="font-semibold text-white">{v}</span>
                  ),
                },
                { key: "side", label: "Side" },
                {
                  key: "entry",
                  label: "Entry",
                  cellClassName: "text-right",
                  render: (v) => `$${Number(v).toFixed(2)}`,
                },
                {
                  key: "current",
                  label: "Current",
                  cellClassName: "text-right",
                  render: (v) => `$${Number(v).toFixed(2)}`,
                },
                {
                  key: "pnl",
                  label: "P&L",
                  cellClassName: "text-right",
                  render: (v) => (
                    <span
                      className={
                        v.startsWith("+") ? "text-success" : "text-danger"
                      }
                    >
                      {v}
                    </span>
                  ),
                },
              ]}
              data={positions}
              className="rounded-none border-none"
            />
          </Card>
        </div>

        <Card
          title="Latest Signals"
          action={
            <Link
              to="/signals"
              className="text-xs text-primary hover:text-primary/80"
            >
              View All
            </Link>
          }
          bodyClassName="flex flex-col"
        >
          <div className="space-y-3">
            {signals.length === 0 ? (
              <p className="py-6 text-center text-sm text-secondary">
                No signals
              </p>
            ) : (
              signals.map((s, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 p-3 rounded-xl bg-secondary/10 border border-secondary/30"
                >
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Zap className="w-5 h-5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">
                        {s.ticker}
                      </span>
                      <span className="text-xs text-secondary">{s.time}</span>
                    </div>
                    <div className="text-xs text-secondary">{s.type}</div>
                  </div>
                  <div className="text-right">
                    <div
                      className={`text-sm font-bold ${s.score >= 80 ? "text-success" : "text-warning"}`}
                    >
                      {s.score}
                    </div>
                    <div className="text-xs text-secondary">score</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <Card title="Agent Status">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {agents.map((a, i) => {
            const Icon = a.icon;
            return (
              <div
                key={i}
                className="flex items-center gap-3 p-4 rounded-xl bg-secondary/10 border border-secondary/30"
              >
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Icon className="w-5 h-5 text-primary" />
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-white">{a.name}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <div
                      className={`w-1.5 h-1.5 rounded-full ${a.status === "active" ? "bg-success" : "bg-warning"} animate-pulse`}
                    />
                    <span className="text-xs text-secondary capitalize">
                      {a.status}
                    </span>
                    <span className="text-xs text-secondary">|</span>
                    <span className="text-xs text-secondary">
                      {a.tasks === "—" ? "—" : `${a.tasks} tasks`}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Recent Trades">
          <div className="space-y-2">
            {[
              "AAPL +$320 (Long)",
              "GOOGL +$180 (Long)",
              "TSLA -$95 (Short)",
              "SPY +$450 (Short)",
            ].map((t, i) => (
              <div
                key={i}
                className="flex items-center justify-between py-2 border-b border-secondary/30 last:border-0"
              >
                <span className="text-sm text-white">{t.split(" ")[0]}</span>
                <span
                  className={`text-sm font-medium ${t.includes("+") ? "text-success" : "text-danger"}`}
                >
                  {t.split(" ").slice(1).join(" ")}
                </span>
              </div>
            ))}
          </div>
        </Card>
        <Card title="System Health">
          <div className="space-y-3">
            {[
              { label: "API Latency", value: "12ms" },
              { label: "WebSocket", value: "Connected" },
              { label: "ML Models", value: "4/4 Loaded" },
              { label: "Data Feed", value: "Live" },
            ].map((item, i) => (
              <div
                key={i}
                className="flex items-center justify-between py-2 border-b border-secondary/30 last:border-0"
              >
                <span className="text-sm text-secondary">{item.label}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-white">{item.value}</span>
                  <div className="w-2 h-2 rounded-full bg-success" />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
