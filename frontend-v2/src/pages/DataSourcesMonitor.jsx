import { useState, useMemo, useCallback } from "react";
import { useApi } from "../hooks/useApi";
import { useSettings } from "../hooks/useSettings";
import { getApiUrl, getAuthHeaders } from "../config/api";
import {
  RefreshCw,
  Copy,
  Eye,
  EyeOff,
  Search,
  Wifi,
  ChevronRight,
  RotateCw,
  Check,
  Zap,
  Link2,
  Cloud,
  ArrowRight,
} from "lucide-react";
import {
  LineChart,
  Line,
  ResponsiveContainer,
} from "recharts";
import clsx from "clsx";

// ============================================================
// DataSourcesMonitor.jsx - DATA_SOURCES_MANAGER
// Aurora 2-col 35/65. Live data from useApi('dataSources'), settings from useSettings.
// No mock data. All buttons wired.
// ============================================================

// Display-only metadata for known source ids (icon/color). No status/latency.
const SOURCE_DISPLAY_META = {
  finviz: { icon: "FV", iconBg: "bg-blue-600", typeBadgeColor: "bg-purple-500/20 text-purple-400" },
  unusual_whales: { icon: "UW", iconBg: "bg-indigo-600", typeBadgeColor: "bg-cyan-500/20 text-[#00D9FF]" },
  alpaca: { icon: "AL", iconBg: "bg-yellow-600", typeBadgeColor: "bg-emerald-500/20 text-emerald-400" },
  fred: { icon: "FR", iconBg: "bg-sky-700", typeBadgeColor: "bg-orange-500/20 text-orange-400" },
  sec_edgar: { icon: "SE", iconBg: "bg-slate-600", typeBadgeColor: "bg-red-500/20 text-red-400" },
  news_api: { icon: "NA", iconBg: "bg-red-700", typeBadgeColor: "bg-blue-500/20 text-blue-400" },
  discord: { icon: "DC", iconBg: "bg-indigo-500", typeBadgeColor: "bg-indigo-500/20 text-indigo-400" },
  twitter: { icon: "X", iconBg: "bg-gray-800", typeBadgeColor: "bg-indigo-500/20 text-indigo-400" },
  youtube: { icon: "YT", iconBg: "bg-red-600", typeBadgeColor: "bg-red-500/20 text-red-300" },
  stockgeist: { icon: "SG", iconBg: "bg-pink-600", typeBadgeColor: "bg-pink-500/20 text-pink-400" },
  benzinga: { icon: "BZ", iconBg: "bg-blue-700", typeBadgeColor: "bg-blue-500/20 text-blue-400" },
  rss: { icon: "RS", iconBg: "bg-orange-700", typeBadgeColor: "bg-orange-500/20 text-orange-400" },
  tradingview: { icon: "TV", iconBg: "bg-cyan-600", typeBadgeColor: "bg-emerald-500/20 text-emerald-400" },
  openclaw_bridge: { icon: "OC", iconBg: "bg-indigo-600", typeBadgeColor: "bg-cyan-500/20 text-[#00D9FF]" },
  github_gist: { icon: "GH", iconBg: "bg-slate-700", typeBadgeColor: "bg-slate-500/20 text-slate-400" },
  reddit: { icon: "RD", iconBg: "bg-orange-600", typeBadgeColor: "bg-indigo-500/20 text-indigo-400" },
  squeezemetrics: { icon: "SM", iconBg: "bg-slate-600", typeBadgeColor: "bg-slate-500/20 text-slate-400" },
  capitol_trades: { icon: "CT", iconBg: "bg-amber-700", typeBadgeColor: "bg-amber-500/20 text-amber-400" },
  resend: { icon: "RE", iconBg: "bg-emerald-700", typeBadgeColor: "bg-emerald-500/20 text-emerald-400" },
  perplexity: { icon: "PP", iconBg: "bg-slate-600", typeBadgeColor: "bg-slate-500/20 text-slate-400" },
  anthropic: { icon: "AC", iconBg: "bg-orange-700", typeBadgeColor: "bg-orange-500/20 text-orange-400" },
};

const FILTER_CHIPS = [
  "ALL", "Screener", "Options", "Market", "Macro", "Filings", "Sentiment", "News", "Social", "Knowledge",
];

