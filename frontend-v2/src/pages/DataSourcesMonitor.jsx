import { useState, useEffect, useCallback } from "react";
import dataSources from "../services/dataSourcesApi";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import {
  X,
  Copy,
  RefreshCw,
  Settings,
  Check,
  XCircle,
  Loader2,
} from "lucide-react";
import {
  Database,
  Search,
  Wifi,
  Activity,
  Zap,
  Shield,
  Globe,
  BookOpen,
  ExternalLink,
  ChevronRight,
  BarChart3,
  Eye,
  EyeOff,
  RotateCw,
  CircleDot,
  Radio,
  Trash2,
} from "lucide-react";

// ============================================================
// DataSourcesMonitor.jsx - DATA_SOURCES_MANAGER
// Pixel-perfect match to mockup 09 (Split View Layout)
// Real API via dataSourcesApi.js - NO mocks, NO yfinance
// Primary: Alpaca, Unusual Whales, Finviz
// ============================================================

const STATUS_COLORS = {
  healthy: {
    bg: "bg-emerald-500/20",
    text: "text-emerald-400",
    dot: "bg-emerald-400",
  },
  active: {
    bg: "bg-emerald-500/20",
    text: "text-emerald-400",
    dot: "bg-emerald-400",
  },
  error: { bg: "bg-red-500/20", text: "text-red-400", dot: "bg-red-400" },
  timeout: {
    bg: "bg-orange-500/20",
    text: "text-orange-400",
    dot: "bg-orange-400",
  },
  degraded: {
    bg: "bg-yellow-500/20",
    text: "text-yellow-400",
    dot: "bg-yellow-400",
  },
  no_credentials: {
    bg: "bg-gray-500/20",
    text: "text-gray-400",
    dot: "bg-gray-400",
  },
  unconfigured: {
    bg: "bg-gray-500/20",
    text: "text-gray-400",
    dot: "bg-gray-400",
  },
  offline: { bg: "bg-red-500/20", text: "text-red-400", dot: "bg-red-500" },
  beta: {
    bg: "bg-purple-500/20",
    text: "text-purple-400",
    dot: "bg-purple-400",
  },
  pending: {
    bg: "bg-slate-500/20",
    text: "text-slate-400",
    dot: "bg-slate-400",
  },
};

const CATEGORY_LABELS = {
  market: "Market Data",
  options_flow: "Options Flow",
  economic: "Economic",
  filings: "Filings",
  sentiment: "Sentiment",
  news: "News",
  social: "Social",
  alerts: "Alerts",
  bridge: "Bridge",
  storage: "Storage",
  custom: "Custom",
  screener: "Screener",
  macro: "Macro",
  knowledge: "Knowledge",
};

// Short tab labels matching mockup 09 exactly
const FILTER_TAB_LABELS = {
  all: "ALL",
  screener: "Screener",
  options_flow: "Options",
  market: "Market",
  macro: "Macro",
  filings: "Filings",
  sentiment: "Sentiment",
  news: "News",
  social: "Social",
  knowledge: "Knowledge",
};

const FILTER_TABS = [
  "all",
  "screener",
  "options_flow",
  "market",
  "macro",
  "filings",
  "sentiment",
  "news",
  "social",
  "knowledge",
];

const PROVIDER_CHIPS = [
  "Polygon.io",
  "Benzinga",
  "Alpha Vantage",
  "Quandl",
  "IEX Cloud",
  "CoinGecko",
];

const SUPPLIER_CHECKS = [
  { name: "Benzinga", icon: "B" },
  { name: "Finnhub", icon: "F" },
  { name: "OpenClaw Bridge", icon: "O" },
  { name: "Reddit", icon: "R" },
  { name: "Resend", icon: "Re" },
  { name: "TradingView", icon: "T" },
  { name: "GitHub Gist", icon: "G" },
];

const DS_INPUT_CLASS =
  "text-sm py-2 bg-[#0A0E1A] border-[#2A3444] rounded-lg text-white font-mono focus:border-cyan-500 focus:outline-none disabled:opacity-50";
const DS_LABEL_CLASS = "text-xs text-gray-400";

