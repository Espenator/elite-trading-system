// ML INSIGHTS PAGE - Embodier.ai Glass House Intelligence System
// ML model performance, predictions, training status, flywheel metrics
// BACKEND: GET /api/v1/flywheel, GET /api/v1/training/models/compare
import { useState, useMemo } from "react";
import { Brain, RefreshCw, Zap, Target, Clock } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";

/** Normalize training models/compare to MODELS shape */
function normalizeModels(backend) {
  if (!Array.isArray(backend)) return [];
  return backend.map((m, i) => ({
    id: i + 1,
    name: m.model || `Model ${i + 1}`,
    accuracy: m.accuracy ?? 0,
    precision: m.precision ?? 0,
    recall: m.recall ?? 0,
    f1: m.f1Score ?? 0,
    lastTrained: m.trainingTime ? `${m.trainingTime} run` : "—",
    status: "active",
    predictions: 0,
  }));
}

const PREDICTIONS = [
  {
    ticker: "AAPL",
    prediction: "Bullish",
    confidence: 88,
    model: "Pattern Classifier",
    target: "+3.2%",
    timeframe: "5 days",
  },
  {
    ticker: "MSFT",
    prediction: "Bullish",
    confidence: 82,
    model: "Price Predictor",
    target: "+2.8%",
    timeframe: "3 days",
  },
  {
    ticker: "NVDA",
    prediction: "Bearish",
    confidence: 71,
    model: "Sentiment Analyzer",
    target: "-2.1%",
    timeframe: "2 days",
  },
  {
    ticker: "TSLA",
    prediction: "Bullish",
    confidence: 74,
    model: "Pattern Classifier",
    target: "+4.5%",
    timeframe: "7 days",
  },
  {
    ticker: "AMD",
    prediction: "Bullish",
    confidence: 79,
    model: "Price Predictor",
    target: "+3.8%",
    timeframe: "5 days",
  },
];

function MetricBar({ label, value, max = 100 }) {
  const pct = (value / max) * 100;
  const color =
    value >= 85
      ? "bg-emerald-500"
      : value >= 70
        ? "bg-blue-500"
        : "bg-amber-500";
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-500 w-16 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-white w-12 text-right">{value}%</span>
    </div>
  );
}