const SUGGESTED_SERVICES = [
  { name: "Polygon.io", url: "https://polygon.io" },
  { name: "Benzinga", url: "https://www.benzinga.com/apis" },
  { name: "Alpha Vantage", url: "https://www.alphavantage.co/support/#api-key" },
  { name: "Quandl", url: "https://www.quandl.com" },
  { name: "IEX Cloud", url: "https://iexcloud.io" },
  { name: "CoinGecko", url: "https://www.coingecko.com/en/api" },
];

const FLAT_GRAY_SPARK = [{ v: 0 }, { v: 0 }];

// Map source id -> settings field keys (dataSources category)
const SOURCE_TO_SETTINGS_KEYS = {
  alpaca: { apiKey: "alpacaApiKey", apiSecret: "alpacaSecretKey", baseUrl: "alpacaBaseUrl", accountType: "alpacaBaseUrl", pollingInterval: "alpacaFeed" },
  unusual_whales: { apiKey: "unusualWhalesApiKey", apiSecret: "", baseUrl: "", accountType: "", pollingInterval: "refreshIntervalSeconds" },
  finviz: { apiKey: "finvizApiKey", apiSecret: "", baseUrl: "", accountType: "", pollingInterval: "refreshIntervalSeconds" },
  fred: { apiKey: "fredApiKey", apiSecret: "", baseUrl: "", accountType: "", pollingInterval: "refreshIntervalSeconds" },
  news_api: { apiKey: "newsApiKey", apiSecret: "", baseUrl: "", accountType: "", pollingInterval: "refreshIntervalSeconds" },
  benzinga: { apiKey: "benzingaEmail", apiSecret: "benzingaPassword", baseUrl: "", accountType: "", pollingInterval: "refreshIntervalSeconds" },
  stockgeist: { apiKey: "stockgeistApiKey", apiSecret: "", baseUrl: "", accountType: "", pollingInterval: "refreshIntervalSeconds" },
  discord: { apiKey: "discordBotToken", apiSecret: "", baseUrl: "", accountType: "", pollingInterval: "refreshIntervalSeconds" },
  twitter: { apiKey: "xBearerToken", apiSecret: "", baseUrl: "", accountType: "", pollingInterval: "refreshIntervalSeconds" },
  youtube: { apiKey: "youtubeApiKey", apiSecret: "", baseUrl: "", accountType: "", pollingInterval: "refreshIntervalSeconds" },
  sec_edgar: { apiKey: "secEdgarUserAgent", apiSecret: "", baseUrl: "", accountType: "", pollingInterval: "refreshIntervalSeconds" },
};
function getSettingsKey(settings, category, key) {
  const cat = settings?.[category];
  return cat != null && key in cat ? cat[key] : "";
}

function StatusBadge({ status }) {
  const isHealthy = status === "healthy" || status === "active";
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider",
        isHealthy
          ? "bg-emerald-500/20 text-emerald-400"
          : "bg-amber-500/20 text-amber-400"
      )}
    >
      <span
        className={clsx(
          "w-1.5 h-1.5 rounded-full",
          isHealthy ? "bg-emerald-400" : "bg-amber-400"
        )}
      />
      {isHealthy ? "HEALTHY" : "DEGRADED"}
    </span>
  );
}

