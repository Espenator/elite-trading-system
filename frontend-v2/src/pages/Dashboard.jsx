// DASHBOARD - Embodier.ai Glass House Intelligence System
// Main overview: Stats, P&L, active positions, signals, agent status
import { useState } from "react";
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
  const [positions] = useState([
    {
      ticker: "AAPL",
      side: "Long",
      entry: 189.5,
      current: 192.3,
      pnl: "+1.48%",
      pnlColor: "text-emerald-400",
    },
    {
      ticker: "TSLA",
      side: "Long",
      entry: 245.3,
      current: 248.1,
      pnl: "+1.14%",
      pnlColor: "text-emerald-400",
    },
    {
      ticker: "NVDA",
      side: "Long",
      entry: 875.0,
      current: 868.2,
      pnl: "-0.78%",
      pnlColor: "text-red-400",
    },
    {
      ticker: "SPY",
      side: "Short",
      entry: 502.1,
      current: 500.85,
      pnl: "+0.25%",
      pnlColor: "text-emerald-400",
    },
  ]);

  const [signals] = useState([
    { ticker: "MSFT", type: "Bullish Breakout", score: 87, time: "2m ago" },
    { ticker: "AMD", type: "Mean Reversion", score: 74, time: "15m ago" },
    { ticker: "META", type: "Momentum Surge", score: 82, time: "28m ago" },
  ]);

  const [agents] = useState([
    { name: "Market Scanner", status: "active", tasks: 142, icon: Eye },
    { name: "Pattern AI", status: "active", tasks: 38, icon: Brain },
    { name: "Risk Manager", status: "active", tasks: 12, icon: ShieldCheck },
    { name: "YouTube Ingestion", status: "learning", tasks: 5, icon: Bot },
  ]);

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
          value="$124,850"
          change="+2.4% today"
          changeType="up"
          icon={DollarSign}
          color="success"
        />
        <StatCard
          title="Daily P&L"
          value="+$2,340"
          change="+1.9%"
          changeType="up"
          icon={TrendingUp}
          color="primary"
        />
        <StatCard
          title="Active Signals"
          value="12"
          change="3 new"
          changeType="up"
          icon={Zap}
          color="secondary"
        />
        <StatCard
          title="Win Rate (30d)"
          value="68.5%"
          change="+2.1%"
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
