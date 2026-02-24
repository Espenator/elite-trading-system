// BACKTESTING LAB - Embodier.ai Glass House Intelligence System
// GET /api/v1/backtest/runs - run history and parallel runs
import { useState } from "react";
import { Play, Square, Download, RotateCcw } from "lucide-react";
import Card from "../components/ui/Card";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import DataTable from "../components/ui/DataTable";
import PageHeader from "../components/ui/PageHeader";
import Slider from "../components/ui/Slider";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";

const STRATEGIES = [
  "Mean Reversion V2",
  "ArbitrageAlpha",
  "TrendFollowerV1",
  "VolSurfaceBeta",
  "MomentumShift",
];

const SAMPLE_TRADES = [
  {
    time: "09:30:00",
    asset: "AAPL",
    type: "BUY",
    qty: 100,
    price: 175.25,
    pnl: 250,
  },
  {
    time: "09:45:15",
    asset: "MSFT",
    type: "SELL",
    qty: 50,
    price: 340.1,
    pnl: -120,
  },
  {
    time: "10:05:30",
    asset: "GOOG",
    type: "BUY",
    qty: 20,
    price: 1200.5,
    pnl: 500,
  },
  {
    time: "10:15:00",
    asset: "TSLA",
    type: "SELL",
    qty: 30,
    price: 230.7,
    pnl: 180,
  },
  {
    time: "10:30:45",
    asset: "AMZN",
    type: "BUY",
    qty: 40,
    price: 150.9,
    pnl: -75,
  },
];

function StatusBadge({ status }) {
  const v =
    { Running: "primary", Completed: "success", Failed: "danger" }[status] ||
    "secondary";
  return <Badge variant={v}>{status}</Badge>;
}

function ResultStat({ label, value }) {
  return (
    <div className="text-center">
      <div className="text-xs text-secondary mb-1">{label}</div>
      <div className="text-lg font-bold text-white">{value}</div>
    </div>
  );
}

