import { useState, useEffect, useCallback } from "react";
import dataSources from "../services/dataSourcesApi";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import {
  X,
  Copy,
  RefreshCw,
  Settings,h
  Check,
  XCircle,
  Loader2,
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
      <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl p-8 text-center">
        <p className="text-gray-500 text-sm">
          Select a source to edit credentials
        </p>
      </div>
    );

  return (
    <div className="bg-[#1A1F2E] border border-[#2A3444] rounded-xl overflow-hidden sticky top-6">
      {/* Panel Header - icon + name + category badge (mockup 09) */}
      <div className="p-4 border-b border-[#2A3444] bg-[#0A0E1A]/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#0A0E1A] rounded-lg flex items-center justify-center text-xl">
              {typeof source.icon === "string" ? (
                source.icon
              ) : typeof source.category === "string" &&
                CATEGORY_LABELS[source.category] ? (
                CATEGORY_LABELS[source.category][0]
              ) : (
                <Settings className="w-5 h-5 text-gray-400" />
              )}
            </div>
            <div>
              <h3 className="text-white font-bold text-base">
                {source.name != null ? String(source.name) : "Unknown"}
              </h3>
              <span className="text-[10px] px-2 py-0.5 bg-cyan-600/20 text-cyan-400 rounded-full font-medium">
                {source.category != null
                  ? CATEGORY_LABELS[source.category] || String(source.category)
                  : "Custom"}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white text-sm p-1"
            aria-label="Close panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Credential Fields */}
      <div className="p-4 space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
        {(source.required_keys || []).map((keyName, idx) => {
          const k =
            typeof keyName === "string"
              ? keyName
              : (keyName?.key ?? keyName?.name ?? String(idx));
          return (
            <div key={k} className="flex flex-col gap-1.5">
              <div className="flex items-end gap-1">
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
                  className="h-10 w-10 flex-shrink-0 flex items-center justify-center bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-gray-500 hover:text-white"
                  title="Copy"
                  aria-label="Copy to clipboard"
                >
                  <Copy className="w-4 h-4" />
                </button>
                <button
                  className="h-10 w-10 flex-shrink-0 flex items-center justify-center bg-[#0A0E1A] border border-[#2A3444] rounded-lg text-gray-500 hover:text-white"
                  title="Rotate"
                  aria-label="Rotate key"
                >
                  <RefreshCw className="w-4 h-4" />
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
            <div className="text-emerald-400 text-xs font-bold">
              Connection Test Result
            </div>
            <div className="text-emerald-400 text-xs mt-1 flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 shrink-0" /> Connected in{" "}
              {testResult.latency}ms
              {testResult.detail ? ` - ${testResult.detail}` : ""}
            </div>
          </div>
        )}

        {/* Action buttons row (mockup 09: Test Connection, Save Changes, Cancel, Reset to Default) */}
        <div className="flex gap-2 pt-2 flex-wrap">
          <button
            onClick={handleTest}
            disabled={testing}
            className="px-3 py-2 bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded-lg hover:bg-cyan-600/30 text-xs font-medium disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            {testing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
            ) : null}
            {testing ? "Testing..." : "Test Connection"}
          </button>
          <button
            onClick={() => onSave(keys)}
            disabled={saving}
            className="px-3 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-xs font-medium disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            {saving ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
            ) : null}
            {saving ? "Saving..." : "Save Changes"}
          </button>
          <button
            onClick={onClose}
            className="px-3 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-xs"
          >
            Cancel
          </button>
          <button className="px-3 py-2 bg-gray-600/20 text-gray-400 rounded-lg hover:bg-gray-600/30 text-xs">
            Reset to Default
          </button>
        </div>

        {/* Connection Log (mockup 09 bottom of panel) */}
        {testLog.length > 0 && (
          <div className="mt-3">
            <div className="bg-[#0A0E1A] border border-[#2A3444] rounded-lg p-2 max-h-32 overflow-y-auto font-mono text-[10px] text-gray-400 space-y-0.5">
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

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-white">Data Sources Manager</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAIDetect(true)}
            className="px-3 py-2 bg-purple-600/20 text-purple-400 border border-purple-500/30 rounded-lg hover:bg-purple-600/30 text-xs font-medium"
          >
            AI Detect Provider
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-3 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 text-xs font-medium"
          >
            Add Source
          </button>
        </div>
      </div>

      {toast.message && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast({ message: null, type: "info" })}
        />
      )}

      <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0 overflow-auto">
        {/* Left: filter tabs + table */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#1A1F2E] border border-[#2A3444] rounded-xl overflow-hidden">
          <div className="flex gap-1 p-2 border-b border-[#2A3444] flex-wrap">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setFilterTab(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium ${filterTab === tab ? "bg-cyan-600/30 text-cyan-400" : "text-gray-400 hover:text-white"}`}
              >
                {FILTER_TAB_LABELS[tab] ?? tab}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-auto">
            {loading && (
              <div className="p-8 text-center text-gray-400 text-sm">
                Loading sources...
              </div>
            )}
            {error && <div className="p-4 text-red-400 text-sm">{error}</div>}
            {!loading && !error && filteredSources.length === 0 && (
              <div className="p-8 text-center text-gray-500 text-sm">
                No data sources match the filter.
              </div>
            )}
            {!loading && !error && filteredSources.length > 0 && (
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-[#0A0E1A] border-b border-[#2A3444] text-gray-400 font-medium">
                  <tr>
                    <th className="px-4 py-3">Source</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Latency</th>
                    <th className="px-4 py-3">Trend</th>
                    <th className="px-4 py-3 w-24">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSources.map((src) => (
                    <tr
                      key={src.id}
                      onClick={() => setSelected(src)}
                      className={`border-b border-[#2A3444] cursor-pointer hover:bg-[#252B3B] ${selected?.id === src.id ? "bg-cyan-600/10" : ""}`}
                    >
                      <td className="px-4 py-3 text-white font-medium">
                        {src.name}
                      </td>
                      <td className="px-4 py-3 text-gray-400">
                        {CATEGORY_LABELS[src.category] || src.category}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={src.status} />
                      </td>
                      <td
                        className={`px-4 py-3 ${latencyColor(src.last_latency_ms)}`}
                      >
                        {src.last_latency_ms != null
                          ? `${Math.round(src.last_latency_ms)} ms`
                          : "--"}
                      </td>
                      <td className="px-4 py-3">
                        <MiniSparkline data={src.latency_series} />
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShowDeleteModal(src.id);
                          }}
                          className="text-red-400 hover:text-red-300 text-xs"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
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
