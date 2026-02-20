import React, { useState, useEffect, useCallback } from "react";
import {
  Shield,
  TrendingUp,
  TrendingDown,
  Mail,
  MessageSquare,
} from "lucide-react";
import { toast } from "react-toastify";
import Card from "../components/ui/Card";
import TextField from "../components/ui/TextField";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import Slider from "../components/ui/Slider";
import Checkbox from "../components/ui/Checkbox";
import RiskHistoryChart from "../components/charts/RiskHistoryChart";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";

function formatRiskHistoryDate(isoDate) {
  if (!isoDate) return "";
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return String(isoDate);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const RiskIntelligence = () => {
  const { data, loading, error, refetch } = useApi("risk", {
    pollIntervalMs: 30000,
  });
  const [maxDrawdown, setMaxDrawdown] = useState(data?.maxDailyDrawdown ?? 10);
  const [positionSizeLimit, setPositionSizeLimit] = useState(
    data?.positionSizeLimit ?? 5,
  );
  const [maxDailyLoss, setMaxDailyLoss] = useState(data?.maxDailyLossPct ?? 2);
  const [varLimit, setVarLimit] = useState(data?.varLimit ?? 1.5);
  const [equityDrop, setEquityDrop] = useState(20);
  const [volatilityIncrease, setVolatilityIncrease] = useState(30);
  const [simulationResults, setSimulationResults] = useState(null);
  const [saving, setSaving] = useState(false);
  // Alert configuration
  const [dailyPnLLossAlert, setDailyPnLLossAlert] = useState(5);
  const [maxDrawdownAlert, setMaxDrawdownAlert] = useState(10);
  const [autoPauseTrading, setAutoPauseTrading] = useState(true);
  const [riskHistory, setRiskHistory] = useState([]);
  const [riskHistoryLoading, setRiskHistoryLoading] = useState(true);

  // Fetch risk history for Historical Risk Metrics chart
  useEffect(() => {
    let cancelled = false;
    setRiskHistoryLoading(true);
    fetch(getApiUrl("risk") + "/history", { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : []))
      .then((raw) => {
        if (cancelled || !Array.isArray(raw)) return;
        const mapped = raw.map((row) => ({
          date: formatRiskHistoryDate(row.date),
          maxDailyLoss: Number(row.maxDailyLoss) || 0,
          var: Number(row.var) || 0,
        }));
        setRiskHistory(mapped);
      })
      .catch(() => {
        if (!cancelled) setRiskHistory([]);
      })
      .finally(() => {
        if (!cancelled) setRiskHistoryLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [data?.var95]);

  // Sync state when API data loads
  useEffect(() => {
    if (data) {
      setMaxDrawdown(data.maxDailyDrawdown ?? 10);
      setPositionSizeLimit(data.positionSizeLimit ?? 5);
      setMaxDailyLoss(data.maxDailyLossPct ?? 2);
      setVarLimit(data.varLimit ?? 1.5);
      if (data.autoPauseTrading !== undefined)
        setAutoPauseTrading(!!data.autoPauseTrading);
      if (data.dailyPnLLossAlert != null)
        setDailyPnLLossAlert(Number(data.dailyPnLLossAlert) || 0);
      if (data.maxDrawdownAlert != null)
        setMaxDrawdownAlert(Number(data.maxDrawdownAlert) || 0);
    }
  }, [data]);

  // Debounced save function (risk limits + alert settings)
  const saveRiskConfig = useCallback(async () => {
    setSaving(true);
    try {
      const response = await fetch(getApiUrl("risk"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          maxDailyDrawdown: maxDrawdown,
          positionSizeLimit: positionSizeLimit,
          maxDailyLossPct: maxDailyLoss,
          varLimit: varLimit,
          autoPauseTrading: autoPauseTrading,
          dailyPnLLossAlert: dailyPnLLossAlert,
          maxDrawdownAlert: maxDrawdownAlert,
        }),
      });
      if (!response.ok) throw new Error("Failed to save");
      await refetch();
    } catch (err) {
      console.error("Failed to save risk config:", err);
    } finally {
      setSaving(false);
    }
  }, [
    maxDrawdown,
    positionSizeLimit,
    maxDailyLoss,
    varLimit,
    autoPauseTrading,
    dailyPnLLossAlert,
    maxDrawdownAlert,
    refetch,
  ]);

  // Debounce saves (save 1 second after user stops changing)
  useEffect(() => {
    if (!data) return; // Don't save on initial load
    const timer = setTimeout(saveRiskConfig, 1000);
    return () => clearTimeout(timer);
  }, [
    maxDrawdown,
    positionSizeLimit,
    maxDailyLoss,
    varLimit,
    autoPauseTrading,
    dailyPnLLossAlert,
    maxDrawdownAlert,
    data,
    saveRiskConfig,
  ]);

  const handleRunSimulation = () => {
    const estimatedMaxDrawdown = (maxDrawdown * (1 + equityDrop / 100)).toFixed(
      1,
    );
    const potentialDailyLoss = (
      maxDailyLoss *
      (1 + volatilityIncrease / 100)
    ).toFixed(1);
    setSimulationResults({
      maxDrawdown: estimatedMaxDrawdown,
      dailyLoss: potentialDailyLoss,
    });
  };

  const handleTestEmailAlert = async () => {
    try {
      const res = await fetch(getApiUrl("alerts") + "/test-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json.ok) {
        toast.success(json.message || "Test email alert sent");
      } else {
        toast.error(json.detail || "Failed to send test email");
      }
    } catch (err) {
      toast.error(err.message || "Failed to send test email");
    }
  };

  const handleTestSMSAlert = async () => {
    try {
      const res = await fetch(getApiUrl("alerts") + "/test-sms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json.ok) {
        toast.success(json.message || "Test SMS alert sent");
      } else {
        toast.error(json.detail || "Failed to send test SMS");
      }
    } catch (err) {
      toast.error(err.message || "Failed to send test SMS");
    }
  };

  return (
    <div className="min-h-full bg-dark text-white space-y-6">
      <PageHeader
        icon={Shield}
        title="Risk Intelligence"
        description={
          error
            ? "Failed to load risk data"
            : "Configure risk limits, VaR, and drawdown parameters"
        }
      >
        {error && (
          <span className="text-xs text-danger font-medium">
            Failed to load
          </span>
        )}
      </PageHeader>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card title="General Risk Parameters">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-white mb-3">
                  Maximum Daily Drawdown
                </label>
                <div className="flex items-center gap-4">
                  <Slider
                    min={0}
                    max={20}
                    value={maxDrawdown}
                    onChange={(e) => setMaxDrawdown(parseFloat(e.target.value))}
                    showValue={false}
                    className="flex-1"
                    inputClassName="accent-primary"
                  />
                  <TextField
                    type="number"
                    value={maxDrawdown}
                    onChange={(e) =>
                      setMaxDrawdown(parseFloat(e.target.value) || 0)
                    }
                    suffix="%"
                    className="w-20"
                    inputClassName="w-16"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-3">
                  Individual Position Size Limit
                </label>
                <div className="flex items-center gap-4">
                  <Slider
                    min={0}
                    max={10}
                    value={positionSizeLimit}
                    onChange={(e) =>
                      setPositionSizeLimit(parseFloat(e.target.value))
                    }
                    showValue={false}
                    className="flex-1"
                    inputClassName="accent-primary"
                  />
                  <TextField
                    type="number"
                    value={positionSizeLimit}
                    onChange={(e) =>
                      setPositionSizeLimit(parseFloat(e.target.value) || 0)
                    }
                    suffix="%"
                    className="w-20"
                    inputClassName="w-16"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-3">
                  Maximum Daily Loss Limit (Account Equity)
                </label>
                <div className="flex items-center gap-4">
                  <Slider
                    min={0}
                    max={5}
                    step={0.5}
                    value={maxDailyLoss}
                    onChange={(e) =>
                      setMaxDailyLoss(parseFloat(e.target.value))
                    }
                    showValue={false}
                    className="flex-1"
                    inputClassName="accent-primary"
                  />
                  <TextField
                    type="number"
                    value={maxDailyLoss}
                    onChange={(e) =>
                      setMaxDailyLoss(parseFloat(e.target.value) || 0)
                    }
                    step="0.1"
                    suffix="%"
                    className="w-20"
                    inputClassName="w-16"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-3">
                  Value at Risk (VaR) Limit
                </label>
                <div className="flex items-center gap-4">
                  <Slider
                    min={0}
                    max={3}
                    step={0.1}
                    value={varLimit}
                    onChange={(e) => setVarLimit(parseFloat(e.target.value))}
                    showValue={false}
                    className="flex-1"
                    inputClassName="accent-primary"
                  />
                  <TextField
                    type="number"
                    value={varLimit}
                    onChange={(e) =>
                      setVarLimit(parseFloat(e.target.value) || 0)
                    }
                    step="0.1"
                    suffix="%"
                    className="w-20"
                    inputClassName="w-16"
                  />
                </div>
              </div>
            </div>
          </Card>

          <Card title="Risk Scenario Simulator">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    Simulated Equity Drop
                  </label>
                  <div className="flex items-center gap-4">
                    <Slider
                      min={0}
                      max={100}
                      step={1}
                      value={equityDrop}
                      onChange={(e) =>
                        setEquityDrop(parseFloat(e.target.value) || 0)
                      }
                      showValue={false}
                      className="flex-1"
                      inputClassName="accent-cyan-500"
                    />
                    <TextField
                      type="number"
                      value={equityDrop}
                      onChange={(e) =>
                        setEquityDrop(parseFloat(e.target.value) || 0)
                      }
                      suffix="%"
                      className="w-20"
                      inputClassName="w-14"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    Simulated Volatility Increase
                  </label>
                  <div className="flex items-center gap-4">
                    <Slider
                      min={0}
                      max={100}
                      step={1}
                      value={volatilityIncrease}
                      onChange={(e) =>
                        setVolatilityIncrease(parseFloat(e.target.value) || 0)
                      }
                      showValue={false}
                      className="flex-1"
                      inputClassName="accent-cyan-500"
                    />
                    <TextField
                      type="number"
                      value={volatilityIncrease}
                      onChange={(e) =>
                        setVolatilityIncrease(parseFloat(e.target.value) || 0)
                      }
                      suffix="%"
                      className="w-20"
                      inputClassName="w-14"
                    />
                  </div>
                </div>
                <Button
                  variant="primary"
                  fullWidth
                  onClick={handleRunSimulation}
                  className="mt-2"
                >
                  Run Simulation
                </Button>
              </div>
              {simulationResults && (
                <div className="rounded-xl bg-dark border border-cyan-500/20 p-4">
                  <div className="space-y-3">
                    <div>
                      <div className="text-sm text-secondary mb-1">
                        Estimated Max Drawdown
                      </div>
                      <div className="text-xl font-bold text-red-400">
                        {simulationResults.maxDrawdown}%
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-secondary mb-1">
                        Potential Daily Loss
                      </div>
                      <div className="text-xl font-bold text-red-400">
                        {simulationResults.dailyLoss}%
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>

          <Card title="Historical Risk Metrics">
            {riskHistoryLoading ? (
              <div className="h-64 flex items-center justify-center text-secondary text-sm">
                Loading…
              </div>
            ) : (
              <RiskHistoryChart data={riskHistory} />
            )}
          </Card>

          <Card title="Alert Configuration">
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Alert on daily P&L loss greater than
                </label>
                <div className="flex items-center gap-4">
                  <Slider
                    min={0}
                    max={50}
                    step={0.5}
                    value={dailyPnLLossAlert}
                    onChange={(e) =>
                      setDailyPnLLossAlert(parseFloat(e.target.value) || 0)
                    }
                    formatValue={(v) => v}
                    suffix="%"
                    className="flex-1"
                    inputClassName="accent-cyan-500"
                  />
                  <TextField
                    type="number"
                    value={dailyPnLLossAlert}
                    onChange={(e) =>
                      setDailyPnLLossAlert(parseFloat(e.target.value) || 0)
                    }
                    step={0.1}
                    suffix="%"
                    className="w-24"
                    inputClassName="w-16"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Alert on maximum drawdown greater than
                </label>
                <div className="flex items-center gap-4">
                  <Slider
                    min={0}
                    max={50}
                    step={0.5}
                    value={maxDrawdownAlert}
                    onChange={(e) =>
                      setMaxDrawdownAlert(parseFloat(e.target.value) || 0)
                    }
                    formatValue={(v) => v}
                    suffix="%"
                    className="flex-1"
                    inputClassName="accent-cyan-500"
                  />
                  <TextField
                    type="number"
                    value={maxDrawdownAlert}
                    onChange={(e) =>
                      setMaxDrawdownAlert(parseFloat(e.target.value) || 0)
                    }
                    step={0.1}
                    suffix="%"
                    className="w-24"
                    inputClassName="w-16"
                  />
                </div>
              </div>
              <div className="flex items-center justify-between pt-4 border-t border-cyan-500/10">
                <label className="text-sm font-medium text-white">
                  Auto-pause trading on critical alerts
                </label>
                <Checkbox
                  checked={autoPauseTrading}
                  onChange={() => setAutoPauseTrading((p) => !p)}
                  className="text-secondary"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <Button
                  variant="secondary"
                  leftIcon={Mail}
                  onClick={handleTestEmailAlert}
                  className="flex-1"
                >
                  Test Email Alert
                </Button>
                <Button
                  variant="secondary"
                  leftIcon={MessageSquare}
                  onClick={handleTestSMSAlert}
                  className="flex-1"
                >
                  Test SMS Alert
                </Button>
              </div>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-1">
          <Card title="Real-time Risk Monitor" className="sticky top-6">
            <div className="space-y-4">
              {[
                {
                  label: "Current Exposure",
                  value: `$${(data?.currentExposure ?? 12500).toLocaleString()}`,
                  trend: "up",
                  color: "text-emerald-400",
                },
                {
                  label: "VaR (95%, 1-day)",
                  value: `$${(data?.var95 ?? 350).toLocaleString()}`,
                  trend: "down",
                  color: "text-red-400",
                },
                {
                  label: "Expected Shortfall",
                  value: `$${(data?.expectedShortfall ?? 520).toLocaleString()}`,
                  trend: "up",
                  color: "text-emerald-400",
                },
              ].map((metric, idx) => (
                <div
                  key={idx}
                  className="rounded-lg bg-secondary/20 border border-cyan-500/10 p-4"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <Shield className="w-4 h-4 text-cyan-400/70 shrink-0" />
                      <span className="text-sm text-secondary truncate">
                        {metric.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-lg font-bold text-white">
                        {metric.value}
                      </span>
                      {metric.trend === "up" ? (
                        <TrendingUp
                          className={`w-4 h-4 ${metric.color}`}
                          aria-hidden
                        />
                      ) : (
                        <TrendingDown
                          className={`w-4 h-4 ${metric.color}`}
                          aria-hidden
                        />
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div
                className={`mt-4 p-4 rounded-xl border ${
                  data?.allWithinLimits !== false
                    ? "bg-emerald-500/10 border-emerald-500/30"
                    : "bg-red-500/10 border-red-500/30"
                }`}
              >
                <p
                  className={`text-sm ${
                    data?.allWithinLimits !== false
                      ? "text-emerald-400"
                      : "text-red-400"
                  }`}
                >
                  {data?.allWithinLimits !== false
                    ? "All risk parameters within acceptable limits"
                    : "Some risk parameters exceed limits"}
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default RiskIntelligence;
