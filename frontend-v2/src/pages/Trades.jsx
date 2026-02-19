// TRADES PAGE - Embodier.ai Glass House Intelligence System
// GET /api/v1/portfolio - positions and trade history. POST /api/v1/orders - place order.
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  TrendingUp,
  Clock,
  DollarSign,
  ArrowUpRight,
  LineChart,
  X,
  Send,
  RefreshCw,
} from "lucide-react";
import Card from "../components/ui/Card";
import DataTable from "../components/ui/DataTable";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import { useToast } from "../context/ToastContext";

export default function Trades() {
  const location = useLocation();
  const navigate = useNavigate();
  const fromSignal = location.state?.fromSignal && location.state?.symbol;
  const [dismissFromSignal, setDismissFromSignal] = useState(false);
  const [orderModalOpen, setOrderModalOpen] = useState(false);
  const [orderSubmitting, setOrderSubmitting] = useState(false);
  const [orderError, setOrderError] = useState(null);
  const [orderSuccess, setOrderSuccess] = useState(false);
  const [orderForm, setOrderForm] = useState({
    symbol: location.state?.symbol || "",
    side:
      (location.state?.side || "Buy").toLowerCase() === "sell" ? "sell" : "buy",
    order_type: "Market",
    quantity: 10,
    price: 0,
  });

  const [tab, setTab] = useState("active");
  const toast = useToast();
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
        <div className="flex items-center gap-3">
          {error && (
            <span className="text-xs font-medium text-danger">
              Failed to load
            </span>
          )}
          <button
            onClick={() => refetch()}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg border border-secondary/40 bg-secondary/10 px-3 py-2 text-xs font-medium text-secondary transition-colors hover:bg-secondary/20 hover:text-white disabled:opacity-50"
            title="Refresh portfolio"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2">
            <div
              className={`h-2 w-2 rounded-full ${loading ? "bg-amber-400 animate-pulse" : "bg-emerald-400 animate-pulse"}`}
            />
            <span className="text-xs font-medium text-success">
              {loading ? "Updating…" : "Live"}
            </span>
          </div>
          <Badge
            variant={totalPnl >= 0 ? "success" : "danger"}
            size="lg"
            className="px-4 py-2"
          >
            Today: {totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(0)}
          </Badge>
        </div>
      </PageHeader>

      {fromSignal && !dismissFromSignal && (
        <Card className="border-primary/40 bg-primary/10 p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
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
            <div className="flex items-center gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setOrderForm((f) => ({
                    ...f,
                    symbol: location.state.symbol,
                    side:
                      (location.state.side || "Buy").toLowerCase() === "sell"
                        ? "sell"
                        : "buy",
                  }));
                  setOrderModalOpen(true);
                  setOrderError(null);
                  setOrderSuccess(false);
                }}
              >
                <Send className="w-4 h-4 mr-1" />
                Place order
              </Button>
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
          </div>
        </Card>
      )}

      {orderModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
          onClick={() => !orderSubmitting && setOrderModalOpen(false)}
        >
          <Card
            className="w-full max-w-md p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Place order</h3>
              <button
                type="button"
                onClick={() => !orderSubmitting && setOrderModalOpen(false)}
                className="p-1 text-secondary hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            {orderSuccess && (
              <p className="mb-4 text-sm text-success">
                Order submitted successfully.
              </p>
            )}
            {orderError && (
              <p className="mb-4 text-sm text-danger">{orderError}</p>
            )}
            <div className="space-y-4">
              <TextField
                label="Symbol"
                value={orderForm.symbol}
                readOnly
                className="opacity-80"
              />
              <Select
                label="Side"
                value={orderForm.side}
                onChange={(e) =>
                  setOrderForm((f) => ({ ...f, side: e.target.value }))
                }
                options={[
                  { value: "buy", label: "Buy" },
                  { value: "sell", label: "Sell" },
                ]}
              />
              <Select
                label="Order type"
                value={orderForm.order_type}
                onChange={(e) =>
                  setOrderForm((f) => ({ ...f, order_type: e.target.value }))
                }
                options={[
                  { value: "Market", label: "Market" },
                  { value: "Limit", label: "Limit" },
                ]}
              />
              <TextField
                label="Quantity"
                type="number"
                min={1}
                value={orderForm.quantity}
                onChange={(e) =>
                  setOrderForm((f) => ({
                    ...f,
                    quantity: parseInt(e.target.value, 10) || 1,
                  }))
                }
              />
              {orderForm.order_type === "Limit" && (
                <TextField
                  label="Limit price"
                  type="number"
                  min={0}
                  step={0.01}
                  value={orderForm.price || ""}
                  onChange={(e) =>
                    setOrderForm((f) => ({
                      ...f,
                      price: parseFloat(e.target.value) || 0,
                    }))
                  }
                />
              )}
            </div>
            <div className="flex gap-2 mt-6">
              <Button
                variant="primary"
                className="flex-1"
                disabled={orderSubmitting}
                onClick={async () => {
                  setOrderSubmitting(true);
                  setOrderError(null);
                  try {
                    const res = await fetch(getApiUrl("orders"), {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        symbol: orderForm.symbol,
                        order_type: orderForm.order_type,
                        side: orderForm.side,
                        quantity: orderForm.quantity,
                        price:
                          orderForm.order_type === "Market"
                            ? 0
                            : orderForm.price || 0,
                      }),
                    });
                    const data = await res.json().catch(() => ({}));
                    if (!res.ok) {
                      const errMsg =
                        data.detail || data.message || `HTTP ${res.status}`;
                      setOrderError(errMsg);
                      toast.error(errMsg);
                      return;
                    }
                    setOrderSuccess(true);
                    toast.success("Order placed successfully");
                    refetch();
                    setTimeout(() => {
                      setOrderModalOpen(false);
                      setOrderSuccess(false);
                    }, 1500);
                  } catch (err) {
                    const errMsg = err.message || "Request failed";
                    setOrderError(errMsg);
                    toast.error(errMsg);
                  } finally {
                    setOrderSubmitting(false);
                  }
                }}
              >
                {orderSubmitting ? "Submitting…" : "Submit order"}
              </Button>
              <Button
                variant="secondary"
                onClick={() => !orderSubmitting && setOrderModalOpen(false)}
                disabled={orderSubmitting}
              >
                Cancel
              </Button>
            </div>
          </Card>
        </div>
      )}

      {loading && positions.length === 0 && !error && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="rounded-xl border border-secondary/40 bg-gradient-to-br from-secondary/10 to-transparent p-4 animate-pulse"
            >
              <div className="h-3 bg-secondary/20 rounded w-2/3 mb-2" />
              <div className="h-6 bg-secondary/20 rounded w-1/2" />
            </div>
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
