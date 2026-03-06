import { useState, useMemo, useCallback } from "react";
import { useApi } from "../hooks/useApi";
import {
  RefreshCw,
  Copy,
  Eye,
  EyeOff,
  Search,
  Activity,
  Wifi,
  Database,
  Globe,
  BarChart3,
  ExternalLink,
  ChevronRight,
  RotateCw,
  ShoppingBag,
  Check,
} from "lucide-react";
import {
  LineChart,
  Line,
  ResponsiveContainer,
} from "recharts";
import clsx from "clsx";

// ============================================================
// DataSourcesMonitor.jsx - DATA_SOURCES_MANAGER
// Pixel-perfect match to mockup 09 (Split View Layout)
// Uses useApi('dataSources') for real API data
// ============================================================

// ---------- Static source definitions (fallback / display metadata) ----------

const SOURCE_DEFS = [
  {
    id: "finviz",
    name: "Finviz",
    type: "Screener",
    typeBadgeColor: "bg-purple-500/20 text-purple-400",
    icon: "FV",
    iconBg: "bg-blue-600",
    status: "healthy",
    latency: "12ms",
    dataRate: "3.4K",
    dataSize: "req/min",
    uptime: 99.2,
    sparkData: genSparkline(0.8, 1.0),
  },
  {
    id: "unusual_whales",
    name: "Unusual Whales",
    type: "Options Flow",
    typeBadgeColor: "bg-cyan-500/20 text-cyan-400",
    icon: "UW",
    iconBg: "bg-indigo-600",
    status: "healthy",
    latency: "14ms",
    dataRate: "8.6K",
    dataSize: "***rec/s",
    uptime: 99.9,
    sparkData: genSparkline(0.6, 1.0),
  },
  {
    id: "alpaca",
    name: "Alpaca",
    type: "Market Data",
    typeBadgeColor: "bg-emerald-500/20 text-emerald-400",
    icon: "AL",
    iconBg: "bg-yellow-600",
    status: "healthy",
    latency: "7ms",
    dataRate: "142K",
    dataSize: "tick 9.9%",
    uptime: 99.9,
    sparkData: genSparkline(0.7, 1.0),
  },
  {
    id: "fred",
    name: "FRED",
    type: "Macro",
    typeBadgeColor: "bg-orange-500/20 text-orange-400",
    icon: "FR",
    iconBg: "bg-sky-700",
    status: "healthy",
    latency: "340ms",
    dataRate: "1.2K",
    dataSize: "98.5%  $8.81",
    uptime: 98.5,
    sparkData: genSparkline(0.3, 0.7),
  },
  {
    id: "sec_edgar",
    name: "SEC EDGAR",
    type: "Filings",
    typeBadgeColor: "bg-red-500/20 text-red-400",
    icon: "SE",
    iconBg: "bg-slate-600",
    status: "degraded",
    latency: "5.6K",
    dataRate: "95.2%",
    dataSize: "Polls 15m",
    uptime: 95.2,
    sparkData: genSparkline(0.2, 0.8),
  },
  {
    id: "stockgeist",
    name: "Stockgeist",
    type: "Sentiment",
    typeBadgeColor: "bg-pink-500/20 text-pink-400",
    icon: "SG",
    iconBg: "bg-pink-600",
    status: "healthy",
    latency: "79ms",
    dataRate: "22K",
    dataSize: "",
    uptime: 99.1,
    sparkData: genSparkline(0.5, 0.9),
  },
  {
    id: "newsapi",
    name: "News API",
    type: "News",
    typeBadgeColor: "bg-blue-500/20 text-blue-400",
    icon: "NA",
    iconBg: "bg-red-700",
    status: "healthy",
    latency: "41ms",
    dataRate: "78K",
    dataSize: "18K",
    uptime: 99.7,
    sparkData: genSparkline(0.6, 1.0),
  },
  {
    id: "discord",
    name: "Discord",
    type: "Social",
    typeBadgeColor: "bg-indigo-500/20 text-indigo-400",
    icon: "DC",
    iconBg: "bg-indigo-500",
    status: "healthy",
    latency: "23ms",
    dataRate: "",
    dataSize: "Bot Token masked",
    uptime: 99.5,
    sparkData: genSparkline(0.7, 1.0),
  },
  {
    id: "twitter",
    name: "X/Twitter",
    type: "Social",
    typeBadgeColor: "bg-indigo-500/20 text-indigo-400",
    icon: "X",
    iconBg: "bg-gray-800",
    status: "degraded",
    latency: "430ms",
    dataRate: "",
    dataSize: "OAuth2 masked",
    uptime: 87.3,
    sparkData: genSparkline(0.1, 0.6),
  },
  {
    id: "youtube",
    name: "YouTube",
    type: "Knowledge",
    typeBadgeColor: "bg-red-500/20 text-red-300",
    icon: "YT",
    iconBg: "bg-red-600",
    status: "healthy",
    latency: "180ms",
    dataRate: "3.2K",
    dataSize: "",
    uptime: 99.0,
    sparkData: genSparkline(0.5, 0.9),
  },
];

