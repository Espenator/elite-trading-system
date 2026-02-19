// PATTERNS PAGE - Embodier.ai Glass House Intelligence System
// Pattern recognition grid with confidence meters and AI detection
import { useState } from "react";
import {
  Search,
  Filter,
  Eye,
  Brain,
  TrendingUp,
  TrendingDown,
  Clock,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";

const PATTERNS = [
  {
    id: 1,
    ticker: "AAPL",
    pattern: "Bull Flag",
    confidence: 92,
    direction: "bullish",
    timeframe: "1D",
    detected: "5m ago",
    priceTarget: 198.5,
    currentPrice: 192.3,
  },
  {
    id: 2,
    ticker: "MSFT",
    pattern: "Cup & Handle",
    confidence: 87,
    direction: "bullish",
    timeframe: "4H",
    detected: "12m ago",
    priceTarget: 430.0,
    currentPrice: 415.2,
  },
  {
    id: 3,
    ticker: "TSLA",
    pattern: "Double Bottom",
    confidence: 78,
    direction: "bullish",
    timeframe: "1D",
    detected: "25m ago",
    priceTarget: 265.0,
    currentPrice: 248.1,
  },
  {
    id: 4,
    ticker: "NVDA",
    pattern: "Head & Shoulders",
    confidence: 74,
    direction: "bearish",
    timeframe: "1D",
    detected: "35m ago",
    priceTarget: 840.0,
    currentPrice: 868.2,
  },
  {
    id: 5,
    ticker: "AMD",
    pattern: "Ascending Triangle",
    confidence: 85,
    direction: "bullish",
    timeframe: "1H",
    detected: "45m ago",
    priceTarget: 180.0,
    currentPrice: 168.5,
  },
  {
    id: 6,
    ticker: "META",
    pattern: "Breakout",
    confidence: 81,
    direction: "bullish",
    timeframe: "4H",
    detected: "1h ago",
    priceTarget: 610.0,
    currentPrice: 582.4,
  },
  {
    id: 7,
    ticker: "SPY",
    pattern: "Bearish Engulfing",
    confidence: 69,
    direction: "bearish",
    timeframe: "1D",
    detected: "1h ago",
    priceTarget: 492.0,
    currentPrice: 502.1,
  },
  {
    id: 8,
    ticker: "GOOGL",
    pattern: "Falling Wedge",
    confidence: 76,
    direction: "bullish",
    timeframe: "1D",
    detected: "2h ago",
    priceTarget: 190.0,
    currentPrice: 175.8,
  },
  {
    id: 9,
    ticker: "QQQ",
    pattern: "Rising Channel",
    confidence: 83,
    direction: "bullish",
    timeframe: "4H",
    detected: "2h ago",
    priceTarget: 445.0,
    currentPrice: 432.5,
  },
];

function ConfidenceBar({ value }) {
  const color =
    value >= 80
      ? "bg-emerald-500"
      : value >= 60
        ? "bg-amber-500"
        : "bg-red-500";
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-500">Confidence</span>
        <span
          className={`font-bold ${value >= 80 ? "text-emerald-400" : value >= 60 ? "text-amber-400" : "text-red-400"}`}
        >
          {value}%
        </span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-700`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

export default function Patterns() {
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  const filtered = PATTERNS.filter(
    (p) => filter === "all" || p.direction === filter,
  ).filter(
    (p) =>
      !search ||
      p.ticker.toLowerCase().includes(search.toLowerCase()) ||
      p.pattern.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Search}
        title="Screener & Patterns"
        description={`${filtered.length} patterns detected by AI`}
      >
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <span className="text-sm text-purple-400">AI Scanning Active</span>
        </div>
      </PageHeader>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 p-4 bg-slate-800/30 border border-white/10 rounded-2xl">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search patterns..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-800/60 border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 outline-none focus:border-blue-500/50"
          />
        </div>
        <div className="flex gap-2">
          {["all", "bullish", "bearish"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                filter === f
                  ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                  : "text-gray-400 hover:text-white bg-slate-800/40 border border-white/10"
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Pattern cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((p) => (
          <div
            key={p.id}
            className="bg-slate-800/30 border border-white/10 rounded-2xl p-5 hover:border-white/20 transition-all"
          >
            {/* Header row */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-white">{p.ticker}</span>
                <span
                  className={`px-2 py-0.5 rounded-lg text-xs font-medium ${
                    p.direction === "bullish"
                      ? "bg-emerald-500/20 text-emerald-400"
                      : "bg-red-500/20 text-red-400"
                  }`}
                >
                  {p.direction === "bullish" ? "Bullish" : "Bearish"}
                </span>
              </div>
              <span className="text-xs text-gray-500">{p.timeframe}</span>
            </div>

            {/* Pattern name */}
            <div className="flex items-center gap-2 mb-3">
              <Eye className="w-4 h-4 text-blue-400" />
              <span className="text-sm font-medium text-blue-400">
                {p.pattern}
              </span>
            </div>

            {/* Confidence meter */}
            <div className="mb-4">
              <ConfidenceBar value={p.confidence} />
            </div>

            {/* Price info */}
            <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
              <span>Current: ${p.currentPrice}</span>
              <span
                className={
                  p.direction === "bullish"
                    ? "text-emerald-400"
                    : "text-red-400"
                }
              >
                Target: ${p.priceTarget}
              </span>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between pt-3 border-t border-white/5">
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Clock className="w-3 h-3" /> {p.detected}
              </span>
              <button className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-medium text-white transition-colors">
                Trade
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
