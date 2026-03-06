import React, { useState, useEffect, useMemo, useCallback } from "react";
import PatternFrequencyLC from '../components/charts/PatternFrequencyLC';
import {
  Search,
  Filter,
  Download,
  ChevronDown,
  ChevronUp,
  Layers,
  Target,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart2,
  Grid3X3,
  Star,
  AlertTriangle,
  CheckCircle,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Eye,
  Zap,
  Brain,
} from "lucide-react";
import { toast } from "react-toastify";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/ui/PageHeader";
import Button from "../components/ui/Button";
import Slider from "../components/ui/Slider";
import Checkbox from "../components/ui/Checkbox";
import TextField from "../components/ui/TextField";
import DataTable from "../components/ui/DataTable";
import MiniChart from "../components/charts/MiniChart";
import { getApiUrl, getAuthHeaders } from "../config/api";
import log from "@/utils/logger";

// ═══════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════
const parseMarketCapNum = (capStr) => {
  if (!capStr) return 0;
  const str = String(capStr).toUpperCase().replace(/[^0-9.BKMTBMK]/g, "");
  const num = parseFloat(str);
  if (isNaN(num)) return 0;
  if (str.includes("T")) return num * 1e12;
  if (str.includes("B")) return num * 1e9;
  if (str.includes("M")) return num * 1e6;
  if (str.includes("K")) return num * 1e3;
  return num;
};

const marketCapCategory = (val) => {
  if (val >= 200e9) return "Mega Cap";
  if (val >= 10e9) return "Large Cap";
  if (val >= 2e9) return "Mid Cap";
  if (val >= 300e6) return "Small Cap";
  return "Micro Cap";
};

const normalizeExchange = (ex) => {
  if (!ex) return "Unknown";
  const u = ex.toUpperCase();
  if (u.includes("NASD")) return "NASDAQ";
  if (u.includes("NYSE")) return "NYSE";
  if (u.includes("AMEX") || u.includes("ARCA")) return "AMEX";
  return ex;
};

// Normalize a row that may use PascalCase / "Market Cap" from Finviz CSV or nested raw
const _r = (row, key, ...altKeys) => {
  const r = row && row.raw ? { ...row.raw, ...row } : row;
  if (!r) return undefined;
  const v = r[key] ?? altKeys.map((k) => r[k]).find((val) => val !== undefined && val !== "");
  return v === undefined || v === "" ? undefined : v;
};

const mapRowToStockData = (row) => {
  const num = (v) => (v === undefined || v === null || v === "") ? null : parseFloat(String(v).replace(/[^0-9.-]/g, ""));
  const price = num(_r(row, "price", "Price")) ?? 0;
  const changePctVal = _r(row, "changePct", "perf_w", "Change");
  const changePctNum = typeof changePctVal === "string" ? parseFloat(String(changePctVal).replace("%", "")) : parseFloat(changePctVal);
  return {
    symbol: (_r(row, "ticker", "symbol", "Ticker") || "").toString().trim().toUpperCase(),
    name: (_r(row, "company", "name", "Company") || "").toString().trim(),
    price,
    change: num(_r(row, "change", "Change")) ?? 0,
    changePct: Number.isFinite(changePctNum) ? changePctNum : (num(_r(row, "Change")) ?? 0),
    volume: parseInt(_r(row, "volume", "Volume") || "0", 10) || 0,
    marketCap: (_r(row, "marketCap", "market_cap", "Market Cap", "market_cap_display") || "").toString().trim(),
    sector: (_r(row, "sector", "Sector") || "").toString().trim(),
    industry: (_r(row, "industry", "Industry") || "").toString().trim(),
    exchange: normalizeExchange(_r(row, "exchange", "Exchange")),
    pe: num(_r(row, "pe", "P/E")) ?? null,
    rsi: num(_r(row, "rsi14", "rsi", "RSI")) ?? null,
    atr: num(_r(row, "atr14", "atr", "ATR")) ?? null,
    sma20: num(_r(row, "sma20", "SMA20")) ?? null,
    sma50: num(_r(row, "sma50", "SMA50")) ?? null,
    sma200: num(_r(row, "sma200", "SMA200")) ?? null,
    raw: row,
  };
};

// ═══════════════════════════════════════════════════
// PATTERN DISPLAY CONFIG
// Icon/name lookup only. winRate & avgR come from /api/v1/patterns (real data).
// ═══════════════════════════════════════════════════
const PATTERN_DISPLAY = [
  { key: "bull_flag",      name: "Bull Flag",            direction: "bullish", icon: "🏁" },
  { key: "bear_flag",      name: "Bear Flag",            direction: "bearish",  icon: "🚩" },
  { key: "ascending_tri", name: "Ascending Triangle",   direction: "bullish", icon: "△" },
  { key: "descending_tri",name: "Descending Triangle",  direction: "bearish",  icon: "▽" },
  { key: "cup_handle",    name: "Cup & Handle",          direction: "bullish", icon: "☕" },
  { key: "dbl_bottom",    name: "Double Bottom",         direction: "bullish", icon: "W" },
  { key: "dbl_top",       name: "Double Top",            direction: "bearish",  icon: "M" },
  { key: "head_shoulders",name: "Head & Shoulders",      direction: "bearish",  icon: "⛰" },
  { key: "compression",   name: "Velez Compression",     direction: "neutral", icon: "⊞" },
  { key: "elephant_bar",  name: "Elephant Bar",          direction: "neutral", icon: "🐘" },
];

// Build a normalized pattern key from API pattern string
const normalizePatternKey = (pat) => {
  if (!pat) return "";
  return pat.toLowerCase().replace(/[^a-z0-9]/g, "_").replace(/_+/g, "_").replace(/^_|_$/g, "");
};

// Find display config for an API pattern name
const findPatternDisplay = (patternName) => {
  const key = normalizePatternKey(patternName);
  return PATTERN_DISPLAY.find((p) => key.includes(p.key) || p.key.includes(key)) || {
    key,
    name: patternName || "Unknown",
    direction: "neutral",
    icon: "?",
  };
};

// Sector color palette for heatmap
const SECTOR_COLORS = {
  "Technology":          "#3b82f6",
  "Healthcare":          "#22c55e",
  "Financials":          "#a855f7",
  "Consumer Cyclical":   "#f59e0b",
  "Industrials":         "#6366f1",
  "Energy":              "#ef4444",
  "Communication":       "#ec4899",
  "Real Estate":         "#14b8a6",
  "Materials":           "#78716c",
  "Utilities":           "#64748b",
  "Consumer Defensive":  "#84cc16",
};
const getSectorColor = (sector) => SECTOR_COLORS[sector] || "#94a3b8";

