// DASHBOARD - Embodier.ai Glass House Intelligence System
// Main overview: Stats, P&L, OpenClaw regime + candidates, active positions, signals, agent status
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
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import Card from "../components/ui/Card";
import PageHeader from "../components/ui/PageHeader";
import DataTable from "../components/ui/DataTable";
import Badge from "../components/ui/Badge";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import { toast } from "react-toastify";

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

// --- V3 ULTRA-DENSE: KPI Micro Card ---
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

// --- V3 ULTRA-DENSE: Sector Heatmap Cell ---
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

  // --- V3 ULTRA-DENSE: Real-time P&L Ticker state ---
  const [pnlTicker, setPnlTicker] = useState([]);
  const tickerRef = useRef(null);

  // --- V3 ULTRA-DENSE: News feed state ---
  const [newsFeed, setNewsFeed] = useState([]);

  // --- V3 ULTRA-DENSE: Mock data effects ---
  useEffect(() => {
    // P&L Ticker mock feed
    const symbols = [
      "AAPL",
      "GOOGL",
      "TSLA",
      "NVDA",
      "MSFT",
      "AMZN",
      "META",
      "SPY",
      "QQQ",
      "BTC",
      "ETH",
      "SOL",
      "AMD",
      "NFLX",
      "CRM",
    ];
    const initial = symbols.map((s) => ({
      id: s,
      symbol: s,
      pnl: (Math.random() * 2000 - 500).toFixed(2),
      pct: (Math.random() * 8 - 2).toFixed(2),
    }));
    setPnlTicker(initial);

    const pnlInterval = setInterval(() => {
      setPnlTicker((prev) =>
        prev.map((item) => ({
          ...item,
          pnl: (parseFloat(item.pnl) + (Math.random() * 40 - 15)).toFixed(2),
          pct: (parseFloat(item.pct) + (Math.random() * 0.4 - 0.15)).toFixed(2),
        })),
      );
    }, 3000);

    // News feed mock
    const headlines = [
      {
        text: "Fed signals pause in rate hikes amid cooling inflation data",
        source: "Reuters",
      },
      {
        text: "NVDA breaks out to new highs on AI datacenter demand surge",
        source: "Bloomberg",
      },
      {
        text: "Crude oil inventories draw down more than expected",
        source: "EIA",
      },
      {
        text: "China PMI rebounds above 50, signaling manufacturing expansion",
        source: "Caixin",
      },
      {
        text: "Treasury yields fall as bond market prices in rate cuts",
        source: "CNBC",
      },
      {
        text: "Bitcoin ETF inflows hit record $1.2B in single day",
        source: "CoinDesk",
      },
      {
        text: "VIX drops below 14, hitting lowest level since January",
        source: "CBOE",
      },
      {
        text: "Semiconductor sector rotation accelerates into Q1 earnings",
        source: "Barron's",
      },
    ];
    setNewsFeed(headlines);

    return () => {
      clearInterval(pnlInterval);
    };
  }, []);

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
  const portfolioValue = performanceData?.portfolioValue ?? 124850;
  const dailyPnL = performanceData?.dailyPnL ?? 0;
  const regimeShort =
    regime === "GREEN" ? "Bull" : regime === "RED" ? "Bear" : "Neutral";
  const regimeMarkdown = typeof regimeReadme === "string" ? regimeReadme : "";

  return (
    <div className="space-y-6">
      <PageHeader
        icon={LayoutDashboard}
        title="Intelligence Dashboard"
        description="Overview of portfolio, signals, OpenClaw regime, and agent status"
      />

      {/* Top stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Portfolio Value"
          value={`$${Number(portfolioValue).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          change={
            dailyPnL != null
              ? `${dailyPnL >= 0 ? "+" : ""}$${Number(dailyPnL).toFixed(0)}`
              : null
          }
          changeType={dailyPnL >= 0 ? "up" : "down"}
          icon={DollarSign}
          color="success"
        />
        <StatCard
          title="OpenClaw Regime"
          value={openclawLoading ? "…" : regimeShort}
          icon={Gauge}
          color="primary"
        />
        <StatCard
          title="OpenClaw Candidates"
          value={openclawLoading ? "…" : candidates.length}
          icon={Target}
          color="secondary"
        />
        <StatCard
          title="Active Positions"
          value={positions.length}
          icon={BarChart3}
          color="secondary"
        />
      </div>

      {/* OpenClaw regime + readme */}
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
            {regime ?? "—"}
          </Badge>
          {openclawHealth && (
            <span className="text-xs text-secondary">
              Bridge: {openclawHealth.connected ? "Connected" : "Disconnected"}
              {openclawHealth.candidate_count != null &&
                ` · ${openclawHealth.candidate_count} candidates`}
            </span>
          )}
        </div>
        {regimeMarkdown && (
          <div className="openclaw-regime prose prose-invert prose-sm max-w-none text-secondary">
            <ReactMarkdown>{regimeMarkdown}</ReactMarkdown>
          </div>
        )}
        {!regimeMarkdown && !openclawLoading && (
          <p className="text-sm text-secondary">
            No regime readme available. OpenClaw scan may not have run yet.
          </p>
        )}
      </Card>

      {/* Two-column: Candidates + Positions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card
          title="Top OpenClaw Candidates"
          subtitle={`Sorted by composite score · ${candidates.length} shown`}
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
            <p className="text-sm text-secondary py-4">Loading…</p>
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
                  <Badge variant="primary" size="sm">
                    {c.composite_score != null
                      ? Number(c.composite_score).toFixed(1)
                      : "—"}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card
          title="Active Positions"
          subtitle="Latest from portfolio"
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
                key: "entry",
                label: "Entry",
                render: (v) => (v != null ? Number(v).toFixed(2) : "—"),
              },
              {
                key: "current",
                label: "Current",
                render: (v) => (v != null ? Number(v).toFixed(2) : "—"),
              },
              { key: "pnl", label: "P&L" },
            ]}
            data={positions}
            emptyMessage="No positions"
            onRowClick={() => {}}
            rowKey={(row) => row.ticker}
          />
        </Card>
      </div>

      {/* Signals + Agents row */}
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
                  <span className="font-medium text-white">{s.ticker}</span>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={s.score >= 70 ? "success" : "warning"}
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
          subtitle="System agents"
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
                    <Badge
                      variant={a.status === "active" ? "success" : "secondary"}
                      size="sm"
                    >
                      {a.status}
                    </Badge>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>

      {/* P&L Ticker strip */}
      {pnlTicker.length > 0 && (
        <Card title="Live P&L Ticker" subtitle="Symbol-level P&L (mock)">
          <div className="flex gap-4 overflow-x-auto pb-2 custom-scrollbar">
            {pnlTicker.slice(0, 10).map((item) => (
              <div
                key={item.id}
                className="shrink-0 px-3 py-2 rounded-lg bg-secondary/10 border border-secondary/30 min-w-[100px] text-center"
              >
                <div className="text-xs font-bold text-white">
                  {item.symbol}
                </div>
                <div
                  className={`text-xs font-mono ${parseFloat(item.pnl) >= 0 ? "text-success" : "text-danger"}`}
                >
                  {parseFloat(item.pnl) >= 0 ? "+" : ""}
                  {item.pnl}
                </div>
                <div
                  className={`text-[10px] ${parseFloat(item.pct) >= 0 ? "text-success" : "text-danger"}`}
                >
                  {parseFloat(item.pct) >= 0 ? "+" : ""}
                  {item.pct}%
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* KPI Micro Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        <KpiMicroCard
          label="VIX"
          value="18.2"
          sub="Fear & Greed"
          color="amber"
          icon={Thermometer}
        />
        <KpiMicroCard
          label="Regime"
          value={regimeShort}
          sub={regime ?? "—"}
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
          label="Signals"
          value={String(signals.length)}
          sub="Latest"
          color="purple"
          icon={Zap}
        />
        <KpiMicroCard
          label="Agents"
          value={String(agents.length)}
          sub="Active"
          color="cyan"
          icon={Bot}
        />
      </div>

      {/* News feed */}
      {newsFeed.length > 0 && (
        <Card title="Headlines" subtitle="Market news (mock)">
          <ul className="space-y-2 max-h-48 overflow-y-auto">
            {newsFeed.map((item, i) => (
              <li
                key={i}
                className="flex items-start gap-2 py-2 border-b border-secondary/20 last:border-0"
              >
                <Newspaper className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-white">{item.text}</p>
                  <p className="text-xs text-secondary mt-0.5">{item.source}</p>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
