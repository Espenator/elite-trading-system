import React, { useState, useEffect, useCallback } from "react";
import {
  Shield,
  TrendingUp,
  TrendingDown,
  Mail,
  MessageSquare,
  DollarSign,
  Activity,
  BarChart3,
  Target,
  AlertTriangle,
  Percent,
  Layers,
  PieChart,
} from "lucide-react";
import { toast } from "react-toastify";
import Card from "../components/ui/Card";
import TextField from "../components/ui/TextField";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import Slider from "../components/ui/Slider";
import Checkbox from "../components/ui/Checkbox";
import RiskHistoryChart from "../components/charts/RiskHistoryChart";
import RiskEquityLC from "../components/charts/RiskEquityLC";
import MonteCarloLC from "../components/charts/MonteCarloLC";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";

function formatRiskHistoryDate(isoDate) {
  if (!isoDate) return "";
  const d = new Date(isoDate);
  if (Number.isNaN(d.getTime())) return String(isoDate);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const KPI_ICONS = [DollarSign, Activity, AlertTriangle, Percent, BarChart3, Target, Layers, PieChart];
const timeframes = ["1D", "1W", "1M", "3M", "YTD"];
const SECTOR_COLORS = ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#f43f5e", "#64748b", "#06b6d4", "#ec4899"];

const RiskIntelligence = () => {
  // ── Primary risk data from GET /api/v1/risk (real Alpaca data) ──
  const { data, loading, error, refetch } = useApi("risk", { pollIntervalMs: 30000 });

  // ── Portfolio positions from GET /api/v1/portfolio (real Alpaca positions) ──
  const { data: portfolioData } = useApi("portfolio", { pollIntervalMs: 60000 });

  // ── Alerts from GET /api/v1/alerts ──
  const { data: alertsData } = useApi("alerts", { pollIntervalMs: 30000 });

  // ── Performance from GET /api/v1/performance ──
  const { data: perfData } = useApi("performance", { pollIntervalMs: 120000 });

  // ── Risk config state (synced from API) ──
  const [maxDrawdown, setMaxDrawdown] = useState(10);
  const [positionSizeLimit, setPositionSizeLimit] = useState(5);
  const [maxDailyLoss, setMaxDailyLoss] = useState(2);
  const [varLimit, setVarLimit] = useState(1.5);
  const [autoPauseTrading, setAutoPauseTrading] = useState(true);
  const [dailyPnLLossAlert, setDailyPnLLossAlert] = useState(5);
  const [maxDrawdownAlert, setMaxDrawdownAlert] = useState(10);

  // ── Simulation state ──
  const [equityDrop, setEquityDrop] = useState(20);
  const [volatilityIncrease, setVolatilityIncrease] = useState(30);
  const [simulationResults, setSimulationResults] = useState(null);
  const [saving, setSaving] = useState(false);
  const [timeframe, setTimeframe] = useState("1M");

  // ── Risk history for chart ──
  const [riskHistory, setRiskHistory] = useState([]);
  const [riskHistoryLoading, setRiskHistoryLoading] = useState(true);

  // Fetch risk history from GET /api/v1/risk/history
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
      .catch(() => { if (!cancelled) setRiskHistory([]); })
      .finally(() => { if (!cancelled) setRiskHistoryLoading(false); });
    return () => { cancelled = true; };
  }, [data?.var95]);

  // Sync config state when API data loads
  useEffect(() => {
    if (data) {
      setMaxDrawdown(data.maxDailyDrawdown ?? 10);
      setPositionSizeLimit(data.positionSizeLimit ?? 5);
      setMaxDailyLoss(data.maxDailyLossPct ?? 2);
      setVarLimit(data.varLimit ?? 1.5);
      if (data.autoPauseTrading !== undefined) setAutoPauseTrading(!!data.autoPauseTrading);
      if (data.dailyPnLLossAlert != null) setDailyPnLLossAlert(Number(data.dailyPnLLossAlert) || 0);
      if (data.maxDrawdownAlert != null) setMaxDrawdownAlert(Number(data.maxDrawdownAlert) || 0);
    }
  }, [data]);

  // Debounced save
  const saveRiskConfig = useCallback(async () => {
    setSaving(true);
    try {
      const response = await fetch(getApiUrl("risk"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          maxDailyDrawdown: maxDrawdown,
          positionSizeLimit,
          maxDailyLossPct: maxDailyLoss,
          varLimit,
          autoPauseTrading,
          dailyPnLLossAlert,
          maxDrawdownAlert,
        }),
      });
      if (!response.ok) throw new Error("Failed to save");
      await refetch();
    } catch (err) {
      console.error("Failed to save risk config:", err);
    } finally {
      setSaving(false);
    }
  }, [maxDrawdown, positionSizeLimit, maxDailyLoss, varLimit, autoPauseTrading, dailyPnLLossAlert, maxDrawdownAlert, refetch]);

  useEffect(() => {
    if (!data) return;
    const timer = setTimeout(saveRiskConfig, 1000);
    return () => clearTimeout(timer);
  }, [maxDrawdown, positionSizeLimit, maxDailyLoss, varLimit, autoPauseTrading, dailyPnLLossAlert, maxDrawdownAlert, data, saveRiskConfig]);

  const handleRunSimulation = () => {
    setSimulationResults({
      maxDrawdown: (maxDrawdown * (1 + equityDrop / 100)).toFixed(1),
      dailyLoss: (maxDailyLoss * (1 + volatilityIncrease / 100)).toFixed(1),
    });
  };

  const handleTestEmailAlert = async () => {
    try {
      const res = await fetch(getApiUrl("alerts") + "/test-email", { method: "POST", headers: { "Content-Type": "application/json" } });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json.ok) toast.success(json.message || "Test email sent");
      else toast.error(json.detail || "Failed");
    } catch (err) { toast.error(err.message || "Failed"); }
  };

  const handleTestSMSAlert = async () => {
    try {
      const res = await fetch(getApiUrl("alerts") + "/test-sms", { method: "POST", headers: { "Content-Type": "application/json" } });
      const json = await res.json().catch(() => ({}));
      if (res.ok && json.ok) toast.success(json.message || "Test SMS sent");
      else toast.error(json.detail || "Failed");
    } catch (err) { toast.error(err.message || "Failed"); }
  };

  // ── Derive KPIs from real API data (no mock fallbacks) ──
  const kpis = [
    { label: "Equity", value: data?.equity ? `$${data.equity.toLocaleString()}` : "—", sub: "Alpaca Account" },
    { label: "Exposure", value: data?.currentExposure ? `$${data.currentExposure.toLocaleString()}` : "—", sub: "Total Market Value" },
    { label: "Daily P&L", value: data?.dailyPnlPct != null ? `${data.dailyPnlPct >= 0 ? "+" : ""}${data.dailyPnlPct}%` : "—", sub: "Today" },
    { label: "VaR 95%", value: data?.var95 ? `$${data.var95.toLocaleString()}` : "—", sub: "1-Day" },
    { label: "CVaR", value: data?.expectedShortfall ? `$${data.expectedShortfall.toLocaleString()}` : "—", sub: "Expected Shortfall" },
    { label: "Positions", value: data?.positionCount != null ? String(data.positionCount) : "—", sub: "Open" },
    { label: "Concentration", value: data?.concentrationPct != null ? `${data.concentrationPct.toFixed(1)}%` : "—", sub: "Largest Position" },
    { label: "Unrealized", value: data?.unrealizedPl != null ? `$${data.unrealizedPl.toLocaleString()}` : "—", sub: "P&L" },
  ];

  // ── Real positions from portfolio API ──
  const positions = Array.isArray(portfolioData?.positions) ? portfolioData.positions : (Array.isArray(portfolioData) ? portfolioData : []);

  // Compute sector weights from real positions
  const totalPortfolioValue = positions.reduce((sum, p) => sum + Math.abs(Number(p.market_value || p.marketValue || 0)), 0);
  const positionWeights = positions.map((p) => ({
    symbol: p.symbol || p.ticker || "?",
    weight: totalPortfolioValue > 0 ? (Math.abs(Number(p.market_value || p.marketValue || 0)) / totalPortfolioValue * 100) : 0,
  })).sort((a, b) => b.weight - a.weight);

  // ── Real alerts from alerts API ──
  const riskAlerts = Array.isArray(alertsData?.alerts) ? alertsData.alerts : (Array.isArray(alertsData) ? alertsData : []);

  // ── Real recommendations from API ──
  const recommendations = Array.isArray(data?.recommendations) ? data.recommendations : [];

  // ── Real equity history from performance API ──
  const histData = Array.isArray(perfData?.equityHistory) ? perfData.equityHistory : (Array.isArray(perfData?.history) ? perfData.history : []);

  // ── Monte Carlo data from performance API ──
  const mcData = Array.isArray(perfData?.monteCarlo) ? perfData.monteCarlo : [];

  return (
    <div className="space-y-4">
      <PageHeader icon={Shield} title="Embodier Trader - Risk Intelligence" subtitle="Real-time risk monitoring, VaR analysis & position analytics">
        {error && <span className="text-red-400 text-xs">Failed to load</span>}
        {saving && <span className="text-yellow-400 text-xs animate-pulse">Saving...</span>}
        {data?.alpacaConnected === false && <span className="text-orange-400 text-xs">Alpaca disconnected</span>}
      </PageHeader>

      {/* ROW 1: KPI Strip */}
      <div className="grid grid-cols-8 gap-2">
        {kpis.map((k, i) => {
          const Icon = KPI_ICONS[i % KPI_ICONS.length];
          return (
            <div key={i} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 hover:bg-slate-700/50 transition-colors">
              <div className="flex items-center gap-1 mb-1"><Icon className="w-3 h-3 text-emerald-500" /><span className="text-[10px] text-slate-400 truncate">{k.label}</span></div>
              <div className="text-lg font-bold text-white">{k.value}</div>
              <div className="text-[9px] text-slate-500">{k.sub}</div>
            </div>
          );
        })}
      </div>

      {/* ROW 2: Equity Chart + Monte Carlo + Position Weights */}
      <div className="grid grid-cols-6 gap-3">
        <div className="col-span-3">
          <Card title="Portfolio Equity & Drawdown" className="relative">
            <div className="absolute top-2 right-3 flex gap-1">
              {timeframes.map(tf => <button key={tf} onClick={() => setTimeframe(tf)} className={`px-2 py-0.5 text-[10px] rounded cursor-pointer transition-colors ${timeframe === tf ? "bg-primary text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}>{tf}</button>)}
            </div>
            {histData.length > 0 ? (
              <RiskEquityLC data={histData} height={220} />
            ) : (
              <div className="h-[220px] flex items-center justify-center text-slate-500 text-sm">No equity history available</div>
            )}
          </Card>
        </div>
        <div className="col-span-1">
          <Card title="Monte Carlo Simulation">
            {mcData.length > 0 ? (
              <>
                <MonteCarloLC data={mcData} height={220} />
                <div className="flex justify-center gap-2 text-[8px] mt-1">
                  {["5th", "25th", "50th", "75th", "95th"].map((p, i) => <span key={i} className="text-slate-400">{p}%ile</span>)}
                </div>
              </>
            ) : (
              <div className="h-[220px] flex items-center justify-center text-slate-500 text-sm">No simulation data</div>
            )}
          </Card>
        </div>
        <div className="col-span-2">
          <Card title="Position Concentration">
            {positionWeights.length > 0 ? (
              <div className="space-y-1 max-h-[240px] overflow-y-auto">
                {positionWeights.map((p, i) => (
                  <div key={p.symbol} className="flex items-center gap-2 text-xs">
                    <span className="w-12 text-slate-400 font-mono">{p.symbol}</span>
                    <div className="flex-1 bg-slate-800 rounded-full h-3 overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${Math.min(p.weight, 100)}%`, backgroundColor: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
                    </div>
                    <span className="w-14 text-right text-white font-medium">{p.weight.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-[220px] flex items-center justify-center text-slate-500 text-sm">No positions</div>
            )}
          </Card>
        </div>
      </div>

      {/* ROW 3: Risk Config + History + Alerts + Monitor */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card title="General Risk Parameters">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-white mb-3">Maximum Daily Drawdown</label>
                <div className="flex items-center gap-4">
                  <Slider min={0} max={20} value={maxDrawdown} onChange={(e) => setMaxDrawdown(parseFloat(e.target.value))} showValue={false} className="flex-1" inputClassName="accent-primary" />
                  <TextField type="number" value={maxDrawdown} onChange={(e) => setMaxDrawdown(parseFloat(e.target.value) || 0)} suffix="%" className="w-20" inputClassName="w-16" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-3">Individual Position Size Limit</label>
                <div className="flex items-center gap-4">
                  <Slider min={0} max={10} value={positionSizeLimit} onChange={(e) => setPositionSizeLimit(parseFloat(e.target.value))} showValue={false} className="flex-1" inputClassName="accent-primary" />
                  <TextField type="number" value={positionSizeLimit} onChange={(e) => setPositionSizeLimit(parseFloat(e.target.value) || 0)} suffix="%" className="w-20" inputClassName="w-16" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-3">Maximum Daily Loss Limit</label>
                <div className="flex items-center gap-4">
                  <Slider min={0} max={5} step={0.5} value={maxDailyLoss} onChange={(e) => setMaxDailyLoss(parseFloat(e.target.value))} showValue={false} className="flex-1" inputClassName="accent-primary" />
                  <TextField type="number" value={maxDailyLoss} onChange={(e) => setMaxDailyLoss(parseFloat(e.target.value) || 0)} step="0.1" suffix="%" className="w-20" inputClassName="w-16" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-3">Value at Risk (VaR) Limit</label>
                <div className="flex items-center gap-4">
                  <Slider min={0} max={3} step={0.1} value={varLimit} onChange={(e) => setVarLimit(parseFloat(e.target.value))} showValue={false} className="flex-1" inputClassName="accent-primary" />
                  <TextField type="number" value={varLimit} onChange={(e) => setVarLimit(parseFloat(e.target.value) || 0)} step="0.1" suffix="%" className="w-20" inputClassName="w-16" />
                </div>
              </div>
            </div>
          </Card>

          <Card title="Risk Scenario Simulator">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-white mb-2">Simulated Equity Drop</label>
                  <div className="flex items-center gap-4">
                    <Slider min={0} max={100} step={1} value={equityDrop} onChange={(e) => setEquityDrop(parseFloat(e.target.value) || 0)} showValue={false} className="flex-1" inputClassName="accent-cyan-500" />
                    <TextField type="number" value={equityDrop} onChange={(e) => setEquityDrop(parseFloat(e.target.value) || 0)} suffix="%" className="w-20" inputClassName="w-14" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-white mb-2">Simulated Volatility Increase</label>
                  <div className="flex items-center gap-4">
                    <Slider min={0} max={100} step={1} value={volatilityIncrease} onChange={(e) => setVolatilityIncrease(parseFloat(e.target.value) || 0)} showValue={false} className="flex-1" inputClassName="accent-cyan-500" />
                    <TextField type="number" value={volatilityIncrease} onChange={(e) => setVolatilityIncrease(parseFloat(e.target.value) || 0)} suffix="%" className="w-20" inputClassName="w-14" />
                  </div>
                </div>
                <Button variant="primary" fullWidth onClick={handleRunSimulation} className="mt-2">Run Simulation</Button>
              </div>
              {simulationResults && (
                <div className="rounded-xl bg-dark border border-cyan-500/20 p-4">
                  <div className="space-y-3">
                    <div>
                      <div className="text-sm text-secondary mb-1">Estimated Max Drawdown</div>
                      <div className="text-xl font-bold text-red-400">{simulationResults.maxDrawdown}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-secondary mb-1">Potential Daily Loss</div>
                      <div className="text-xl font-bold text-red-400">{simulationResults.dailyLoss}%</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>

          <Card title="Historical Risk Metrics">
            {riskHistoryLoading ? (
              <div className="h-64 flex items-center justify-center text-secondary text-sm">Loading...</div>
            ) : riskHistory.length > 0 ? (
              <RiskHistoryChart data={riskHistory} />
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-500 text-sm">No historical data yet</div>
            )}
          </Card>

          <Card title="Alert Configuration">
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-white mb-2">Alert on daily P&L loss greater than</label>
                <div className="flex items-center gap-4">
                  <Slider min={0} max={50} step={0.5} value={dailyPnLLossAlert} onChange={(e) => setDailyPnLLossAlert(parseFloat(e.target.value) || 0)} formatValue={(v) => v} suffix="%" className="flex-1" inputClassName="accent-cyan-500" />
                  <TextField type="number" value={dailyPnLLossAlert} onChange={(e) => setDailyPnLLossAlert(parseFloat(e.target.value) || 0)} step={0.1} suffix="%" className="w-24" inputClassName="w-16" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-2">Alert on maximum drawdown greater than</label>
                <div className="flex items-center gap-4">
                  <Slider min={0} max={50} step={0.5} value={maxDrawdownAlert} onChange={(e) => setMaxDrawdownAlert(parseFloat(e.target.value) || 0)} formatValue={(v) => v} suffix="%" className="flex-1" inputClassName="accent-cyan-500" />
                  <TextField type="number" value={maxDrawdownAlert} onChange={(e) => setMaxDrawdownAlert(parseFloat(e.target.value) || 0)} step={0.1} suffix="%" className="w-24" inputClassName="w-16" />
                </div>
              </div>
              <div className="flex items-center justify-between pt-4 border-t border-cyan-500/10">
                <label className="text-sm font-medium text-white">Auto-pause trading on critical alerts</label>
                <Checkbox checked={autoPauseTrading} onChange={() => setAutoPauseTrading((p) => !p)} className="text-secondary" />
              </div>
              <div className="flex gap-3 pt-2">
                <Button variant="secondary" leftIcon={Mail} onClick={handleTestEmailAlert} className="flex-1">Test Email Alert</Button>
                <Button variant="secondary" leftIcon={MessageSquare} onClick={handleTestSMSAlert} className="flex-1">Test SMS Alert</Button>
              </div>
            </div>
          </Card>

          {/* Risk Alerts Table - from real alerts API */}
          {riskAlerts.length > 0 && (
            <Card title="Recent Risk Alerts">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-700/50">
                      <th className="text-left p-2">Time</th>
                      <th className="text-left p-2">Symbol</th>
                      <th className="text-left p-2">Signal</th>
                      <th className="text-right p-2">Price</th>
                      <th className="text-right p-2">Change</th>
                      <th className="text-center p-2">Severity</th>
                      <th className="text-center p-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {riskAlerts.slice(0, 20).map((alert, i) => (
                      <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                        <td className="p-2 text-slate-400">{alert.time || alert.timestamp || "—"}</td>
                        <td className="p-2 text-white font-medium">{alert.symbol || "—"}</td>
                        <td className={`p-2 font-medium ${alert.signal === "SELL" ? "text-red-400" : "text-emerald-400"}`}>{alert.signal || "—"}</td>
                        <td className="p-2 text-right text-white">{alert.price || "—"}</td>
                        <td className={`p-2 text-right ${String(alert.change).startsWith("-") ? "text-red-400" : "text-emerald-400"}`}>{alert.change || "—"}</td>
                        <td className="p-2 text-center">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${alert.severity === "High" ? "bg-red-500/20 text-red-400" : alert.severity === "Medium" ? "bg-yellow-500/20 text-yellow-400" : "bg-emerald-500/20 text-emerald-400"}`}>{alert.severity || "—"}</span>
                        </td>
                        <td className="p-2 text-center">
                          <span className={`px-2 py-0.5 rounded text-[10px] ${alert.status === "Triggered" ? "bg-red-500/20 text-red-400" : "bg-slate-700 text-slate-300"}`}>{alert.status || "—"}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Recommendations - from real API data */}
          {recommendations.length > 0 && (
            <Card title="AI Recommendations">
              <ul className="space-y-2">
                {recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <AlertTriangle className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
                    <span className="text-slate-300">{typeof rec === "string" ? rec : rec.text || rec.message || JSON.stringify(rec)}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>

        {/* Right sidebar: Real-time Risk Monitor */}
        <div className="lg:col-span-1">
          <Card title="Real-time Risk Monitor" className="sticky top-6">
            <div className="space-y-4">
              {[
                { label: "Current Exposure", value: data?.currentExposure != null ? `$${data.currentExposure.toLocaleString()}` : "—", trend: data?.currentExposure > 0 ? "up" : "down", color: "text-emerald-400" },
                { label: "VaR (95%, 1-day)", value: data?.var95 != null ? `$${data.var95.toLocaleString()}` : "—", trend: "down", color: "text-red-400" },
                { label: "Expected Shortfall", value: data?.expectedShortfall != null ? `$${data.expectedShortfall.toLocaleString()}` : "—", trend: "down", color: "text-red-400" },
                { label: "Portfolio Value", value: data?.portfolioValue != null ? `$${data.portfolioValue.toLocaleString()}` : "—", trend: "up", color: "text-emerald-400" },
                { label: "Buying Power", value: data?.buyingPower != null ? `$${data.buyingPower.toLocaleString()}` : "—", trend: "up", color: "text-emerald-400" },
                { label: "Daily P&L", value: data?.dailyPnlPct != null ? `${data.dailyPnlPct >= 0 ? "+" : ""}${data.dailyPnlPct}%` : "—", trend: data?.dailyPnlPct >= 0 ? "up" : "down", color: data?.dailyPnlPct >= 0 ? "text-emerald-400" : "text-red-400" },
              ].map((metric, idx) => (
                <div key={idx} className="rounded-lg bg-secondary/20 border border-cyan-500/10 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <Shield className="w-4 h-4 text-cyan-400/70 shrink-0" />
                      <span className="text-sm text-secondary truncate">{metric.label}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-lg font-bold text-white">{metric.value}</span>
                      {metric.trend === "up" ? (
                        <TrendingUp className={`w-4 h-4 ${metric.color}`} aria-hidden />
                      ) : (
                        <TrendingDown className={`w-4 h-4 ${metric.color}`} aria-hidden />
                      )}
                    </div>
                  </div>
                </div>
              ))}

              <div className={`mt-4 p-4 rounded-xl border ${data?.allWithinLimits !== false ? "bg-emerald-500/10 border-emerald-500/30" : "bg-red-500/10 border-red-500/30"}`}>
                <p className={`text-sm ${data?.allWithinLimits !== false ? "text-emerald-400" : "text-red-400"}`}>
                  {data?.allWithinLimits !== false ? "All risk parameters within acceptable limits" : "Some risk parameters exceed limits"}
                </p>
              </div>

              {data?.alpacaConnected === false && (
                <div className="mt-2 p-3 rounded-lg bg-orange-500/10 border border-orange-500/30">
                  <p className="text-xs text-orange-400">Alpaca API not connected. Risk metrics unavailable.</p>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default RiskIntelligence;