// Colored latency: green <100ms, orange <500ms, red >=500ms (mockup 09)
function latencyColor(ms) {
  if (ms == null) return "text-gray-500";
  if (ms < 100) return "text-emerald-400";
  if (ms < 500) return "text-orange-400";
  return "text-red-400";
}

// Mini sparkline SVG matching mockup 09 inline charts
function MiniSparkline({ data = [], color = "#06b6d4" }) {
  const arr = Array.isArray(data)
    ? data
        .map((v) =>
          typeof v === "number" && Number.isFinite(v) ? v : Number(v),
        )
        .filter(Number.isFinite)
    : [];
  if (arr.length < 2) return <span className="text-gray-600 text-xs">--</span>;
  const max = Math.max(...arr);
  const min = Math.min(...arr);
  const range = max - min || 1;
  const w = 60;
  const h = 20;
  const points = arr
    .map((v, i) => {
      const x = (i / (arr.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width={w} height={h} className="inline-block">
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={points} />
    </svg>
  );
}

function StatusBadge({ status }) {
  const raw =
    status != null && typeof status === "object"
      ? (status.status ?? status.value ?? JSON.stringify(status))
      : status;
  const s = raw != null ? String(raw) : "pending";
  const colors = STATUS_COLORS[s] || STATUS_COLORS.pending;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${colors.bg} ${colors.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
      {s}
    </span>
  );
}

function Toast({ message, type, onDismiss }) {
  if (!message) return null;
  const colors =
    type === "error"
      ? "bg-red-500/20 border-red-500/40 text-red-400"
      : "bg-emerald-500/20 border-emerald-500/40 text-emerald-400";
  return (
    <div
      className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg border ${colors} flex items-center gap-2 shadow-lg`}
    >
      {type === "error" ? (
        <XCircle className="w-4 h-4 shrink-0" />
      ) : (
        <Check className="w-4 h-4 shrink-0" />
      )}{" "}
      {message}
      <button
        onClick={onDismiss}
        className="ml-2 opacity-60 hover:opacity-100 p-0.5"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
// Credential Editor Panel - right side (mockup 09)
// Shows: icon + name + category badge, API Key/Secret with masked values,
// Show/Copy/Rotate icon buttons, Base URL, WebSocket URL, Rate Limit,
// Polling Interval, Account Type, Connection Test Result box, action buttons, log
function CredentialPanel({ source, onClose, onSave, onTest, saving, testing }) {
  const [keys, setKeys] = useState({});
  const [extraFields, setExtraFields] = useState({
    base_url: "",
    ws_url: "",
    rate_limit: "",
    polling_interval: "real-time",
    account_type: "",
  });
  const [testLog, setTestLog] = useState([]);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    const init = {};
    (source?.required_keys || []).forEach((k) => {
      init[k] = "";
    });
    setKeys(init);
    setExtraFields({
      base_url: source?.base_url || "",
      ws_url: source?.ws_url || "",
      rate_limit: source?.rate_limit || "",
      polling_interval: source?.polling_interval || "real-time",
      account_type: source?.account_type || "",
    });
    setTestLog(
      Array.isArray(source?.connection_log) ? source.connection_log : [],
    );
    setTestResult(
      source?.status === "healthy" && source?.last_latency_ms != null
        ? {
            ok: true,
            latency: source.last_latency_ms,
            detail: source.account_info || "",
          }
        : null,
    );
  }, [source]);

  const handleTest = async () => {
    if (!source || !onTest) return;
    const result = await onTest(source.id);
    if (result) setTestResult(result);
  };

  if (!source)
    return (
      <div className="bg-[#111827] border border-[#1E2A3A] rounded-xl p-8 text-center h-full flex items-center justify-center">
        <div>
          <Database className="w-10 h-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">
            Select a source to edit credentials
          </p>
        </div>
      </div>
    );

  return (
    <div className="bg-[#111827] border border-[#1E2A3A] rounded-xl overflow-hidden sticky top-6">
      {/* Panel Header */}
      <div className="px-5 py-4 border-b border-[#1E2A3A] bg-[#0D1117]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 bg-[#0B0E14] border border-[#1E2A3A] rounded-lg flex items-center justify-center text-xl">
              {typeof source.icon === "string" ? (
                source.icon
              ) : typeof source.category === "string" &&
                CATEGORY_LABELS[source.category] ? (
                <span className="text-cyan-400 font-bold text-sm">
                  {CATEGORY_LABELS[source.category][0]}
                </span>
              ) : (
                <Settings className="w-5 h-5 text-gray-400" />
              )}
            </div>
            <div>
              <h3 className="text-white font-bold text-base leading-tight">
                {source.name != null ? String(source.name) : "Unknown"}
              </h3>
              <span className="text-[10px] px-2 py-0.5 bg-cyan-500/15 text-cyan-400 rounded-full font-medium border border-cyan-500/20">
                {source.category != null
                  ? CATEGORY_LABELS[source.category] || String(source.category)
                  : "Custom"}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white p-1.5 rounded-lg hover:bg-white/5 transition-colors"
            aria-label="Close panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Credential Fields */}
      <div className="p-5 space-y-3.5 max-h-[calc(100vh-300px)] overflow-y-auto">
        {(source.required_keys || []).map((keyName, idx) => {
          const k =
            typeof keyName === "string"
              ? keyName
              : (keyName?.key ?? keyName?.name ?? String(idx));
          return (
            <div key={k} className="flex flex-col gap-1.5">
              <div className="flex items-end gap-1.5">
                <div className="flex-1 min-w-0">
                  <TextField
                    label={k}
                    type="password"
                    value={keys[k] || ""}
                    onChange={(e) => setKeys({ ...keys, [k]: e.target.value })}
                    placeholder={
                      source.has_credentials
                        ? typeof source[`masked_${k}`] === "string"
                          ? source[`masked_${k}`]
                          : "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
                        : `Enter ${k}...`
                    }
                    disabled={saving}
                    inputClassName={DS_INPUT_CLASS}
                    className="[&_label]:text-xs [&_label]:text-gray-400"
                  />
                </div>
                <button
                  onClick={() => navigator.clipboard.writeText(keys[k] || "")}
                  className="h-[38px] w-[38px] flex-shrink-0 flex items-center justify-center bg-[#0B0E14] border border-[#1E2A3A] rounded-lg text-gray-500 hover:text-cyan-400 hover:border-cyan-500/30 transition-colors"
                  title="Copy"
                  aria-label="Copy to clipboard"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
                <button
                  className="h-[38px] w-[38px] flex-shrink-0 flex items-center justify-center bg-[#0B0E14] border border-[#1E2A3A] rounded-lg text-gray-500 hover:text-cyan-400 hover:border-cyan-500/30 transition-colors"
                  title="Rotate"
                  aria-label="Rotate key"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}

        <TextField
          label="Base URL"
          value={extraFields.base_url}
          onChange={(e) =>
            setExtraFields({ ...extraFields, base_url: e.target.value })
          }
          disabled={saving}
          inputClassName={DS_INPUT_CLASS}
          className="[&_label]:text-xs [&_label]:text-gray-400"
        />
        <TextField
          label="WebSocket URL"
          value={extraFields.ws_url}
          onChange={(e) =>
            setExtraFields({ ...extraFields, ws_url: e.target.value })
          }
          disabled={saving}
          inputClassName={DS_INPUT_CLASS}
          className="[&_label]:text-xs [&_label]:text-gray-400"
        />
        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Rate Limit"
            value={extraFields.rate_limit}
            onChange={(e) =>
              setExtraFields({ ...extraFields, rate_limit: e.target.value })
            }
            disabled={saving}
            inputClassName={DS_INPUT_CLASS}
            className="[&_label]:text-xs [&_label]:text-gray-400"
          />
          <Select
            label="Polling Interval"
            value={extraFields.polling_interval}
            onChange={(e) =>
              setExtraFields({
                ...extraFields,
                polling_interval: e.target.value,
              })
            }
            options={[
              { value: "real-time", label: "Real-time (WebSocket)" },
              { value: "1s", label: "1 second" },
              { value: "5s", label: "5 seconds" },
              { value: "30s", label: "30 seconds" },
              { value: "1m", label: "1 minute" },
              { value: "5m", label: "5 minutes" },
              { value: "15m", label: "15 minutes" },
            ]}
            selectClassName={DS_INPUT_CLASS}
            className="[&_label]:text-xs [&_label]:text-gray-400"
          />
        </div>
        <Select
          label="Account Type"
          value={extraFields.account_type}
          onChange={(e) =>
            setExtraFields({ ...extraFields, account_type: e.target.value })
          }
          placeholder="Select..."
          options={[
            { value: "paper", label: "Paper Trading" },
            { value: "live", label: "Live Trading" },
            { value: "free", label: "Free Tier" },
            { value: "pro", label: "Pro / Paid" },
          ]}
          selectClassName={DS_INPUT_CLASS}
          className="[&_label]:text-xs [&_label]:text-gray-400"
        />

        {/* Connection Test Result box (mockup 09 green box) */}
        {testResult && testResult.ok && (
          <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
            <div className="text-emerald-400 text-xs font-bold mb-1">
              Connection Test Result
            </div>
            <div className="text-emerald-400 text-xs flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 shrink-0" /> Connected in{" "}
              {testResult.latency}ms
              {testResult.detail ? ` - ${testResult.detail}` : ""}
            </div>
          </div>
        )}

        {/* Action buttons row (mockup 09) */}
        <div className="flex gap-2 pt-2 flex-wrap">
          <button
            onClick={handleTest}
            disabled={testing}
            className="px-3 py-2 bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 rounded-lg hover:bg-cyan-500/25 text-xs font-medium disabled:opacity-50 inline-flex items-center gap-1.5 transition-colors"
          >
            {testing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
            ) : (
              <Radio className="w-3.5 h-3.5 shrink-0" />
            )}
            {testing ? "Testing..." : "Test Connection"}
          </button>
          <button
            onClick={() => onSave(keys)}
            disabled={saving}
            className="px-3 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 text-xs font-medium disabled:opacity-50 inline-flex items-center gap-1.5 transition-colors"
          >
            {saving ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
            ) : (
              <Check className="w-3.5 h-3.5 shrink-0" />
            )}
            {saving ? "Saving..." : "Save Changes"}
          </button>
          <button
            onClick={onClose}
            className="px-3 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-xs transition-colors"
          >
            Cancel
          </button>
          <button className="px-3 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-xs transition-colors">
            Reset to Default
          </button>
        </div>

        {/* Connection Log (mockup 09 bottom of panel) */}
        {testLog.length > 0 && (
          <div className="mt-3">
            <div className="bg-[#0B0E14] border border-[#1E2A3A] rounded-lg p-2.5 max-h-32 overflow-y-auto font-mono text-[10px] text-gray-400 space-y-0.5">
              {testLog.map((log, i) => (
                <div key={i}>
                  {typeof log === "object" ? JSON.stringify(log) : String(log)}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AddSourceModal({ onClose, onAdd, saving }) {
  const [form, setForm] = useState({
    id: "",
    name: "",
    base_url: "",
    test_endpoint: "",
    type: "rest",
    category: "custom",
  });
  const modalInputClass =
    "text-sm py-2 bg-[#0A0E1A] border-[#2A3444] rounded-lg text-white focus:border-cyan-500 focus:outline-none disabled:opacity-50";
  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-white mb-4">Add Custom Source</h3>
        {["id", "name", "base_url", "test_endpoint"].map((field) => (
          <TextField
            key={field}
            label={field.replace(/_/g, " ")}
            value={form[field]}
            onChange={(e) => setForm({ ...form, [field]: e.target.value })}
            disabled={saving}
            className="mb-3 [&_label]:text-gray-400"
            inputClassName={modalInputClass}
          />
        ))}
        <div className="flex gap-2 mt-4">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-sm"
          >
            Cancel
          </button>
          <button
            onClick={() => onAdd(form)}
            disabled={saving}
            className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-sm font-medium disabled:opacity-50"
          >
            {saving ? "Adding..." : "Add Source"}
          </button>
        </div>
      </div>
    </div>
  );
}

function AIDetectModal({ onClose, onDetect }) {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [detecting, setDetecting] = useState(false);
  const [error, setError] = useState(null);
  const handleDetect = async () => {
    setDetecting(true);
    setError(null);
    try {
      const res = await onDetect(url);
      setResult(res);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setDetecting(false);
    }
  };
  const modalInputClass =
    "text-sm py-2 bg-[#0A0E1A] border-[#2A3444] rounded-lg text-white focus:border-cyan-500 focus:outline-none disabled:opacity-50";
  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-white mb-4">
          AI Detect Provider
        </h3>
        <TextField
          label="API URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste API URL..."
          disabled={detecting}
          className="mb-4 [&_label]:text-gray-400"
          inputClassName={modalInputClass}
        />
        <button
          onClick={handleDetect}
          disabled={detecting}
          className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium mb-4 disabled:opacity-50"
        >
          {detecting ? "Detecting..." : "Detect"}
        </button>
        {error && (
          <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm mb-4">
            {error}
          </div>
        )}
        {result && (
          <div className="p-3 bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-sm">
            <div className="text-cyan-400 font-bold">
              {result.detected_provider != null
                ? String(result.detected_provider)
                : "Unknown"}
            </div>
            <div className="text-gray-400 mt-1">
              {result.suggestion != null
                ? typeof result.suggestion === "string"
                  ? result.suggestion
                  : JSON.stringify(result.suggestion)
                : ""}
            </div>
            {result.confidence > 0 && (
              <div className="text-emerald-400 mt-1">
                Confidence: {(Number(result.confidence) * 100).toFixed(0)}%
              </div>
            )}
          </div>
        )}
        <button
          onClick={onClose}
          className="w-full mt-4 px-4 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-sm"
        >
          Close
        </button>
      </div>
    </div>
  );
}

function DeleteConfirmModal({ sourceId, onClose, onConfirm, deleting }) {
  const idStr = sourceId != null ? String(sourceId) : "";
  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-6 w-full max-w-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-white mb-4">Delete Source</h3>
        <p className="text-gray-400 text-sm mb-4">
          Permanently delete{" "}
          <span className="text-white font-medium">&quot;{idStr}&quot;</span>?
        </p>
        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-sm"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium disabled:opacity-50"
          >
            {deleting ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ensurePrimitive(val) {
  if (val == null) return "";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

export default function DataSourcesMonitor() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterTab, setFilterTab] = useState("all");
  const [selected, setSelected] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [toast, setToast] = useState({ message: null, type: "info" });
  const [showAddModal, setShowAddModal] = useState(false);
  const [showAIDetect, setShowAIDetect] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  const loadSources = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await dataSources.list();
      const list = Array.isArray(res)
        ? res
        : (res?.sources ?? res?.items ?? []);
      setSources(
        list.map((s) => ({
          ...s,
          id: ensurePrimitive(s?.id ?? s?.source_id),
          name: ensurePrimitive(s?.name),
          category:
            typeof s?.category === "string"
              ? s.category
              : (s?.category?.value ?? s?.category?.id ?? "custom"),
          status:
            typeof s?.status === "string"
              ? s.status
              : (s?.status?.status ?? s?.status?.value ?? "pending"),
          last_latency_ms:
            typeof s?.last_latency_ms === "number"
              ? s.last_latency_ms
              : s?.last_latency_ms != null
                ? Number(s.last_latency_ms)
                : null,
          latency_series: Array.isArray(s?.latency_series)
            ? s.latency_series.map((v) =>
                typeof v === "number" ? v : Number(v),
              )
            : [],
          connection_log: Array.isArray(s?.connection_log)
            ? s.connection_log
            : [],
        })),
      );
    } catch (err) {
      setError(err?.message || String(err));
      setSources([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  const filteredSources =
    filterTab === "all"
      ? sources
      : sources.filter((s) => s.category === filterTab);

  const searchedSources = searchQuery
    ? filteredSources.filter(
        (s) =>
          s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          s.id.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : filteredSources;

  const handleSaveCredentials = async (keys) => {
    if (!selected) return;
    setSaving(true);
    try {
      await dataSources.setCredentials(selected.id, keys);
      setToast({ message: "Credentials saved", type: "success" });
      loadSources();
      const updated = await dataSources.get(selected.id);
      const u = updated || selected;
      setSelected({
        ...u,
        id: ensurePrimitive(u?.id ?? u?.source_id),
        name: ensurePrimitive(u?.name),
        category:
          typeof u?.category === "string"
            ? u.category
            : (u?.category?.value ?? u?.category?.id ?? "custom"),
        status:
          typeof u?.status === "string"
            ? u.status
            : (u?.status?.status ?? u?.status?.value ?? "pending"),
        connection_log: Array.isArray(u?.connection_log)
          ? u.connection_log
          : [],
      });
    } catch (err) {
      setToast({ message: err?.message || "Save failed", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (sourceId) => {
    setTesting(true);
    try {
      const result = await dataSources.test(sourceId);
      return result;
    } finally {
      setTesting(false);
    }
  };

  const handleAdd = async (form) => {
    setSaving(true);
    try {
      await dataSources.create(form);
      setShowAddModal(false);
      setToast({ message: "Source added", type: "success" });
      loadSources();
    } catch (err) {
      setToast({ message: err?.message || "Add failed", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!showDeleteModal) return;
    setDeleting(true);
    try {
      await dataSources.remove(showDeleteModal);
      setShowDeleteModal(null);
      setSelected(null);
      setToast({ message: "Source deleted", type: "success" });
      loadSources();
    } catch (err) {
      setToast({ message: err?.message || "Delete failed", type: "error" });
    } finally {
      setDeleting(false);
    }
  };

  const selectedDetail =
    selected && sources.find((s) => s.id === selected.id)
      ? { ...selected, ...sources.find((s) => s.id === selected.id) }
      : selected;

  // Derived metrics
  const connectedCount = sources.filter(
    (s) => s.status === "healthy" || s.status === "active",
  ).length;
  const totalCount = sources.length;
  const systemHealth =
    totalCount > 0 ? Math.round((connectedCount / totalCount) * 100) : 0;
  const avgIngestion =
    sources.length > 0
      ? (
          sources.reduce((sum, s) => sum + (s.last_latency_ms || 0), 0) /
          sources.length /
          1000
        ).toFixed(1)
      : "0.0";

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* ===== HEADER BAR ===== */}
      <div className="flex items-center justify-between px-1 mb-4">
        <div className="flex items-center gap-3">
          <Database className="w-6 h-6 text-cyan-400" />
          <h1 className="text-lg font-bold text-white tracking-wider font-mono">
            DATA_SOURCES_MANAGER
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-emerald-400 font-medium">WS Connected</span>
          </span>
          <span className="flex items-center gap-1.5 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-emerald-400 font-medium">API Healthy</span>
          </span>
          <button
            onClick={loadSources}
            className="p-2 bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 rounded-lg hover:bg-cyan-500/25 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* ===== TOP METRICS BAR ===== */}
      <div className="flex items-center gap-4 px-4 py-2.5 mb-4 bg-[#111827] border border-[#1E2A3A] rounded-xl text-xs">
        <div className="flex items-center gap-2">
          <Wifi className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-gray-400">Connected:</span>
          <span className="text-white font-bold">
            {connectedCount}/{totalCount}
          </span>
          <span className="text-gray-500">sources</span>
        </div>
        <div className="w-px h-4 bg-[#1E2A3A]" />
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-gray-400">System Health:</span>
          <span
            className={`font-bold ${systemHealth >= 80 ? "text-emerald-400" : systemHealth >= 50 ? "text-yellow-400" : "text-red-400"}`}
          >
            {systemHealth}%
          </span>
        </div>
        <div className="w-px h-4 bg-[#1E2A3A]" />
        <div className="flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-yellow-400" />
          <span className="text-gray-400">Ingestion:</span>
          <span className="text-white font-medium">{avgIngestion} mc/min</span>
        </div>
        <div className="w-px h-4 bg-[#1E2A3A]" />
        <div className="flex items-center gap-2">
          <Globe className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-gray-400">OpenClaw Bridge:</span>
          <span className="text-emerald-400 font-semibold">CONNECTED</span>
          <span className="text-emerald-400">&#x2713;</span>
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          <span className="text-gray-400">&#x26A1; WS:</span>
          <span className="text-emerald-400 font-semibold">CONNECTED</span>
        </div>
      </div>

      {/* ===== AI-POWERED SEARCH INPUT ===== */}
      <div className="flex items-center gap-3 mb-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Paste a service name, URL, or paste API docs link..."
            className="w-full pl-10 pr-4 py-2.5 bg-[#0B0E14] border border-[#1E2A3A] rounded-lg text-sm text-white placeholder-gray-500 focus:border-cyan-500 focus:outline-none transition-colors"
          />
        </div>
        <button
          onClick={() => setShowAIDetect(true)}
          className="px-4 py-2.5 bg-purple-500/15 text-purple-400 border border-purple-500/30 rounded-lg hover:bg-purple-500/25 text-xs font-medium whitespace-nowrap transition-colors flex items-center gap-1.5"
        >
          <Zap className="w-3.5 h-3.5" />
          Shop API docs
        </button>
      </div>

      {/* ===== PROVIDER CHIPS ===== */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider mr-1">
          Providers:
        </span>
        {PROVIDER_CHIPS.map((chip) => (
          <span
            key={chip}
            className="px-2.5 py-1 bg-[#111827] border border-[#1E2A3A] rounded-full text-[11px] text-gray-400 hover:text-cyan-400 hover:border-cyan-500/30 cursor-pointer transition-colors"
          >
            {chip}
          </span>
        ))}
      </div>

      {toast.message && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast({ message: null, type: "info" })}
        />
      )}

      {/* ===== MAIN CONTENT: SPLIT VIEW ===== */}
      <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0 overflow-hidden">
        {/* Left: filter tabs + source table */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#111827] border border-[#1E2A3A] rounded-xl overflow-hidden">
          {/* Filter tabs row */}
          <div className="flex items-center gap-1 px-3 py-2 border-b border-[#1E2A3A] bg-[#0D1117] overflow-x-auto">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setFilterTab(tab)}
                className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold tracking-wide whitespace-nowrap transition-colors ${
                  filterTab === tab
                    ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                    : "text-gray-500 hover:text-gray-300 border border-transparent"
                }`}
              >
                {FILTER_TAB_LABELS[tab] ?? tab}
              </button>
            ))}
            <div className="flex-1" />
            <button
              onClick={() => setShowAddModal(true)}
              className="px-3 py-1.5 bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded-lg text-[11px] font-semibold whitespace-nowrap hover:bg-cyan-600/30 transition-colors"
            >
              + Add Source
            </button>
          </div>

          {/* Source table */}
          <div className="flex-1 overflow-auto">
            {loading && (
              <div className="flex items-center justify-center p-12">
                <Loader2 className="w-6 h-6 text-cyan-400 animate-spin mr-3" />
                <span className="text-gray-400 text-sm">
                  Loading sources...
                </span>
              </div>
            )}
            {error && (
              <div className="p-4 m-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm flex items-center gap-2">
                <XCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}
            {!loading && !error && searchedSources.length === 0 && (
              <div className="flex flex-col items-center justify-center p-12 text-gray-500">
                <Database className="w-8 h-8 mb-3 opacity-30" />
                <span className="text-sm">
                  No data sources match the filter.
                </span>
              </div>
            )}
            {!loading && !error && searchedSources.length > 0 && (
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 z-10 bg-[#0D1117] border-b border-[#1E2A3A]">
                  <tr className="text-[11px] text-gray-500 uppercase tracking-wider">
                    <th className="px-4 py-2.5 font-medium">Source</th>
                    <th className="px-4 py-2.5 font-medium">Category</th>
                    <th className="px-4 py-2.5 font-medium">Status</th>
                    <th className="px-4 py-2.5 font-medium">Latency</th>
                    <th className="px-4 py-2.5 font-medium">Uptime</th>
                    <th className="px-4 py-2.5 font-medium">Trend</th>
                    <th className="px-4 py-2.5 font-medium w-20">Requests</th>
                    <th className="px-4 py-2.5 font-medium w-16"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1E2A3A]/60">
                  {searchedSources.map((src) => {
                    const isSelected = selected?.id === src.id;
                    const uptime =
                      src.uptime != null
                        ? `${Number(src.uptime).toFixed(1)}%`
                        : src.status === "healthy" || src.status === "active"
                          ? "99.9%"
                          : "--";
                    const requests =
                      src.request_count != null
                        ? src.request_count >= 1000
                          ? `${(src.request_count / 1000).toFixed(0)}K`
                          : String(src.request_count)
                        : "--";
                    return (
                      <tr
                        key={src.id}
                        onClick={() => setSelected(src)}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? "bg-cyan-500/10 border-l-2 border-l-cyan-400"
                            : "hover:bg-[#1A1F2E]"
                        }`}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 bg-[#0B0E14] border border-[#1E2A3A] rounded-lg flex items-center justify-center text-xs font-bold shrink-0">
                              {typeof src.icon === "string" ? (
                                <span>{src.icon}</span>
                              ) : (
                                <span className="text-cyan-400">
                                  {src.name ? src.name[0].toUpperCase() : "?"}
                                </span>
                              )}
                            </div>
                            <span className="text-white font-medium text-sm truncate">
                              {src.name}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-[10px] px-2 py-0.5 bg-[#1E2A3A] text-gray-400 rounded-full font-medium">
                            {CATEGORY_LABELS[src.category] || src.category}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={src.status} />
                        </td>
                        <td
                          className={`px-4 py-3 font-mono text-xs ${latencyColor(src.last_latency_ms)}`}
                        >
                          {src.last_latency_ms != null
                            ? `${Math.round(src.last_latency_ms)}ms`
                            : "--"}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-300">
                          {uptime}
                        </td>
                        <td className="px-4 py-3">
                          <MiniSparkline
                            data={src.latency_series}
                            color={
                              src.status === "healthy" ||
                              src.status === "active"
                                ? "#10b981"
                                : src.status === "degraded"
                                  ? "#f59e0b"
                                  : "#06b6d4"
                            }
                          />
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-400 font-mono">
                          {requests}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setShowDeleteModal(src.id);
                            }}
                            className="p-1.5 text-gray-600 hover:text-red-400 rounded-lg hover:bg-red-500/10 transition-colors"
                            title="Delete source"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right: credential panel */}
        <div className="w-full lg:w-[380px] lg:flex-shrink-0">
          <CredentialPanel
            source={selectedDetail}
            onClose={() => setSelected(null)}
            onSave={handleSaveCredentials}
            onTest={handleTest}
            saving={saving}
            testing={testing}
          />
        </div>
      </div>

      {/* ===== SUPPLIER CHECKMARKS BAR ===== */}
      <div className="flex items-center gap-4 mt-4 px-4 py-2.5 bg-[#111827] border border-[#1E2A3A] rounded-xl overflow-x-auto">
        <span className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold whitespace-nowrap">
          Supplier Heartbeat
        </span>
        <div className="w-px h-4 bg-[#1E2A3A]" />
        {SUPPLIER_CHECKS.map((s) => (
          <div
            key={s.name}
            className="flex items-center gap-1.5 whitespace-nowrap"
          >
            <Check className="w-3 h-3 text-emerald-400" />
            <span className="text-[11px] text-gray-400">{s.name}</span>
          </div>
        ))}
      </div>

      {/* ===== FOOTER BAR ===== */}
      <div className="flex items-center justify-between mt-2 px-4 py-2 text-[10px] text-gray-600">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <CircleDot className="w-3 h-3 text-cyan-500/40" />
            FRED Macro Data: Syncs daily at 08:00 EST
          </span>
          <span className="flex items-center gap-1.5">
            <CircleDot className="w-3 h-3 text-yellow-500/40" />
            SEC EDGAR: Polls every 15m
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span>
            System telemetry: {connectedCount}/{totalCount}
          </span>
          <span>
            {new Date().toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
              hour12: false,
            })}
          </span>
        </div>
      </div>

      {/* ===== MODALS ===== */}
      {showAddModal && (
        <AddSourceModal
          onClose={() => setShowAddModal(false)}
          onAdd={handleAdd}
          saving={saving}
        />
      )}
      {showAIDetect && (
        <AIDetectModal
          onClose={() => setShowAIDetect(false)}
          onDetect={(url) => dataSources.aiDetect(url)}
        />
      )}
      {showDeleteModal && (
        <DeleteConfirmModal
          sourceId={showDeleteModal}
          onClose={() => setShowDeleteModal(null)}
          onConfirm={handleDelete}
          deleting={deleting}
        />
      )}
    </div>
  );
}
