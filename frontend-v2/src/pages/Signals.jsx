// SIGNALS PAGE - Embodier.ai Glass House Intelligence System
// GET /api/v1/signals - live signals (backend returns as_of + signals[] with symbol, prob_up, action)
import { useState, useMemo } from "react";
import {
  Zap,
  Clock,
  Target,
  Brain,
  Search,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  ArrowUpRight,
  Sparkles,
} from "lucide-react";
import Card from "../components/ui/Card";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";

/** Normalize backend signal { symbol, date, prob_up, action } to UI shape */
function normalizeSignals(backend) {
  if (!backend?.signals?.length) return [];
  return backend.signals.map((s, i) => ({
    id: i + 1,
    ticker: s.symbol || s.ticker || "—",
    type: "ML Signal",
    direction: s.action === "BUY" ? "long" : "short",
    score: Math.round((s.prob_up ?? 0.5) * 100),
    mlConfidence: Math.round((s.prob_up ?? 0.5) * 100),
    price: 0,
    target: 0,
    stop: 0,
    timeframe: "1D",
    time: "—",
    source: "ML Engine",
  }));
}

function ScoreRing({ score, size = 56, showGlow = false }) {
  const r = (size - 6) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const isHigh = score >= 75;
  const isMid = score >= 55 && score < 75;
  const stroke =
    isHigh ? "#22c55e" : isMid ? "#eab308" : "#ef4444";
  return (
    <div className="relative inline-flex items-center justify-center">
      {showGlow && isHigh && (
        <div
          className="absolute inset-0 rounded-full opacity-40 blur-md"
          style={{ background: "radial-gradient(circle, #22c55e40 0%, transparent 70%)" }}
        />
      )}
      <svg width={size} height={size} className="-rotate-90 shrink-0">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="rgba(30,41,59,0.6)"
          strokeWidth={4}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth={4}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white"
        style={{ fontSize: size * 0.28 }}
      >
        {score}
      </span>
    </div>
  );
}

