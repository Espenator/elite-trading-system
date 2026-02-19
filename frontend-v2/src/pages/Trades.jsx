// TRADES PAGE - Embodier.ai Glass House Intelligence System
// GET /api/v1/portfolio - positions and trade history
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  TrendingUp,
  Clock,
  DollarSign,
  ArrowUpRight,
  LineChart,
  X,
} from "lucide-react";
import Card from "../components/ui/Card";
import DataTable from "../components/ui/DataTable";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";

export default function Trades() {
  const location = useLocation();
  const navigate = useNavigate();
  const fromSignal = location.state?.fromSignal && location.state?.symbol;
  const [dismissFromSignal, setDismissFromSignal] = useState(false);

  const [tab, setTab] = useState("active");
  const { data, loading, error, refetch } = useApi("portfolio", {
    pollIntervalMs: 30000,
  });
  const positions = Array.isArray(data?.positions) ? data.positions : [];
  const history = Array.isArray(data?.history) ? data.history : [];
  const totalPnl = positions.reduce((sum, p) => sum + (p.pnl ?? 0), 0);

  return (
    <div className="space-y-6">
      <PageHeader
        icon={LineChart}
        title="Trade Execution"
        description={
          error
            ? "Failed to load portfolio"
            : "Manage positions and review history"
        }
      >
        {error && (
          <span className="text-xs text-danger font-medium">
            Failed to load
          </span>
        )}
        <Badge
          variant={totalPnl >= 0 ? "success" : "danger"}
          size="lg"
          className="px-4 py-2"
        >
          Today: {totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(0)}
        </Badge>
      </PageHeader>

      {fromSignal && !dismissFromSignal && (
        <Card className="border-primary/40 bg-primary/10 p-4">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-white">
              <span className="font-medium">From Signal:</span> Place order for{" "}
              <span className="font-bold text-primary">
                {location.state.symbol}
              </span>
              {location.state.side && (
                <span className="ml-1 text-secondary">
                  ({location.state.side})
                </span>
              )}
            </p>
            <button
              type="button"
              onClick={() => {
                setDismissFromSignal(true);
                navigate("/trades", { replace: true, state: {} });
              }}
              className="shrink-0 rounded p-1 text-secondary hover:bg-secondary/20 hover:text-white"
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </Card>
      )}

      {loading && positions.length === 0 && !error && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-4 animate-pulse">
              <div className="h-4 bg-secondary/20 rounded w-2/3 mb-2" />
              <div className="h-6 bg-secondary/20 rounded w-1/2" />
            </Card>
          ))}
        </div>
      )}
      {error && positions.length === 0 && (
        <Card className="p-6 text-center">
          <p className="text-secondary mb-2">
            Could not load portfolio. Check GET /api/v1/portfolio.
          </p>
          <Button variant="outline" size="sm" onClick={refetch}>
            Retry
          </Button>
        </Card>
      )}
      {!loading && !error && positions.length === 0 && history.length === 0 && (
        <Card className="p-6 text-center">
          <p className="text-secondary">No positions or trade history yet.</p>
        </Card>
      )}
      {!loading && (positions.length > 0 || history.length > 0) && (
        <>
          {/* Stats row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                label: "Active Positions",
                value: positions.length,
                icon: TrendingUp,
                color: "text-primary",
              },
              {
                label: "Unrealized P&L",
                value: `$${totalPnl >= 0 ? "+" : ""}${totalPnl}`,
                icon: DollarSign,
                color: totalPnl >= 0 ? "text-success" : "text-danger",
              },
              {
                label: "Win Rate (30d)",
                value: "68.5%",
                icon: ArrowUpRight,
                color: "text-success",
              },
              {
                label: "Avg Hold Time",
                value: "1.4 days",
                icon: Clock,
                color: "text-warning",
              },
            ].map((stat, i) => (
              <Card key={i} noPadding className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <stat.icon className={`w-4 h-4 ${stat.color}`} />
                  <span className="text-xs text-secondary">{stat.label}</span>
                </div>
                <div className="text-xl font-bold text-white">{stat.value}</div>
              </Card>
            ))}
          </div>

          <div className="flex gap-2 border-b border-secondary/50 pb-0">
            {["active", "history"].map((t) => (
              <Button
                key={t}
                variant={tab === t ? "primary" : "ghost"}
                size="sm"
                onClick={() => setTab(t)}
                className={
                  tab === t
                    ? "border-b-2 border-primary rounded-b-none"
                    : "rounded-b-none"
                }
              >
                {t === "active"
                  ? `Active (${positions.length})`
                  : `History (${history.length})`}
              </Button>
            ))}
          </div>

          {tab === "active" && (
            <Card noPadding className="overflow-hidden">
              <DataTable
                columns={[
                  {
                    key: "ticker",
                    label: "Ticker",
                    render: (v) => (
                      <span className="font-semibold text-white">{v}</span>
                    ),
                  },
                  {
                    key: "side",
                    label: "Side",
                    render: (v) => (
                      <Badge variant={v === "Long" ? "success" : "danger"}>
                        {v}
                      </Badge>
                    ),
                  },
                  { key: "qty", label: "Qty", cellClassName: "text-right" },
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
                    render: (_, row) => (
                      <span
                        className={
                          row.pnl >= 0 ? "text-success" : "text-danger"
                        }
                      >
                        {row.pnl >= 0 ? "+" : ""}${row.pnl} (
                        {row.pnlPct >= 0 ? "+" : ""}
                        {row.pnlPct}%)
                      </span>
                    ),
                  },
                  {
                    key: "stop",
                    label: "Stop",
                    cellClassName: "text-right text-danger",
                    render: (v) => `$${Number(v).toFixed(2)}`,
                  },
                  {
                    key: "target",
                    label: "Target",
                    cellClassName: "text-right text-success",
                    render: (v) => `$${Number(v).toFixed(2)}`,
                  },
                  {
                    key: "signal",
                    label: "Signal",
                    render: (v) => <span className="text-secondary">{v}</span>,
                  },
                  {
                    key: "id",
                    label: "Actions",
                    cellClassName: "text-right",
                    render: () => (
                      <Button variant="danger" size="sm">
                        Close
                      </Button>
                    ),
                  },
                ]}
                data={positions}
              />
            </Card>
          )}

          {tab === "history" && (
            <Card noPadding className="overflow-hidden">
              <DataTable
                columns={[
                  {
                    key: "date",
                    label: "Date",
                    render: (v) => <span className="text-secondary">{v}</span>,
                  },
                  {
                    key: "ticker",
                    label: "Ticker",
                    render: (v) => (
                      <span className="font-semibold text-white">{v}</span>
                    ),
                  },
                  {
                    key: "side",
                    label: "Side",
                    render: (v) => (
                      <Badge variant={v === "Long" ? "success" : "danger"}>
                        {v}
                      </Badge>
                    ),
                  },
                  { key: "qty", label: "Qty", cellClassName: "text-right" },
                  {
                    key: "entry",
                    label: "Entry",
                    cellClassName: "text-right",
                    render: (v) => `$${Number(v).toFixed(2)}`,
                  },
                  {
                    key: "exit",
                    label: "Exit",
                    cellClassName: "text-right",
                    render: (v) => `$${Number(v).toFixed(2)}`,
                  },
                  {
                    key: "pnl",
                    label: "P&L",
                    cellClassName: "text-right",
                    render: (_, row) => (
                      <span
                        className={
                          row.pnl >= 0 ? "text-success" : "text-danger"
                        }
                      >
                        {row.pnl >= 0 ? "+" : ""}${row.pnl} (
                        {row.pnlPct >= 0 ? "+" : ""}
                        {row.pnlPct}%)
                      </span>
                    ),
                  },
                  {
                    key: "duration",
                    label: "Duration",
                    cellClassName: "text-right",
                    render: (v) => <span className="text-secondary">{v}</span>,
                  },
                ]}
                data={history}
              />
            </Card>
          )}
        </>
      )}
    </div>
  );
}
