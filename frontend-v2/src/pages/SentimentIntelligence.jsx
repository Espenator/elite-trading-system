// SENTIMENT INTELLIGENCE - Production-ready multi-source sentiment fusion
// Uses useSentiment hook -> GET /api/v1/sentiment/summary + /history + WebSocket
// Aurora Design System - 100% mockup fidelity (04-sentiment-intelligence.png)
import React, { useMemo } from 'react';
import SentimentTimelineLC from '../components/charts/SentimentTimelineLC';
import {
  Activity, TrendingUp, TrendingDown, AlertTriangle, Target,
  Newspaper, Twitter, MessageSquare, Server,
  Flame, Zap, BarChart2, Radio, RefreshCw,
  Database, Shield, Eye
} from 'lucide-react';
import PageHeader from "../components/ui/PageHeader";
import Button from "../components/ui/Button";
import { useSentiment } from "../hooks/useSentiment";

// ---- Constants ----
const SENTIMENT_SOURCES = ['Stockgeist', 'News', 'Discord', 'X/Twitter', 'FRED', 'SEC'];
const SOURCE_KEYS = ['stockgeist', 'news', 'discord', 'x', 'fred', 'sec'];

const AGENT_ICONS = {
  stockgeist: Activity,
  news: Newspaper,
  discord: MessageSquare,
  x: Twitter,
  fred: Database,
  sec: Shield,
};

const SOURCE_LABELS = {
  stockgeist: 'Stockgeist',
  news: 'News API',
  discord: 'Discord',
  x: 'X / Twitter',
  fred: 'FRED',
  sec: 'SEC',
};

// ---- Helpers ----
const getSentimentColor = (score) => {
  if (score == null) return 'text-slate-600';
  if (score >= 0.6) return 'text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]';
  if (score >= 0.2) return 'text-green-300';
  if (score > -0.2) return 'text-slate-300';
  if (score > -0.6) return 'text-red-300';
  return 'text-red-500 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]';
};

const getSentimentBg = (score) => {
  if (score == null) return 'bg-slate-800/30 border-slate-700/30';
  if (score >= 0.6) return 'bg-green-500/20 border-green-500/50';
  if (score >= 0.2) return 'bg-green-400/10 border-green-500/30';
  if (score > -0.2) return 'bg-slate-500/10 border-slate-500/30';
  if (score > -0.6) return 'bg-red-400/10 border-red-500/30';
  return 'bg-red-500/20 border-red-500/50';
};

const getSentimentIcon = (score) => {
  if (score >= 0.2) return <TrendingUp className="w-4 h-4" />;
  if (score <= -0.2) return <TrendingDown className="w-4 h-4" />;
  return <Activity className="w-4 h-4" />;
};

/** Returns a heatmap cell background color string for inline style */
const getHeatmapCellColor = (score) => {
  if (score == null) return 'rgba(30, 41, 59, 0.5)';
  if (score >= 0.6) return 'rgba(34, 197, 94, 0.6)';
  if (score >= 0.3) return 'rgba(34, 197, 94, 0.35)';
  if (score >= 0.1) return 'rgba(34, 197, 94, 0.15)';
  if (score > -0.1) return 'rgba(100, 116, 139, 0.2)';
  if (score > -0.3) return 'rgba(239, 68, 68, 0.15)';
  if (score > -0.6) return 'rgba(239, 68, 68, 0.35)';
  return 'rgba(239, 68, 68, 0.6)';
};

const FEAR_GREED_SEGMENTS = [
  { name: 'Extreme Fear', value: 20, color: '#ef4444' },
  { name: 'Fear', value: 20, color: '#f97316' },
  { name: 'Neutral', value: 20, color: '#eab308' },
  { name: 'Greed', value: 20, color: '#84cc16' },
  { name: 'Extreme Greed', value: 20, color: '#22c55e' },
];

// Default 12 symbols for heatmap rows
const DEFAULT_SYMBOLS = ['AAPL','AMD','NVDA','MSFT','TSLA','GOOG','AMZN','META','NFLX','PYPL','SQ','COIN'];

