// Screener & Patterns — Embodier.ai Glass House Intelligence System
// Layout and behavior copied from frontend/src/pages/ScreenerResults.tsx; data from GET /api/v1/stocks/list (Finviz).
import { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Download,
  Save,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import Button from "../components/ui/Button";
import Slider from "../components/ui/Slider";
import Checkbox from "../components/ui/Checkbox";
import TextField from "../components/ui/TextField";
import DataTable from "../components/ui/DataTable";
import MiniChart from "../components/charts/MiniChart";
import { toast } from "react-toastify";
import { getApiUrl } from "../config/api";

const ITEMS_PER_PAGE = 10;
const SAVED_FILTER_KEY = "patterns-screener-filter";

/** Parse market cap string (e.g. "35.73B", "1.2M", "—") to numeric (dollars). */
function parseMarketCapNum(str) {
  if (!str || str === "-" || str === "—") return null;
  const s = String(str).trim().toUpperCase();
  const num = parseFloat(s.replace(/[^0-9.-]/g, ""));
  if (!Number.isFinite(num)) return null;
  if (s.endsWith("B")) return num * 1e9;
  if (s.endsWith("M")) return num * 1e6;
  if (s.endsWith("K")) return num * 1e3;
  return num * 1e6; // assume millions if plain number
}

/** small < 2B, mid 2B–10B, large > 10B */
function marketCapCategory(marketCapNum) {
  if (marketCapNum == null || marketCapNum <= 0) return null;
  if (marketCapNum < 2e9) return "small";
  if (marketCapNum <= 10e9) return "mid";
  return "large";
}

/** Normalize exchange string to our filter key (nasdaq, nyse, amex). */
function normalizeExchange(ex) {
  if (!ex) return null;
  const s = String(ex).trim().toLowerCase();
  if (s.includes("nasdaq")) return "nasdaq";
  if (s.includes("nyse")) return "nyse";
  if (s.includes("amex") || s.includes("american")) return "amex";
  return null;
}

/** Map Finviz API row to stock data. Prefers backend-enriched market_cap_category, market_cap_display, exchange when present. */
function mapRowToStockData(row) {
  const priceStr = String(row.Price ?? row.price ?? "0").replace(
    /[^0-9.-]/g,
    "",
  );
  const changeStr = String(row.Change ?? row.change ?? "0").replace(
    /[^0-9.-]/g,
    "",
  );
  const peStr = String(row["P/E"] ?? row.PE ?? row.pe ?? "0").replace(
    /[^0-9.-]/g,
    "",
  );
  const marketCapRaw = String(
    row["Market Cap"] ?? row.MarketCap ?? row.market_cap ?? "-",
  ).trim();
  const marketCapNum = parseMarketCapNum(marketCapRaw);
  const exchangeRaw = row.Exchange ?? row.exchange ?? "";
  const backendCategory =
    row.market_cap_category ?? marketCapCategory(marketCapNum);
  const backendExchange = row.exchange ?? normalizeExchange(exchangeRaw);
  const displayCap = row.market_cap_display ?? marketCapRaw;
  return {
    symbol: String(row.Ticker ?? row.ticker ?? "").trim(),
    company: String(row.Company ?? row.company ?? "").trim(),
    price: parseFloat(priceStr) || 0,
    change: parseFloat(changeStr) || 0,
    marketCap: displayCap,
    marketCapCategory: backendCategory,
    exchange: backendExchange,
    peRatio: parseFloat(peStr) || 0,
  };
}

export default function Patterns() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [priceRangeMax, setPriceRangeMax] = useState(2000);
  const [screenerResults, setScreenerResults] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [assetTypes, setAssetTypes] = useState({
    stocks: true,
    options: false,
    futures: false,
    crypto: false,
  });
  const [marketCaps, setMarketCaps] = useState({
    small: false,
    mid: false,
    large: true,
  });
  const [exchanges, setExchanges] = useState({
    nasdaq: true,
    nyse: true,
    amex: true,
  });
  const [expandedFilters, setExpandedFilters] = useState({
    assetType: true,
    priceRange: true,
    marketCap: true,
    exchange: true,
  });

  // Load saved filter from localStorage on page access
  useEffect(() => {
    try {
      const raw = localStorage.getItem(SAVED_FILTER_KEY);
      if (!raw) return;
      const payload = JSON.parse(raw);
      setSearchQuery(payload.searchQuery ?? "");
      setPriceRangeMax(Number(payload.priceRangeMax) ?? 2000);
      if (payload.assetTypes) setAssetTypes(payload.assetTypes);
      if (payload.marketCaps) setMarketCaps(payload.marketCaps);
      if (payload.exchanges) setExchanges(payload.exchanges);
      setCurrentPage(1);
    } catch (_) {
      // ignore invalid or missing saved filter
    }
  }, []);

  // Fetch stock list from Finviz API (stocks/list)
  useEffect(() => {
    let cancelled = false;
    setError(null);
    setIsLoading(true);
    fetch(getApiUrl("stocks") + "/list", { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error(res.statusText || "Failed to load");
        return res.json();
      })
      .then((rows) => {
        if (cancelled) return;
        const mapped = (Array.isArray(rows) ? rows : [])
          .map(mapRowToStockData)
          .filter((s) => s.symbol);
        setScreenerResults(mapped);
        if (mapped.length > 0 && !selectedSymbol)
          setSelectedSymbol(mapped[0].symbol);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Failed to load screener results");
          setScreenerResults([]);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredResults = useMemo(() => {
    let list = screenerResults;

    // Asset type: screener data is stocks only; when "stocks" unchecked, show none
    if (!assetTypes.stocks) return [];

    // Exchange: when at least one selected, keep rows that match or have unknown exchange
    const exchangeKeys = ["nasdaq", "nyse", "amex"];
    const anyExchangeSelected = exchangeKeys.some((k) => exchanges[k]);
    if (anyExchangeSelected) {
      list = list.filter((s) => {
        const ex = s.exchange;
        if (!ex) return true; // unknown exchange: include
        return exchanges[ex];
      });
    } else {
      list = []; // none selected => show none
    }

    // Market cap: when at least one selected, keep rows that match or have unknown cap
    const capKeys = ["small", "mid", "large"];
    const anyCapSelected = capKeys.some((k) => marketCaps[k]);
    if (anyCapSelected) {
      list = list.filter((s) => {
        const cap = s.marketCapCategory;
        if (!cap) return true; // unknown: include
        return marketCaps[cap];
      });
    } else {
      list = [];
    }

    // Search
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter(
        (s) =>
          s.symbol.toLowerCase().includes(q) ||
          s.company.toLowerCase().includes(q),
      );
    }

    // Price range
    return list.filter((s) => s.price <= priceRangeMax);
  }, [
    screenerResults,
    searchQuery,
    priceRangeMax,
    assetTypes.stocks,
    marketCaps.small,
    marketCaps.mid,
    marketCaps.large,
    exchanges.nasdaq,
    exchanges.nyse,
    exchanges.amex,
  ]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredResults.length / ITEMS_PER_PAGE),
  );
  const paginatedResults = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredResults.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredResults, currentPage]);

  const selectedStock = useMemo(
    () =>
      screenerResults.find((s) => s.symbol === selectedSymbol) ??
      paginatedResults[0] ??
      null,
    [screenerResults, selectedSymbol, paginatedResults],
  );

  useEffect(() => {
    setCurrentPage(1);
  }, [
    searchQuery,
    assetTypes.stocks,
    marketCaps.small,
    marketCaps.mid,
    marketCaps.large,
    exchanges.nasdaq,
    exchanges.nyse,
    exchanges.amex,
  ]);

  const toggleFilter = (category, key) => {
    if (category === "assetType")
      setAssetTypes((prev) => ({ ...prev, [key]: !prev[key] }));
    else if (category === "marketCap")
      setMarketCaps((prev) => ({ ...prev, [key]: !prev[key] }));
    else if (category === "exchange")
      setExchanges((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleFilterSection = (section) => {
    setExpandedFilters((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  /** Export current filtered results to CSV and trigger download */
  const handleExportData = () => {
    if (filteredResults.length === 0) return;
    const headers = [
      "Symbol",
      "Company",
      "Price",
      "Change (%)",
      "Market Cap",
      "P/E Ratio",
      "Exchange",
    ];
    const escapeCsv = (v) => {
      const s = String(v ?? "");
      if (s.includes(",") || s.includes('"') || s.includes("\n"))
        return `"${s.replace(/"/g, '""')}"`;
      return s;
    };
    const rows = filteredResults.map((s) =>
      [
        s.symbol,
        s.company,
        s.price != null ? s.price.toFixed(2) : "",
        s.change != null ? s.change.toFixed(2) : "",
        s.marketCap ?? "",
        s.peRatio != null ? s.peRatio.toFixed(2) : "",
        s.exchange ?? "",
      ]
        .map(escapeCsv)
        .join(","),
    );
    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `screener-export-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  /** Save current filter state to localStorage */
  const handleSaveFilter = () => {
    const payload = {
      searchQuery,
      priceRangeMax,
      assetTypes: { ...assetTypes },
      marketCaps: { ...marketCaps },
      exchanges: { ...exchanges },
    };
    try {
      localStorage.setItem(SAVED_FILTER_KEY, JSON.stringify(payload));
      toast.success("Filter saved");
    } catch (e) {
      toast.error("Save failed");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Search}
        title="Screener & Patterns"
        description={
          error
            ? "Failed to load screener"
            : `${filteredResults.length} symbols from Finviz screener`
        }
      >
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="secondary"
            leftIcon={Download}
            onClick={handleExportData}
            disabled={filteredResults.length === 0}
          >
            Export Data
          </Button>
          <Button variant="success" leftIcon={Save} onClick={handleSaveFilter}>
            Save Filter
          </Button>
        </div>
      </PageHeader>

      {error && (
        <div className="rounded-xl bg-red-500/10 border border-red-500/30 px-4 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* 3-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left — Filters */}
        <div className="lg:col-span-3">
          <div className="rounded-2xl border border-cyan-500/20 bg-secondary/10 backdrop-blur-sm p-5">
            <h2 className="text-base font-semibold text-white mb-4">Filters</h2>

            {/* Asset Type */}
            <div className="mb-4">
              <button
                type="button"
                onClick={() => toggleFilterSection("assetType")}
                className="w-full flex items-center justify-between text-sm font-medium text-cyan-400"
              >
                <span>Asset Type</span>
                {expandedFilters.assetType ? (
                  <ChevronDown className="w-4 h-4 text-secondary" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-secondary" />
                )}
              </button>
              {expandedFilters.assetType && (
                <div className="grid space-y-2 mt-2">
                  {Object.entries(assetTypes).map(([key, value]) => (
                    <Checkbox
                      key={key}
                      checked={value}
                      onChange={() => toggleFilter("assetType", key)}
                      label={key.charAt(0).toUpperCase() + key.slice(1)}
                      className="text-sm text-secondary"
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Price Range */}
            <div className="mb-4">
              <button
                type="button"
                onClick={() => toggleFilterSection("priceRange")}
                className="w-full flex items-center justify-between text-sm font-medium text-cyan-400"
              >
                <span>Price Range</span>
                {expandedFilters.priceRange ? (
                  <ChevronDown className="w-4 h-4 text-secondary" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-secondary" />
                )}
              </button>
              {expandedFilters.priceRange && (
                <div className="mt-2">
                  <Slider
                    min={0}
                    max={2000}
                    value={priceRangeMax}
                    onChange={(e) => setPriceRangeMax(Number(e.target.value))}
                    formatValue={(v) => `$${v}`}
                  />
                </div>
              )}
            </div>

            {/* Market Cap */}
            <div className="mb-4">
              <button
                type="button"
                onClick={() => toggleFilterSection("marketCap")}
                className="w-full flex items-center justify-between text-sm font-medium text-cyan-400"
              >
                <span>Market Cap</span>
                {expandedFilters.marketCap ? (
                  <ChevronDown className="w-4 h-4 text-secondary" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-secondary" />
                )}
              </button>
              {expandedFilters.marketCap && (
                <div className="grid space-y-2 mt-2">
                  {Object.entries(marketCaps).map(([key, value]) => (
                    <Checkbox
                      key={key}
                      checked={value}
                      onChange={() => toggleFilter("marketCap", key)}
                      label={`${key.charAt(0).toUpperCase() + key.slice(1)} Cap`}
                      className="text-sm text-secondary"
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Exchange */}
            <div className="mb-4">
              <button
                type="button"
                onClick={() => toggleFilterSection("exchange")}
                className="w-full flex items-center justify-between text-sm font-medium text-cyan-400"
              >
                <span>Exchange</span>
                {expandedFilters.exchange ? (
                  <ChevronDown className="w-4 h-4 text-secondary" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-secondary" />
                )}
              </button>
              {expandedFilters.exchange && (
                <div className="grid space-y-2 mt-2">
                  {Object.entries(exchanges).map(([key, value]) => (
                    <Checkbox
                      key={key}
                      checked={value}
                      onChange={() => toggleFilter("exchange", key)}
                      label={key.toUpperCase()}
                      className="text-sm text-secondary"
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Middle — Results table */}
        <div className="lg:col-span-5">
          <div className="rounded-2xl border border-cyan-500/20 bg-secondary/10 backdrop-blur-sm overflow-hidden">
            <div className="p-4 border-b border-cyan-500/10 flex items-center justify-between gap-4">
              <h2 className="text-base font-semibold text-white">
                Screener Results
              </h2>
              <TextField
                placeholder="Search symbols or companies"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                prefix={<Search className="w-4 h-4 text-cyan-400/70" />}
                className="flex-1 min-w-0 max-w-xs"
                inputClassName="bg-dark border-cyan-500/30 focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50"
              />
            </div>
            <div className="overflow-x-auto">
              {isLoading ? (
                <div className="flex items-center justify-center py-16 text-secondary">
                  <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mr-2" />
                  Loading screener results...
                </div>
              ) : (
                <DataTable
                  columns={[
                    {
                      key: "symbol",
                      label: "Symbol",
                      cellClassName: "font-medium text-white",
                    },
                    { key: "company", label: "Company" },
                    {
                      key: "price",
                      label: "Price",
                      render: (val) =>
                        val != null ? `$${Number(val).toFixed(2)}` : "—",
                    },
                    {
                      key: "change",
                      label: "Change (%)",
                      render: (val) =>
                        val != null ? (
                          <span
                            className={
                              val >= 0 ? "text-emerald-400" : "text-red-400"
                            }
                          >
                            {val >= 0 ? "+" : ""}
                            {Number(val).toFixed(2)}%
                          </span>
                        ) : (
                          "—"
                        ),
                      cellClassName: "font-medium",
                    },
                    { key: "marketCap", label: "Market Cap" },
                    {
                      key: "peRatio",
                      label: "P/E",
                      render: (val) =>
                        val != null && Number(val) > 0
                          ? Number(val).toFixed(2)
                          : "—",
                    },
                  ]}
                  data={paginatedResults}
                  onRowClick={(row) => setSelectedSymbol(row.symbol)}
                  rowKey={(row) => row.symbol}
                  rowClassName={(row) =>
                    selectedSymbol === row.symbol ? "bg-cyan-500/20" : ""
                  }
                  emptyMessage="No results. Try adjusting your search or filters."
                  className="border-0 !rounded-none bg-transparent"
                />
              )}
            </div>
            {!isLoading && filteredResults.length > 0 && (
              <div className="p-4 border-t border-cyan-500/10 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1.5 text-sm text-cyan-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </button>
                <span className="text-sm text-secondary">
                  Page {currentPage} of {totalPages} ({filteredResults.length}{" "}
                  results)
                </span>
                <button
                  type="button"
                  onClick={() =>
                    setCurrentPage(Math.min(totalPages, currentPage + 1))
                  }
                  disabled={currentPage >= totalPages}
                  className="px-3 py-1.5 text-sm text-cyan-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right — Detail panel */}
        <div className="lg:col-span-4">
          <div className="rounded-2xl border border-cyan-500/20 bg-secondary/10 backdrop-blur-sm p-5">
            {selectedStock ? (
              <>
                <div className="mb-4">
                  <h2 className="text-xl font-bold text-white">
                    {selectedStock.symbol}
                  </h2>
                  <p className="text-sm text-secondary">
                    {selectedStock.company}
                  </p>
                </div>

                <div className="mb-6 rounded-xl bg-dark border border-cyan-500/20 p-3">
                  <MiniChart
                    symbol={selectedSymbol}
                    height={160}
                    className="w-full"
                  />
                </div>

                <div className="mb-6 space-y-3">
                  <h3 className="text-sm font-semibold text-cyan-400">
                    Key Metrics
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-xs text-secondary mb-1">Price</div>
                      <div className="text-sm font-medium text-white">
                        ${selectedStock.price.toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-secondary mb-1">
                        Change (%)
                      </div>
                      <div
                        className={`text-sm font-medium flex items-center gap-1 ${
                          selectedStock.change >= 0
                            ? "text-emerald-400"
                            : "text-red-400"
                        }`}
                      >
                        {selectedStock.change >= 0 ? (
                          <TrendingUp className="w-4 h-4" />
                        ) : (
                          <TrendingDown className="w-4 h-4" />
                        )}
                        {selectedStock.change >= 0 ? "+" : ""}
                        {selectedStock.change.toFixed(2)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-secondary mb-1">
                        Market Cap
                      </div>
                      <div className="text-sm font-medium text-white">
                        {selectedStock.marketCap}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-secondary mb-1">
                        P/E Ratio
                      </div>
                      <div className="text-sm font-medium text-white">
                        {selectedStock.peRatio > 0
                          ? selectedStock.peRatio.toFixed(2)
                          : "-"}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-cyan-400 mb-3">
                    ML Insights
                  </h3>
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className="px-3 py-1 bg-cyan-500/20 text-cyan-300 rounded-full text-xs font-medium">
                      Bullish Trend
                    </span>
                    <span className="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-xs font-medium">
                      Strong Buy Signal
                    </span>
                  </div>
                  <p className="text-xs text-secondary leading-relaxed">
                    AI detects increasing institutional interest and positive
                    news sentiment, driving short-term momentum.
                  </p>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-cyan-400 mb-3">
                    Recent News
                  </h3>
                  <ul className="space-y-2">
                    <li className="text-xs text-secondary flex items-start gap-2">
                      <span className="text-cyan-400/70 mt-1">•</span>
                      <span>
                        Tech giant announces new chip breakthrough, boosting
                        stock outlook.
                      </span>
                    </li>
                    <li className="text-xs text-secondary flex items-start gap-2">
                      <span className="text-cyan-400/70 mt-1">•</span>
                      <span>
                        Analysts upgrade rating for company on strong Q3
                        earnings.
                      </span>
                    </li>
                    <li className="text-xs text-secondary flex items-start gap-2">
                      <span className="text-cyan-400/70 mt-1">•</span>
                      <span>
                        Partnership with leading AI firm expands market reach.
                      </span>
                    </li>
                  </ul>
                </div>
              </>
            ) : (
              <div className="py-8 text-center text-sm text-secondary">
                Select a stock from the table or wait for data to load.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
