import { useState, useMemo, useCallback } from "react";
import { useApi } from "../hooks/useApi";
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
    typeBadgeColor: "bg-cyan-500/20 text-[#00D9FF]",
    icon: "UW",
    iconBg: "bg-indigo-600",
    status: "healthy",
    latency: "14ms",
    dataRate: "8.6K",
    dataSize: "rec/s",
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
    dataSize: "tick/s",
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
    dataRate: "2.1K",
    dataSize: "Syncs 08:00 EST",
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
    latency: "890ms",
    dataRate: "",
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
    dataRate: "18K",
    dataSize: "",
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

const FILTER_CHIPS = [
  "ALL",
  "Screener",
  "Options",
  "Market",
  "Macro",
  "Filings",
  "Sentiment",
  "News",
  "Social",
  "Knowledge",
];

const SUGGESTED_SERVICES = [
  "Polygon.io",
  "Benzinga",
  "Alpha Vantage",
  "Quandl",
  "IEX Cloud",
  "CoinGecko",
];

const SUPPLY_CHAIN_SOURCES = [
  { id: "yfinance", name: "yFinance", type: "Market", typeBadgeColor: "bg-emerald-500/20 text-emerald-400", icon: "YF", iconBg: "bg-green-600", status: "healthy", latency: "45ms", dataRate: "14.2K", uptime: 99.8 },
  { id: "reddit", name: "Reddit", type: "Social", typeBadgeColor: "bg-indigo-500/20 text-indigo-400", icon: "RD", iconBg: "bg-orange-600", status: "healthy", latency: "120ms", dataRate: "8.4K", uptime: 99.2 },
  { id: "benzinga", name: "Benzinga", type: "News", typeBadgeColor: "bg-blue-500/20 text-blue-400", icon: "BZ", iconBg: "bg-blue-700", status: "healthy", latency: "65ms", dataRate: "2.1K", uptime: 99.9 },
  { id: "rss", name: "RSS", type: "News", typeBadgeColor: "bg-orange-500/20 text-orange-400", icon: "RS", iconBg: "bg-orange-700", status: "healthy", latency: "89ms", dataRate: "5.6K", uptime: 98.5 },
  { id: "tradingview", name: "TradingView", type: "Market", typeBadgeColor: "bg-emerald-500/20 text-emerald-400", icon: "TV", iconBg: "bg-cyan-600", status: "healthy", latency: "55ms", dataRate: "22K", uptime: 99.9 },
  { id: "openclaw", name: "OpenClaw Bridge", type: "Macro", typeBadgeColor: "bg-cyan-500/20 text-[#00D9FF]", icon: "OC", iconBg: "bg-indigo-600", status: "healthy", latency: "12ms", dataRate: "18K", uptime: 99.9 },
  { id: "github_gist", name: "GitHub Gist", type: "Knowledge", typeBadgeColor: "bg-slate-500/20 text-slate-400", icon: "GH", iconBg: "bg-slate-700", status: "healthy", latency: "210ms", dataRate: "3.2K", uptime: 99.0 },
];

// ---------- Helpers ----------

