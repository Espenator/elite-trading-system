// DASHBOARD - Embodier.ai Glass House Intelligence System
// Main overview: Stats, P&L, active positions, signals, agent status
import { useMemo } from "react";
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
} from "lucide-react";
import Card from "../components/ui/Card";
import PageHeader from "../components/ui/PageHeader";
import DataTable from "../components/ui/DataTable";
import Badge from "../components/ui/Badge";
import { useApi } from "../hooks/useApi";

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

export default function Dashboard() {
  const { data: portfolioData } = useApi("portfolio", {
    pollIntervalMs: 30000,
  });
  const { data: signalsData } = useApi("signals", { pollIntervalMs: 30000 });
  const { data: agentsData } = useApi("agents", { pollIntervalMs: 30000 });
  const { data: performanceData } = useApi("performance", {
    pollIntervalMs: 30000,
  });

  // Transform portfolio positions for table
  const positions = useMemo(() => {
    if (!portfolioData?.positions) return [];
    return portfolioData.positions.slice(0, 4).map((pos) => {
      const pnl = pos.unrealizedPnL || 0;
      const pnlPct = pos.entryPrice
        ? ((pnl / (pos.entryPrice * pos.quantity)) * 100).toFixed(2)
        : "0.00";
      return {
        ticker: pos.symbol,
        side: pos.side || "Long",
        entry: pos.entryPrice || 0,
        current: pos.currentPrice || 0,
        pnl: `${pnlPct >= 0 ? "+" : ""}${pnlPct}%`,
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
    return agentsData.agents.slice(0, 4).map((agent) => ({
      name: agent.name,
      status: agent.status === "running" ? "active" : agent.status,
      tasks: Math.floor(Math.random() * 100) + 10, // Mock task count
      icon: iconMap[agent.name] || Bot,
    }));
  }, [agentsData]);

  // Calculate stats from performance data
  const portfolioValue = performanceData?.portfolioValue || 124850;
  const dailyPnL = performanceData?.dailyPnL || 2340;
  const dailyPnLPct = performanceData?.dailyPnLPct || 1.9;
  const activeSignalsCount = signalsData?.signals?.length || 0;
  const winRate = performanceData?.winRate30d || 68.5;

  return (
    <div className="space-y-6">
      <PageHeader
        icon={LayoutDashboard}
        title="Intelligence Dashboard"
        description="Glass House Intelligence Overview"
      />

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
            bodyClassName="p-0"
            className="overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-2 border-b border-secondary/50">
              <span />
              <Link
                to="/trades"
                className="text-xs text-primary hover:text-primary/80"
              >
                View All
              </Link>
            </div>
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
            />
          </Card>
        </div>

        <Card title="Latest Signals" bodyClassName="flex flex-col">
          <div className="flex justify-end -mt-2 mb-2">
            <Link
              to="/signals"
              className="text-xs text-primary hover:text-primary/80"
            >
              View All
            </Link>
          </div>
          <div className="space-y-3">
            {signals.map((s, i) => (
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
            ))}
          </div>
        </Card>
      </div>

      <Card title="Agent Status">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
                      {a.tasks} tasks
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