function ScoreBar({ score }) {
  const width = Math.min(100, Math.max(0, score));
  const bg =
    score >= 75
      ? "from-emerald-500 to-green-400"
      : score >= 55
        ? "from-amber-500 to-yellow-400"
        : "from-red-500 to-rose-400";
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary/30">
      <div
        className={`h-full rounded-full bg-gradient-to-r ${bg} transition-all duration-500`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

export default function Signals() {
  const [filter, setFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("score");
  const { data, loading, error, refetch } = useApi("signals", {
    pollIntervalMs: 30000,
  });
  const signals = useMemo(() => normalizeSignals(data), [data]);
  const filtered = useMemo(
    () =>
      signals
        .filter((s) => filter === "all" || s.direction === filter)
        .filter(
          (s) =>
            !searchQuery ||
            s.ticker.toLowerCase().includes(searchQuery.toLowerCase())
        )
        .sort((a, b) => (sortBy === "score" ? b.score - a.score : 0)),
    [signals, filter, searchQuery, sortBy]
  );

  const stats = useMemo(() => {
    const long = signals.filter((s) => s.direction === "long").length;
    const short = signals.filter((s) => s.direction === "short").length;
    const avg =
      signals.length > 0
        ? Math.round(
            signals.reduce((a, s) => a + s.score, 0) / signals.length
          )
        : 0;
    return {
      total: signals.length,
      avg,
      long,
      short,
    };
  }, [signals]);

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Zap}
        title="Signal Intelligence"
        description={
          error
            ? "Failed to load signals"
            : `${filtered.length} active signal${filtered.length !== 1 ? "s" : ""}`
        }
      >
        <div className="flex items-center gap-3">
          {error && (
            <span className="text-xs font-medium text-danger">Failed to load</span>
          )}
          <button
            onClick={refetch}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg border border-secondary/40 bg-secondary/10 px-3 py-2 text-xs font-medium text-secondary transition-colors hover:bg-secondary/20 hover:text-white disabled:opacity-50"
            title="Refresh signals"
          >
            <RefreshCw
              className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
          <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2">
            <div
              className={`h-2 w-2 rounded-full ${loading ? "bg-amber-400 animate-pulse" : "bg-emerald-400 animate-pulse"}`}
            />
            <span className="text-xs font-medium text-success">
              {loading ? "Updating…" : "Live"}
            </span>
          </div>
        </div>
      </PageHeader>

      {/* Stats strip */}
      {!loading && signals.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl border border-secondary/40 bg-gradient-to-br from-secondary/10 to-transparent p-4">
            <div className="flex items-center gap-2 text-secondary">
              <Sparkles className="h-4 w-4" />
              <span className="text-xs font-medium uppercase tracking-wider">
                Total
              </span>
            </div>
            <div className="mt-1 text-2xl font-bold text-white">
              {stats.total}
            </div>
          </div>
          <div className="rounded-xl border border-secondary/40 bg-gradient-to-br from-secondary/10 to-transparent p-4">
            <div className="flex items-center gap-2 text-secondary">
              <Target className="h-4 w-4" />
              <span className="text-xs font-medium uppercase tracking-wider">
                Avg Score
              </span>
            </div>
            <div className="mt-1 text-2xl font-bold text-white">
              {stats.avg}
              <span className="ml-0.5 text-sm font-normal text-secondary">/100</span>
            </div>
          </div>
          <div className="rounded-xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-transparent p-4">
            <div className="flex items-center gap-2 text-emerald-400/80">
              <TrendingUp className="h-4 w-4" />
              <span className="text-xs font-medium uppercase tracking-wider">
                Long
              </span>
            </div>
            <div className="mt-1 text-2xl font-bold text-emerald-400">
              {stats.long}
            </div>
          </div>
          <div className="rounded-xl border border-rose-500/30 bg-gradient-to-br from-rose-500/10 to-transparent p-4">
            <div className="flex items-center gap-2 text-rose-400/80">
              <TrendingDown className="h-4 w-4" />
              <span className="text-xs font-medium uppercase tracking-wider">
                Short
              </span>
            </div>
            <div className="mt-1 text-2xl font-bold text-rose-400">
              {stats.short}
            </div>
          </div>
        </div>
      )}

      {/* Filters & search */}
      {!loading && signals.length > 0 && (
        <Card noPadding className="p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="relative min-w-[200px] max-w-xs flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-secondary pointer-events-none" />
              <input
                type="text"
                placeholder="Search ticker..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-secondary/50 bg-secondary/10 py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-secondary focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
            </div>
            <div className="flex gap-1 rounded-lg bg-secondary/20 p-1">
              {[
                { value: "all", label: "All" },
                { value: "long", label: "Long" },
                { value: "short", label: "Short" },
              ].map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => setFilter(value)}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    filter === value
                      ? "bg-primary text-white shadow-sm"
                      : "text-secondary hover:text-white"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <Select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              options={[
                { value: "score", label: "Highest score first" },
                { value: "time", label: "Most recent" },
              ]}
              className="min-w-[11rem]"
            />
          </div>
        </Card>
      )}

      {/* Loading skeletons */}
      {loading && signals.length === 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="overflow-hidden p-0">
              <div className="flex items-center gap-5 p-5">
                <div className="h-14 w-14 shrink-0 animate-pulse rounded-full bg-secondary/30" />
                <div className="min-w-0 flex-1 space-y-3">
                  <div className="h-5 w-24 animate-pulse rounded bg-secondary/30" />
                  <div className="h-3 w-3/4 animate-pulse rounded bg-secondary/20" />
                  <div className="h-2 w-full animate-pulse rounded bg-secondary/20" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Error state */}
      {!loading && error && signals.length === 0 && (
        <Card className="flex flex-col items-center justify-center py-12 text-center">
          <div className="mb-4 rounded-full bg-danger/20 p-4">
            <Zap className="h-10 w-10 text-danger" />
          </div>
          <p className="mb-1 text-white font-medium">Could not load signals</p>
          <p className="mb-4 text-sm text-secondary">
            Check that the backend is running and GET /api/v1/signals is available.
          </p>
          <Button variant="outline" size="sm" onClick={refetch}>
            Retry
          </Button>
        </Card>
      )}

      {/* Empty state */}
      {!loading && !error && filtered.length === 0 && (
        <Card className="flex flex-col items-center justify-center py-12 text-center">
          <div className="mb-4 rounded-full bg-secondary/20 p-4">
            <Sparkles className="h-10 w-10 text-secondary" />
          </div>
          <p className="mb-1 text-white font-medium">No signals match</p>
          <p className="text-sm text-secondary">
            {signals.length === 0
              ? "Signals will appear here once the ML pipeline runs."
              : "Try a different filter or search."}
          </p>
        </Card>
      )}

      {/* Signal cards */}
      {!loading && filtered.length > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {filtered.map((signal) => {
            const isHigh = signal.score >= 75;
            const isLong = signal.direction === "long";
            const borderAccent = isHigh
              ? "border-l-emerald-500/60"
              : signal.score >= 55
                ? "border-l-amber-500/60"
                : "border-l-rose-500/60";
            return (
              <Card
                key={signal.id}
                noPadding
                className={`overflow-hidden border-l-4 transition-all duration-200 hover:border-secondary hover:bg-secondary/5 ${borderAccent}`}
              >
                <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
                  <div className="flex items-center gap-4 sm:gap-5">
                    <ScoreRing
                      score={signal.score}
                      size={56}
                      showGlow={isHigh}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xl font-bold tracking-tight text-white">
                          {signal.ticker}
                        </span>
                        <Badge
                          variant={isLong ? "success" : "danger"}
                          size="sm"
                        >
                          {isLong ? "LONG" : "SHORT"}
                        </Badge>
                        <span className="text-xs text-secondary">
                          {signal.timeframe}
                        </span>
                      </div>
                      <p className="mt-0.5 text-sm text-secondary">
                        {signal.type} · {signal.source}
                      </p>
                      <div className="mt-2 flex items-center gap-3 text-xs text-secondary">
                        <span className="flex items-center gap-1">
                          <Brain className="h-3.5 w-3.5 text-primary" />
                          ML {signal.mlConfidence}%
                        </span>
                        {signal.time !== "—" && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3.5 w-3.5" />
                            {signal.time}
                          </span>
                        )}
                      </div>
                      <div className="mt-2 w-full max-w-[140px]">
                        <ScoreBar score={signal.score} />
                      </div>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2 sm:ml-auto">
                    <Button
                      variant="primary"
                      size="sm"
                      className="group gap-1.5"
                    >
                      Trade
                      <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
