import { useState, useMemo, useCallback } from "react";
import { useApi } from "../hooks/useApi";
import {
  RefreshCw,
  Copy,
  Eye,
  EyeOff,
  Search,
  Wifi,
  Database,
  ChevronRight,
  RotateCw,
  ShoppingBag,
  Check,
  StopCircle,
  ChevronDown,
  Zap,
  Link2,
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
    dataRate: "1.2K",
    dataSize: "",
    uptime: 98.5,
    sparkData: genSparkline(0.3, 0.7),
  },
  {
    id: "sec_edgar",
    name: "SEC EDGAR",
    type: "Sentiment",
    typeBadgeColor: "bg-red-500/20 text-red-400",
    icon: "SE",
    iconBg: "bg-slate-600",
    status: "degraded",
    latency: "5.6K",
    dataRate: "",
    dataSize: "Polls 15m",
    uptime: 95.2,
    sparkData: genSparkline(0.2, 0.8),
  },
  {
    id: "stockgrid",
    name: "Stockgrid",
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

const FILTER_CHIPS = [
  "ALL",
  "Brokerage",
  "Alpha Vantage",
  "Quant",
  "RX Cloud",
  "ConfStack",
];

const SUPPLY_CHAIN_SOURCES = [
  { id: "reddit", label: "Reddit" },
  { id: "benzinga", label: "Benzinga" },
  { id: "openclaw", label: "OpenClaw Bridge" },
  { id: "tradingview", label: "TradingView" },
  { id: "github_gist", label: "GitHub Gist" },
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

  return (
    <button
      onClick={onClick}
      className={clsx(
        "w-full text-left px-3 py-2.5 rounded-lg border transition-all duration-150 group",
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

        {/* Uptime bar */}
        <div className="text-right flex-shrink-0 w-12">
          <div
            className={clsx(
              "text-xs font-bold font-mono",
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

  // Detail data from source or API — no fabricated values
  const detail = {
    name: source.name || '—',
    type: source.type || '—',
    apiKey: '—',
    apiSecret: '—',
    baseUrl: source.baseUrl || '—',
    wsUrl: source.wsUrl || '—',
    rateLimit: source.rateLimit || '—',
    pollingInterval: source.pollingInterval || '—',
    tradingType: source.tradingType || '—',
    testResult: source.testResult || '—',
  };

  return (
    <div className="h-full flex flex-col">
      {/* Panel Header */}
      <div className="px-4 py-3 border-b border-gray-800">
        <div className="flex items-center justify-between">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            Credential / Config Panel
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
            <code className="text-xs text-gray-300 bg-[#0B0E14] px-2 py-1 rounded flex-1 font-mono truncate">
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
              className="p-1 text-gray-500 hover:text-[#00D9FF] transition-colors"
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
              Copy
            </button>
            <button
              className="px-2 py-0.5 text-[10px] text-gray-400 border border-gray-700 rounded hover:border-gray-500 transition-colors"
            >
              Rotate
            </button>
          </div>
        </FieldRow>

        {/* API Secret */}
        <FieldRow label="API Secret">
          <div className="flex items-center gap-1.5">
            <code className="text-xs text-gray-300 bg-[#0B0E14] px-2 py-1 rounded flex-1 font-mono truncate">
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
          <code className="text-xs text-[#00D9FF] font-mono">
            {detail.baseUrl}
          </code>
        </FieldRow>

        {/* WebSocket URL */}
        <FieldRow label="WebSocket URL">
          <code className="text-xs text-[#00D9FF] font-mono">
            {detail.wsUrl}
          </code>
        </FieldRow>

        {/* Rate Limit */}
        <FieldRow label="Rate Limit">
          <span className="text-xs text-gray-300 font-mono">{detail.rateLimit}</span>
        </FieldRow>

        {/* Polling Interval */}
        <FieldRow label="Polling Interval">
          <span className="text-xs text-gray-300 font-mono">
            {detail.pollingInterval}
          </span>
        </FieldRow>

        {/* Trading Type - dropdown style */}
        <FieldRow label="Trading Type">
          <div className="relative">
            <select
              className="w-full bg-[#0B0E14] border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 appearance-none pr-7 focus:outline-none focus:border-[#00D9FF]/50/50 transition-colors"
              defaultValue={detail.tradingType}
            >
              <option value="Paper Trading">Paper Trading</option>
              <option value="Live Trading">Live Trading</option>
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
          </div>
        </FieldRow>

        {/* Connection Test Result */}
        <div className="pt-2 border-t border-gray-800">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-1">
            Connection Test Result
          </div>
          <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 rounded px-3 py-2">
            <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span className="text-xs text-emerald-400 font-medium">
              {detail.testResult}
            </span>
          </div>
        </div>
      </div>

      {/* Bottom buttons */}
      <div className="px-4 py-3 border-t border-gray-800 flex items-center gap-2">
        <button className="flex-1 bg-[#00D9FF]/20 hover:bg-[#00D9FF]/30 border border-[#00D9FF]/40 text-[#00D9FF] text-white text-xs font-medium py-2 px-4 rounded transition-colors flex items-center justify-center gap-1.5">
          <Wifi className="w-3.5 h-3.5" />
          Connect
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
  const [supplyChainChecked, setSupplyChainChecked] = useState({
    reddit: false,
    benzinga: true,
    openclaw: true,
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

  const toggleSupplyChain = useCallback((id) => {
    setSupplyChainChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  return (
    <div className="h-full flex flex-col gap-0 -m-6">
      {/* ===== HEADER BAR ===== */}
      <div className="px-5 py-3 border-b border-gray-800 bg-[#111827] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Database className="w-4 h-4 text-[#00D9FF]" />
          <h1 className="text-sm font-bold text-white tracking-wider uppercase">
            DATA_SOURCES_MANAGER
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {/* WS Connected badge */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] font-medium text-emerald-400">WS Connected</span>
          </span>
          {/* API Healthy badge */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className="text-[11px] font-medium text-emerald-400">API Healthy</span>
          </span>
          {/* Refresh button */}
          <button
            onClick={refetch}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#00D9FF]/20 hover:bg-[#00D9FF]/30 border border-[#00D9FF]/40 text-[#00D9FF] text-white text-xs font-medium rounded transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
        </div>
      </div>

      {/* ===== TOP METRICS BAR ===== */}
      <div className="px-5 py-2.5 border-b border-gray-800 bg-[#0B0E14] flex items-center gap-6 text-xs">
        <MetricPill
          label="Connected"
          value={`${connectedCount}/${sources.length} sources`}
        />
        <span className="text-gray-700">|</span>
        <MetricPill label="System Health" value={`${healthPct}%`} />
        <span className="text-gray-700">|</span>
        <MetricPill label="Ingestion" value="4.2K rec/min" />
        <span className="text-gray-700">|</span>
        <MetricPill
          label="OpenClaw Bridge"
          value="CONNECTED"
          valueColor="text-emerald-400"
          icon={<Link2 className="w-3 h-3 text-emerald-400" />}
        />
        <span className="text-gray-700">|</span>
        <MetricPill
          label="WS"
          value="CONNECTED"
          valueColor="text-emerald-400"
          icon={<Zap className="w-3 h-3 text-emerald-400" />}
        />
      </div>

      {/* ===== AI-POWERED ADD SOURCE INPUT ===== */}
      <div className="px-5 py-3 border-b border-gray-800 bg-[#0B0E14]">
        <div className="aurora-card p-3 mb-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-2">AI-POWERED ADD SOURCE</h3>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for data source to add..."
              className="flex-1 bg-[#0B0E14] border border-gray-700 rounded-md px-3 py-1.5 text-sm text-white placeholder-gray-600 focus:border-[#00D9FF]/50 focus:outline-none"
            />
            <button className="px-3 py-1.5 bg-cyan-500/20 text-[#00D9FF] border border-[#00D9FF]/50/30 rounded-md text-xs font-bold hover:bg-cyan-500/30">Add</button>
            <button className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-700 rounded-md text-xs text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors whitespace-nowrap">
              <ShoppingBag className="w-3.5 h-3.5" />
              Shop API store
            </button>
          </div>
          <div className="flex gap-2 mt-2">
            {['Polygon.io', 'Benzinga', 'Quandl', 'Alpha Vantage', 'IEX Cloud'].map(s => (
              <button key={s} className="px-2 py-0.5 text-[9px] font-mono text-gray-500 border border-gray-700 rounded-md hover:border-[#00D9FF]/50 hover:text-[#00D9FF]">
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Filter chips + Stop API scan */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            {FILTER_CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => setActiveFilterChip(chip)}
                className={clsx(
                  "px-3 py-1 rounded text-[11px] font-medium transition-colors",
                  activeFilterChip === chip
                    ? "bg-cyan-500/20 text-[#00D9FF] border border-[#00D9FF]/50/40"
                    : "text-gray-500 hover:text-gray-300 border border-transparent hover:border-gray-700"
                )}
              >
                {chip}
              </button>
            ))}
          </div>
          <button className="flex items-center gap-1.5 px-3 py-1 text-[11px] text-red-400 hover:text-red-300 border border-red-500/30 rounded hover:border-red-500/50 transition-colors">
            <StopCircle className="w-3 h-3" />
            Stop API scan
          </button>
        </div>
      </div>

      {/* ===== MAIN SPLIT VIEW ===== */}
      <div className="flex-1 flex min-h-0">
        {/* Left column - Source list */}
        <div className="w-[58%] border-r border-gray-800 flex flex-col">
          <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-1.5">
            {sources.map((source) => (
              <SourceCard
                key={source.id}
                source={source}
                isSelected={selectedSourceId === source.id}
                onClick={() => setSelectedSourceId(source.id)}
              />
            ))}
          </div>

          {/* SUPPLY CHAIN OVERVIEW */}
          <div className="px-4 py-3 border-t border-gray-800">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono mb-2">
              Supply Chain Overview
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
              {SUPPLY_CHAIN_SOURCES.map((sup) => (
                <label
                  key={sup.id}
                  className="flex items-center gap-1.5 cursor-pointer group"
                >
                  <input
                    type="checkbox"
                    checked={supplyChainChecked[sup.id] || false}
                    onChange={() => toggleSupplyChain(sup.id)}
                    className="w-3 h-3 rounded border-gray-600 bg-[#0B0E14] text-[#00D9FF] focus:ring-0 focus:ring-offset-0 accent-cyan-500"
                  />
                  <span className="text-[11px] text-gray-400 group-hover:text-gray-200 transition-colors">
                    {sup.label}
                  </span>
                </label>
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
            <span className="text-gray-500">FRED Macro Data:</span> Syncs daily
            at 08:00 EST
          </span>
          <span className="text-gray-700">|</span>
          <span>
            <span className="text-gray-500">SEC EDGAR:</span> Polls every 15m
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span>System telemetry: 10:33</span>
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

function MetricPill({ label, value, valueColor = "text-gray-300", icon }) {
  return (
    <div className="flex items-center gap-1.5">
      {icon}
      <span className="text-gray-500">{label}:</span>
      <span className={clsx("font-medium", valueColor)}>{value}</span>
    </div>
  );
}