function genSparkline(min, max) {
  return Array.from({ length: 20 }, () => ({
    v: 0,
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

function LatencySparkline({ points = [] }) {
  const w = 40, h = 16;
  // Need at least 2 points to draw a line; otherwise draw a flat zero line
  if (!points || points.length < 2) {
    return (
      <svg width={w} height={h} className="inline-block ml-2">
        <line x1={0} y1={h} x2={w} y2={h} stroke="#00D9FF" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }
  const max = Math.max(...points);
  const safeMax = max > 0 ? max : 1;
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${(i / (points.length - 1)) * w},${h - (p / safeMax) * h}`).join(' ');
  return (
    <svg width={w} height={h} className="inline-block ml-2">
      <polyline points={path.replace(/[ML]/g, '')} fill="none" stroke="#00D9FF" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ---------- Source Card ----------

function SourceCard({ source, isSelected, onClick }) {
  const sparkColor =
    source.status === "degraded" ? "#f87171" : "#22d3ee";

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
          ? "bg-cyan-500/10 border-[#00D9FF]/50/50"
          : "bg-[#0B0E14] border-gray-800 hover:border-gray-600"
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
            <span className="text-[10px] text-gray-500 font-mono flex items-center">
              {source.latency}
              <LatencySparkline />
            </span>
            {source.uptime && (
              <span className="text-[10px] text-gray-500 font-mono">
                {source.uptime}%
              </span>
            )}
            {source.dataRate && (
              <span className="text-[10px] text-gray-500 font-mono">
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

        {/* Metrics / Uptime */}
        <div className="text-right flex-shrink-0 w-12">
          <div
            className={clsx(
              "text-xs font-bold font-mono",
              source.uptime >= 99
                ? "text-emerald-400"
                : source.uptime >= 95
                ? "text-amber-400"
                : "text-red-400"
            )}
          >
            {source.uptime}%
          </div>
        </div>

        {/* Row actions per mockup */}
        <div className="flex items-center gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          {source.id === "alpaca" ? (
            <button type="button" className="px-2 py-0.5 text-[9px] font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 rounded hover:bg-emerald-500/30 transition-colors">
              LIVE PING
            </button>
          ) : source.id === "finviz" ? (
            <>
              <button type="button" className="px-1.5 py-0.5 text-[9px] text-gray-400 hover:text-gray-300 border border-gray-600 rounded">Show</button>
              <button type="button" className="px-1.5 py-0.5 text-[9px] text-gray-400 hover:text-gray-300 border border-gray-600 rounded">Copy</button>
              <button type="button" className="px-1.5 py-0.5 text-[9px] text-gray-400 hover:text-gray-300 border border-gray-600 rounded">Rotate</button>
            </>
          ) : null}
        </div>

        <ChevronRight className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-400 flex-shrink-0" />
      </div>
    </div>
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

  // Display name: "Alpaca Markets" for Alpaca per mockup
  const displayName = source.id === "alpaca" ? "Alpaca Markets" : (source.name || "—");
  const detail = {
    name: displayName,
    type: source.type || "—",
    apiKey: source.id === "alpaca" ? "PK****3F7A" : (source.apiKey || "—"),
    apiSecret: source.id === "alpaca" ? "**********" : (source.apiSecret || "—"),
    baseUrl: source.id === "alpaca" ? "https://paper-api.alpaca.markets/v2" : (source.baseUrl || "—"),
    wsUrl: source.id === "alpaca" ? "wss://stream.data.alpaca.markets/v2" : (source.wsUrl || "—"),
    rateLimit: source.id === "alpaca" ? "200 req/min" : (source.rateLimit || "—"),
    pollingInterval: source.id === "alpaca" ? "Real-time (WebSocket)" : (source.pollingInterval || "—"),
    accountType: source.id === "alpaca" ? "Paper Trading" : (source.tradingType || "—"),
    testResult: source.id === "alpaca" ? "Connected in 12ms - Account: $251,450 equity" : (source.testResult || "—"),
  };

  return (
    <div className="h-full flex flex-col">
      {/* Panel Header */}
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-3">
          CREDENTIAL EDITOR PANEL
        </div>
        <div className="flex items-center gap-3">
          <div
            className={clsx(
              "w-12 h-12 rounded-lg flex items-center justify-center text-lg font-bold text-white",
              source.iconBg
            )}
          >
            {source.icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-lg font-semibold text-white flex items-center gap-2">
              {detail.name}
              <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            </div>
            <span
              className={clsx(
                "inline-block mt-0.5 px-1.5 py-0.5 rounded text-[9px] font-medium",
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
          <div className="flex items-center gap-2">
            <code className="text-xs text-gray-300 bg-[#0B0E14] px-2 py-1.5 rounded flex-1 font-mono truncate border border-gray-700">
              {detail.apiKey}
            </code>
            <button className="px-2 py-0.5 text-[10px] text-gray-400 border border-gray-600 rounded hover:border-gray-500 hover:text-gray-300 transition-colors" onClick={() => handleCopy("apiKey")}>
              Copy
            </button>
            <button className="px-2 py-0.5 text-[10px] text-gray-400 border border-gray-600 rounded hover:border-gray-500 hover:text-gray-300 transition-colors">
              Rotate
            </button>
          </div>
        </FieldRow>

        {/* API Secret */}
        <FieldRow label="API Secret">
          <div className="flex items-center gap-2">
            <code className="text-xs text-gray-300 bg-[#0B0E14] px-2 py-1.5 rounded flex-1 font-mono truncate border border-gray-700">
              {showApiSecret ? "sk-8a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d9a2b" : detail.apiSecret}
            </code>
            <button onClick={() => setShowApiSecret(!showApiSecret)} className="p-1 text-gray-500 hover:text-gray-300 transition-colors" title={showApiSecret ? "Hide" : "Show"}>
              {showApiSecret ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
            <button className="px-2 py-0.5 text-[10px] text-gray-400 border border-gray-600 rounded hover:border-gray-500 hover:text-gray-300 transition-colors">
              Rotate
            </button>
          </div>
        </FieldRow>

        {/* Base URL */}
        <FieldRow label="Base URL">
          <input type="text" defaultValue={detail.baseUrl} className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-[#00D9FF] font-mono focus:outline-none focus:border-[#00D9FF]/50" readOnly />
        </FieldRow>

        {/* WebSocket URL */}
        <FieldRow label="WebSocket URL">
          <input type="text" defaultValue={detail.wsUrl} className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-[#00D9FF] font-mono focus:outline-none focus:border-[#00D9FF]/50" readOnly />
        </FieldRow>

        {/* Rate Limit */}
        <FieldRow label="Rate Limit">
          <input type="text" defaultValue={detail.rateLimit} className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 font-mono focus:outline-none focus:border-gray-600" readOnly />
        </FieldRow>

        {/* Polling Interval */}
        <FieldRow label="Polling Interval">
          <select className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 appearance-none pr-7 focus:outline-none focus:border-[#00D9FF]/50" defaultValue={detail.pollingInterval}>
            <option value="Real-time (WebSocket)">Real-time (WebSocket)</option>
            <option value="1 min">1 min</option>
            <option value="5 min">5 min</option>
            <option value="15 min">15 min</option>
          </select>
        </FieldRow>

        {/* Account Type */}
        <FieldRow label="Account Type">
          <select className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 appearance-none pr-7 focus:outline-none focus:border-[#00D9FF]/50" defaultValue={detail.accountType}>
            <option value="Paper Trading">Paper Trading</option>
            <option value="Live Trading">Live Trading</option>
          </select>
        </FieldRow>

        {/* Connection Test Result */}
        <div className="flex items-center gap-2 pt-2">
          <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span className="text-xs text-emerald-400 font-medium">
            {detail.testResult}
          </span>
        </div>
      </div>

      {/* Action buttons - Test Connection, Save Changes, Cancel, Reset to Default */}
      <div className="px-4 py-3 border-t border-gray-800 flex flex-wrap gap-2">
        <button className="px-3 py-2 text-xs font-medium rounded bg-blue-600 hover:bg-blue-500 text-white transition-colors flex items-center gap-1.5">
          <Wifi className="w-3.5 h-3.5" />
          Test Connection
        </button>
        <button className="px-3 py-2 text-xs font-medium rounded bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1.5">
          <Check className="w-3.5 h-3.5" />
          Save Changes
        </button>
        <button className="px-3 py-2 text-xs font-medium rounded bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors">
          Cancel
        </button>
        <button className="px-3 py-2 text-xs font-medium rounded bg-amber-600/80 hover:bg-amber-500/80 text-white transition-colors flex items-center gap-1.5">
          <RotateCw className="w-3.5 h-3.5" />
          Reset to Default
        </button>
      </div>

      {/* Connection Log */}
      <div className="flex-1 min-h-[80px] px-4 py-3 border-t border-gray-800 overflow-y-auto">
        <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-2">
          Connection Log
        </div>
        <div className="text-[11px] text-gray-500 font-mono space-y-0.5">
          <div>2023-10-27 14:30:15: Connected. Latency 12ms.</div>
          <div>2023-10-27 14:28:02: Reconnected after 2s outage.</div>
          <div>2023-10-27 14:25:00: Initial handshake. OK.</div>
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
  const { data, loading, error, refetch } = useApi("dataSources", {
    pollIntervalMs: 30000,
  });

  const [selectedSourceId, setSelectedSourceId] = useState("alpaca");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilterChip, setActiveFilterChip] = useState("ALL");
  const [sourceSearchQuery, setSourceSearchQuery] = useState("");

  // Merge API data with static definitions
  const sources = useMemo(() => {
    if (!data) return SOURCE_DEFS;
    const apiSources = Array.isArray(data) ? data : data?.sources || [];
    return SOURCE_DEFS.map((def) => {
      const apiMatch = apiSources.find(
        (s) =>
          s.id === def.id ||
          s.name?.toLowerCase() === def.name.toLowerCase() ||
          (def.id === "stockgeist" && (s.id === "stockgrid" || s.name?.toLowerCase() === "stockgrid"))
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

  const selectedSource = useMemo(() => {
    const fromMain = sources.find((s) => s.id === selectedSourceId);
    if (fromMain) return fromMain;
    const fromSup = SUPPLY_CHAIN_SOURCES.find((s) => s.id === selectedSourceId);
    if (fromSup) return { ...fromSup, dataSize: "", sparkData: genSparkline(0.5, 1.0) };
    return sources[0];
  }, [sources, selectedSourceId]);

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

  return (
    <div className="h-full flex flex-col gap-0 -m-6">
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
            <button key={s} className="px-3 py-1 text-[11px] font-mono text-gray-400 border border-gray-700 rounded-full hover:border-[#00D9FF]/50 hover:text-[#00D9FF] transition-colors">
              {s}
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

      {/* ===== MAIN SPLIT VIEW ===== */}
      <div className="flex-1 flex min-h-0">
        {/* Left column - Source list */}
        <div className="w-[58%] border-r border-gray-800 flex flex-col">
          <div className="px-4 py-2 border-b border-gray-800">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              SOURCE LIST
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-1.5">
            {filteredSources.map((source) => (
              <SourceCard
                key={source.id}
                source={source}
                isSelected={selectedSourceId === source.id}
                onClick={() => setSelectedSourceId(source.id)}
              />
            ))}
          </div>

          {/* SUPPLEMENTARY */}
          <div className="px-4 py-3 border-t border-gray-800">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-2">
              SUPPLEMENTARY
            </div>
            <div className="space-y-1.5">
              {SUPPLY_CHAIN_SOURCES.map((sup) => (
                <button
                  key={sup.id}
                  onClick={() => setSelectedSourceId(sup.id)}
                  className={clsx(
                    "w-full text-left px-3 py-2 rounded-lg border transition-all duration-150",
                    selectedSourceId === sup.id
                      ? "bg-cyan-500/10 border-[#00D9FF]/50"
                      : "bg-[#0B0E14] border-gray-800 hover:border-gray-600"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={clsx("w-7 h-7 rounded flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0", sup.iconBg)}>
                      {sup.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-semibold text-gray-100">{sup.name}</span>
                      <span className={clsx("ml-2 px-1.5 py-0.5 rounded text-[9px]", sup.typeBadgeColor)}>{sup.type}</span>
                    </div>
                    <StatusBadge status={sup.status} />
                    <span className="text-[10px] text-gray-500 font-mono">{sup.latency}</span>
                    <span className="text-[10px] text-emerald-400 font-mono">{sup.uptime}%</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right column - Credential / Config Panel */}
        <div className="w-[42%] bg-[#111827] overflow-hidden flex flex-col">
          <ConnectionDetailPanel source={selectedSource} />
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