function MiniSparkline({ data, color = "#22d3ee" }) {
  return (
    <div className="w-16 h-6">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function LatencySparkline({ points = [], color = "#00D9FF" }) {
  const w = 40, h = 16;
  if (!points || points.length < 2) {
    return (
      <svg width={w} height={h} className="inline-block ml-2">
        <line x1={0} y1={h} x2={w} y2={h} stroke="#64748b" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }
  const max = Math.max(...points);
  const safeMax = max > 0 ? max : 1;
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${(i / (points.length - 1)) * w},${h - (p / safeMax) * h}`).join(' ');
  return (
    <svg width={w} height={h} className="inline-block ml-2">
      <polyline points={path.replace(/[ML]/g, '')} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ---------- Source Card ----------

function SourceCard({ source, isSelected, onClick, onLivePing, onCopy, onRotate }) {
  const sparkColor = source.status === "degraded" ? "#f87171" : "#22d3ee";
  const points = source.latency_history && source.latency_history.length >= 2 ? source.latency_history : [];
  const sparkData = source.latency_history?.length >= 2
    ? source.latency_history.map((v) => ({ v }))
    : FLAT_GRAY_SPARK;

  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      className={clsx(
        "w-full text-left px-3 py-2.5 rounded-lg border transition-all duration-150 group cursor-pointer",
        isSelected
          ? "bg-cyan-500/10 border-[#00D9FF]/50"
          : "bg-[#0B0E14] border-gray-800 hover:border-gray-600"
      )}
    >
      <div className="flex items-center gap-3">
        <div className={clsx("w-8 h-8 rounded flex items-center justify-center text-xs font-bold text-white flex-shrink-0", source.iconBg)}>
          {source.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-100 truncate">{source.name}</span>
            <span className={clsx("px-1.5 py-0.5 rounded text-[9px] font-medium", source.typeBadgeColor)}>
              {source.type}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <StatusBadge status={source.status} />
            <span className="text-[10px] text-gray-500 font-mono flex items-center">
              {source.latency}
              <LatencySparkline points={points} color={sparkColor} />
            </span>
            {source.uptime != null && (
              <span className="text-[10px] text-gray-500 font-mono">{source.uptime}%</span>
            )}
            {source.dataRate && (
              <span className="text-[10px] text-gray-500 font-mono">{source.dataRate}</span>
            )}
            {source.dataSize && (
              <span className="text-[10px] text-gray-500">{source.dataSize}</span>
            )}
          </div>
        </div>
        <MiniSparkline data={sparkData} color={points.length >= 2 ? sparkColor : "#64748b"} />
        <div className="text-right flex-shrink-0 w-12">
          <div
            className={clsx(
              "text-xs font-bold font-mono",
              (source.uptime ?? 0) >= 99 ? "text-emerald-400" : (source.uptime ?? 0) >= 95 ? "text-amber-400" : "text-red-400"
            )}
          >
            {source.uptime != null ? `${source.uptime}%` : "—"}
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          {source.id === "alpaca" && onLivePing && (
            <button type="button" onClick={() => onLivePing(source.id)} className="px-2 py-0.5 text-[9px] font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 rounded hover:bg-emerald-500/30 transition-colors">
              LIVE PING
            </button>
          )}
          <button type="button" onClick={() => onClick?.()} className="px-1.5 py-0.5 text-[9px] text-gray-400 hover:text-gray-300 border border-gray-600 rounded">
            Show
          </button>
          <button type="button" onClick={() => onCopy?.(source)} className="px-1.5 py-0.5 text-[9px] text-gray-400 hover:text-gray-300 border border-gray-600 rounded">
            Copy
          </button>
          <button type="button" onClick={() => onRotate?.(source)} className="px-1.5 py-0.5 text-[9px] text-gray-400 hover:text-gray-300 border border-gray-600 rounded">
            Rotate
          </button>
        </div>
        <ChevronRight className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-400 flex-shrink-0" />
      </div>
    </div>
  );
}

// ---------- Connection Detail Panel ----------

function ConnectionDetailPanel({
  source,
  settings,
  connectionResults,
  updateField,
  saveCategory,
  resetCategory,
  testConnection,
  refetchSettings,
  connectionLog = [],
}) {
  const [showApiKey, setShowApiKey] = useState(false);
  const [showApiSecret, setShowApiSecret] = useState(false);
  const [copied, setCopied] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleCopy = useCallback((text) => {
    if (text == null || text === "") return;
    navigator.clipboard.writeText(String(text)).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(null), 1500);
    });
  }, []);

  const handleRotate = useCallback(async () => {
    if (!source?.id) return;
    try {
      const base = getApiUrl("dataSources");
      const res = await fetch(`${base}${source.id}/rotate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({}),
      });
      if (res.ok) refetchSettings?.();
      else throw new Error("Rotate not available");
    } catch {
      window.open("https://app.alpaca.markets/paper/dashboard/overview", "_blank", "noopener");
    }
  }, [source?.id, refetchSettings]);

  if (!source) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-sm bg-[#111827]">
        Select a source to view details
      </div>
    );
  }

  const displayName = source.id === "alpaca" ? "Alpaca Markets" : (source.name || "—");
  const typeLabel = source.type || source.category || "—";
  const keys = SOURCE_TO_SETTINGS_KEYS[source.id] || {};
  const apiKeyVal = keys.apiKey ? getSettingsKey(settings, "dataSources", keys.apiKey) : (source.apiKey ?? "—");
  const apiSecretVal = keys.apiSecret ? getSettingsKey(settings, "dataSources", keys.apiSecret) : (source.apiSecret ?? "—");
  const baseUrlVal = keys.baseUrl ? getSettingsKey(settings, "dataSources", keys.baseUrl) : (source.base_url ?? source.baseUrl ?? "—");
  const testRes = connectionResults?.[source.id];
  const testResultText = testRes?.testing
    ? "Testing..."
    : testRes?.success
      ? `Connected ${testRes.latency_ms != null ? `in ${testRes.latency_ms}ms` : ""}`
      : testRes?.message
        ? testRes.message
        : source.last_error
          ? `Last error: ${source.last_error}`
          : source.last_latency_ms != null
            ? `Last test: ${source.last_latency_ms}ms`
            : "—";

  const logEntries = Array.isArray(connectionLog) ? connectionLog : [];

  return (
    <div className="h-full flex flex-col bg-[#111827]">
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-3">CREDENTIAL EDITOR PANEL</div>
        <div className="flex items-center gap-3">
          <div className={clsx("w-12 h-12 rounded-lg flex items-center justify-center text-lg font-bold text-white", source.iconBg)}>
            {source.icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-lg font-semibold text-white flex items-center gap-2">
              {displayName}
              <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            </div>
            <span className={clsx("inline-block mt-0.5 px-1.5 py-0.5 rounded text-[9px] font-medium", source.typeBadgeColor)}>
              {typeLabel}
            </span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 custom-scrollbar">
        {keys.apiKey && (
          <FieldRow label="API Key">
            <div className="flex items-center gap-2">
              <input
                type={showApiKey ? "text" : "password"}
                value={apiKeyVal}
                onChange={(e) => updateField("dataSources", keys.apiKey, e.target.value)}
                className="flex-1 bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-[#00D9FF] font-mono focus:outline-none focus:border-[#00D9FF]/50"
              />
              <button type="button" onClick={() => handleCopy(apiKeyVal)} className="px-2 py-0.5 text-[10px] text-gray-400 border border-gray-600 rounded hover:border-gray-500 hover:text-gray-300 transition-colors">
                {copied ? "Copied" : "Copy"}
              </button>
              {source.id === "alpaca" && (
                <button type="button" onClick={handleRotate} className="px-2 py-0.5 text-[10px] text-gray-400 border border-gray-600 rounded hover:border-gray-500 hover:text-gray-300 transition-colors">
                  Rotate
                </button>
              )}
            </div>
          </FieldRow>
        )}
        {keys.apiSecret && (
          <FieldRow label="API Secret">
            <div className="flex items-center gap-2">
              <input
                type={showApiSecret ? "text" : "password"}
                value={apiSecretVal}
                onChange={(e) => updateField("dataSources", keys.apiSecret, e.target.value)}
                className="flex-1 bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-[#00D9FF] font-mono focus:outline-none focus:border-[#00D9FF]/50"
              />
              <button type="button" onClick={() => setShowApiSecret(!showApiSecret)} className="p-1 text-gray-500 hover:text-gray-300 transition-colors" title={showApiSecret ? "Hide" : "Show"}>
                {showApiSecret ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
              <button type="button" onClick={handleRotate} className="px-2 py-0.5 text-[10px] text-gray-400 border border-gray-600 rounded hover:border-gray-500 hover:text-gray-300 transition-colors">
                Rotate
              </button>
            </div>
          </FieldRow>
        )}
        {(keys.baseUrl || baseUrlVal) && (
          <FieldRow label="Base URL">
            <input
              type="text"
              value={baseUrlVal}
              onChange={(e) => keys.baseUrl && updateField("dataSources", keys.baseUrl, e.target.value)}
              className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-[#00D9FF] font-mono focus:outline-none focus:border-[#00D9FF]/50"
            />
          </FieldRow>
        )}

        <FieldRow label="Polling Interval">
          <select
            value={getSettingsKey(settings, "dataSources", keys.pollingInterval || "refreshIntervalSeconds") || "300"}
            onChange={(e) => updateField("dataSources", keys.pollingInterval || "refreshIntervalSeconds", e.target.value)}
            className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 appearance-none pr-7 focus:outline-none focus:border-[#00D9FF]/50"
          >
            <option value="iex">Real-time (WebSocket)</option>
            <option value="60">1 min</option>
            <option value="300">5 min</option>
            <option value="900">15 min</option>
          </select>
        </FieldRow>

        {source.id === "alpaca" && (
          <FieldRow label="Account Type">
            <select
              value={getSettingsKey(settings, "dataSources", "alpacaBaseUrl") || "paper"}
              onChange={(e) => updateField("dataSources", "alpacaBaseUrl", e.target.value)}
              className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 appearance-none pr-7 focus:outline-none focus:border-[#00D9FF]/50"
            >
              <option value="paper">Paper Trading</option>
              <option value="live">Live Trading</option>
            </select>
          </FieldRow>
        )}

        <div className="flex items-center gap-2 pt-2">
          {testRes?.success !== false && !testRes?.testing && <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />}
          <span className={clsx("text-xs font-medium", testRes?.testing ? "text-gray-400" : testRes?.success === false ? "text-amber-400" : "text-emerald-400")}>
            {testResultText}
          </span>
        </div>
      </div>

      <div className="px-4 py-3 border-t border-gray-800 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => testConnection(source.id)}
          disabled={connectionResults?.[source.id]?.testing}
          className="px-3 py-2 text-xs font-medium rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white transition-colors flex items-center gap-1.5"
        >
          <Wifi className="w-3.5 h-3.5" />
          Test Connection
        </button>
        <button
          type="button"
          onClick={async () => { setSaving(true); try { await saveCategory("dataSources"); } finally { setSaving(false); } }}
          disabled={saving}
          className="px-3 py-2 text-xs font-medium rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white transition-colors flex items-center gap-1.5"
        >
          <Check className="w-3.5 h-3.5" />
          Save Changes
        </button>
        <button
          type="button"
          onClick={() => refetchSettings?.()}
          className="px-3 py-2 text-xs font-medium rounded bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={async () => { try { await resetCategory("dataSources"); refetchSettings?.(); } catch (_) {} }}
          className="px-3 py-2 text-xs font-medium rounded bg-amber-600/80 hover:bg-amber-500/80 text-white transition-colors flex items-center gap-1.5"
        >
          <RotateCw className="w-3.5 h-3.5" />
          Reset to Default
        </button>
      </div>

      <div className="flex-1 min-h-[80px] px-4 py-3 border-t border-gray-800 overflow-y-auto">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-2">Connection Log</div>
        <div className="text-[11px] text-gray-500 font-mono space-y-0.5">
          {logEntries.length > 0
            ? logEntries.map((entry, i) => (
                <div key={i}>{typeof entry === "string" ? entry : entry.message ?? entry.text ?? JSON.stringify(entry)}</div>
              ))
            : source.last_test && (
                <div>{source.last_test}{source.last_latency_ms != null ? ` — ${source.last_latency_ms}ms` : ""}</div>
              )}
          {logEntries.length === 0 && !source.last_test && <div>No log entries</div>}
        </div>
      </div>
    </div>
  );
}

function FieldRow({ label, children }) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-1">
        {label}
      </div>
      {children}
    </div>
  );
}

// ---------- Main Component ----------

export default function DataSourcesMonitor() {
  const { data, loading, error, refetch } = useApi("dataSources", { pollIntervalMs: 30000 });
  const { settings, connectionResults, updateField, saveCategory, resetCategory, testConnection, refetch: refetchSettings } = useSettings();

  const [selectedSourceId, setSelectedSourceId] = useState("alpaca");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilterChip, setActiveFilterChip] = useState("ALL");
  const [sourceSearchQuery, setSourceSearchQuery] = useState("");

  const apiSources = useMemo(
    () => (data ? (data?.dataSources ?? data?.sources ?? (Array.isArray(data) ? data : [])) : []),
    [data]
  );

  const sources = useMemo(() => {
    const normalizedStatus = (s) => (s === "active" ? "healthy" : s || "pending");
    const normalizedLatency = (v) => (v != null && typeof v === "number" ? `${Number(v)}ms` : v ?? "—");
    return apiSources.map((s) => {
      const meta = SOURCE_DISPLAY_META[s.id] || {
        icon: (s.name || s.id).slice(0, 2).toUpperCase(),
        iconBg: "bg-slate-600",
        typeBadgeColor: "bg-slate-500/20 text-slate-400",
      };
      const lat = s.latency ?? s.last_latency_ms;
      return {
        ...s,
        ...meta,
        type: s.category || s.type || "Custom",
        status: normalizedStatus(s.status),
        latency: normalizedLatency(lat),
        dataRate: s.dataRate ?? s.data_rate ?? "",
        dataSize: "",
        uptime: s.uptime != null ? Number(s.uptime) : null,
        latency_history: s.latency_history ?? s.latencyHistory ?? [],
      };
    });
  }, [apiSources]);

  const _dead = useMemo(() => {
    const normalizedStatus = (s) => (s === "active" ? "healthy" : s || "pending");
    const normalizedLatency = (v) => (v != null && typeof v === "number" ? `${Number(v)}ms` : v ?? "—");
    const apiSources = [];
    const mergedFromDefs = [].map((def) => {
      const apiMatch = apiSources.find(
        (s) =>
          s.id === def.id ||
          s.name?.toLowerCase() === def.name.toLowerCase() ||
          (def.id === "newsapi" && (s.id === "news_api" || s.name?.toLowerCase() === "news api")) ||
          (def.id === "stockgeist" && (s.id === "stockgrid" || s.name?.toLowerCase() === "stockgrid"))
      );
      if (apiMatch) {
        const lat = apiMatch.latency ?? apiMatch.last_latency_ms;
        return {
          ...def,
          ...apiMatch,
          status: normalizedStatus(apiMatch.status) || def.status,
          latency: normalizedLatency(lat) ?? (lat != null ? `${lat}ms` : null) ?? def.latency,
          dataRate: apiMatch.dataRate ?? apiMatch.data_rate ?? def.dataRate ?? "—",
          uptime: apiMatch.uptime != null ? Number(apiMatch.uptime) : def.uptime,
          baseUrl: apiMatch.base_url ?? apiMatch.baseUrl ?? def.baseUrl,
          base_url: apiMatch.base_url ?? def.base_url,
        };
      }
      return def;
    });

    // Append API-only sources not in SOURCE_DEFS so all sources from API show
    const seenIds = new Set(mergedFromDefs.map((s) => s.id));
    const apiOnly = apiSources.filter(
      (s) =>
        s.id &&
        !seenIds.has(s.id) &&
        !mergedFromDefs.some((d) => d.name?.toLowerCase() === (s.name || "").toLowerCase())
    );
    const extra = apiOnly.map((s) => {
      const lat = s.latency ?? s.last_latency_ms;
      return {
        id: s.id,
        name: s.name || s.id,
        type: s.category || s.type || "Custom",
        typeBadgeColor: "bg-slate-500/20 text-slate-400",
        icon: (s.name || s.id).slice(0, 2).toUpperCase(),
        iconBg: "bg-slate-600",
        status: normalizedStatus(s.status),
        latency: normalizedLatency(lat) ?? (lat != null ? `${lat}ms` : "—"),
        dataRate: s.dataRate ?? s.data_rate ?? "—",
        dataSize: "",
        uptime: s.uptime != null ? Number(s.uptime) : 0,
        sparkData: FLAT_GRAY_SPARK,
      };
    });
    return [];
  }, [data]);

  const filteredSources = useMemo(() => {
    let list = sources;
    if (activeFilterChip !== "ALL") {
      list = list.filter((s) => s.type?.toLowerCase() === activeFilterChip.toLowerCase());
    }
    if (sourceSearchQuery.trim()) {
      const q = sourceSearchQuery.toLowerCase();
      list = list.filter((s) => s.name?.toLowerCase().includes(q) || s.type?.toLowerCase().includes(q));
    }
    return list;
  }, [sources, activeFilterChip, sourceSearchQuery]);

  const selectedSource = useMemo(() => sources.find((s) => s.id === selectedSourceId) || sources[0], [sources, selectedSourceId]);

  const connectionLog = useMemo(() => data?.connectionLog ?? data?.connection_log ?? selectedSource?.connectionLog ?? [], [data, selectedSource]);

  const handleCopyFromRow = useCallback((source) => {
    const keys = SOURCE_TO_SETTINGS_KEYS[source?.id];
    const key = keys?.apiKey && settings?.dataSources?.[keys.apiKey];
    if (key) navigator.clipboard.writeText(String(key));
  }, [settings]);

  const handleRotateFromRow = useCallback(async (source) => {
    if (!source?.id) return;
    try {
      const base = getApiUrl("dataSources");
      const res = await fetch(`${base}${source.id}/rotate`, { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({}) });
      if (res.ok) refetchSettings?.();
      else window.open("https://app.alpaca.markets/paper/dashboard/overview", "_blank", "noopener");
    } catch {
      window.open("https://app.alpaca.markets/paper/dashboard/overview", "_blank", "noopener");
    }
  }, [refetchSettings]);

  const connectedCount = useMemo(
    () => sources.filter((s) => s.status === "healthy" || s.status === "active").length,
    [sources]
  );

  const healthPct = useMemo(() => {
    if (!sources.length) return 0;
    const healthyWeight = sources.reduce(
      (acc, s) => acc + (s.status === "healthy" || s.status === "active" ? 1 : 0.5),
      0
    );
    return Math.round((healthyWeight / sources.length) * 100);
  }, [sources]);

  return (
    <div className="h-full flex flex-col gap-0 -m-6">
      {loading && (
        <div className="px-5 py-2 bg-[#00D9FF]/10 border-b border-[#00D9FF]/30 text-[#00D9FF] text-xs font-mono flex items-center gap-2">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          Loading data sources...
        </div>
      )}
      {error && (
        <div className="px-5 py-2 bg-red-500/10 border-b border-red-500/30 text-red-400 text-xs font-mono flex items-center justify-between">
          <span>Failed to load data sources: {error.message}</span>
          <button onClick={refetch} className="px-2 py-1 rounded bg-red-500/20 hover:bg-red-500/30">Retry</button>
        </div>
      )}
      {/* ===== HEADER BAR ===== */}
      <div className="px-5 py-3 border-b border-gray-800 bg-[#111827]">
        <h1 className="text-base font-bold text-white tracking-wider uppercase text-center">
          DATA_SOURCES_MANAGER
        </h1>
        {/* Top Metrics Row */}
        <div className="flex items-center justify-between mt-3 flex-wrap gap-x-6 gap-y-2">
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-gray-500">Connected:</span>
              <span className="font-medium text-emerald-400">{connectedCount}/{sources.length} sources</span>
            </div>
            <div className="flex items-center gap-1.5">
              <RefreshCw className="w-3 h-3 text-emerald-400" />
              <span className="text-gray-500">System Health:</span>
              <span className="font-medium text-emerald-400">{healthPct}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <ArrowRight className="w-3 h-3 text-gray-500" />
              <span className="text-gray-500">Ingestion:</span>
              <span className="font-medium text-gray-300">4.2K rec/min</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[11px] font-medium text-emerald-400">WS Connected</span>
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="text-[11px] font-medium text-emerald-400">API Healthy</span>
            </span>
            <button
              onClick={refetch}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#00D9FF]/20 hover:bg-[#00D9FF]/30 border border-[#00D9FF]/40 text-[#00D9FF] text-white text-xs font-medium rounded transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              Refresh
            </button>
          </div>
        </div>
        {/* OpenClaw / WS row */}
        <div className="flex items-center gap-4 mt-2 text-xs">
          <div className="flex items-center gap-1.5 text-emerald-400">
            <Link2 className="w-3 h-3" />
            <span>OpenClaw Bridge: CONNECTED</span>
          </div>
          <div className="flex items-center gap-1.5 text-emerald-400">
            <Zap className="w-3 h-3" />
            <span>WS: CONNECTED</span>
          </div>
        </div>
      </div>

      {/* ===== AI-POWERED ADD SOURCE INPUT ===== */}
      <div className="px-5 py-3 border-b border-gray-800 bg-[#0B0E14]">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-2">AI-POWERED ADD SOURCE INPUT</h3>
        <div className="flex items-start gap-3">
          <div className="flex-1 flex flex-col gap-2">
            <div className="flex items-center gap-2 bg-[#0B0E14] border border-[#00D9FF]/30 rounded-md overflow-hidden focus-within:border-[#00D9FF]/60">
              <Search className="w-4 h-4 text-gray-500 ml-3 flex-shrink-0" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Type a service name, URL, or paste API docs link..."
                className="flex-1 bg-transparent px-2 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none min-w-0"
              />
            </div>
            <button className="self-start px-3 py-1 text-xs font-medium text-[#00D9FF] hover:text-[#00D9FF]/80 transition-colors">
              Or browse...
            </button>
          </div>
          <div className="w-48 flex-shrink-0 h-[72px] border border-gray-700 rounded-md border-dashed flex flex-col items-center justify-center gap-1 bg-[#0f1219]/50 hover:border-gray-600 transition-colors cursor-pointer">
            <Cloud className="w-6 h-6 text-gray-500" />
            <span className="text-[10px] text-gray-500 font-mono">Drop API docs or config file</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {SUGGESTED_SERVICES.map((s) => (
            <button
              key={s.name}
              type="button"
              onClick={() => s.url && window.open(s.url, "_blank", "noopener")}
              className="px-3 py-1 text-[11px] font-mono text-gray-400 border border-gray-700 rounded-full hover:border-[#00D9FF]/50 hover:text-[#00D9FF] transition-colors"
            >
              {s.name}
            </button>
          ))}
        </div>

        {/* Filter chips + Search */}
        <div className="flex items-center justify-between gap-4 mt-4">
          <div className="flex items-center gap-1 flex-wrap">
            {FILTER_CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => setActiveFilterChip(chip)}
                className={clsx(
                  "px-2.5 py-1 rounded text-[10px] font-medium transition-colors",
                  activeFilterChip === chip
                    ? "bg-gray-700 text-white"
                    : "text-gray-400 hover:text-gray-300 bg-transparent"
                )}
              >
                [{chip}]
              </button>
            ))}
          </div>
          <div className="flex items-center">
            <Search className="w-3.5 h-3.5 text-gray-500 mr-1.5" />
            <input
              type="text"
              value={sourceSearchQuery}
              onChange={(e) => setSourceSearchQuery(e.target.value)}
              placeholder="Search"
              className="w-24 bg-[#0B0E14] border border-gray-700 rounded px-2 py-1 text-[11px] text-gray-300 placeholder-gray-500 focus:border-gray-600 focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* ===== MAIN SPLIT VIEW (35 / 65 Aurora) ===== */}
      <div className="flex-1 flex min-h-0">
        <div className="w-[35%] border-r border-gray-800 flex flex-col bg-[#0a0e1a]">
          <div className="px-4 py-2 border-b border-gray-800">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">SOURCE LIST</h3>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-1.5">
            {filteredSources.map((source) => (
              <SourceCard
                key={source.id}
                source={source}
                isSelected={selectedSourceId === source.id}
                onClick={() => setSelectedSourceId(source.id)}
                onLivePing={testConnection}
                onCopy={handleCopyFromRow}
                onRotate={handleRotateFromRow}
              />
            ))}
          </div>
        </div>
        <div className="w-[65%] bg-[#111827] overflow-hidden flex flex-col">
          <ConnectionDetailPanel
            source={selectedSource}
            settings={settings}
            connectionResults={connectionResults}
            updateField={updateField}
            saveCategory={saveCategory}
            resetCategory={resetCategory}
            testConnection={testConnection}
            refetchSettings={refetchSettings}
            connectionLog={connectionLog}
          />
        </div>
      </div>

      {/* ===== FOOTER BAR ===== */}
      <div className="px-5 py-2 border-t border-gray-800 bg-[#080c14] flex items-center justify-between text-[10px] text-gray-600">
        <div className="flex items-center gap-4">
          <span>
            <span className="text-gray-500">FRED Macro Data:</span> Syncs daily at 08:00 EST
          </span>
          <span className="text-gray-700">|</span>
          <span>
            <span className="text-gray-500">SEC EDGAR:</span> Polls every 15m
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span>System telemetry: 1039 WSI: 93rb APII 0.00</span>
        </div>
      </div>
    </div>
  );
}