export default function Backtesting() {
  const [strategy, setStrategy] = useState("Mean Reversion V2");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2023-12-31");
  const [assets, setAssets] = useState("AAPL, MSFT, GOOG, TSLA, AMZN");
  const [capital, setCapital] = useState("100000");
  const [paramA, setParamA] = useState(50);
  const [paramBMin, setParamBMin] = useState("10");
  const [paramBMax, setParamBMax] = useState("100");
  const [runMode, setRunMode] = useState("single");
  const [isRunning, setIsRunning] = useState(false);
  const [runningBacktest, setRunningBacktest] = useState(false);
  const { data, loading, error, refetch } = useApi("backtestRuns", {
    pollIntervalMs: 60000,
  });
  const parallelRuns = Array.isArray(data?.runs) ? data.runs : [];
  const runHistory = Array.isArray(data?.runHistory) ? data.runHistory : [];

  const handleRunBacktest = async () => {
    setRunningBacktest(true);
    setIsRunning(true);
    try {
      const response = await fetch(getApiUrl("backtest"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          strategy,
          startDate,
          endDate,
          assets,
          capital: parseFloat(capital) || 100000,
          paramA,
          paramBMin: parseFloat(paramBMin) || 10,
          paramBMax: parseFloat(paramBMax) || 100,
          runMode,
        }),
      });
      if (!response.ok) throw new Error("Failed to run backtest");
      const result = await response.json();
      console.log("Backtest result:", result);
      await refetch(); // Refresh run history
    } catch (err) {
      console.error("Failed to run backtest:", err);
    } finally {
      setRunningBacktest(false);
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={RotateCcw}
        title="Backtesting Lab"
        description="Run strategy backtests with parameter optimization"
      />

      {/* Configuration row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Backtest Configuration">
          <div className="space-y-4">
            <Select
              label="Strategy"
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              options={STRATEGIES.map((s) => ({ value: s, label: s }))}
            />
            <div className="grid grid-cols-2 gap-4">
              <TextField
                label="Start Date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <TextField
                label="End Date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <TextField
              label="Asset Universe (CSV)"
              multiline
              rows={2}
              value={assets}
              onChange={(e) => setAssets(e.target.value)}
            />
            <TextField
              label="Initial Capital"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
            />
          </div>
        </Card>

        <Card title="Parameter Sweeps & Controls">
          <div className="space-y-5">
            <Slider
              label={`Parameter A (Sensitivity): ${paramA}`}
              min={0}
              max={100}
              value={paramA}
              onChange={(e) => setParamA(Number(e.target.value))}
              inputClassName="accent-primary"
            />
            <div className="grid grid-cols-2 gap-4">
              <TextField
                label="Parameter B Min"
                value={paramBMin}
                onChange={(e) => setParamBMin(e.target.value)}
              />
              <TextField
                label="Parameter B Max"
                value={paramBMax}
                onChange={(e) => setParamBMax(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-secondary mb-2 block">
                Run Mode
              </label>
              <div className="flex items-center gap-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="runMode"
                    value="single"
                    checked={runMode === "single"}
                    onChange={() => setRunMode("single")}
                    className="accent-primary"
                  />
                  <span className="text-sm text-white">Single Run</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="runMode"
                    value="sweep"
                    checked={runMode === "sweep"}
                    onChange={() => setRunMode("sweep")}
                    className="accent-primary"
                  />
                  <span className="text-sm text-white">Parameter Sweep</span>
                </label>
              </div>
            </div>
            <div className="flex items-center gap-3 pt-2">
              <Button
                variant="primary"
                leftIcon={Play}
                onClick={handleRunBacktest}
                disabled={runningBacktest}
              >
                {runningBacktest ? "Running..." : "Run Backtest"}
              </Button>
              <Button
                variant="secondary"
                leftIcon={Square}
                onClick={() => setIsRunning(false)}
              >
                Stop Run
              </Button>
              <Button variant="secondary" leftIcon={Download}>
                Export Configuration
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Results + Parallel Runs row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card title="Results Visualization">
            <div className="grid grid-cols-5 gap-4 mb-6">
              <ResultStat label="Net PnL" value="+$25,000" />
              <ResultStat label="Sharpe Ratio" value="1.15" />
              <ResultStat label="Max Drawdown" value="-8.2%" />
              <ResultStat label="Win Rate" value="68%" />
              <ResultStat label="Total Trades" value="1,250" />
            </div>
            <div className="h-40 bg-dark/50 rounded-xl border border-secondary/50 flex items-end px-4 pb-4 gap-1">
              {[
                40, 42, 38, 45, 50, 48, 55, 60, 58, 65, 70, 68, 75, 80, 78, 85,
                90, 88, 95, 98,
              ].map((v, i) => (
                <div
                  key={i}
                  className="flex-1 bg-primary/60 rounded-t"
                  style={{ height: `${v}%` }}
                />
              ))}
            </div>
            <div className="flex justify-center gap-4 mt-3">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-primary" />
                <span className="text-xs text-secondary">Equity</span>
              </div>
            </div>
            <div className="h-24 bg-dark/50 rounded-xl border border-secondary/50 mt-4 flex items-start px-4 pt-4 gap-1">
              {[
                5, 8, 3, 12, 18, 15, 10, 20, 25, 18, 12, 22, 28, 20, 15, 10, 8,
                12, 5, 3,
              ].map((v, i) => (
                <div
                  key={i}
                  className="flex-1 bg-danger/40 rounded-b"
                  style={{ height: `${v * 3}%` }}
                />
              ))}
            </div>
            <div className="flex justify-center gap-4 mt-3">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-danger" />
                <span className="text-xs text-secondary">Drawdown</span>
              </div>
            </div>
          </Card>
        </div>

        <Card title="Parallel Run Manager" noPadding>
          <DataTable
            columns={[
              {
                key: "id",
                label: "Run ID",
                render: (v) => (
                  <span className="font-medium text-white">{v}</span>
                ),
              },
              {
                key: "strategy",
                label: "Strategy",
                render: (v) => <span className="text-secondary">{v}</span>,
              },
              {
                key: "status",
                label: "Status",
                cellClassName: "text-right",
                render: (v) => <StatusBadge status={v} />,
              },
            ]}
            data={parallelRuns}
          />
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Trade-by-Trade Simulator" noPadding>
          <DataTable
            columns={[
              {
                key: "time",
                label: "Time",
                render: (v) => <span className="text-secondary">{v}</span>,
              },
              {
                key: "asset",
                label: "Asset",
                render: (v) => (
                  <span className="font-medium text-white">{v}</span>
                ),
              },
              {
                key: "type",
                label: "Type",
                render: (v) => (
                  <Badge variant={v === "BUY" ? "success" : "danger"}>
                    {v}
                  </Badge>
                ),
              },
              { key: "qty", label: "QTY", cellClassName: "text-right" },
              { key: "price", label: "Price", cellClassName: "text-right" },
              {
                key: "pnl",
                label: "PNL",
                cellClassName: "text-right",
                render: (v) => (
                  <span className={v >= 0 ? "text-success" : "text-danger"}>
                    {v >= 0 ? "+" : ""}
                    {v}
                  </span>
                ),
              },
            ]}
            data={SAMPLE_TRADES}
          />
        </Card>

        <Card title="Run History & Export">
          <DataTable
            columns={[
              {
                key: "date",
                label: "Date",
                render: (v) => <span className="text-secondary">{v}</span>,
              },
              {
                key: "strategy",
                label: "Strategy",
                render: (v) => <span className="text-white">{v}</span>,
              },
              {
                key: "pnl",
                label: "PNL",
                cellClassName: "text-right",
                render: (v) => (
                  <span className={v >= 0 ? "text-success" : "text-danger"}>
                    {v >= 0 ? "+" : ""}${Math.abs(v).toLocaleString()}
                  </span>
                ),
              },
            ]}
            data={runHistory}
          />
          <Button
            variant="secondary"
            fullWidth
            leftIcon={Download}
            className="mt-4"
          >
            Export All Results
          </Button>
        </Card>
      </div>
    </div>
  );
}
