import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Brain, RotateCw } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import Button from "../components/ui/Button";
import { useApi } from "../hooks/useApi";

/**
 * ML Brain & Flywheel - Production Ready
 * Uses useApi hook for all data fetching with polling.
 * API endpoints: flywheel (performance, signals/staged, flywheel-logs)
 * Route: /ml-brain
 */
export default function MLBrainFlywheel() {
  const { data: perfData, loading: perfLoading } = useApi("flywheel", {
    endpoint: "/performance",
    pollIntervalMs: 900000,
  });
  const { data: infData, loading: infLoading } = useApi("flywheel", {
    endpoint: "/signals/staged",
    pollIntervalMs: 60000,
  });
  const { data: logData, loading: logLoading } = useApi("flywheel", {
    endpoint: "/logs",
    pollIntervalMs: 60000,
  });
  const { data: kpiData } = useApi("flywheel", {
    endpoint: "/kpis",
    pollIntervalMs: 60000,
  });

  const performanceData = Array.isArray(perfData) ? perfData : [];
  const liveInferences = Array.isArray(infData) ? infData : [];
  const flywheelLogs = Array.isArray(logData) ? logData : [];
  const kpis = kpiData || {};

  const loading = perfLoading && performanceData.length === 0;

  if (loading) {
    return (
      <div className="bg-[#0a0a0f] text-slate-50 min-h-screen flex items-center justify-center">
        <div className="text-cyan-500 text-xl animate-pulse">
          Loading ML Brain & Flywheel...
        </div>
      </div>
    );
  }

  const kpiCards = [
    {
      title: "Stage 4 Active Models",
      val: kpis.activeModels ?? "--",
      icon: "\uD83D\uDCDA",
      color: "text-purple-500",
      bg: "bg-purple-500/15",
      sub: kpis.modelType ?? "Loading...",
    },
    {
      title: "Walk-Forward Accuracy",
      val: kpis.walkForwardAccuracy ? `${kpis.walkForwardAccuracy}%` : "--",
      icon: "\uD83C\uDFAF",
      color: "text-emerald-500",
      bg: "bg-emerald-500/15",
      sub: kpis.walkForwardWindow ?? "Loading...",
    },
    {
      title: "Live Signals Today",
      val: kpis.liveSignalsToday ?? liveInferences.length ?? "--",
      icon: "\u26A1",
      color: "text-cyan-500",
      bg: "bg-cyan-500/15",
      sub: "Stage 3 Ignitions",
    },
    {
      title: "Flywheel Validations",
      val: kpis.flywheelValidations ?? flywheelLogs.length ?? "--",
      icon: "\uD83D\uDD04",
      color: "text-amber-500",
      bg: "bg-amber-500/15",
      sub: "Trade Outcomes Logged",
    },
    {
      title: "System Health",
      val: kpis.systemHealth ?? "--",
      icon: "\u2705",
      color: "text-emerald-500",
      bg: "bg-emerald-500/15",
      sub: kpis.healthDetail ?? "Checking...",
    },
    {
      title: "Prediction Confidence",
      val: kpis.predictionConfidence ? `>${kpis.predictionConfidence}%` : "--",
      icon: "\uD83D\uDCC8",
      color: "text-cyan-500",
      bg: "bg-cyan-500/15",
      sub: "Minimum Threshold",
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Brain}
        title="ML Brain & Flywheel"
        description="Walk-forward accuracy, staged inferences, and flywheel learning log"
      >
        <Button
          variant="outline"
          size="lg"
          leftIcon={RotateCw}
          className="bg-cyan-500/15 border-cyan-500 text-cyan-500 hover:bg-cyan-500/30 font-bold"
        >
          Retrain Models
        </Button>
      </PageHeader>

      {/* KPI CARDS */}
      <div className="grid grid-cols-6 gap-6 mb-8">
        {kpiCards.map((kpi, idx) => (
          <div
            key={idx}
            className="bg-[#13131a] border border-[#23232f] p-6 rounded-lg"
          >
            <p className="text-slate-400 text-sm mb-2">{kpi.title}</p>
            <div className="flex justify-between items-end mb-2">
              <h3 className="text-3xl font-bold">{kpi.val}</h3>
              <div
                className={`w-12 h-12 rounded flex items-center justify-center text-2xl ${kpi.bg} ${kpi.color}`}
              >
                {kpi.icon}
              </div>
            </div>
            <p className={`text-xs ${kpi.color}`}>{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* MAIN CONTENT ROWS */}
      <div className="grid grid-cols-12 gap-6">
        {/* CHART PANEL */}
        <div className="col-span-7 bg-[#13131a] border border-[#23232f] p-6 rounded-lg">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold">
              {"\uD83D\uDCC8"} Model Performance Tracking
            </h2>
            <button className="bg-cyan-500/15 border border-cyan-500 text-cyan-500 px-4 py-2 rounded text-sm">
              Model Matrix
            </button>
          </div>
          <p className="text-slate-400 text-sm font-bold tracking-widest mb-4">
            252-DAY WALK-FORWARD ACCURACY {"\u2022"} XGBOOST VS ENSEMBLE
          </p>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#23232f" />
                <XAxis dataKey="day" stroke="#64748b" />
                <YAxis domain={[60, 90]} stroke="#64748b" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#13131a",
                    borderColor: "#23232f",
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="xgboost_acc"
                  name="XGBoost v3.2 (Prod)"
                  stroke="#10b981"
                  strokeWidth={3}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="rf_acc"
                  name="Random Forest (Val)"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* INFERENCE TABLE */}
        <div className="col-span-5 bg-[#13131a] border border-[#23232f] p-6 rounded-lg overflow-y-auto max-h-[550px]">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold">
              {"\u26A1"} Stage 4: ML Probability Ranking
            </h2>
            <button className="text-slate-300">Filter {"\u2304"}</button>
          </div>
          <table className="w-full text-left">
            <thead className="text-slate-400 text-xs tracking-wider border-b border-[#23232f]">
              <tr>
                <th className="pb-3">SYMBOL</th>
                <th className="pb-3">DIR</th>
                <th className="pb-3">WIN PROB</th>
                <th className="pb-3">COMPRESSION</th>
                <th className="pb-3">VELEZ SCORE</th>
                <th className="pb-3">VOL RATIO</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#23232f]">
              {liveInferences.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No staged inferences available
                  </td>
                </tr>
              )}
              {liveInferences.map((row, i) => (
                <tr key={i} className="text-sm">
                  <td className="py-4 font-bold text-lg">{row.symbol}</td>
                  <td className="py-4">
                    <span
                      className={`px-2 py-1 rounded text-xs font-bold ${row.dir === "LONG" ? "bg-emerald-500/15 text-emerald-500" : "bg-red-500/15 text-red-500"}`}
                    >
                      {row.dir}
                    </span>
                  </td>
                  <td className="py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-[#23232f] rounded overflow-hidden">
                        <div
                          className={`h-full ${row.dir === "LONG" ? "bg-emerald-500" : "bg-red-500"}`}
                          style={{ width: `${row.prob}%` }}
                        ></div>
                      </div>
                      <span className="font-bold">{row.prob}%</span>
                    </div>
                  </td>
                  <td className="py-4 text-slate-400">
                    {row.compression_days} Days
                  </td>
                  <td className="py-4 text-slate-400">{row.velez_score}%</td>
                  <td className="py-4 text-slate-400">{row.vol_ratio}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* FLYWHEEL LOG SECTION */}
      <div className="mt-6 bg-[#13131a] border border-[#23232f] p-6 rounded-lg">
        <h2 className="text-2xl font-bold mb-4">
          {"\uD83D\uDD04"} Flywheel Learning Log (Trade Outcomes)
        </h2>
        <p className="text-slate-400 text-sm mb-4">
          Auto-recording positive trading outcomes, retraining and adjusting
          feature weights.
        </p>
        <div className="space-y-2 max-h-[300px] overflow-y-auto text-xs">
          {flywheelLogs.length === 0 && (
            <p className="text-slate-500 py-4">No flywheel logs yet</p>
          )}
          {flywheelLogs.map((log, i) => (
            <div
              key={i}
              className={`${log.level === "WARNING" ? "text-amber-400" : log.level === "SUCCESS" ? "text-emerald-400" : "text-slate-400"}`}
            >
              [{log.timestamp}] [{log.level}] {log.message}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
