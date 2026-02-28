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
import { getApiUrl } from "../config/api";

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

const mapRowToStockData = (row) => ({
  symbol: row.ticker || row.symbol || "",
  name: row.company || row.name || "",
  price: parseFloat(row.price) || 0,
  change: parseFloat(row.change) || 0,
  changePct: parseFloat(row.changePct || row.perf_w) || 0,
  volume: parseInt(row.volume) || 0,
  marketCap: row.marketCap || row.market_cap || "",
  sector: row.sector || "",
  industry: row.industry || "",
  exchange: normalizeExchange(row.exchange),
  pe: parseFloat(row.pe) || null,
  rsi: parseFloat(row.rsi14 || row.rsi) || null,
  atr: parseFloat(row.atr14 || row.atr) || null,
  sma20: parseFloat(row.sma20) || null,
  sma50: parseFloat(row.sma50) || null,
  sma200: parseFloat(row.sma200) || null,
  raw: row,
});

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
    marketCap: ["mega", "large", "mid"],
    exchanges: ["NASDAQ", "NYSE"],
    assetType: "stocks",
    minVolume: 500000,
    rsiRange: [20, 80],
    patternTypes: [],
    patternDirection: "ALL", // ALL, bullish, bearish, neutral
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
        const res = await fetch(getApiUrl("/api/v1/stocks/list"));
        if (!res.ok) throw new Error(`Stocks API ${res.status}`);
        const json = await res.json();
        const rows = json.data || json.stocks || json || [];
        setStocks(rows.map(mapRowToStockData));
        setError(null);
      } catch (err) {
        console.error("Stocks fetch error:", err);
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
        const res = await fetch(getApiUrl("/api/v1/patterns"));
        if (!res.ok) throw new Error(`Patterns API ${res.status}`);
        const json = await res.json();
        setPatterns(json.patterns || []);
      } catch (err) {
        console.error("Patterns fetch error:", err);
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
    return enrichedStocks.filter((s) => {
      if (
        filters.search &&
        !s.symbol.toLowerCase().includes(filters.search.toLowerCase()) &&
        !s.name.toLowerCase().includes(filters.search.toLowerCase())
      )
        return false;
      if (s.price < filters.priceRange[0] || s.price > filters.priceRange[1])
        return false;
      if (s.volume < filters.minVolume) return false;
      if (
        s.rsi !== null &&
        (s.rsi < filters.rsiRange[0] || s.rsi > filters.rsiRange[1])
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
  // RENDER
  // ═════════════════════════════════════════════
  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end mb-6 gap-4">
        <PageHeader
          icon={Layers}
          title="Patterns & Screener"
          description={`${filteredStocks.length} matches from ${stocks.length} universe · ${patterns.length} patterns detected`}
        >
          <div className="flex items-center gap-3 flex-wrap">
            <div className="bg-slate-800/50 p-1 rounded-lg border border-slate-700/50 flex">
              {[
                { id: "TABLE",   icon: <Grid3X3 className="w-4 h-4" />, label: "Table" },
                { id: "HEATMAP",icon: <BarChart2 className="w-4 h-4" />, label: "Heatmap" },
                { id: "STATS",  icon: <Target className="w-4 h-4" />, label: "Stats" },
              ].map((v) => (
                <button
                  key={v.id}
                  onClick={() => setActiveView(v.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold transition-all ${
                    activeView === v.id
                      ? "bg-blue-600 text-white shadow-lg"
                      : "text-slate-400 hover:text-slate-200"
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
      </div>

      {/* 3-COLUMN LAYOUT */}
      <div className="flex gap-6">
        {/* LEFT: FILTER PANEL */}
        <div
          className={`transition-all duration-300 ${filtersCollapsed ? "w-12" : "w-72"} flex-shrink-0`}
        >
          <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl backdrop-blur-md sticky top-6 overflow-hidden">
            <button
              onClick={() => setFiltersCollapsed(!filtersCollapsed)}
              className="w-full flex items-center justify-between p-4 border-b border-slate-700/50 hover:bg-slate-800/30 transition-colors"
            >
              {!filtersCollapsed && (
                <span className="text-sm font-bold text-white flex items-center gap-2">
                  <Filter className="w-4 h-4" /> Filters
                </span>
              )}
              {filtersCollapsed ? (
                <ChevronDown className="w-4 h-4 text-slate-400 mx-auto" />
              ) : (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              )}
            </button>
            {!filtersCollapsed && (
              <div className="p-4 space-y-5 max-h-[calc(100vh-200px)] overflow-y-auto custom-scrollbar">
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
                  <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2 block">Pattern Direction</label>
                  <div className="flex gap-2">
                    {["ALL", "bullish", "bearish"].map((dir) => (
                      <button
                        key={dir}
                        onClick={() => setFilters((f) => ({ ...f, patternDirection: dir }))}
                        className={`flex-1 py-1.5 text-xs font-bold rounded transition-all ${
                          filters.patternDirection === dir
                            ? dir === "bullish"
                              ? "bg-green-600 text-white"
                              : dir === "bearish"
                              ? "bg-red-600 text-white"
                              : "bg-blue-600 text-white"
                            : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                        }`}
                      >
                        {dir === "ALL" ? "ALL" : dir === "bullish" ? "LONG" : "SHORT"}
                      </button>
                    ))}
                  </div>
                </div>
                {/* Pattern Types from API */}
                <div>
                  <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2 block">Pattern Type</label>
                  <div className="space-y-1 max-h-48 overflow-y-auto custom-scrollbar">
                    {PATTERN_DISPLAY.map((pt) => (
                      <label key={pt.key} className="flex items-center gap-2 p-1.5 rounded hover:bg-slate-800/30 cursor-pointer text-xs">
                        <Checkbox
                          checked={filters.patternTypes.includes(pt.key)}
                          onChange={(e) => {
                            setFilters((f) => ({
                              ...f,
                              patternTypes: e.target.checked
                                ? [...f.patternTypes, pt.key]
                                : f.patternTypes.filter((p) => p !== pt.key),
                            }));
                          }}
                        />
                        <span className="text-base mr-1">{pt.icon}</span>
                        <span className="text-slate-300">{pt.name}</span>
                      </label>
                    ))}
                  </div>
                </div>
                {/* Min Confidence (replaces fake winRate filter) */}
                <div>
                  <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1 block">
                    Min Confidence:{" "}
                    <span className="text-blue-400">{filters.minConfidence}%</span>
                  </label>
                  <Slider
                    min={0}
                    max={100}
                    step={5}
                    value={filters.minConfidence}
                    onChange={(val) => setFilters((f) => ({ ...f, minConfidence: val }))}
                  />
                </div>
                {/* Price Range */}
                <div>
                  <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1 block">
                    Price: ${filters.priceRange[0]} – ${filters.priceRange[1]}
                  </label>
                  <Slider
                    min={0}
                    max={1000}
                    step={5}
                    value={filters.priceRange}
                    onChange={(val) => setFilters((f) => ({ ...f, priceRange: val }))}
                  />
                </div>
                {/* RSI Range */}
                <div>
                  <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1 block">
                    RSI: {filters.rsiRange[0]} – {filters.rsiRange[1]}
                  </label>
                  <Slider
                    min={0}
                    max={100}
                    step={1}
                    value={filters.rsiRange}
                    onChange={(val) => setFilters((f) => ({ ...f, rsiRange: val }))}
                  />
                </div>
                {/* Market Cap */}
                <div>
                  <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2 block">Market Cap</label>
                  {["mega", "large", "mid", "small", "micro"].map((cap) => (
                    <label key={cap} className="flex items-center gap-2 p-1 cursor-pointer text-xs">
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
                        {cap
                          .replace("mega", "Mega ($200B+)")
                          .replace("large", "Large ($10B+)")
                          .replace("mid", "Mid ($2B+)")
                          .replace("small", "Small ($300M+)")
                          .replace("micro", "Micro (<$300M)")}
                      </span>
                    </label>
                  ))}
                </div>
                {/* Exchange */}
                <div>
                  <label className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-2 block">Exchange</label>
                  {["NASDAQ", "NYSE", "AMEX"].map((ex) => (
                    <label key={ex} className="flex items-center gap-2 p-1 cursor-pointer text-xs">
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
                {/* Only Active Patterns */}
                <div>
                  <label className="flex items-center gap-2 cursor-pointer text-xs">
                    <Checkbox
                      checked={filters.onlyActivePatterns}
                      onChange={(e) => setFilters((f) => ({ ...f, onlyActivePatterns: e.target.checked }))}
                    />
                    <span className="text-slate-300">Only stocks with detected patterns</span>
                  </label>
                </div>
                {/* Reset */}
                <Button
                  variant="ghost"
                  className="w-full text-xs"
                  onClick={() => { setFilters(defaultFilters); toast.info("Filters reset"); }}
                >
                  Reset All Filters
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* CENTER + RIGHT: Dynamic Content */}
        <div className="flex-1 min-w-0">
          {/* ═══ VIEW: TABLE ═══ */}
          {activeView === "TABLE" && (
            <div className="flex gap-6">
              {/* Table */}
              <div className="flex-1 min-w-0">
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-xl backdrop-blur-md overflow-hidden">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-800/60 border-b border-slate-700/50 text-[10px] uppercase tracking-wider text-slate-400">
                        <th className="p-3 font-semibold">Asset</th>
                        <th className="p-3 font-semibold">Price</th>
                        <th className="p-3 font-semibold hidden lg:table-cell">Vol</th>
                        <th className="p-3 font-semibold hidden md:table-cell">RSI</th>
                        <th className="p-3 font-semibold">Pattern</th>
                        <th className="p-3 font-semibold text-center">Conf%</th>
                        <th className="p-3 font-semibold">Timeframe</th>
                        <th className="p-3 font-semibold w-24">Spark</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/30">
                      {paginatedStocks.map((stock) => (
                        <tr
                          key={stock.symbol}
                          onClick={() => setSelectedStock(stock)}
                          className={`cursor-pointer transition-colors ${
                            selectedStock?.symbol === stock.symbol
                              ? "bg-blue-900/20"
                              : "hover:bg-slate-800/40"
                          }`}
                        >
                          <td className="p-3">
                            <div className="font-black text-white text-sm tracking-wider">{stock.symbol}</div>
                            <div className="text-[10px] text-slate-500 truncate max-w-[120px]">{stock.sector}</div>
                          </td>
                          <td className="p-3 text-sm">
                            <div className="text-white">${stock.price.toFixed(2)}</div>
                            <div className={`text-[10px] flex items-center gap-0.5 ${stock.changePct >= 0 ? "text-green-400" : "text-red-400"}`}>
                              {stock.changePct >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                              {Math.abs(stock.changePct).toFixed(2)}%
                            </div>
                          </td>
                          <td className="p-3 text-xs text-slate-400 hidden lg:table-cell">
                            {(stock.volume / 1e6).toFixed(1)}M
                          </td>
                          <td className="p-3 text-xs hidden md:table-cell">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              stock.rsi > 70 ? "text-red-400 bg-red-500/10"
                                : stock.rsi < 30 ? "text-green-400 bg-green-500/10"
                                : "text-slate-300 bg-slate-700/30"
                            }`}>
                              {stock.rsi?.toFixed(0) || "--"}
                            </span>
                          </td>
                          <td className="p-3">
                            {stock.pattern ? (
                              <div className="flex items-center gap-1.5">
                                <span className="text-base">{stock.pattern.icon}</span>
                                <div>
                                  <div className="text-xs font-bold text-white">{stock.pattern.name}</div>
                                  <div className={`text-[10px] font-bold ${
                                    stock.pattern.direction === "bullish" ? "text-green-400"
                                      : stock.pattern.direction === "bearish" ? "text-red-400"
                                      : "text-blue-400"
                                  }`}>
                                    {stock.pattern.direction?.toUpperCase()}
                                  </div>
                                </div>
                              </div>
                            ) : (
                              <span className="text-slate-600 text-xs">No pattern</span>
                            )}
                          </td>
                          <td className="p-3 text-center">
                            {stock.pattern?.confidence != null ? (
                              <span className={`text-sm font-bold ${
                                stock.pattern.confidence >= 70 ? "text-green-400" : "text-slate-300"
                              }`}>
                                {stock.pattern.confidence}%
                              </span>
                            ) : <span className="text-slate-600">--</span>}
                          </td>
                          <td className="p-3 text-center text-xs text-blue-400 font-bold">
                            {stock.pattern?.timeframe || "--"}
                          </td>
                          <td className="p-3">
                            <div className="w-24 h-8">
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
                <div className="flex justify-between items-center mt-4 px-2">
                  <span className="text-xs text-slate-500">
                    {filteredStocks.length} results · Page {page}/{totalPages || 1}
                  </span>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</Button>
                    <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
                  </div>
                </div>
              </div>
              {/* RIGHT: Detail Panel */}
              <div className="w-80 flex-shrink-0 hidden xl:block">
                {selectedStock ? (
                  <div className="bg-slate-900/50 border border-slate-700/50 rounded-xl backdrop-blur-md sticky top-6 overflow-hidden">
                    <div className="p-5 border-b border-slate-700/50 bg-slate-800/30">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h3 className="text-2xl font-black text-white tracking-widest">{selectedStock.symbol}</h3>
                          <p className="text-xs text-slate-400 mt-0.5">{selectedStock.name}</p>
                        </div>
                        {selectedStock.pattern && (
                          <span className={`text-[10px] px-2 py-0.5 rounded font-bold border ${
                            selectedStock.pattern.direction === "bullish"
                              ? "bg-green-500/20 text-green-400 border-green-500/30"
                              : selectedStock.pattern.direction === "bearish"
                              ? "bg-red-500/20 text-red-400 border-red-500/30"
                              : "bg-blue-500/20 text-blue-400 border-blue-500/30"
                          }`}>
                            {selectedStock.pattern.direction?.toUpperCase()}
                          </span>
                        )}
                      </div>
                      <div className={`text-3xl font-black ${selectedStock.changePct >= 0 ? "text-green-400" : "text-red-400"}`}>
                        ${selectedStock.price.toFixed(2)}
                      </div>
                    </div>
                    {/* Pattern Card */}
                    {selectedStock.pattern ? (
                      <div className="p-5 border-b border-slate-700/50">
                        <h4 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">Detected Pattern</h4>
                        <div className="bg-slate-800/60 rounded-lg p-4 border border-slate-700/40 flex items-center gap-4">
                          <span className="text-4xl">{selectedStock.pattern.icon}</span>
                          <div>
                            <div className="font-bold text-white">{selectedStock.pattern.name}</div>
                            <div className="flex items-center gap-3 mt-1 text-xs">
                              <span className="text-green-400 font-bold">{selectedStock.pattern.confidence}% Conf</span>
                              <span className="text-blue-400 font-bold">{selectedStock.pattern.timeframe}</span>
                            </div>
                            {selectedStock.pattern.priceTarget && (
                              <div className="text-xs text-slate-400 mt-1">
                                Target: <span className="text-white font-bold">${selectedStock.pattern.priceTarget?.toFixed(2)}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="p-5 border-b border-slate-700/50">
                        <h4 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">Detected Pattern</h4>
                        <p className="text-xs text-slate-500">No pattern detected by agents yet.</p>
                      </div>
                    )}
                    {/* Key Metrics */}
                    <div className="p-5 border-b border-slate-700/50">
                      <h4 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">Key Metrics</h4>
                      <div className="grid grid-cols-2 gap-3">
                        {[
                          { label: "Market Cap", value: selectedStock.marketCap || "--" },
                          { label: "P/E Ratio", value: selectedStock.pe?.toFixed(1) || "--" },
                          { label: "RSI (14)", value: selectedStock.rsi?.toFixed(1) || "--" },
                          { label: "ATR (14)", value: selectedStock.atr?.toFixed(2) || "--" },
                          { label: "SMA 20", value: selectedStock.sma20 ? `$${selectedStock.sma20.toFixed(2)}` : "--" },
                          { label: "SMA 200", value: selectedStock.sma200 ? `$${selectedStock.sma200.toFixed(2)}` : "--" },
                        ].map((m, i) => (
                          <div key={i} className="bg-slate-900/50 rounded p-2">
                            <div className="text-[10px] text-slate-500">{m.label}</div>
                            <div className="text-sm font-bold text-white">{m.value}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                    {/* ML Insight */}
                    <div className="p-5">
                      <h4 className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3 flex items-center gap-1">
                        <Brain className="w-3 h-3" /> ML Insight
                      </h4>
                      <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-3 text-xs text-slate-300 leading-relaxed">
                        {selectedStock.pattern
                          ? `Agent detected ${selectedStock.pattern.name} on ${selectedStock.symbol} with ${selectedStock.pattern.confidence}% confidence via ${selectedStock.pattern.source || "ML agent"} on ${selectedStock.pattern.timeframe} timeframe.`
                          : `No pattern has been detected for ${selectedStock.symbol} yet. Agents scan continuously — check back shortly.`}
                      </div>
                      <Button
                        variant="primary"
                        className="w-full mt-4 text-xs"
                        onClick={() => navigate("/trade-execution")}
                      >
                        <Zap className="w-4 h-4 mr-1" /> Route to Execution
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="bg-slate-900/30 border border-slate-700/30 rounded-xl p-12 text-center">
                    <Eye className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                    <p className="text-slate-500 text-sm">Select a row to inspect</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ═══ VIEW: SECTOR HEATMAP ═══ */}
          {activeView === "HEATMAP" && (
            <div className="space-y-6">
              <div className="bg-slate-900/40 border border-slate-700/50 rounded-xl backdrop-blur-md p-6">
                <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                  <Grid3X3 className="w-5 h-5 text-purple-400" /> Sector Pattern Heatmap
                </h3>
                <p className="text-xs text-slate-400 mb-6">
                  Derived from real stock universe and detected patterns. Tile size = stock count. Color = pattern density.
                </p>
                {sectorPatternData.length === 0 ? (
                  <div className="text-center text-slate-500 py-12">
                    <Activity className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p>No sector data yet. Stocks loading...</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                    {sectorPatternData.map((sector) => {
                      const intensity = sector.size > 0 ? sector.patterns / sector.size : 0;
                      return (
                        <div
                          key={sector.name}
                          className="rounded-lg border border-slate-700/50 p-4 flex flex-col justify-between transition-all hover:scale-[1.03] cursor-pointer"
                          style={{
                            background: `linear-gradient(135deg, ${sector.color}15, ${sector.color}05)`,
                            borderColor: `${sector.color}40`,
                            minHeight: `${Math.max(100, sector.size * 3.5)}px`,
                          }}
                        >
                          <div>
                            <div className="font-bold text-white text-sm mb-1">{sector.name}</div>
                            <div className="text-[10px] text-slate-400">{sector.size} stocks</div>
                          </div>
                          <div className="mt-3">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-400">Patterns</span>
                              <span className="font-bold text-white">{sector.patterns}</span>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                              <div
                                className="h-1.5 rounded-full"
                                style={{ width: `${intensity * 100}%`, backgroundColor: sector.color }}
                              />
                            </div>
                            <div className="flex justify-between text-[10px] mt-2">
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
              <div className="bg-slate-900/40 border border-slate-700/50 rounded-xl backdrop-blur-md p-6">
                <h3 className="text-lg font-bold text-white mb-4">Pattern Frequency Across Sectors</h3>
                <PatternFrequencyLC data={sectorPatternData} height={256} />
              </div>
            </div>
          )}

          {/* ═══ VIEW: PATTERN STATS ═══ */}
          {activeView === "STATS" && (
            <div className="space-y-6">
              {/* Top Stats Row */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-md text-center">
                  <div className="text-3xl font-black text-white">{patternStats.length}</div>
                  <div className="text-xs text-slate-400 mt-1">Active Pattern Types</div>
                </div>
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-md text-center">
                  <div className="text-3xl font-black text-green-400">
                    {patternStats.length > 0
                      ? Math.round(patternStats.reduce((a, p) => a + (p.avgConfidence || 0), 0) / patternStats.length)
                      : 0}%
                  </div>
                  <div className="text-xs text-slate-400 mt-1">Avg Confidence (Detected)</div>
                </div>
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-md text-center">
                  <div className="text-3xl font-black text-blue-400">{patterns.length}</div>
                  <div className="text-xs text-slate-400 mt-1">Total Patterns (API)</div>
                </div>
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-md text-center">
                  <div className="text-3xl font-black text-purple-400">
                    {enrichedStocks.filter((s) => s.pattern).length}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">Stocks w/ Patterns</div>
                </div>
              </div>
              {/* Pattern Type Cards */}
              {patternStats.length === 0 ? (
                <div className="bg-slate-900/40 border border-slate-700/50 rounded-xl p-12 text-center">
                  <Activity className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                  <p className="text-slate-500">No patterns detected yet. Agents scan continuously.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {patternStats.map((pt) => (
                    <div
                      key={pt.key || pt.name}
                      className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 backdrop-blur-sm hover:border-slate-600/50 transition-all"
                    >
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex items-center gap-3">
                          <span className="text-3xl">{pt.icon}</span>
                          <div>
                            <h4 className="font-bold text-white">{pt.name}</h4>
                            <span className={`text-[10px] font-bold tracking-widest ${
                              pt.direction === "bullish" ? "text-green-400"
                                : pt.direction === "bearish" ? "text-red-400"
                                : "text-blue-400"
                            }`}>
                              {pt.direction?.toUpperCase()}
                            </span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-black text-white">{pt.count}</div>
                          <div className="text-[10px] text-slate-500">Matches</div>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3 mb-4">
                        <div className="bg-slate-900/50 rounded-lg p-2.5 text-center">
                          <div className={`text-lg font-bold ${pt.avgConfidence >= 70 ? "text-green-400" : "text-slate-200"}`}>
                            {pt.avgConfidence}%
                          </div>
                          <div className="text-[10px] text-slate-500">Avg Confidence</div>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-2.5 text-center">
                          <div className="text-lg font-bold text-blue-400">{pt.count}</div>
                          <div className="text-[10px] text-slate-500">Detections</div>
                        </div>
                      </div>
                      <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden">
                        <div
                          className="h-2 rounded-full transition-all"
                          style={{
                            width: `${pt.avgConfidence}%`,
                            background: pt.avgConfidence >= 70
                              ? "linear-gradient(90deg, #22c55e, #4ade80)"
                              : "linear-gradient(90deg, #6366f1, #818cf8)",
                          }}
                        />
                      </div>
                      {pt.stocks && (
                        <div className="mt-3 flex flex-wrap gap-1">
                          {pt.stocks.slice(0, 6).map((sym) => (
                            <span
                              key={sym}
                              className="text-[10px] bg-slate-900/50 border border-slate-700/50 rounded px-1.5 py-0.5 text-slate-400"
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
      </div>
    </div>
  );
}