export default function MLInsights() {
  const [tab, setTab] = useState("models");
  const { data: flywheelData } = useApi("flywheel", { pollIntervalMs: 30000 });
  const {
    data: modelsData,
    loading: modelsLoading,
    error: modelsError,
  } = useApi("training", {
    endpoint: "/models/compare",
    pollIntervalMs: 60000,
  });

  const models = useMemo(() => normalizeModels(modelsData), [modelsData]);
  const flywheel = flywheelData || {};
  const activeModels = models.length;
  const avgAccuracy = models.length
    ? (models.reduce((s, m) => s + m.accuracy, 0) / models.length).toFixed(1)
    : flywheel.accuracy30d != null
      ? (flywheel.accuracy30d * 100).toFixed(1)
      : "—";
  const totalPredictions = flywheel.resolvedSignals ?? 0;
  const flywheelCycles = Array.isArray(flywheel.history)
    ? flywheel.history.length
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Brain}
        title="ML Brain & Flywheel"
        description="Model performance and AI predictions"
      >
        <button className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-500 rounded-xl text-sm font-medium text-white transition-colors">
          <RefreshCw className="w-4 h-4" /> Retrain All
        </button>
      </PageHeader>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Active Models",
            value: String(activeModels),
            icon: Brain,
            color: "text-purple-400",
          },
          {
            label: "Avg Accuracy",
            value:
              typeof avgAccuracy === "string" && avgAccuracy !== "—"
                ? `${avgAccuracy}%`
                : avgAccuracy,
            icon: Target,
            color: "text-emerald-400",
          },
          {
            label: "Total Predictions",
            value: totalPredictions.toLocaleString(),
            icon: Zap,
            color: "text-blue-400",
          },
          {
            label: "Flywheel Cycles",
            value: String(flywheelCycles),
            icon: RefreshCw,
            color: "text-amber-400",
          },
        ].map((s, i) => (
          <div
            key={i}
            className="bg-slate-800/30 border border-white/10 rounded-2xl p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <s.icon className={`w-4 h-4 ${s.color}`} />
              <span className="text-xs text-gray-500">{s.label}</span>
            </div>
            <div className="text-xl font-bold text-white">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-white/10">
        {["models", "predictions", "training"].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-all capitalize ${
              tab === t
                ? "text-blue-400 border-blue-400"
                : "text-gray-500 border-transparent hover:text-white"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Models tab */}
      {tab === "models" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {modelsLoading && models.length === 0 && (
            <div className="col-span-full p-8 text-center text-gray-500">
              Loading models...
            </div>
          )}
          {!modelsLoading && modelsError && models.length === 0 && (
            <div className="col-span-full p-8 text-center text-amber-400">
              Failed to load models. Check GET /api/v1/training/models/compare.
            </div>
          )}
          {models.map((m) => (
            <div
              key={m.id}
              className="bg-slate-800/30 border border-white/10 rounded-2xl p-5"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Brain className="w-5 h-5 text-purple-400" />
                  <span className="text-lg font-semibold text-white">
                    {m.name}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs text-gray-500 capitalize">
                    {m.status}
                  </span>
                </div>
              </div>
              <div className="space-y-2 mb-4">
                <MetricBar label="Accuracy" value={m.accuracy} />
                <MetricBar label="Precision" value={m.precision} />
                <MetricBar label="Recall" value={m.recall} />
                <MetricBar label="F1 Score" value={m.f1} />
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500 pt-3 border-t border-white/5">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" /> {m.lastTrained}
                </span>
                <span>
                  {m.predictions > 0
                    ? `${m.predictions.toLocaleString()} predictions`
                    : "—"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Predictions tab */}
      {tab === "predictions" && (
        <div className="bg-slate-800/30 border border-white/10 rounded-2xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="text-xs text-gray-500 uppercase border-b border-white/5">
                <th className="text-left px-5 py-3">Ticker</th>
                <th className="text-left px-3 py-3">Prediction</th>
                <th className="text-right px-3 py-3">Confidence</th>
                <th className="text-left px-3 py-3">Model</th>
                <th className="text-right px-3 py-3">Target</th>
                <th className="text-right px-5 py-3">Timeframe</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {PREDICTIONS.map((p, i) => (
                <tr key={i} className="hover:bg-white/5 transition-colors">
                  <td className="px-5 py-4 text-sm font-semibold text-white">
                    {p.ticker}
                  </td>
                  <td className="px-3 py-4">
                    <span
                      className={`px-2 py-1 rounded-lg text-xs font-medium ${p.prediction === "Bullish" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}
                    >
                      {p.prediction}
                    </span>
                  </td>
                  <td className="px-3 py-4 text-sm text-right">
                    <span
                      className={`font-bold ${p.confidence >= 80 ? "text-emerald-400" : "text-amber-400"}`}
                    >
                      {p.confidence}%
                    </span>
                  </td>
                  <td className="px-3 py-4 text-xs text-gray-400">{p.model}</td>
                  <td
                    className={`px-3 py-4 text-sm font-medium text-right ${p.target.startsWith("+") ? "text-emerald-400" : "text-red-400"}`}
                  >
                    {p.target}
                  </td>
                  <td className="px-5 py-4 text-sm text-gray-500 text-right">
                    {p.timeframe}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Training tab */}
      {tab === "training" && (
        <div className="space-y-4">
          <div className="bg-slate-800/30 border border-white/10 rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">
              Self-Learning Flywheel
            </h3>
            <div className="space-y-4">
              {[
                {
                  step: "Data Ingestion",
                  desc: "Market data, YouTube transcripts, news feeds",
                  status: "complete",
                  progress: 100,
                },
                {
                  step: "Feature Engineering",
                  desc: "Technical indicators, sentiment scores",
                  status: "complete",
                  progress: 100,
                },
                {
                  step: "Model Training",
                  desc: "Pattern classifier retraining cycle #142",
                  status: "running",
                  progress: 67,
                },
                {
                  step: "Validation",
                  desc: "Backtesting on recent market data",
                  status: "pending",
                  progress: 0,
                },
                {
                  step: "Deployment",
                  desc: "Push updated models to production",
                  status: "pending",
                  progress: 0,
                },
              ].map((s, i) => (
                <div key={i} className="flex items-center gap-4">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                      s.status === "complete"
                        ? "bg-emerald-500/20 text-emerald-400"
                        : s.status === "running"
                          ? "bg-blue-500/20 text-blue-400"
                          : "bg-slate-700 text-gray-500"
                    }`}
                  >
                    {i + 1}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-white">
                      {s.step}
                    </div>
                    <div className="text-xs text-gray-500">{s.desc}</div>
                    {s.status === "running" && (
                      <div className="h-1 bg-slate-700 rounded-full mt-2 overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full animate-pulse"
                          style={{ width: `${s.progress}%` }}
                        />
                      </div>
                    )}
                  </div>
                  <span
                    className={`text-xs font-medium capitalize ${
                      s.status === "complete"
                        ? "text-emerald-400"
                        : s.status === "running"
                          ? "text-blue-400"
                          : "text-gray-500"
                    }`}
                  >
                    {s.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
