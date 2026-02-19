// PATTERNS PAGE - Embodier.ai Glass House Intelligence System
// GET /api/v1/patterns - pattern recognition grid with confidence meters
import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Eye, Brain, Clock } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";

function usePatterns() {
  const { data, loading, error, refetch } = useApi("patterns", {
    pollIntervalMs: 30000,
  });
  const patterns = Array.isArray(data?.patterns) ? data.patterns : [];
  return { patterns, loading, error, refetch };
}

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
  const navigate = useNavigate();
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const { patterns, loading, error, refetch } = usePatterns();

  const filtered = useMemo(
    () =>
      patterns
        .filter((p) => filter === "all" || p.direction === filter)
        .filter(
          (p) =>
            !search ||
            (p.ticker || "").toLowerCase().includes(search.toLowerCase()) ||
            (p.pattern || "").toLowerCase().includes(search.toLowerCase()),
        ),
    [patterns, filter, search],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Search}
        title="Screener & Patterns"
        description={
          error
            ? "Failed to load patterns"
            : `${filtered.length} patterns detected by AI`
        }
      >
        {error && (
          <button
            onClick={() => refetch()}
            className="text-xs text-amber-400 hover:text-amber-300"
          >
            Retry
          </button>
        )}
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <span className="text-sm text-purple-400">
            {loading ? "Loading…" : "AI Scanning Active"}
          </span>
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

      {loading && filtered.length === 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="bg-slate-800/30 border border-white/10 rounded-2xl p-5 animate-pulse"
            >
              <div className="h-5 bg-slate-600/30 rounded w-1/3 mb-3" />
              <div className="h-4 bg-slate-600/20 rounded w-2/3 mb-4" />
              <div className="h-2 bg-slate-600/20 rounded w-full" />
            </div>
          ))}
        </div>
      )}
      {!loading && error && filtered.length === 0 && (
        <div className="p-8 text-center rounded-2xl bg-slate-800/30 border border-white/10">
          <p className="text-amber-400 mb-2">Could not load patterns.</p>
          <button
            onClick={() => refetch()}
            className="text-sm text-blue-400 hover:underline"
          >
            Retry
          </button>
        </div>
      )}
      {!loading && !error && filtered.length === 0 && (
        <div className="p-8 text-center rounded-2xl bg-slate-800/30 border border-white/10 text-gray-500">
          No patterns detected yet.
        </div>
      )}
      {/* Pattern cards grid */}
      {!loading && filtered.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((p) => (
            <div
              key={p.id}
              className="bg-slate-800/30 border border-white/10 rounded-2xl p-5 hover:border-white/20 transition-all"
            >
              {/* Header row */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg font-bold text-white">
                    {p.ticker}
                  </span>
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
                <button
                  onClick={() =>
                    navigate("/trades", {
                      state: {
                        symbol: p.ticker,
                        side: p.direction === "bullish" ? "Buy" : "Sell",
                        fromSignal: true,
                      },
                    })
                  }
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-medium text-white transition-colors"
                >
                  Trade
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
