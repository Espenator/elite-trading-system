// SIGNALS PAGE - Embodier.ai Glass House Intelligence System
// GET /api/v1/signals - live signals (backend returns as_of + signals[] with symbol, prob_up, action)
import { useState, useMemo } from "react";
import { Zap, Clock, Target, Brain, Search } from "lucide-react";
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

function ScoreRing({ score, size = 48 }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = score >= 80 ? "#22c55e" : score >= 60 ? "#eab308" : "#ef4444";
  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="rgba(30,41,59,0.8)"
        strokeWidth={3}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={3}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-700"
      />
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="central"
        className="rotate-90 origin-center"
        fill="white"
        fontSize="13"
        fontWeight="bold"
      >
        {score}
      </text>
    </svg>
  );
}

export default function Signals() {
  const [filter, setFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("score");
  const { data, loading, error, refetch } = useApi("signals", { pollIntervalMs: 30000 });
  const signals = useMemo(() => normalizeSignals(data), [data]);
  const filtered = signals.filter(
    (s) => filter === "all" || s.direction === filter,
  )
    .filter(
      (s) =>
        !searchQuery ||
        s.ticker.toLowerCase().includes(searchQuery.toLowerCase()),
    )
    .sort((a, b) => (sortBy === "score" ? b.score - a.score : 0));

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Zap}
        title="Signal Intelligence"
        description={error ? "Failed to load signals" : `${filtered.length} active signals detected`}
      >
        {error && (
          <span className="text-xs text-danger font-medium">Failed to load</span>
        )}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${loading ? "bg-secondary animate-pulse" : "bg-success animate-pulse"}`} />
          <span className="text-sm text-success">{loading ? "Loading…" : "Live"}</span>
        </div>
      </PageHeader>

      {loading && signals.length === 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-5 animate-pulse">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-secondary/20" />
                <div className="flex-1 space-y-2">
                  <div className="h-5 bg-secondary/20 rounded w-1/3" />
                  <div className="h-3 bg-secondary/20 rounded w-2/3" />
                  <div className="h-3 bg-secondary/20 rounded w-1/2" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
      {!loading && error && signals.length === 0 && (
        <Card className="p-8 text-center">
          <p className="text-secondary mb-2">Could not load signals. Check backend GET /api/v1/signals.</p>
          <Button variant="outline" size="sm" onClick={refetch}>Retry</Button>
        </Card>
      )}
      {!loading && !error && filtered.length === 0 && (
        <Card className="p-8 text-center">
          <p className="text-secondary">No signals yet. Backend may return an empty list until ML model runs.</p>
        </Card>
      )}
      {!loading && filtered.length > 0 && (
      <>
      <Card noPadding className="p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary pointer-events-none z-10" />
            <TextField
              placeholder="Search ticker..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="[&_input]:pl-10"
            />
          </div>
          <div className="flex gap-2">
            {["all", "long", "short"].map((f) => (
              <Button
                key={f}
                variant={filter === f ? "primary" : "secondary"}
                size="sm"
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "All" : f === "long" ? "Long" : "Short"}
              </Button>
            ))}
          </div>
          <Select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            options={[
              { value: "score", label: "Sort by Score" },
              { value: "time", label: "Sort by Time" },
            ]}
            className="min-w-[10rem]"
          />
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filtered.map((signal) => (
          <Card
            key={signal.id}
            className="p-5 hover:border-primary/30 transition-all"
          >
            <div className="flex items-start gap-4">
              <ScoreRing score={signal.score} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg font-bold text-white">
                    {signal.ticker}
                  </span>
                  <Badge
                    variant={signal.direction === "long" ? "success" : "danger"}
                  >
                    {signal.direction === "long" ? "LONG" : "SHORT"}
                  </Badge>
                  <span className="text-xs text-secondary">
                    {signal.timeframe}
                  </span>
                </div>
                <div className="text-sm text-secondary mb-2">{signal.type}</div>
                <div className="flex items-center gap-4 text-xs text-secondary">
                  <span className="flex items-center gap-1">
                    <Target className="w-3 h-3" /> T: ${signal.target}
                  </span>
                  <span className="flex items-center gap-1 text-danger">
                    S: ${signal.stop}
                  </span>
                  <span className="flex items-center gap-1">
                    <Brain className="w-3 h-3" /> ML: {signal.mlConfidence}%
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {signal.time}
                  </span>
                </div>
              </div>
              <Button variant="primary" size="sm">
                Trade
              </Button>
            </div>
          </Card>
        ))}
      </div>
      </>
      )}
    </div>
  );
}