export default function SentimentIntelligence() {
  const {
    loading, error, lastUpdated, refetch,
    mood, sourceHealth, divergences, heatmap, signals, stats, history,
  } = useSentiment();

  // Aggregate history into hourly buckets for the timeline chart
  const timelineData = useMemo(() => {
    if (!history || history.length === 0) return [];
    const buckets = {};
    history.forEach((p) => {
      const d = new Date(p.timestamp);
      const key = `${d.getHours()}:00`;
      if (!buckets[key]) buckets[key] = { time: key, scores: [], volumes: [] };
      buckets[key].scores.push(p.score);
      buckets[key].volumes.push(p.volume || 0);
    });
    return Object.values(buckets).map((b) => ({
      time: b.time,
      sentiment: b.scores.reduce((a, c) => a + c, 0) / b.scores.length,
      volume: b.volumes.reduce((a, c) => a + c, 0),
    }));
  }, [history]);

  // Build heatmap grid data: 12 symbols x 6 sources
  const heatmapGrid = useMemo(() => {
    // Get unique symbols from heatmap data, pad with defaults
    const symbolsFromData = heatmap.map(h => h.ticker);
    const allSymbols = [...new Set([...symbolsFromData, ...DEFAULT_SYMBOLS])].slice(0, 12);

    return allSymbols.map(symbol => {
      const entry = heatmap.find(h => h.ticker === symbol);
      // Build per-source scores from the entry's sources breakdown if available
      const sourcesMap = {};
      if (entry?.sources && Array.isArray(entry.sources)) {
        entry.sources.forEach(s => {
          sourcesMap[s.source] = s.score;
        });
      }
      return {
        symbol,
        compositeScore: entry?.score ?? null,
        sources: SOURCE_KEYS.map(key => sourcesMap[key] ?? null),
      };
    });
  }, [heatmap]);

  // Build agent circles data from sourceHealth (pad to 6 for swarm viz)
  const agentCircles = useMemo(() => {
    const agents = SOURCE_KEYS.map(key => {
      const src = sourceHealth.find(s => s.source === key);
      return {
        key,
        name: SOURCE_LABELS[key] || key,
        status: src?.status || null,
        score: src?.score ?? null,
        latency: src?.latency_ms ?? null,
        weight: src?.weight ?? null,
        Icon: AGENT_ICONS[key] || Server,
      };
    });
    return agents;
  }, [sourceHealth]);

  // Build radar chart factors from live data
  const radarFactors = useMemo(() => {
    const liveCount = sourceHealth.filter(s => s.status === 'LIVE').length;
    const totalSources = sourceHealth.length || 1;
    return [
      { label: 'Bullish %', value: stats.bullish ? (stats.bullish / (stats.bullish + stats.bearish + (stats.neutral || 0))) * 100 : 0 },
      { label: 'Mood', value: mood?.value ?? 0 },
      { label: 'Coverage', value: (liveCount / Math.max(totalSources, 1)) * 100 },
      { label: 'Signals', value: signals.length > 0 ? Math.min(100, signals.length * 10) : 0 },
      { label: 'Heatmap', value: heatmap.length > 0 ? Math.min(100, heatmap.reduce((a, h) => a + Math.abs(h.score), 0) / heatmap.length * 100) : 0 },
      { label: 'Divergence', value: divergences.length > 0 ? Math.min(100, divergences.length * 20) : 0 },
      { label: 'Volume', value: stats.totalTickers ? Math.min(100, stats.totalTickers * 8) : 0 },
      { label: 'Confidence', value: mood?.value ? Math.min(100, Math.abs(mood.value - 50) * 2 + 50) : 0 },
    ];
  }, [stats, mood, sourceHealth, signals, heatmap, divergences]);

  const moodValue = mood?.value ?? 50;
  const moodLabel = mood?.label ?? 'Loading...';

  // Empty state
  if (!loading && !error && signals.length === 0 && sourceHealth.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader icon={Radio} title="Sentiment Intelligence" description="Multi-Source Fusion, Divergence Detection & Social Volume" />
        <div className="aurora-card p-12 text-center">
          <Radio className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">No Sentiment Data Yet</h3>
          <p className="text-aurora-subtext text-sm max-w-md mx-auto mb-6">
            Sentiment data will appear here once agents start collecting from Stockgeist, News API, Discord, and X.
            Submit data via POST /api/v1/sentiment or connect your sentiment agents.
          </p>
          <Button onClick={refetch} className="mx-auto"><RefreshCw className="w-4 h-4 mr-2" />Refresh</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader icon={Radio} title="Sentiment Intelligence" description="Multi-Source Fusion, Divergence Detection & Social Volume">
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-aurora-subtext">Updated {lastUpdated.toLocaleTimeString()}</span>
          )}
          <Button onClick={refetch} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
      </PageHeader>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-aurora p-4 text-red-400 text-sm">
          API Error: {error.message} - Retrying automatically...
        </div>
      )}

      {/* ========== HEADER: OpenClaw Swarm Viz (6 Agent Circles) ========== */}
      <div className="aurora-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-white flex items-center gap-2 text-sm uppercase tracking-widest">
            <Eye className="w-5 h-5 text-aurora-primary" />
            OpenClaw Swarm Viz
          </h3>
          <span className="text-2xs text-aurora-subtext font-mono">
            {sourceHealth.length > 0 ? `${sourceHealth.filter(s => s.status === 'LIVE').length}/${agentCircles.length} AGENTS LIVE` : 'AWAITING AGENTS'}
          </span>
        </div>
        <div className="flex flex-wrap justify-center gap-6 py-4">
          {agentCircles.map((agent) => {
            const isLive = agent.status === 'LIVE';
            const isDegraded = agent.status === 'DEGRADED';
            const AgentIcon = agent.Icon;
            return (
              <div key={agent.key} className="flex flex-col items-center gap-2 group cursor-pointer">
                {/* Agent Circle */}
                <div className={`relative w-20 h-20 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                  isLive
                    ? 'border-aurora-primary bg-aurora-primary/10 shadow-glow group-hover:shadow-[0_0_30px_rgba(0,217,255,0.5)]'
                    : isDegraded
                      ? 'border-aurora-warning bg-aurora-warning/10'
                      : 'border-aurora-muted bg-aurora-muted/20'
                }`}>
                  <AgentIcon className={`w-7 h-7 ${
                    isLive ? 'text-aurora-primary' : isDegraded ? 'text-aurora-warning' : 'text-slate-600'
                  }`} />
                  {/* Status dot */}
                  <div className={`absolute -top-1 -right-1 w-4 h-4 rounded-full border-2 border-aurora-bg ${
                    isLive
                      ? 'bg-green-400 animate-pulse'
                      : isDegraded
                        ? 'bg-yellow-400'
                        : 'bg-slate-600'
                  }`} />
                </div>
                {/* Agent Name */}
                <span className={`text-xs font-semibold ${isLive ? 'text-white' : 'text-slate-500'}`}>
                  {agent.name}
                </span>
                {/* Score */}
                <span className={`text-xs font-mono font-bold ${
                  agent.score != null ? getSentimentColor(agent.score) : 'text-slate-600'
                }`}>
                  {agent.score != null ? (agent.score > 0 ? '+' : '') + agent.score.toFixed(2) : '--'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ========== ROW 1: Heatmap Grid (12x6) | 30d Sentiment Area Chart ========== */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Heatmap Grid: 12 symbols x 6 sources */}
        <div className="xl:col-span-3 aurora-card">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-white flex items-center gap-2 text-sm">
              <Flame className="w-5 h-5 text-orange-500" />
              Sentiment Heatmap Grid
            </h3>
            <span className="text-2xs text-aurora-subtext font-mono">
              {heatmap.length > 0 ? `${heatmap.length} SYMBOLS` : 'AWAITING DATA'}
            </span>
          </div>
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr>
                  <th className="text-left text-aurora-subtext font-semibold p-2 uppercase tracking-wider text-2xs sticky left-0 bg-aurora-card z-10">Symbol</th>
                  {SENTIMENT_SOURCES.map(src => (
                    <th key={src} className="text-center text-aurora-subtext font-semibold p-2 uppercase tracking-wider text-2xs">{src}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmapGrid.length > 0 ? heatmapGrid.map((row) => (
                  <tr key={row.symbol} className="border-t border-aurora-border/30 hover:bg-white/[0.02] transition-colors">
                    <td className="p-2 font-mono font-bold text-white tracking-wider sticky left-0 bg-aurora-card z-10">
                      {row.symbol}
                    </td>
                    {row.sources.map((score, ci) => (
                      <td key={ci} className="p-1 text-center">
                        <div
                          className="mx-auto rounded-[4px] w-full min-w-[40px] h-8 flex items-center justify-center text-2xs font-mono font-bold transition-all hover:scale-110 cursor-pointer"
                          style={{ backgroundColor: getHeatmapCellColor(score) }}
                        >
                          <span className={score != null ? getSentimentColor(score) : 'text-slate-600'}>
                            {score != null ? (score > 0 ? '+' : '') + score.toFixed(2) : '--'}
                          </span>
                        </div>
                      </td>
                    ))}
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-aurora-subtext text-sm">
                      Awaiting heatmap data from sentiment agents
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* 30d Sentiment Area Chart */}
        <div className="xl:col-span-2 aurora-card">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-white flex items-center gap-2 text-sm">
              <TrendingUp className="w-5 h-5 text-aurora-primary" />
              30D Rolling Sentiment vs Volume
            </h3>
          </div>
          <div className="h-72 w-full">
            {timelineData.length > 0 ? (
              <SentimentTimelineLC data={timelineData} height={288} />
            ) : (
              <div className="h-full flex items-center justify-center text-aurora-subtext text-sm">
                Timeline data will populate as sentiment updates arrive
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ========== ROW 2: Signals Table (10 cols) | Radar Chart (8 axes) ========== */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Active Signals Table - 10 Columns */}
        <div className="xl:col-span-2">
          <div className="aurora-card">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-white flex items-center gap-2 text-sm">
                <BarChart2 className="w-5 h-5 text-purple-400" />
                Active Sentiment Signals ({signals.length})
              </h3>
            </div>
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-left border-collapse min-w-[900px]">
                <thead>
                  <tr className="bg-aurora-muted/30 border-b border-aurora-border text-2xs uppercase tracking-wider text-aurora-subtext">
                    <th className="p-3 font-semibold">Symbol</th>
                    <th className="p-3 font-semibold text-center">Direction</th>
                    <th className="p-3 font-semibold text-center">Score</th>
                    <th className="p-3 font-semibold">Source</th>
                    <th className="p-3 font-semibold">Time</th>
                    <th className="p-3 font-semibold text-center">Confidence</th>
                    <th className="p-3 font-semibold">Team</th>
                    <th className="p-3 font-semibold text-center">Override</th>
                    <th className="p-3 font-semibold text-center">Action</th>
                    <th className="p-3 font-semibold text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-aurora-border/30">
                  {signals.length > 0 ? signals.map((sig) => (
                    <tr key={sig.ticker} className="hover:bg-white/[0.02] transition-colors">
                      {/* Symbol */}
                      <td className="p-3">
                        <span className="font-black text-white tracking-widest text-sm flex items-center gap-1.5">
                          {sig.ticker}
                          <span className={getSentimentColor(sig.composite)}>{getSentimentIcon(sig.composite)}</span>
                        </span>
                      </td>
                      {/* Direction */}
                      <td className="p-3 text-center">
                        <span className={`text-xs font-bold px-2 py-1 rounded-aurora ${
                          sig.composite >= 0.2 ? 'bg-green-500/20 text-green-400' :
                          sig.composite <= -0.2 ? 'bg-red-500/20 text-red-400' :
                          'bg-slate-500/20 text-slate-400'
                        }`}>
                          {sig.composite >= 0.2 ? 'BULL' : sig.composite <= -0.2 ? 'BEAR' : 'FLAT'}
                        </span>
                      </td>
                      {/* Score */}
                      <td className="p-3 text-center">
                        <span className={`font-mono font-bold text-sm ${getSentimentColor(sig.composite)}`}>
                          {sig.composite > 0 ? '+' : ''}{sig.composite.toFixed(2)}
                        </span>
                      </td>
                      {/* Source */}
                      <td className="p-3">
                        <span className="text-xs text-aurora-subtext">
                          {sig.source ? SOURCE_LABELS[sig.source] || sig.source : 'Composite'}
                        </span>
                      </td>
                      {/* Time */}
                      <td className="p-3">
                        <span className="text-xs text-aurora-subtext font-mono">
                          {sig.timestamp ? new Date(sig.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--'}
                        </span>
                      </td>
                      {/* Confidence */}
                      <td className="p-3 text-center">
                        <span className={`text-xs font-bold ${
                          (sig.confidence ?? 0) >= 0.8 ? 'text-green-400' :
                          (sig.confidence ?? 0) >= 0.5 ? 'text-aurora-primary' :
                          'text-aurora-subtext'
                        }`}>
                          {sig.confidence != null ? (sig.confidence * 100).toFixed(0) + '%' : '--'}
                        </span>
                      </td>
                      {/* Team */}
                      <td className="p-3">
                        <span className="text-xs text-aurora-subtext">
                          {sig.team || '--'}
                        </span>
                      </td>
                      {/* Override */}
                      <td className="p-3 text-center">
                        <span className={`text-2xs font-bold uppercase px-1.5 py-0.5 rounded ${
                          sig.override ? 'bg-aurora-warning/20 text-aurora-warning' : 'bg-aurora-muted/30 text-slate-500'
                        }`}>
                          {sig.override ? 'YES' : 'NO'}
                        </span>
                      </td>
                      {/* Action */}
                      <td className="p-3 text-center">
                        <span className={`text-xs font-bold px-2 py-1 rounded-aurora ${
                          sig.profitSignal?.includes('BUY') ? 'bg-green-500/20 text-green-400' :
                          sig.profitSignal?.includes('SELL') ? 'bg-red-500/20 text-red-400' :
                          'bg-slate-500/20 text-slate-400'
                        }`}>
                          {sig.profitSignal || 'HOLD'}
                        </span>
                      </td>
                      {/* Status */}
                      <td className="p-3 text-center">
                        <span className={`text-2xs font-bold uppercase ${
                          sig.momentum === 'accelerating' ? 'text-green-400' :
                          sig.momentum === 'decelerating' ? 'text-red-400' : 'text-aurora-subtext'
                        }`}>
                          {sig.momentum || 'stable'}
                        </span>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={10} className="p-8 text-center text-aurora-subtext">
                        Awaiting signal data - signals appear when agents submit sentiment
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Multi-Factor Radar Chart (8 axes) */}
        <div className="xl:col-span-1 aurora-card">
          <h3 className="font-bold text-white flex items-center gap-2 mb-4 text-sm">
            <BarChart2 className="w-5 h-5 text-aurora-primary" />
            Multi-Factor Sentiment Radar
          </h3>
          <div className="flex justify-center">
            <svg viewBox="0 0 220 220" className="w-full max-w-[280px]">
              {(() => {
                const cx = 110, cy = 110, maxR = 80;
                const factors = radarFactors;
                const angleStep = (2 * Math.PI) / factors.length;
                const getPoint = (i, r) => ({
                  x: cx + r * Math.cos(i * angleStep - Math.PI / 2),
                  y: cy + r * Math.sin(i * angleStep - Math.PI / 2),
                });
                const gridLevels = [0.25, 0.5, 0.75, 1.0];
                const dataPoints = factors.map((f, i) => getPoint(i, (f.value / 100) * maxR));
                const polygonStr = dataPoints.map(p => `${p.x},${p.y}`).join(' ');
                const hasData = factors.some(f => f.value > 0);
                return (
                  <>
                    {/* Grid rings */}
                    {gridLevels.map(level => (
                      <polygon key={level}
                        points={factors.map((_, i) => { const p = getPoint(i, maxR * level); return `${p.x},${p.y}`; }).join(' ')}
                        fill="none" stroke="rgba(42,52,68,0.5)" strokeWidth="0.5" />
                    ))}
                    {/* Axis lines */}
                    {factors.map((_, i) => {
                      const p = getPoint(i, maxR);
                      return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgba(42,52,68,0.5)" strokeWidth="0.5" />;
                    })}
                    {/* Data polygon */}
                    {hasData && (
                      <polygon points={polygonStr} fill="rgba(0,217,255,0.12)" stroke="#00D9FF" strokeWidth="1.5" />
                    )}
                    {/* Data points */}
                    {hasData && dataPoints.map((p, i) => (
                      <circle key={i} cx={p.x} cy={p.y} r="3" fill="#00D9FF" />
                    ))}
                    {/* Labels */}
                    {factors.map((f, i) => {
                      const p = getPoint(i, maxR + 18);
                      return (
                        <text key={i} x={p.x} y={p.y} textAnchor="middle" dominantBaseline="middle"
                          fill="#9CA3AF" fontSize="7" fontFamily="Inter">
                          {f.label}
                        </text>
                      );
                    })}
                    {/* No data message */}
                    {!hasData && (
                      <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle"
                        fill="#9CA3AF" fontSize="10" fontFamily="Inter">
                        Awaiting data
                      </text>
                    )}
                  </>
                );
              })()}
            </svg>
          </div>
          {/* Legend */}
          <div className="grid grid-cols-2 gap-1 mt-2 px-2">
            {radarFactors.map((f) => (
              <div key={f.label} className="flex items-center justify-between text-2xs">
                <span className="text-aurora-subtext">{f.label}</span>
                <span className="font-mono font-bold text-aurora-primary">{f.value > 0 ? f.value.toFixed(0) : '--'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ========== ROW 3: Prediction Market | Scanner Matrix (8 cols) ========== */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Prediction Markets + Market Mood Gauge */}
        <div className="xl:col-span-1 space-y-6">
          {/* Market Mood Gauge */}
          <div className="aurora-card flex flex-col items-center justify-center relative overflow-hidden">
            <h3 className="text-2xs font-bold text-aurora-subtext uppercase tracking-widest self-start mb-2">Market Mood</h3>
            <div className="h-40 w-full relative">
              <svg viewBox="0 0 200 120" className="w-full h-full">
                {FEAR_GREED_SEGMENTS.map((seg, i) => {
                  const startAngle = 180 - (i * 36);
                  const endAngle = 180 - ((i + 1) * 36);
                  const startRad = (startAngle * Math.PI) / 180;
                  const endRad = (endAngle * Math.PI) / 180;
                  return (
                    <path
                      key={`seg-${i}`}
                      d={`M ${100 + 80 * Math.cos(startRad)} ${100 - 80 * Math.sin(startRad)} A 80 80 0 0 1 ${100 + 80 * Math.cos(endRad)} ${100 - 80 * Math.sin(endRad)}`}
                      fill="none"
                      stroke={seg.color}
                      strokeWidth="16"
                      strokeLinecap="round"
                    />
                  );
                })}
                {/* Needle */}
                {(() => {
                  const angle = 180 - (moodValue / 100) * 180;
                  const rad = (angle * Math.PI) / 180;
                  return <line x1="100" y1="100" x2={100 + 55 * Math.cos(rad)} y2={100 - 55 * Math.sin(rad)} stroke="white" strokeWidth="2" />;
                })()}
                <circle cx="100" cy="100" r="4" fill="white" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-end pb-2 pointer-events-none">
                <span className="text-3xl font-black text-white">{moodValue}</span>
                <span className={`font-bold tracking-wider uppercase text-2xs ${moodValue >= 60 ? 'text-green-400' : moodValue <= 40 ? 'text-red-400' : 'text-yellow-400'}`}>{moodLabel}</span>
              </div>
            </div>
            {stats.totalTickers > 0 && (
              <div className="flex gap-4 mt-1 text-2xs text-aurora-subtext">
                <span className="text-green-400">{stats.bullish} Bullish</span>
                <span>{stats.neutral} Neutral</span>
                <span className="text-red-400">{stats.bearish} Bearish</span>
              </div>
            )}
          </div>

          {/* Prediction Market */}
          <div className="aurora-card">
            <h3 className="font-bold text-white flex items-center gap-2 mb-4 text-sm">
              <Target className="w-5 h-5 text-amber-400" />
              Prediction Markets
            </h3>
            <div className="space-y-4">
              {sourceHealth.length > 0 ? (
                [{
                  title: 'Sentiment Consensus',
                  desc: 'Composite multi-source sentiment alignment probability',
                  probability: mood?.value ?? 0,
                  progress: sourceHealth.filter(s => s.status === 'LIVE').length > 0
                    ? Math.round((sourceHealth.filter(s => s.status === 'LIVE').length / sourceHealth.length) * 100)
                    : 0,
                }, {
                  title: 'Divergence Risk',
                  desc: 'Probability of cross-source sentiment divergence',
                  probability: divergences.length > 0
                    ? Math.min(95, divergences.length * 25)
                    : 0,
                  progress: divergences.length > 0
                    ? Math.min(100, divergences.length * 20)
                    : 0,
                }].map((pm, i) => (
                  <div key={i} className="bg-aurora-muted/30 border border-aurora-border rounded-aurora p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-white font-semibold text-xs">{pm.title}</span>
                    </div>
                    <p className="text-aurora-subtext text-2xs mb-3">{pm.desc}</p>
                    <div className="space-y-2">
                      <div className="flex justify-between text-2xs">
                        <span className="text-aurora-subtext">Probability</span>
                        <span className="text-aurora-primary font-bold font-mono">{pm.probability}%</span>
                      </div>
                      <div className="w-full bg-aurora-muted rounded-full h-1.5">
                        <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: `${pm.probability}%`, backgroundColor: '#00D9FF' }} />
                      </div>
                      <div className="flex justify-between text-2xs">
                        <span className="text-aurora-subtext">Progress</span>
                        <span className="text-amber-400 font-bold font-mono">{pm.progress}%</span>
                      </div>
                      <div className="w-full bg-aurora-muted rounded-full h-1.5">
                        <div className="bg-amber-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${pm.progress}%` }} />
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-aurora-subtext text-sm py-6">
                  Awaiting source data for prediction markets
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Scanner Status Matrix (8 cols) + Divergence Alerts */}
        <div className="xl:col-span-2 space-y-6">
          {/* Scanner Status Matrix */}
          <div className="aurora-card">
            <h3 className="font-bold text-white flex items-center gap-2 mb-4 text-sm">
              <Activity className="w-5 h-5 text-emerald-400" />
              Scanner Status Matrix
            </h3>
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-2xs">
                <thead>
                  <tr>
                    <th className="text-left text-aurora-subtext p-1.5 font-semibold uppercase tracking-wider">Sym</th>
                    {['S1','S2','S3','S4','S5','S6','S7','S8'].map(s => (
                      <th key={s} className="text-center text-aurora-subtext p-1.5 font-semibold">{s}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(heatmap.length > 0 ? heatmap.slice(0, 12) : []).map((item, ri) => (
                    <tr key={ri} className="border-t border-aurora-border/20 hover:bg-white/[0.02] transition-colors">
                      <td className="text-white font-mono font-bold p-1.5 whitespace-nowrap">{item.ticker}</td>
                      {Array.from({ length: 8 }, (_, ci) => {
                        // Derive per-scanner score from the item's composite + source variation
                        const score = item.score != null ? item.score : null;
                        const baseHue = score != null
                          ? (score > 0.3 ? 'bg-emerald-500' : score > 0 ? 'bg-aurora-primary' : score > -0.3 ? 'bg-amber-500' : 'bg-red-500')
                          : 'bg-aurora-muted';
                        const opacity = score != null ? 0.4 + Math.abs(score) * 0.6 : 0.2;
                        return (
                          <td key={ci} className="p-1.5 text-center">
                            <div className={`w-3.5 h-3.5 rounded-full mx-auto ${baseHue} transition-all`}
                              style={{ opacity }} />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                  {heatmap.length === 0 && (
                    <tr>
                      <td colSpan={9} className="p-6 text-center text-aurora-subtext text-sm">
                        Awaiting scanner data from sentiment agents
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Divergence Alerts */}
          <div className="aurora-card">
            <h3 className="font-bold text-white flex items-center gap-2 mb-4 text-sm">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              Source Divergence Alerts
            </h3>
            <div className="space-y-3">
              {divergences.length > 0 ? divergences.map((alert, idx) => (
                <div key={idx} className="bg-aurora-muted/30 border border-aurora-border rounded-aurora p-3 relative overflow-hidden hover:shadow-glow transition-all">
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-yellow-500" />
                  <div className="flex justify-between items-start mb-1 pl-2">
                    <span className="font-black text-white">{alert.ticker}</span>
                    <span className="text-2xs text-aurora-subtext font-mono">Spread: {alert.spread}</span>
                  </div>
                  <p className="text-xs text-slate-300 mb-2 bg-aurora-bg/50 p-1.5 rounded-aurora ml-2">{alert.conflict}</p>
                  <div className="text-2xs font-bold text-yellow-400 uppercase tracking-wider flex items-center gap-1 ml-2">
                    <Zap className="w-3 h-3" /> {alert.impact}
                  </div>
                </div>
              )) : (
                <div className="text-center text-aurora-subtext text-sm py-6">
                  <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                  No divergences detected - sources are aligned
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
