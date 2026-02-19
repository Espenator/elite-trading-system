// SIGNALS PAGE - Embodier.ai Glass House Intelligence System
// Signal scanner with filters, composite scoring, and signal cards
import { useState } from "react";
import { Zap, Clock, Target, Brain, Search } from "lucide-react";
import Card from "../components/ui/Card";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";

const MOCK_SIGNALS = [
  {
    id: 1,
    ticker: "AAPL",
    type: "Bullish Breakout",
    direction: "long",
    score: 92,
    mlConfidence: 88,
    price: 192.3,
    target: 198.5,
    stop: 188.0,
    timeframe: "1D",
    time: "2m ago",
    source: "Pattern AI",
  },
  {
    id: 2,
    ticker: "MSFT",
    type: "Momentum Surge",
    direction: "long",
    score: 87,
    mlConfidence: 82,
    price: 415.2,
    target: 428.0,
    stop: 408.0,
    timeframe: "4H",
    time: "8m ago",
    source: "Market Scanner",
  },
  {
    id: 3,
    ticker: "TSLA",
    type: "Mean Reversion",
    direction: "long",
    score: 74,
    mlConfidence: 71,
    price: 248.1,
    target: 260.0,
    stop: 240.0,
    timeframe: "1D",
    time: "15m ago",
    source: "ML Engine",
  },
  {
    id: 4,
    ticker: "AMD",
    type: "Support Bounce",
    direction: "long",
    score: 81,
    mlConfidence: 78,
    price: 168.5,
    target: 178.0,
    stop: 163.0,
    timeframe: "1H",
    time: "22m ago",
    source: "Pattern AI",
  },
  {
    id: 5,
    ticker: "NVDA",
    type: "Bearish Divergence",
    direction: "short",
    score: 68,
    mlConfidence: 64,
    price: 868.2,
    target: 840.0,
    stop: 885.0,
    timeframe: "1D",
    time: "35m ago",
    source: "ML Engine",
  },
  {
    id: 6,
    ticker: "META",
    type: "Channel Breakout",
    direction: "long",
    score: 85,
    mlConfidence: 80,
    price: 582.4,
    target: 600.0,
    stop: 570.0,
    timeframe: "4H",
    time: "42m ago",
    source: "Market Scanner",
  },
  {
    id: 7,
    ticker: "SPY",
    type: "Bearish Engulfing",
    direction: "short",
    score: 72,
    mlConfidence: 69,
    price: 502.1,
    target: 495.0,
    stop: 506.0,
    timeframe: "1D",
    time: "1h ago",
    source: "Pattern AI",
  },
  {
    id: 8,
    ticker: "GOOGL",
    type: "Golden Cross",
    direction: "long",
    score: 79,
    mlConfidence: 75,
    price: 175.8,
    target: 185.0,
    stop: 170.0,
    timeframe: "1D",
    time: "1h ago",
    source: "ML Engine",
  },
];

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

  const filtered = MOCK_SIGNALS.filter(
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
        description={`${filtered.length} active signals detected`}
      >
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
          <span className="text-sm text-success">Live Scanning</span>
        </div>
      </PageHeader>

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
    </div>
  );
}