// ═══════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════
export default function Patterns() {
  const navigate = useNavigate();

  // State: Data
  const [stocks, setStocks] = useState([]);
  const [patterns, setPatterns] = useState([]); // real patterns from /api/v1/patterns
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedStock, setSelectedStock] = useState(null);

  // State: Filters (with localStorage persistence)
  const loadFilters = () => {
    try {
      const saved = localStorage.getItem("patterns_filters_v3");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  };
  const defaultFilters = {
    search: "",
    priceRange: [0, 500],
    marketCap: [], // show all by default; was ["mega","large","mid"] which excluded stocks without parseable marketCap
    exchanges: [], // show all by default
    assetType: "stocks",
    minVolume: 0, // was 500000; show all, user can raise
    rsiRange: [0, 100],
    patternTypes: [],
    patternDirection: "ALL",
    minConfidence: 0,
    onlyActivePatterns: false,
  };
  const [filters, setFilters] = useState(loadFilters() || defaultFilters);
  const [filtersCollapsed, setFiltersCollapsed] = useState(false);
  const [activeView, setActiveView] = useState("TABLE"); // TABLE, HEATMAP, STATS
  const [page, setPage] = useState(1);
  const perPage = 12;

  // Persist filters
  useEffect(() => {
    localStorage.setItem("patterns_filters_v3", JSON.stringify(filters));
  }, [filters]);

  // Fetch Stocks from /api/v1/stocks/list (Finviz/Alpaca — no yfinance)
  useEffect(() => {
    const fetchStocks = async () => {
      setLoading(true);
      try {
        const res = await fetch(getApiUrl("/api/v1/stocks/list"), { headers: getAuthHeaders() });
        if (!res.ok) throw new Error(`Stocks API ${res.status}`);
        const json = await res.json();
        const rows = json.data || json.stocks || json || [];
        setStocks(rows.map(mapRowToStockData));
        setError(null);
      } catch (err) {
        log.error("Stocks fetch error:", err);
        setError(err.message);
        toast.error(`Failed to load stock data: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };
    fetchStocks();
    const interval = setInterval(fetchStocks, 60000);
    return () => clearInterval(interval);
  }, []);

  // Fetch Patterns from /api/v1/patterns (DB-backed, populated by detection agents)
  useEffect(() => {
    const fetchPatterns = async () => {
      try {
        const res = await fetch(getApiUrl("/api/v1/patterns"), { headers: getAuthHeaders() });
        if (!res.ok) throw new Error(`Patterns API ${res.status}`);
        const json = await res.json();
        setPatterns(json.patterns || []);
      } catch (err) {
        log.error("Patterns fetch error:", err);
        // Non-fatal: page still works, stocks show without pattern overlay
      }
    };
    fetchPatterns();
    const interval = setInterval(fetchPatterns, 30000);
    return () => clearInterval(interval);
  }, []);

  // Build ticker -> pattern lookup from real API data
  const patternByTicker = useMemo(() => {
    const map = {};
    patterns.forEach((p) => {
      const sym = (p.ticker || "").toUpperCase();
      if (sym && !map[sym]) {
        // Use most recent pattern per ticker
        map[sym] = {
          ...findPatternDisplay(p.pattern),
          confidence: p.confidence,
          direction: p.direction || "neutral",
          timeframe: p.timeframe,
          priceTarget: p.priceTarget,
          currentPrice: p.currentPrice,
          source: p.source,
          detected: p.detected,
          raw: p,
        };
      }
    });
    return map;
  }, [patterns]);

  // Enrich stocks with real pattern data (no hash-based fake assignment)
  const enrichedStocks = useMemo(() => {
    return stocks.map((s) => ({
      ...s,
      pattern: patternByTicker[s.symbol] || null,
    }));
  }, [stocks, patternByTicker]);

  const filteredStocks = useMemo(() => {
    const priceRange = Array.isArray(filters.priceRange) && filters.priceRange.length >= 2
      ? filters.priceRange
      : [0, 1000];
    const rsiRange = Array.isArray(filters.rsiRange) && filters.rsiRange.length >= 2
      ? filters.rsiRange
      : [0, 100];
    return enrichedStocks.filter((s) => {
      if (
        filters.search &&
        !s.symbol.toLowerCase().includes(filters.search.toLowerCase()) &&
        !s.name.toLowerCase().includes(filters.search.toLowerCase())
      )
        return false;
      if (s.price < priceRange[0] || s.price > priceRange[1])
        return false;
      if (s.volume < filters.minVolume) return false;
      if (
        s.rsi !== null &&
        (s.rsi < rsiRange[0] || s.rsi > rsiRange[1])
      )
        return false;
      if (filters.onlyActivePatterns && !s.pattern) return false;
      if (
        filters.patternDirection !== "ALL" &&
        s.pattern &&
        s.pattern.direction !== filters.patternDirection
      )
        return false;
      if (
        filters.patternTypes.length > 0 &&
        s.pattern &&
        !filters.patternTypes.includes(s.pattern.key)
      )
        return false;
      if (filters.minConfidence > 0 && s.pattern &&
        (s.pattern.confidence || 0) < filters.minConfidence)
        return false;
      const capNum = parseMarketCapNum(s.marketCap);
      const capCat = marketCapCategory(capNum);
      const capMap = {
        "Mega Cap": "mega",
        "Large Cap": "large",
        "Mid Cap": "mid",
        "Small Cap": "small",
        "Micro Cap": "micro",
      };
      if (
        filters.marketCap.length > 0 &&
        !filters.marketCap.includes(capMap[capCat])
      )
        return false;
      if (
        filters.exchanges.length > 0 &&
        !filters.exchanges.includes(s.exchange)
      )
        return false;
      return true;
    });
  }, [enrichedStocks, filters]);

  const paginatedStocks = useMemo(() => {
    const start = (page - 1) * perPage;
    return filteredStocks.slice(start, start + perPage);
  }, [filteredStocks, page]);
  const totalPages = Math.ceil(filteredStocks.length / perPage);

  // CSV Export
  const exportCSV = useCallback(() => {
    const headers = [
      "Symbol", "Name", "Price", "Change%", "Volume", "MarketCap",
      "Sector", "RSI", "Pattern", "Confidence", "Direction", "Timeframe",
    ];
    const rows = filteredStocks.map((s) =>
      [
        s.symbol, s.name, s.price, s.changePct, s.volume, s.marketCap,
        s.sector, s.rsi,
        s.pattern?.name || "",
        s.pattern?.confidence || "",
        s.pattern?.direction || "",
        s.pattern?.timeframe || "",
      ].join(","),
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `patterns_scan_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Exported ${filteredStocks.length} rows`);
  }, [filteredStocks]);

  // Pattern Stats from real API data
  const patternStats = useMemo(() => {
    const counts = {};
    enrichedStocks.forEach((s) => {
      if (!s.pattern) return;
      const key = s.pattern.key || s.pattern.name;
      if (!counts[key]) {
        counts[key] = {
          ...s.pattern,
          count: 0,
          stocks: [],
          totalConfidence: 0,
        };
      }
      counts[key].count++;
      counts[key].stocks.push(s.symbol);
      counts[key].totalConfidence += s.pattern.confidence || 0;
    });
    return Object.values(counts)
      .map((c) => ({ ...c, avgConfidence: c.count > 0 ? Math.round(c.totalConfidence / c.count) : 0 }))
      .sort((a, b) => b.count - a.count);
  }, [enrichedStocks]);

  // Sector heatmap data derived from real stock + pattern data
  // FIX: replaces the old hardcoded SECTOR_PATTERN_DATA static array
  const sectorPatternData = useMemo(() => {
    const sectorMap = {};
    enrichedStocks.forEach((s) => {
      if (!s.sector) return;
      if (!sectorMap[s.sector]) {
        sectorMap[s.sector] = {
          name: s.sector,
          size: 0,
          patterns: 0,
          totalConfidence: 0,
          color: getSectorColor(s.sector),
        };
      }
      sectorMap[s.sector].size++;
      if (s.pattern) {
        sectorMap[s.sector].patterns++;
        sectorMap[s.sector].totalConfidence += s.pattern.confidence || 0;
      }
    });
    return Object.values(sectorMap)
      .map((sec) => ({
        ...sec,
        avgConfidence: sec.patterns > 0
          ? Math.round(sec.totalConfidence / sec.patterns)
          : 0,
      }))
      .filter((s) => s.size > 0)
      .sort((a, b) => b.size - a.size)
      .slice(0, 10);
  }, [enrichedStocks]);

  // ═════════════════════════════════════════════
  // Scanner agent metrics config (for Screening Engine panel)
  // ═════════════════════════════════════════════
  const scannerMetrics = [
    { key: 'betaThreshold', label: 'Beta Threshold 0-3', min: 0, max: 3, step: 0.1 },
    { key: 'mfi', label: 'MFI 0-50', min: 0, max: 50, step: 5 },
    { key: 'shortInterest', label: 'Short Interest', min: 0, max: 50, step: 1 },
    { key: 'relStrengthSPX', label: 'Rel Strength vs SPX', min: -100, max: 100, step: 5 },
    { key: 'optionsFlow', label: 'Options Flow Filter', min: 0, max: 100, step: 5 },
    { key: 'volatilityRegime', label: 'Volatility Regime', min: 0, max: 100, step: 5 },
    { key: 'darkPoolActivity', label: 'Volume Profile', min: 0, max: 100, step: 5 },
    { key: 'instAccumulation', label: 'Institutional Accumulation', min: -100, max: 100, step: 5 },
    { key: 'sectorMomentum', label: 'Sector Momentum', min: -100, max: 100, step: 5 },
  ];

  // ML metric controls for Pattern Intelligence panel
  const mlMetrics = [
    { key: 'minConfidence', label: 'Recursive Self-improvement', min: 0, max: 100, step: 5 },
    { key: 'accuracyValidation', label: 'Accuracy Validation Score %', min: 0, max: 100, step: 1 },
    { key: 'profitFactor', label: 'Profit Factor', min: 0, max: 10, step: 0.1 },
    { key: 'maxDrawdown', label: 'Max Drawdown', min: 0, max: 100, step: 1 },
    { key: 'walkForward', label: 'Walk-Forward Efficiency', min: 0, max: 100, step: 1 },
    { key: 'outOfSample', label: 'Out-of-Sample Accuracy', min: 0, max: 100, step: 1 },
    { key: 'monteCarlo', label: 'Monte Carlo CI (90/95/99%)', min: 0, max: 100, step: 1 },
    { key: 'patternComplexity', label: 'Pattern Complexity', min: 0, max: 100, step: 1 },
  ];

  // ═════════════════════════════════════════════
  // RENDER
  // ═════════════════════════════════════════════
  return (
    <div className="space-y-4">
      {/* PAGE HEADER */}
      <PageHeader
        icon={Layers}
        title="SCREENER AND PATTERNS"
        description={`${filteredStocks.length} matches from ${stocks.length} universe \u00B7 ${patterns.length} patterns detected`}
      >
        <div className="flex items-center gap-3 flex-wrap">
          <div className="bg-[#111827] p-1 rounded-[8px] border border-[rgba(42,52,68,0.5)] flex">
            {[
              { id: "TABLE", icon: <Grid3X3 className="w-4 h-4" />, label: "Table" },
              { id: "HEATMAP", icon: <BarChart2 className="w-4 h-4" />, label: "Heatmap" },
              { id: "STATS", icon: <Target className="w-4 h-4" />, label: "Stats" },
            ].map((v) => (
              <button
                key={v.id}
                onClick={() => setActiveView(v.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
                  activeView === v.id
                    ? "bg-[rgba(0,217,255,0.15)] text-[#00D9FF] shadow-[0_0_12px_rgba(0,217,255,0.15)]"
                    : "text-slate-400 hover:text-slate-200 hover:bg-[rgba(0,217,255,0.05)]"
                }`}
              >
                {v.icon} {v.label}
              </button>
            ))}
          </div>
          <Button variant="outline" onClick={exportCSV} leftIcon={Download}>
            CSV
          </Button>
        </div>
      </PageHeader>

      {/* ═══ TOP: TWO-PANEL AGENT FLEET ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* LEFT: SCREENING ENGINE */}
        <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] overflow-hidden">
          <div className="px-4 py-2.5 border-b border-[rgba(42,52,68,0.5)] bg-[#0B0E14] flex items-center justify-between">
            <h3 className="text-xs font-bold text-[#00D9FF] uppercase tracking-widest flex items-center gap-2">
              <Target className="w-4 h-4" /> Screening Engine
            </h3>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Scan Agent Fleet</span>
          </div>

          <div className="p-4 space-y-4">
            {/* Scanner Agent Cards */}
            <div className="bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-[6px] p-3">
              <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2">Scanner Agent Cards</div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Name:</span>
                  <span className="text-white font-mono">{filters.search || 'AlphaHunter_V4'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Type:</span>
                  <span className="text-[#00D9FF] font-mono">Volatility Scanner</span>
                </div>
                <div className="flex justify-between col-span-2">
                  <span className="text-slate-400">Timeframe:</span>
                  <div className="flex gap-1">
                    {['1D', '5M', '15M', '1H', '4H', 'D', 'W'].map((tf) => (
                      <span key={tf} className="text-[10px] px-1.5 py-0.5 rounded bg-[rgba(0,217,255,0.08)] text-[#00D9FF] border border-[rgba(0,217,255,0.2)] font-mono">{tf}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Trading Metric Controls */}
            <div>
              <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2">Trading Metric Controls</div>
              <div className="space-y-2 max-h-[280px] overflow-y-auto custom-scrollbar pr-1">
                {scannerMetrics.map((metric) => {
                  const val = filters[metric.key] != null ? filters[metric.key] : metric.min;
                  return (
                    <div key={metric.key} className="flex items-center gap-3">
                      <span className="text-[10px] text-slate-400 w-40 flex-shrink-0 truncate">{metric.label}</span>
                      <div className="flex-1">
                        <Slider
                          min={metric.min} max={metric.max} step={metric.step}
                          value={val}
                          onChange={(v) => setFilters((f) => ({ ...f, [metric.key]: v }))}
                        />
                      </div>
                      <span className="text-[10px] text-[#00D9FF] font-bold font-mono w-10 text-right flex-shrink-0">{val}</span>
                    </div>
                  );
                })}
                {/* Extra toggles */}
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-slate-400 w-40 flex-shrink-0">Market Regime</span>
                  <div className="flex gap-1 flex-1">
                    {['Bull', 'Put Spreads'].map((t) => (
                      <span key={t} className="text-[10px] px-2 py-0.5 rounded bg-[rgba(0,217,255,0.08)] text-[#00D9FF] border border-[rgba(0,217,255,0.15)] font-mono">{t}</span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-slate-400 w-40 flex-shrink-0">Volume Profile</span>
                  <span className="text-[10px] text-white font-mono">Value Area High</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] text-slate-400 w-40 flex-shrink-0">Dark Pool Activity</span>
                  <span className="text-[10px] text-white font-mono">Expansion</span>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-2 pt-2 border-t border-[rgba(42,52,68,0.3)]">
              <button className="px-3 py-1.5 text-[10px] font-bold rounded bg-[rgba(0,217,255,0.12)] text-[#00D9FF] border border-[rgba(0,217,255,0.3)] hover:bg-[rgba(0,217,255,0.2)] transition-colors">
                Spawn New Scanner Agent
              </button>
              <button className="px-3 py-1.5 text-[10px] font-bold rounded bg-[#0B0E14] text-slate-300 border border-[rgba(42,52,68,0.5)] hover:border-[rgba(0,217,255,0.3)] transition-colors">
                Clone Agent
              </button>
              <button className="px-3 py-1.5 text-[10px] font-bold rounded bg-[rgba(0,217,255,0.08)] text-[#00D9FF] border border-[rgba(0,217,255,0.2)] hover:bg-[rgba(0,217,255,0.15)] transition-colors">
                Power Scans
              </button>
              <button className="px-3 py-1.5 text-[10px] font-bold rounded bg-[#0B0E14] text-slate-300 border border-[rgba(42,52,68,0.5)] hover:border-[rgba(0,217,255,0.3)] transition-colors">
                Spawn Template
              </button>
              <button
                className="px-3 py-1.5 text-[10px] font-bold rounded bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 transition-colors"
                onClick={() => { setFilters(defaultFilters); toast.info("Filters reset"); }}
              >
                Kill All Agents
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT: PATTERN INTELLIGENCE */}
        <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] overflow-hidden">
          <div className="px-4 py-2.5 border-b border-[rgba(42,52,68,0.5)] bg-[#0B0E14] flex items-center justify-between">
            <h3 className="text-xs font-bold text-[#00D9FF] uppercase tracking-widest flex items-center gap-2">
              <Brain className="w-4 h-4" /> Pattern Intelligence
            </h3>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Pattern Agent Fleet</span>
          </div>

          <div className="p-4 space-y-4">
            {/* Pattern Agent Cards */}
            <div className="bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded-[6px] p-3">
              <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2">Pattern Agent Cards</div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Name:</span>
                  <span className="text-white font-mono">Fractal_Prophet_G4</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">LLM Model:</span>
                  <span className="text-[#00D9FF] font-mono">GPT-4L</span>
                </div>
                <div className="flex justify-between col-span-2">
                  <span className="text-slate-400">Architecture:</span>
                  <span className="text-white font-mono">Transformer</span>
                </div>
              </div>
            </div>

            {/* ML Metric Controls */}
            <div>
              <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2">ML Metric Controls</div>
              <div className="space-y-2 max-h-[280px] overflow-y-auto custom-scrollbar pr-1">
                {mlMetrics.map((metric) => {
                  const val = filters[metric.key] != null ? filters[metric.key] : metric.min;
                  return (
                    <div key={metric.key} className="flex items-center gap-3">
                      <span className="text-[10px] text-slate-400 w-44 flex-shrink-0 truncate">{metric.label}</span>
                      <div className="flex-1">
                        <Slider
                          min={metric.min} max={metric.max} step={metric.step}
                          value={val}
                          onChange={(v) => setFilters((f) => ({ ...f, [metric.key]: v }))}
                        />
                      </div>
                      <span className="text-[10px] text-[#00D9FF] font-bold font-mono w-10 text-right flex-shrink-0">
                        {typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(1)) : val}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-2 pt-2 border-t border-[rgba(42,52,68,0.3)]">
              <button className="px-3 py-1.5 text-[10px] font-bold rounded bg-[rgba(0,217,255,0.12)] text-[#00D9FF] border border-[rgba(0,217,255,0.3)] hover:bg-[rgba(0,217,255,0.2)] transition-colors">
                Spawn New Pattern Agent
              </button>
              <button className="px-3 py-1.5 text-[10px] font-bold rounded bg-[#0B0E14] text-slate-300 border border-[rgba(42,52,68,0.5)] hover:border-[rgba(0,217,255,0.3)] transition-colors">
                Spawn Discovery Search
              </button>
              <button className="px-3 py-1.5 text-[10px] font-bold rounded bg-[rgba(0,217,255,0.08)] text-[#00D9FF] border border-[rgba(0,217,255,0.2)] hover:bg-[rgba(0,217,255,0.15)] transition-colors">
                Spawn Template
              </button>
              <button
                className="px-3 py-1.5 text-[10px] font-bold rounded bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 transition-colors"
              >
                Kill All Agents
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ═══ BOTTOM ROW: Live Feed + Pattern Arsenal + Forming Detections ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* CONSOLIDATED LIVE FEED */}
        <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[rgba(42,52,68,0.5)] bg-[#0B0E14]">
            <Activity className="w-4 h-4 text-[#00D9FF]" />
            <h3 className="text-xs font-bold text-[#00D9FF] uppercase tracking-widest">Consolidated Live Feed</h3>
            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse ml-1" />
          </div>
          <div className="p-3">
            <div className="space-y-1 max-h-[280px] overflow-y-auto custom-scrollbar">
              {patterns.length > 0 ? patterns.slice(0, 20).map((p, i) => (
                <div key={i} className="flex items-center gap-2 px-2 py-1.5 rounded bg-[#0B0E14] hover:bg-[rgba(0,217,255,0.04)] transition-colors text-[11px] border border-transparent hover:border-[rgba(42,52,68,0.5)]">
                  <span className="text-[10px] text-slate-600 font-mono w-14 flex-shrink-0">
                    {p.detected ? new Date(p.detected).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--:--'}
                  </span>
                  <span className={`font-bold font-mono w-12 flex-shrink-0 ${p.direction === 'bullish' ? 'text-green-400' : p.direction === 'bearish' ? 'text-red-400' : 'text-[#00D9FF]'}`}>
                    {p.ticker || '--'}
                  </span>
                  <span className="text-slate-400 truncate flex-1">
                    {p.pattern || '--'}, {p.source || 'Agent'}
                  </span>
                  <span className="text-slate-500 font-mono text-[10px] flex-shrink-0">{p.confidence != null ? `${p.confidence}%` : '--'}</span>
                </div>
              )) : (
                <div className="text-center py-8 text-slate-600">
                  <Activity className="w-6 h-6 mx-auto mb-2 opacity-40" />
                  <p className="text-xs">Awaiting pattern detections from agents...</p>
                </div>
              )}
            </div>
          </div>
          {/* Status bar */}
          <div className="px-4 py-2 border-t border-[rgba(42,52,68,0.3)] bg-[#0B0E14] flex items-center justify-between text-[10px] text-slate-500">
            <span>Patterns: {patterns.length} | Agents: {patternStats.length}</span>
            <span className="text-[#00D9FF] font-mono">Status: ONLINE</span>
          </div>
        </div>

        {/* PATTERN ARSENAL */}
        <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[rgba(42,52,68,0.5)] bg-[#0B0E14]">
            <Star className="w-4 h-4 text-amber-400" />
            <h3 className="text-xs font-bold text-[#00D9FF] uppercase tracking-widest">Pattern Arsenal</h3>
          </div>
          <div className="p-3">
            <div className="grid grid-cols-2 gap-2">
              {PATTERN_DISPLAY.map((pat) => {
                const count = enrichedStocks.filter(s => s.pattern?.key === pat.key).length;
                const isActive = filters.patternTypes.includes(pat.key);
                return (
                  <div
                    key={pat.key}
                    className={`rounded-[6px] p-2.5 cursor-pointer transition-all hover:scale-[1.02] hover:shadow-[0_0_12px_rgba(0,217,255,0.08)] border ${
                      isActive
                        ? 'bg-[rgba(0,217,255,0.1)] border-[rgba(0,217,255,0.3)]'
                        : count > 0
                          ? 'bg-[#0B0E14] border-[rgba(42,52,68,0.5)]'
                          : 'bg-[#0B0E14] border-[rgba(42,52,68,0.3)] opacity-50'
                    }`}
                    onClick={() => {
                      setFilters(f => ({
                        ...f,
                        patternTypes: f.patternTypes.includes(pat.key)
                          ? f.patternTypes.filter(k => k !== pat.key)
                          : [...f.patternTypes, pat.key]
                      }));
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{pat.icon}</span>
                      <div className="min-w-0">
                        <div className="text-[10px] text-white font-bold truncate">{pat.name}</div>
                        <div className={`text-[10px] font-bold font-mono ${
                          pat.direction === 'bullish' ? 'text-green-400'
                            : pat.direction === 'bearish' ? 'text-red-400'
                            : 'text-[#00D9FF]'
                        }`}>
                          {count > 0 ? `${count} detected` : 'None'}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* FORMING DETECTIONS */}
        <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-[rgba(42,52,68,0.5)] bg-[#0B0E14]">
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
            <h3 className="text-xs font-bold text-[#00D9FF] uppercase tracking-widest">Forming Detections</h3>
            <span className="text-[10px] text-slate-500 ml-auto">Patterns in progress</span>
          </div>
          <div className="p-3">
            {patterns.filter(p => (p.confidence || 0) < 70).length > 0 ? (
              <div className="space-y-2 max-h-[300px] overflow-y-auto custom-scrollbar">
                {patterns.filter(p => (p.confidence || 0) < 70).slice(0, 6).map((p, i) => (
                  <div key={i} className="bg-[#0B0E14] border border-yellow-500/20 rounded-[6px] p-3 hover:shadow-[0_0_12px_rgba(234,179,8,0.08)] transition-shadow">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-white font-bold text-xs font-mono">{p.ticker || '--'}</span>
                      <span className="text-yellow-400 text-[10px] font-bold font-mono">{p.confidence != null ? `${p.confidence}%` : '--'}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 mb-1">{p.pattern || '--'}</div>
                    {p.timeframe && (
                      <div className="text-[10px] text-slate-500 font-mono mb-1.5">{p.timeframe}</div>
                    )}
                    <div className="w-full bg-slate-900 rounded-full h-1 overflow-hidden">
                      <div className="h-1 rounded-full bg-yellow-500/60 transition-all" style={{ width: `${p.confidence || 0}%` }} />
                    </div>
                    {/* Mini sparkline placeholder */}
                    <div className="mt-2 h-8">
                      <MiniChart symbol={p.ticker} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-600 text-xs">
                <AlertTriangle className="w-6 h-6 mx-auto mb-2 opacity-30" />
                No forming patterns below 70% confidence threshold.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ═══ VIEWS: TABLE / HEATMAP / STATS ═══ */}
      {activeView === "TABLE" && (
        <div className="flex gap-4">
          {/* LEFT: FILTER SIDEBAR */}
          <div className={`transition-all duration-300 ${filtersCollapsed ? "w-12" : "w-64"} flex-shrink-0 hidden lg:block`}>
            <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] sticky top-4 overflow-hidden">
              <button
                onClick={() => setFiltersCollapsed(!filtersCollapsed)}
                className="w-full flex items-center justify-between px-4 py-2.5 border-b border-[rgba(42,52,68,0.5)] bg-[#0B0E14] hover:bg-[rgba(0,217,255,0.05)] transition-colors"
              >
                {!filtersCollapsed && (
                  <span className="text-[10px] font-bold text-[#00D9FF] uppercase tracking-widest flex items-center gap-2">
                    <Filter className="w-3.5 h-3.5" /> Filters
                  </span>
                )}
                {filtersCollapsed ? (
                  <ChevronDown className="w-4 h-4 text-slate-400 mx-auto" />
                ) : (
                  <ChevronUp className="w-4 h-4 text-slate-400" />
                )}
              </button>
              {!filtersCollapsed && (
                <div className="p-3 space-y-4 max-h-[calc(100vh-200px)] overflow-y-auto custom-scrollbar">
                  {/* Search */}
                  <div>
                    <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1 block">Search</label>
                    <TextField
                      placeholder="Symbol or Name..."
                      value={filters.search}
                      onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
                    />
                  </div>
                  {/* Pattern Direction */}
                  <div>
                    <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1.5 block">Direction</label>
                    <div className="flex gap-1.5">
                      {["ALL", "bullish", "bearish"].map((dir) => (
                        <button
                          key={dir}
                          onClick={() => setFilters((f) => ({ ...f, patternDirection: dir }))}
                          className={`flex-1 py-1 text-[10px] font-bold rounded transition-all ${
                            filters.patternDirection === dir
                              ? dir === "bullish"
                                ? "bg-green-600/20 text-green-400 border border-green-500/30"
                                : dir === "bearish"
                                ? "bg-red-600/20 text-red-400 border border-red-500/30"
                                : "bg-[rgba(0,217,255,0.15)] text-[#00D9FF] border border-[rgba(0,217,255,0.3)]"
                              : "bg-[#0B0E14] text-slate-400 border border-[rgba(42,52,68,0.5)] hover:bg-[rgba(0,217,255,0.05)]"
                          }`}
                        >
                          {dir === "ALL" ? "ALL" : dir === "bullish" ? "LONG" : "SHORT"}
                        </button>
                      ))}
                    </div>
                  </div>
                  {/* Price Range */}
                  <div>
                    <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1 block">
                      Price: ${filters.priceRange[0]} - ${filters.priceRange[1]}
                    </label>
                    <Slider min={0} max={1000} step={5} value={filters.priceRange} onChange={(val) => setFilters((f) => ({ ...f, priceRange: val }))} />
                  </div>
                  {/* RSI */}
                  <div>
                    <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1 block">
                      RSI: {filters.rsiRange[0]} - {filters.rsiRange[1]}
                    </label>
                    <Slider min={0} max={100} step={1} value={filters.rsiRange} onChange={(val) => setFilters((f) => ({ ...f, rsiRange: val }))} />
                  </div>
                  {/* Market Cap */}
                  <div>
                    <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1.5 block">Market Cap</label>
                    {["mega", "large", "mid", "small", "micro"].map((cap) => (
                      <label key={cap} className="flex items-center gap-2 py-0.5 cursor-pointer text-[11px]">
                        <Checkbox
                          checked={filters.marketCap.includes(cap)}
                          onChange={(e) => {
                            setFilters((f) => ({
                              ...f,
                              marketCap: e.target.checked
                                ? [...f.marketCap, cap]
                                : f.marketCap.filter((c) => c !== cap),
                            }));
                          }}
                        />
                        <span className="text-slate-300 capitalize">
                          {cap.replace("mega", "Mega ($200B+)").replace("large", "Large ($10B+)").replace("mid", "Mid ($2B+)").replace("small", "Small ($300M+)").replace("micro", "Micro (<$300M)")}
                        </span>
                      </label>
                    ))}
                  </div>
                  {/* Exchange */}
                  <div>
                    <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1.5 block">Exchange</label>
                    {["NASDAQ", "NYSE", "AMEX"].map((ex) => (
                      <label key={ex} className="flex items-center gap-2 py-0.5 cursor-pointer text-[11px]">
                        <Checkbox
                          checked={filters.exchanges.includes(ex)}
                          onChange={(e) => {
                            setFilters((f) => ({
                              ...f,
                              exchanges: e.target.checked
                                ? [...f.exchanges, ex]
                                : f.exchanges.filter((x) => x !== ex),
                            }));
                          }}
                        />
                        <span className="text-slate-300">{ex}</span>
                      </label>
                    ))}
                  </div>
                  {/* Only Active */}
                  <label className="flex items-center gap-2 cursor-pointer text-[11px]">
                    <Checkbox
                      checked={filters.onlyActivePatterns}
                      onChange={(e) => setFilters((f) => ({ ...f, onlyActivePatterns: e.target.checked }))}
                    />
                    <span className="text-slate-300">Only w/ patterns</span>
                  </label>
                  {/* Reset */}
                  <Button
                    variant="ghost"
                    className="w-full text-[10px]"
                    size="sm"
                    onClick={() => { setFilters(defaultFilters); toast.info("Filters reset"); }}
                  >
                    Reset All Filters
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* CENTER: DATA TABLE */}
          <div className="flex-1 min-w-0">
            <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 z-10">
                  <tr className="bg-[#0B0E14] border-b border-[rgba(42,52,68,0.5)] text-[10px] uppercase tracking-wider text-slate-400">
                    <th className="p-2.5 font-semibold">Asset</th>
                    <th className="p-2.5 font-semibold">Price</th>
                    <th className="p-2.5 font-semibold hidden lg:table-cell">Vol</th>
                    <th className="p-2.5 font-semibold hidden md:table-cell">RSI</th>
                    <th className="p-2.5 font-semibold">Pattern</th>
                    <th className="p-2.5 font-semibold text-center">Conf%</th>
                    <th className="p-2.5 font-semibold">TF</th>
                    <th className="p-2.5 font-semibold w-20">Spark</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(42,52,68,0.3)]">
                  {paginatedStocks.map((stock) => (
                    <tr
                      key={stock.symbol}
                      onClick={() => setSelectedStock(stock)}
                      className={`cursor-pointer transition-all ${
                        selectedStock?.symbol === stock.symbol
                          ? "bg-[rgba(0,217,255,0.08)] shadow-[inset_2px_0_0_#00D9FF]"
                          : "hover:bg-[rgba(0,217,255,0.04)]"
                      }`}
                    >
                      <td className="p-2.5">
                        <div className="font-black text-white text-xs tracking-wider">{stock.symbol}</div>
                        <div className="text-[10px] text-slate-500 truncate max-w-[100px]">{stock.sector}</div>
                      </td>
                      <td className="p-2.5 text-xs">
                        <div className="text-white font-mono">${stock.price.toFixed(2)}</div>
                        <div className={`text-[10px] flex items-center gap-0.5 font-mono ${stock.changePct >= 0 ? "text-green-400" : "text-red-400"}`}>
                          {stock.changePct >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                          {stock.changePct >= 0 ? "+" : ""}{Math.abs(stock.changePct).toFixed(2)}%
                        </div>
                      </td>
                      <td className="p-2.5 text-[11px] text-slate-400 hidden lg:table-cell font-mono">
                        {(stock.volume / 1e6).toFixed(1)}M
                      </td>
                      <td className="p-2.5 text-xs hidden md:table-cell">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono ${
                          stock.rsi > 70 ? "text-red-400 bg-red-500/10"
                            : stock.rsi < 30 ? "text-green-400 bg-green-500/10"
                            : "text-slate-300 bg-slate-700/30"
                        }`}>
                          {stock.rsi?.toFixed(0) || "--"}
                        </span>
                      </td>
                      <td className="p-2.5">
                        {stock.pattern ? (
                          <div className="flex items-center gap-1">
                            <span className="text-sm">{stock.pattern.icon}</span>
                            <div>
                              <div className="text-[11px] font-bold text-white">{stock.pattern.name}</div>
                              <div className={`text-[10px] font-bold ${
                                stock.pattern.direction === "bullish" ? "text-green-400"
                                  : stock.pattern.direction === "bearish" ? "text-red-400"
                                  : "text-[#00D9FF]"
                              }`}>
                                {stock.pattern.direction?.toUpperCase()}
                              </div>
                            </div>
                          </div>
                        ) : (
                          <span className="text-slate-600 text-[11px]">--</span>
                        )}
                      </td>
                      <td className="p-2.5 text-center">
                        {stock.pattern?.confidence != null ? (
                          <span className={`text-xs font-bold font-mono ${
                            stock.pattern.confidence >= 70 ? "text-green-400" : "text-slate-300"
                          }`}>
                            {stock.pattern.confidence}%
                          </span>
                        ) : <span className="text-slate-600 font-mono text-xs">--</span>}
                      </td>
                      <td className="p-2.5 text-center text-[11px] text-[#00D9FF] font-bold font-mono">
                        {stock.pattern?.timeframe || "--"}
                      </td>
                      <td className="p-2.5">
                        <div className="w-20 h-7">
                          <MiniChart symbol={stock.symbol} />
                        </div>
                      </td>
                    </tr>
                  ))}
                  {paginatedStocks.length === 0 && (
                    <tr>
                      <td colSpan={8} className="p-12 text-center text-slate-500">
                        {loading ? "Loading..." : "No matches. Adjust filters."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {/* Pagination */}
            <div className="flex justify-between items-center mt-3 px-1">
              <span className="text-[10px] text-slate-500">
                {filteredStocks.length} results \u00B7 Page {page}/{totalPages || 1}
              </span>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</Button>
                <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
              </div>
            </div>
          </div>

          {/* RIGHT: DETAIL PANEL */}
          <div className="w-72 flex-shrink-0 hidden xl:block">
            {selectedStock ? (
              <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] sticky top-4 overflow-hidden">
                <div className="p-4 border-b border-[rgba(42,52,68,0.5)] bg-[#0B0E14]">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="text-xl font-black text-white tracking-widest">{selectedStock.symbol}</h3>
                      <p className="text-[10px] text-slate-400 mt-0.5">{selectedStock.name}</p>
                    </div>
                    {selectedStock.pattern && (
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold border ${
                        selectedStock.pattern.direction === "bullish"
                          ? "bg-green-500/20 text-green-400 border-green-500/30"
                          : selectedStock.pattern.direction === "bearish"
                          ? "bg-red-500/20 text-red-400 border-red-500/30"
                          : "bg-[rgba(0,217,255,0.15)] text-[#00D9FF] border-[rgba(0,217,255,0.3)]"
                      }`}>
                        {selectedStock.pattern.direction?.toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div className={`text-2xl font-black font-mono ${selectedStock.changePct >= 0 ? "text-green-400" : "text-red-400"}`}>
                    ${selectedStock.price.toFixed(2)}
                  </div>
                </div>
                {/* Pattern Card */}
                {selectedStock.pattern ? (
                  <div className="p-4 border-b border-[rgba(42,52,68,0.5)]">
                    <h4 className="text-[10px] text-[#00D9FF] uppercase tracking-widest font-bold mb-2">Detected Pattern</h4>
                    <div className="bg-[#0B0E14] rounded-[6px] p-3 border border-[rgba(42,52,68,0.5)] flex items-center gap-3">
                      <span className="text-3xl">{selectedStock.pattern.icon}</span>
                      <div>
                        <div className="font-bold text-white text-sm">{selectedStock.pattern.name}</div>
                        <div className="flex items-center gap-2 mt-0.5 text-[11px] font-mono">
                          <span className="text-green-400 font-bold">{selectedStock.pattern.confidence ?? '--'}%</span>
                          <span className="text-[#00D9FF] font-bold">{selectedStock.pattern.timeframe || '--'}</span>
                        </div>
                        {selectedStock.pattern.priceTarget && (
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            Target: <span className="text-white font-bold font-mono">${selectedStock.pattern.priceTarget?.toFixed(2)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 border-b border-[rgba(42,52,68,0.5)]">
                    <h4 className="text-[10px] text-[#00D9FF] uppercase tracking-widest font-bold mb-2">Detected Pattern</h4>
                    <p className="text-[11px] text-slate-500">No pattern detected by agents yet.</p>
                  </div>
                )}
                {/* Key Metrics */}
                <div className="p-4 border-b border-[rgba(42,52,68,0.5)]">
                  <h4 className="text-[10px] text-[#00D9FF] uppercase tracking-widest font-bold mb-2">Key Metrics</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { label: "Market Cap", value: selectedStock.marketCap || "--" },
                      { label: "P/E Ratio", value: selectedStock.pe?.toFixed(1) || "--" },
                      { label: "RSI (14)", value: selectedStock.rsi?.toFixed(1) || "--" },
                      { label: "ATR (14)", value: selectedStock.atr?.toFixed(2) || "--" },
                      { label: "SMA 20", value: selectedStock.sma20 ? `$${selectedStock.sma20.toFixed(2)}` : "--" },
                      { label: "SMA 200", value: selectedStock.sma200 ? `$${selectedStock.sma200.toFixed(2)}` : "--" },
                    ].map((m, i) => (
                      <div key={i} className="bg-[#0B0E14] rounded-[4px] p-1.5 border border-[rgba(42,52,68,0.3)]">
                        <div className="text-[10px] text-slate-500">{m.label}</div>
                        <div className="text-xs font-bold text-white font-mono">{m.value}</div>
                      </div>
                    ))}
                  </div>
                </div>
                {/* ML Insight */}
                <div className="p-4">
                  <h4 className="text-[10px] text-[#00D9FF] uppercase tracking-widest font-bold mb-2 flex items-center gap-1">
                    <Brain className="w-3 h-3" /> ML Insight
                  </h4>
                  <div className="bg-[rgba(0,217,255,0.03)] border border-[rgba(0,217,255,0.15)] rounded-[6px] p-2.5 text-[11px] text-slate-300 leading-relaxed">
                    {selectedStock.pattern
                      ? `Agent detected ${selectedStock.pattern.name} on ${selectedStock.symbol} with ${selectedStock.pattern.confidence}% confidence via ${selectedStock.pattern.source || "ML agent"} on ${selectedStock.pattern.timeframe} timeframe.`
                      : `No pattern detected for ${selectedStock.symbol} yet. Agents scan continuously.`}
                  </div>
                  <Button
                    variant="primary"
                    className="w-full mt-3 text-[11px]"
                    size="sm"
                    onClick={() => navigate("/trade-execution")}
                  >
                    <Zap className="w-3.5 h-3.5 mr-1" /> Route to Execution
                  </Button>
                </div>
              </div>
            ) : (
              <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-10 text-center">
                <Eye className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-slate-500 text-xs">Select a row to inspect</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══ VIEW: SECTOR HEATMAP ═══ */}
      {activeView === "HEATMAP" && (
        <div className="space-y-4">
          <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-5">
            <h3 className="text-sm font-bold text-white mb-1 flex items-center gap-2">
              <Grid3X3 className="w-4 h-4 text-[#00D9FF]" /> Sector Pattern Heatmap
            </h3>
            <p className="text-[10px] text-slate-400 mb-4">
              Derived from real stock universe and detected patterns. Tile size = stock count. Color = pattern density.
            </p>
            {sectorPatternData.length === 0 ? (
              <div className="text-center text-slate-500 py-12">
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p className="text-xs">No sector data yet. Stocks loading...</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {sectorPatternData.map((sector) => {
                  const intensity = sector.size > 0 ? sector.patterns / sector.size : 0;
                  return (
                    <div
                      key={sector.name}
                      className="rounded-[6px] border border-[rgba(42,52,68,0.5)] p-3 flex flex-col justify-between transition-all hover:scale-[1.03] hover:shadow-[0_0_16px_rgba(0,217,255,0.1)] cursor-pointer"
                      style={{
                        background: `linear-gradient(135deg, ${sector.color}15, ${sector.color}05)`,
                        borderColor: `${sector.color}40`,
                        minHeight: `${Math.max(90, sector.size * 3)}px`,
                      }}
                    >
                      <div>
                        <div className="font-bold text-white text-xs mb-0.5">{sector.name}</div>
                        <div className="text-[10px] text-slate-400">{sector.size} stocks</div>
                      </div>
                      <div className="mt-2">
                        <div className="flex justify-between text-[10px] mb-0.5">
                          <span className="text-slate-400">Patterns</span>
                          <span className="font-bold text-white">{sector.patterns}</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-1 overflow-hidden">
                          <div className="h-1 rounded-full" style={{ width: `${intensity * 100}%`, backgroundColor: sector.color }} />
                        </div>
                        <div className="flex justify-between text-[10px] mt-1">
                          <span className="text-slate-500">Avg Conf</span>
                          <span className={`font-bold ${sector.avgConfidence >= 70 ? "text-green-400" : "text-slate-300"}`}>
                            {sector.avgConfidence > 0 ? `${sector.avgConfidence}%` : "--"}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          {/* Pattern Frequency Chart */}
          <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-5">
            <h3 className="text-sm font-bold text-white mb-3">Pattern Frequency Across Sectors</h3>
            <PatternFrequencyLC data={sectorPatternData} height={256} />
          </div>
        </div>
      )}

      {/* ═══ VIEW: PATTERN STATS ═══ */}
      {activeView === "STATS" && (
        <div className="space-y-4">
          {/* Top Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-3 text-center">
              <div className="text-2xl font-black text-white font-mono">{patternStats.length}</div>
              <div className="text-[10px] text-slate-400 mt-0.5">Active Pattern Types</div>
            </div>
            <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-3 text-center">
              <div className="text-2xl font-black text-green-400 font-mono">
                {patternStats.length > 0
                  ? Math.round(patternStats.reduce((a, p) => a + (p.avgConfidence || 0), 0) / patternStats.length)
                  : 0}%
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">Avg Confidence</div>
            </div>
            <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-3 text-center">
              <div className="text-2xl font-black text-[#00D9FF] font-mono">{patterns.length}</div>
              <div className="text-[10px] text-slate-400 mt-0.5">Total Patterns (API)</div>
            </div>
            <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-3 text-center">
              <div className="text-2xl font-black text-purple-400 font-mono">
                {enrichedStocks.filter((s) => s.pattern).length}
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">Stocks w/ Patterns</div>
            </div>
          </div>
          {/* Pattern Type Cards */}
          {patternStats.length === 0 ? (
            <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-12 text-center">
              <Activity className="w-8 h-8 mx-auto mb-2 text-slate-600" />
              <p className="text-slate-500 text-xs">No patterns detected yet. Agents scan continuously.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {patternStats.map((pt) => (
                <div
                  key={pt.key || pt.name}
                  className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-[8px] p-4 hover:shadow-[0_0_20px_rgba(0,217,255,0.12)] transition-all"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{pt.icon}</span>
                      <div>
                        <h4 className="font-bold text-white text-sm">{pt.name}</h4>
                        <span className={`text-[10px] font-bold tracking-widest ${
                          pt.direction === "bullish" ? "text-green-400"
                            : pt.direction === "bearish" ? "text-red-400"
                            : "text-[#00D9FF]"
                        }`}>
                          {pt.direction?.toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-black text-white">{pt.count}</div>
                      <div className="text-[10px] text-slate-500">Matches</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mb-3">
                    <div className="bg-[#0B0E14] rounded-[4px] p-2 text-center border border-[rgba(42,52,68,0.3)]">
                      <div className={`text-sm font-bold font-mono ${pt.avgConfidence >= 70 ? "text-green-400" : "text-slate-200"}`}>
                        {pt.avgConfidence}%
                      </div>
                      <div className="text-[10px] text-slate-500">Avg Confidence</div>
                    </div>
                    <div className="bg-[#0B0E14] rounded-[4px] p-2 text-center border border-[rgba(42,52,68,0.3)]">
                      <div className="text-sm font-bold text-[#00D9FF] font-mono">{pt.count}</div>
                      <div className="text-[10px] text-slate-500">Detections</div>
                    </div>
                  </div>
                  <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="h-1.5 rounded-full transition-all"
                      style={{
                        width: `${pt.avgConfidence}%`,
                        background: pt.avgConfidence >= 70
                          ? "linear-gradient(90deg, #22c55e, #4ade80)"
                          : "linear-gradient(90deg, #6366f1, #818cf8)",
                      }}
                    />
                  </div>
                  {pt.stocks && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {pt.stocks.slice(0, 6).map((sym) => (
                        <span
                          key={sym}
                          className="text-[10px] bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded px-1.5 py-0.5 text-slate-400 font-mono"
                        >
                          {sym}
                        </span>
                      ))}
                      {pt.stocks.length > 6 && (
                        <span className="text-[10px] text-slate-500">+{pt.stocks.length - 6}</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