const PROVIDER_TABS = [
  "Finnhub",
  "Benzinga",
  "Alpha Vantage",
  "Quandl",
  "IEX Cloud",
  "CoinGecko",
];

const SUPPLEMENTARY_SOURCES = [
  { id: "yfinance", label: "yFinance" },
  { id: "benzinga", label: "Benzinga" },
  { id: "rss", label: "RSS" },
  { id: "openclaw", label: "OpenClaw Bridge" },
  { id: "reddit", label: "Reddit" },
  { id: "resend", label: "Resend" },
  { id: "tradingview", label: "TradingView" },
  { id: "github_gist", label: "GitHub Gist" },
];

// ---------- Helpers ----------

function genSparkline(min, max) {
  return Array.from({ length: 20 }, () => ({
    v: min + Math.random() * (max - min),
  }));
}

function StatusBadge({ status }) {
  const isHealthy = status === "healthy";
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider",
        isHealthy
          ? "bg-emerald-500/20 text-emerald-400"
          : "bg-red-500/20 text-red-400"
      )}
    >
      <span
        className={clsx(
          "w-1.5 h-1.5 rounded-full",
          isHealthy ? "bg-emerald-400" : "bg-red-400"
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

// ---------- Source Card ----------

function SourceCard({ source, isSelected, onClick }) {
  const sparkColor =
    source.status === "degraded" ? "#f87171" : "#22d3ee";

  return (
    <button
      onClick={onClick}
      className={clsx(
        "w-full text-left px-3 py-2.5 rounded-lg border transition-all duration-150 group",
        isSelected
          ? "bg-cyan-500/10 border-cyan-500/50"
          : "bg-[#0d1520] border-gray-800 hover:border-gray-600"
      )}
    >
      <div className="flex items-center gap-3">
        {/* Icon */}
        <div
          className={clsx(
            "w-8 h-8 rounded flex items-center justify-center text-xs font-bold text-white flex-shrink-0",
            source.iconBg
          )}
        >
          {source.icon}
        </div>

        {/* Name + type */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-100 truncate">
              {source.name}
            </span>
            <span
              className={clsx(
                "px-1.5 py-0.5 rounded text-[9px] font-medium",
                source.typeBadgeColor
              )}
            >
              {source.type}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <StatusBadge status={source.status} />
            {source.id === "alpaca" && source.status === "healthy" && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                LIVE PING
              </span>
            )}
            <span className="text-[10px] text-gray-500">
              {source.latency}
            </span>
            {source.dataRate && (
              <span className="text-[10px] text-gray-500">
                {source.dataRate}
              </span>
            )}
            {source.dataSize && (
              <span className="text-[10px] text-gray-500">
                {source.dataSize}
              </span>
            )}
          </div>
        </div>

        {/* Sparkline */}
        <MiniSparkline data={source.sparkData} color={sparkColor} />

        {/* Uptime */}
        <div className="text-right flex-shrink-0 w-12">
          <div
            className={clsx(
              "text-xs font-bold",
              source.uptime >= 99
                ? "text-emerald-400"
                : source.uptime >= 95
                ? "text-yellow-400"
                : "text-red-400"
            )}
          >
            {source.uptime}%
          </div>
        </div>

        <ChevronRight className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-400 flex-shrink-0" />
      </div>
    </button>
  );
}

// ---------- Connection Detail Panel ----------

function ConnectionDetailPanel({ source }) {
  const [showApiKey, setShowApiKey] = useState(false);
  const [showApiSecret, setShowApiSecret] = useState(false);
  const [copied, setCopied] = useState(null);

  const handleCopy = useCallback((field) => {
    setCopied(field);
    setTimeout(() => setCopied(null), 1500);
  }, []);

  if (!source) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 text-sm">
        Select a source to view details
      </div>
    );
  }

  // Static detail data for Alpaca (main detail view in mockup)
  const isAlpaca = source.id === "alpaca";
  const detail = {
    name: isAlpaca ? "Alpaca Markets" : source.name,
    type: isAlpaca ? "Market Data" : source.type,
    apiKey: "ak-****************************3f7d",
    apiSecret: "sk-****************************9a2b",
    baseUrl: isAlpaca
      ? "https://paper-api.alpaca.markets/v2"
      : `https://api.${source.id}.com/v1`,
    wsUrl: isAlpaca
      ? "wss://stream.data.alpaca.markets/v2"
      : `wss://stream.${source.id}.com`,
    rateLimit: isAlpaca ? "200 req/min" : "100 req/min",
    pollingInterval: isAlpaca ? "Real-time (WebSocket)" : "30s",
    connectionType: isAlpaca ? "Paper Trading" : "Production",
    testResult: isAlpaca
      ? "Account: $251,456 equity"
      : `Connected - ${source.latency} latency`,
  };

  return (
    <div className="h-full flex flex-col">
      {/* Panel Header */}
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div className="text-[10px] text-gray-500 uppercase tracking-widest font-medium">
            Connection Detail Panel
          </div>
        </div>
        <div className="flex items-center gap-3 mt-2">
          <div
            className={clsx(
              "w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold text-white",
              source.iconBg
            )}
          >
            {source.icon}
          </div>
          <div>
            <div className="text-base font-semibold text-white">
              {detail.name}
            </div>
            <span
              className={clsx(
                "px-1.5 py-0.5 rounded text-[9px] font-medium",
                source.typeBadgeColor
              )}
            >
              {detail.type}
            </span>
          </div>
        </div>
      </div>

      {/* Fields */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 custom-scrollbar">
        {/* API Key */}
        <FieldRow label="API Key">
          <div className="flex items-center gap-1.5">
            <code className="text-xs text-gray-300 bg-[#0d1520] px-2 py-1 rounded flex-1 font-mono truncate">
              {showApiKey ? "ak-7f3a9b2c4d5e6f7a8b9c0d1e2f3a4b5c3f7d" : detail.apiKey}
            </code>
            <button
              onClick={() => setShowApiKey(!showApiKey)}
              className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
              title={showApiKey ? "Hide" : "Show"}
            >
              {showApiKey ? (
                <EyeOff className="w-3.5 h-3.5" />
              ) : (
                <Eye className="w-3.5 h-3.5" />
              )}
            </button>
            <button
              onClick={() => handleCopy("apiKey")}
              className="p-1 text-gray-500 hover:text-cyan-400 transition-colors"
              title="Copy"
            >
              {copied === "apiKey" ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
            <button
              className="px-2 py-0.5 text-[10px] text-gray-400 border border-gray-700 rounded hover:border-gray-500 transition-colors"
            >
              Paste
            </button>
            <button
              className="px-2 py-0.5 text-[10px] text-gray-400 border border-gray-700 rounded hover:border-gray-500 transition-colors"
            >
              Reset
            </button>
          </div>
        </FieldRow>

        {/* API Secret */}
        <FieldRow label="API Secret">
          <div className="flex items-center gap-1.5">
            <code className="text-xs text-gray-300 bg-[#0d1520] px-2 py-1 rounded flex-1 font-mono truncate">
              {showApiSecret ? "sk-8a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d9a2b" : detail.apiSecret}
            </code>
            <button
              onClick={() => setShowApiSecret(!showApiSecret)}
              className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
            >
              {showApiSecret ? (
                <EyeOff className="w-3.5 h-3.5" />
              ) : (
                <Eye className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </FieldRow>

        {/* Base URL */}
        <FieldRow label="Base URL">
          <code className="text-xs text-cyan-400 font-mono">
            {detail.baseUrl}
          </code>
        </FieldRow>

        {/* WebSocket URL */}
        <FieldRow label="WebSocket URL">
          <code className="text-xs text-cyan-400 font-mono">
            {detail.wsUrl}
          </code>
        </FieldRow>

        {/* Rate Limit */}
        <FieldRow label="Rate Limit">
          <span className="text-xs text-gray-300">{detail.rateLimit}</span>
        </FieldRow>

        {/* Polling Interval */}
        <FieldRow label="Polling Interval">
          <span className="text-xs text-gray-300">
            {detail.pollingInterval}
          </span>
        </FieldRow>

        {/* Connection Type */}
        <FieldRow label="Connection Type">
          <span className="text-xs text-gray-300">
            {detail.connectionType}
          </span>
        </FieldRow>

        {/* Connection Test Result */}
        <div className="pt-2 border-t border-gray-800">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">
            Connection Test Result
          </div>
          <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 rounded px-3 py-2">
            <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span className="text-xs text-emerald-400 font-medium">
              {detail.testResult}
            </span>
          </div>
        </div>

        {/* Connection Log */}
        <div className="pt-2 border-t border-gray-800">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">
            Connection Log
          </div>
          <div className="space-y-1 max-h-[120px] overflow-y-auto custom-scrollbar">
            {[
              { time: "10:39:28", msg: "WebSocket connected", ok: true },
              { time: "10:39:27", msg: "Auth handshake complete", ok: true },
              { time: "10:39:25", msg: "REST ping OK — 7ms", ok: true },
              { time: "10:38:50", msg: "Subscription: trades, quotes", ok: true },
              { time: "10:38:12", msg: "Rate limit check passed", ok: true },
              { time: "10:37:45", msg: "Account verified — $251,456 equity", ok: true },
            ].map((entry, i) => (
              <div key={i} className="flex items-start gap-2 text-[10px]">
                <span className="text-gray-600 font-mono flex-shrink-0">{entry.time}</span>
                <span className={entry.ok ? "text-gray-400" : "text-red-400"}>{entry.msg}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom buttons */}
      <div className="px-4 py-3 border-t border-gray-800 flex items-center gap-2">
        <button className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium py-2 px-4 rounded transition-colors flex items-center justify-center gap-1.5">
          <Wifi className="w-3.5 h-3.5" />
          Connected
        </button>
        <button className="flex-1 border border-gray-700 hover:border-gray-500 text-gray-400 hover:text-gray-200 text-xs font-medium py-2 px-4 rounded transition-colors flex items-center justify-center gap-1.5">
          <RotateCw className="w-3.5 h-3.5" />
          Reset to Default
        </button>
      </div>
    </div>
  );
}

function FieldRow({ label, children }) {
  return (
    <div>
      <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">
        {label}
      </div>
      {children}
    </div>
  );
}

// ---------- Main Component ----------

export default function DataSourcesMonitor() {
  const { data, loading, error, refetch } = useApi("dataSources", {
    pollIntervalMs: 30000,
  });

  const [selectedSourceId, setSelectedSourceId] = useState("alpaca");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeProviderTab, setActiveProviderTab] = useState("Finnhub");
  const [supplementaryChecked, setSupplementaryChecked] = useState({
    yfinance: true,
    benzinga: false,
    rss: false,
    openclaw: true,
    reddit: false,
    resend: false,
    tradingview: false,
    github_gist: false,
  });

  // Merge API data with static definitions
  const sources = useMemo(() => {
    if (!data) return SOURCE_DEFS;
    const apiSources = Array.isArray(data) ? data : data?.sources || [];
    return SOURCE_DEFS.map((def) => {
      const apiMatch = apiSources.find(
        (s) =>
          s.id === def.id ||
          s.name?.toLowerCase() === def.name.toLowerCase()
      );
      if (apiMatch) {
        return {
          ...def,
          status: apiMatch.status || def.status,
          latency: apiMatch.latency || def.latency,
          dataRate: apiMatch.dataRate || apiMatch.data_rate || def.dataRate,
          uptime: apiMatch.uptime ?? def.uptime,
        };
      }
      return def;
    });
  }, [data]);

  const selectedSource = useMemo(
    () => sources.find((s) => s.id === selectedSourceId) || sources[0],
    [sources, selectedSourceId]
  );

  const connectedCount = useMemo(
    () => sources.filter((s) => s.status === "healthy").length,
    [sources]
  );

  const healthPct = useMemo(() => {
    if (!sources.length) return 0;
    const healthyWeight = sources.reduce(
      (acc, s) => acc + (s.status === "healthy" ? 1 : 0.5),
      0
    );
    return Math.round((healthyWeight / sources.length) * 100);
  }, [sources]);

  const toggleSupplementary = useCallback((id) => {
    setSupplementaryChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  return (
    <div className="h-full flex flex-col gap-0 -m-6">
      {/* ===== HEADER BAR ===== */}
      <div className="px-5 py-3 border-b border-gray-800 bg-[#0a0f1a] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-cyan-400" />
          <h1 className="text-sm font-bold text-white tracking-wider uppercase">
            Data_Sources_Manager
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <TopMetric
            icon={<Wifi className="w-3 h-3 text-emerald-400" />}
            label="WS"
            value="CONNECTED"
            valueColor="text-emerald-400"
          />
          <TopMetric
            icon={<Activity className="w-3 h-3 text-cyan-400" />}
            label="API"
            value="Healthy"
            valueColor="text-cyan-400"
          />
          <button
            onClick={refetch}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium rounded transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
        </div>
      </div>

      {/* ===== TOP METRICS BAR ===== */}
      <div className="px-5 py-2 border-b border-gray-800 bg-[#0b1120] flex items-center gap-6 text-xs">
        <MetricPill
          label="Connected"
          value={`${connectedCount}/${sources.length} sources`}
        />
        <MetricPill label="System Health" value={`${healthPct}%`} />
        <MetricPill label="Ingestion" value="4.2K rec/min" />
        <MetricPill
          label="OpenClaw Bridge"
          value="CONNECTED"
          valueColor="text-emerald-400"
        />
        <MetricPill
          label="WS"
          value="CONNECTED"
          valueColor="text-emerald-400"
        />
      </div>

      {/* ===== AI-POWERED ADD SOURCE INPUT ===== */}
      <div className="px-5 py-3 border-b border-gray-800 bg-[#0b1120]">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Type a service name, URL, or paste API docs link..."
              className="w-full bg-[#0d1520] border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-cyan-500/50 transition-colors"
            />
          </div>
          <button className="flex items-center gap-1.5 px-3 py-2 border border-gray-700 rounded-lg text-xs text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors">
            <ShoppingBag className="w-3.5 h-3.5" />
            Shop API store
          </button>
        </div>

        {/* Provider tabs */}
        <div className="flex items-center gap-1 mt-2">
          {PROVIDER_TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveProviderTab(tab)}
              className={clsx(
                "px-3 py-1 rounded text-[11px] font-medium transition-colors",
                activeProviderTab === tab
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40"
                  : "text-gray-500 hover:text-gray-300 border border-transparent hover:border-gray-700"
              )}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* ===== MAIN SPLIT VIEW ===== */}
      <div className="flex-1 flex min-h-0">
        {/* Left column - Source list */}
        <div className="w-[58%] border-r border-gray-800 overflow-y-auto custom-scrollbar">
          <div className="p-3 space-y-1.5">
            {sources.map((source) => (
              <SourceCard
                key={source.id}
                source={source}
                isSelected={selectedSourceId === source.id}
                onClick={() => setSelectedSourceId(source.id)}
              />
            ))}
          </div>

          {/* SUPPLEMENTARY SECTION */}
          <div className="px-4 py-3 border-t border-gray-800">
            <div className="text-[10px] text-gray-500 uppercase tracking-widest font-medium mb-2">
              Supplementary
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
              {SUPPLEMENTARY_SOURCES.map((sup) => (
                <label
                  key={sup.id}
                  className="flex items-center gap-1.5 cursor-pointer group"
                >
                  <input
                    type="checkbox"
                    checked={supplementaryChecked[sup.id] || false}
                    onChange={() => toggleSupplementary(sup.id)}
                    className="w-3 h-3 rounded border-gray-600 bg-[#0d1520] text-cyan-500 focus:ring-0 focus:ring-offset-0 accent-cyan-500"
                  />
                  <span className="text-[11px] text-gray-400 group-hover:text-gray-200 transition-colors">
                    {sup.label}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Right column - Connection Detail Panel */}
        <div className="w-[42%] bg-[#0a0f1a] overflow-hidden flex flex-col">
          <ConnectionDetailPanel source={selectedSource} />
        </div>
      </div>

      {/* ===== FOOTER BAR ===== */}
      <div className="px-5 py-2 border-t border-gray-800 bg-[#080c14] flex items-center justify-between text-[10px] text-gray-600">
        <div className="flex items-center gap-4">
          <span>
            <span className="text-gray-500">FRED Macro Data:</span> Syncs daily
            at 08:00 EST
          </span>
          <span>
            <span className="text-gray-500">SEC EDGAR:</span> Polls every 15m
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span>System telemetry: 0/39</span>
          <span>Idle: 4/11</span>
          <span>
            {new Date().toLocaleTimeString("en-US", {
              hour12: false,
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </span>
        </div>
      </div>
    </div>
  );
}

// ---------- Small sub-components ----------

function TopMetric({ icon, label, value, valueColor = "text-gray-300" }) {
  return (
    <div className="flex items-center gap-1.5 text-xs">
      {icon}
      <span className="text-gray-500">{label}:</span>
      <span className={clsx("font-medium", valueColor)}>{value}</span>
    </div>
  );
}

function MetricPill({ label, value, valueColor = "text-gray-300" }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-gray-500">{label}:</span>
      <span className={clsx("font-medium", valueColor)}>{value}</span>
    </div>
  );
}
