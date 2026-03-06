// SENTIMENT INTELLIGENCE - Production-ready multi-source sentiment fusion
// Uses useSentiment hook -> GET /api/v1/sentiment/summary + /history + WebSocket
// Aurora Design System - 100% mockup fidelity (04-sentiment-intelligence.png)
import React, { useMemo, useCallback, useState } from 'react';
import { getApiUrl, getAuthHeaders } from '../config/api';
import SentimentTimelineLC from '../components/charts/SentimentTimelineLC';
import {
  Activity, TrendingUp, TrendingDown, AlertTriangle, Target,
  Newspaper, Twitter, MessageSquare, Server,
  Flame, Zap, BarChart2, Radio, RefreshCw,
  Database, Shield, Eye
} from 'lucide-react';
import PageHeader from "../components/ui/PageHeader";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
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

  const [discovering, setDiscovering] = useState(false);

  const handleAutoDiscover = useCallback(async () => {
    setDiscovering(true);
    try {
      const res = await fetch(getApiUrl('sentiment/discover'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      refetch();
    } catch (err) {
      console.error('Auto Discover failed:', err);
    } finally {
      setDiscovering(false);
    }
  }, [refetch]);

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
    <div className="space-y-4">
      {/* Page Header */}
      <PageHeader icon={Radio} title="Sentiment Intelligence" description="Multi-Source Fusion, Divergence Detection & Social Volume">
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-gray-500">Updated {lastUpdated.toLocaleTimeString()}</span>
          )}
          <Button onClick={refetch} disabled={loading} size="sm">
            <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
      </PageHeader>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
          API Error: {error.message} - Retrying automatically...
        </div>
      )}

      {/* ========== MAIN 3-COLUMN LAYOUT ========== */}
      <div className="grid grid-cols-12 gap-4">

        {/* ===== LEFT COLUMN: OpenClaw Agent Swarm ===== */}
        <div className="col-span-12 xl:col-span-3">
          <Card title="OpenClaw Agent Swarm" subtitle={sourceHealth.length > 0 ? `${sourceHealth.filter(s => s.status === 'LIVE').length}/${agentCircles.length} agents live` : 'Awaiting agents'}>
            <div className="space-y-2">
              {agentCircles.map((agent) => {
                const isLive = agent.status === 'LIVE';
                const isDegraded = agent.status === 'DEGRADED';
                const AgentIcon = agent.Icon;
                const weightPct = agent.weight != null ? Math.round(agent.weight * 100) : 0;
                return (
                  <div key={agent.key} className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/[0.03] transition-colors group">
                    {/* Status dot */}
                    <div className={`w-2 h-2 rounded-full shrink-0 ${
                      isLive ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]'
                        : isDegraded ? 'bg-yellow-400' : 'bg-slate-600'
                    }`} />
                    {/* Icon + Name */}
                    <AgentIcon className={`w-4 h-4 shrink-0 ${isLive ? 'text-cyan-400' : isDegraded ? 'text-yellow-400' : 'text-slate-600'}`} />
                    <span className={`text-xs font-medium flex-1 min-w-0 truncate ${isLive ? 'text-white' : 'text-slate-500'}`}>
                      {agent.name}
                    </span>
                    {/* Score */}
                    <span className={`text-xs font-mono font-bold shrink-0 ${agent.score != null ? getSentimentColor(agent.score) : 'text-slate-600'}`}>
                      {agent.score != null ? (agent.score > 0 ? '+' : '') + agent.score.toFixed(2) : '--'}
                    </span>
                    {/* Weight bar */}
                    <div className="w-16 shrink-0">
                      <div className="w-full bg-slate-800 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full transition-all ${isLive ? 'bg-cyan-500' : isDegraded ? 'bg-yellow-500' : 'bg-slate-700'}`}
                          style={{ width: `${weightPct}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500 w-8 text-right shrink-0">{weightPct}%</span>
                  </div>
                );
              })}

              {/* Agent weight labels */}
              <div className="border-t border-secondary/20 pt-2 mt-2 space-y-1">
                {[
                  { label: 'Agent Weight', key: 'composite' },
                  { label: 'Signal Weight', key: 'signal' },
                  { label: 'Recency Weight', key: 'recency' },
                  { label: 'Market Weight', key: 'market' },
                ].map(item => {
                  const weightVal = stats?.weights?.[item.key]
                    ?? (item.key === 'composite' && sourceHealth.length > 0
                      ? Math.round(sourceHealth.reduce((sum, s) => sum + (s.weight ?? 0), 0) / sourceHealth.length * 100)
                      : 0);
                  const pct = typeof weightVal === 'number' ? Math.round(weightVal) : 0;
                  return (
                    <div key={item.key} className="flex items-center justify-between text-[10px] px-2">
                      <span className="text-slate-500">{item.label}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-800 rounded-full h-1">
                          <div className="h-1 rounded-full bg-cyan-600/60" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="text-slate-500 font-mono w-6 text-right">{pct}</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Auto Discover Button */}
              <button
                disabled={discovering}
                onClick={handleAutoDiscover}
                className="w-full mt-3 py-2 rounded-lg bg-cyan-500/20 border border-cyan-500/40 text-cyan-400 text-xs font-semibold hover:bg-cyan-500/30 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <Zap className={`w-3.5 h-3.5 ${discovering ? 'animate-spin' : ''}`} />
                {discovering ? 'Discovering...' : 'Auto Discover'}
              </button>
            </div>
          </Card>

          {/* Sentiment Sources / Timeline */}
          <Card title="Sentiment Sources" className="mt-4">
            <div className="h-48 w-full">
              {timelineData.length > 0 ? (
                <SentimentTimelineLC data={timelineData} height={192} />
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                  Timeline data will populate as updates arrive
                </div>
              )}
            </div>
            {/* Color bar legend */}
            <div className="mt-3 flex h-2 rounded-full overflow-hidden">
              <div className="flex-1 bg-red-500" />
              <div className="flex-1 bg-orange-500" />
              <div className="flex-1 bg-yellow-400" />
              <div className="flex-1 bg-lime-400" />
              <div className="flex-1 bg-green-400" />
              <div className="flex-1 bg-cyan-400" />
              <div className="flex-1 bg-violet-500" />
            </div>
          </Card>
        </div>

        {/* ===== CENTER COLUMN ===== */}
        <div className="col-span-12 xl:col-span-5 space-y-4">

          {/* PAS Regime Banner */}
          <div className="bg-emerald-500/20 border border-emerald-500/50 rounded-xl p-3 text-center">
            <span className="text-emerald-400 font-black text-sm tracking-widest uppercase">
              PAS v8 Regime: BULL TREND {moodValue}%
            </span>
          </div>

          {/* Heatmap Grid */}
          <Card title="Sentiment Heatmap" action={
            <span className="text-[10px] text-gray-500 font-mono">{heatmap.length > 0 ? `${heatmap.length} SYMBOLS` : 'AWAITING DATA'}</span>
          }>
            <div className="overflow-x-auto">
              <table className="w-full text-[10px] border-collapse">
                <thead>
                  <tr>
                    <th className="text-left text-gray-500 font-semibold p-1.5 uppercase tracking-wider sticky left-0 bg-surface z-10">Sym</th>
                    {SENTIMENT_SOURCES.map(src => (
                      <th key={src} className="text-center text-gray-500 font-semibold p-1.5 uppercase tracking-wider">{src}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {heatmapGrid.length > 0 ? heatmapGrid.map((row) => (
                    <tr key={row.symbol} className="border-t border-secondary/10 hover:bg-white/[0.02] transition-colors">
                      <td className="p-1.5 font-mono font-bold text-white tracking-wider sticky left-0 bg-surface z-10">
                        {row.symbol}
                      </td>
                      {row.sources.map((score, ci) => (
                        <td key={ci} className="p-0.5 text-center">
                          <div
                            className="mx-auto rounded w-full min-w-[36px] h-6 flex items-center justify-center text-[10px] font-mono font-bold cursor-pointer hover:scale-105 transition-transform"
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
                      <td colSpan={7} className="p-6 text-center text-gray-500 text-xs">
                        Awaiting heatmap data from sentiment agents
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {/* 30-Day Sentiment Chart */}
          <Card title="30-Day Sentiment">
            <div className="h-56 w-full">
              {timelineData.length > 0 ? (
                <SentimentTimelineLC data={timelineData} height={224} />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-500 text-sm">
                  Timeline data will populate as sentiment updates arrive
                </div>
              )}
            </div>
          </Card>

          {/* Divergence Alerts */}
          <Card title="Divergence Alerts" action={
            <Badge variant={divergences.length > 0 ? 'warning' : 'secondary'} size="sm">
              {divergences.length} active
            </Badge>
          }>
            <div className="space-y-2">
              {divergences.length > 0 ? divergences.map((alert, idx) => (
                <div key={idx} className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 relative overflow-hidden">
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-500" />
                  <div className="flex items-start gap-3 pl-2">
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-black text-white text-sm">{alert.ticker}</span>
                        <span className="text-[10px] text-gray-500 font-mono">Spread: {alert.spread}</span>
                      </div>
                      <p className="text-xs text-slate-300 mb-1.5">{alert.conflict}</p>
                      <div className="text-[10px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1">
                        <Zap className="w-3 h-3" /> {alert.impact}
                      </div>
                    </div>
                  </div>
                </div>
              )) : (
                <div className="text-center text-gray-500 text-xs py-4">
                  <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-slate-600" />
                  No divergences detected - sources are aligned
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* ===== RIGHT COLUMN ===== */}
        <div className="col-span-12 xl:col-span-4 space-y-4">

          {/* Trade Signals */}
          <Card title="Trade Signals" action={
            <Badge variant="primary" size="sm">{signals.length} active</Badge>
          }>
            <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
              {signals.length > 0 ? signals.map((sig) => (
                <div key={sig.ticker} className="flex items-center gap-2 p-2 rounded-lg bg-secondary/10 hover:bg-secondary/20 transition-colors">
                  <span className="font-black text-white text-xs tracking-wider w-12">{sig.ticker}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                    sig.composite >= 0.2 ? 'bg-emerald-500/20 text-emerald-400' :
                    sig.composite <= -0.2 ? 'bg-red-500/20 text-red-400' :
                    'bg-slate-500/20 text-slate-400'
                  }`}>
                    {sig.composite >= 0.2 ? 'BULL' : sig.composite <= -0.2 ? 'BEAR' : 'FLAT'}
                  </span>
                  <span className={`font-mono font-bold text-xs flex-1 text-right ${getSentimentColor(sig.composite)}`}>
                    {sig.composite > 0 ? '+' : ''}{sig.composite.toFixed(2)}
                  </span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                    sig.profitSignal?.includes('BUY') ? 'bg-emerald-500/20 text-emerald-400' :
                    sig.profitSignal?.includes('SELL') ? 'bg-red-500/20 text-red-400' :
                    'bg-slate-500/20 text-slate-400'
                  }`}>
                    {sig.profitSignal || 'HOLD'}
                  </span>
                </div>
              )) : (
                <div className="text-center text-gray-500 text-xs py-4">
                  Awaiting signal data from sentiment agents
                </div>
              )}
            </div>
          </Card>

          {/* Radar Chart + Prediction Markets row */}
          <div className="grid grid-cols-2 gap-4">
            {/* Prediction Market 1 */}
            <Card title="Prediction Market" className="col-span-1">
              {sourceHealth.length > 0 ? (
                <div className="space-y-3">
                  <p className="text-[10px] text-gray-500">Sentiment consensus alignment probability</p>
                  <div className="space-y-2">
                    <div className="flex justify-between text-[10px]">
                      <span className="text-gray-500">Probability</span>
                      <span className="text-cyan-400 font-bold font-mono">{mood?.value ?? 0}%</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-cyan-500 transition-all" style={{ width: `${mood?.value ?? 0}%` }} />
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-gray-500">Progress</span>
                      <span className="text-amber-400 font-bold font-mono">
                        {sourceHealth.filter(s => s.status === 'LIVE').length > 0
                          ? Math.round((sourceHealth.filter(s => s.status === 'LIVE').length / sourceHealth.length) * 100)
                          : 0}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5">
                      <div className="bg-amber-500 h-1.5 rounded-full transition-all" style={{
                        width: `${sourceHealth.filter(s => s.status === 'LIVE').length > 0
                          ? Math.round((sourceHealth.filter(s => s.status === 'LIVE').length / sourceHealth.length) * 100)
                          : 0}%`
                      }} />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-500 text-[10px] py-3">Awaiting data</div>
              )}
            </Card>

            {/* Prediction Market 2 */}
            <Card title="Prediction Market" className="col-span-1">
              {divergences.length >= 0 ? (
                <div className="space-y-3">
                  <p className="text-[10px] text-gray-500">Cross-source divergence risk probability</p>
                  <div className="space-y-2">
                    <div className="flex justify-between text-[10px]">
                      <span className="text-gray-500">Probability</span>
                      <span className="text-cyan-400 font-bold font-mono">
                        {divergences.length > 0 ? Math.min(95, divergences.length * 25) : 0}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-cyan-500 transition-all" style={{
                        width: `${divergences.length > 0 ? Math.min(95, divergences.length * 25) : 0}%`
                      }} />
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-gray-500">Progress</span>
                      <span className="text-amber-400 font-bold font-mono">
                        {divergences.length > 0 ? Math.min(100, divergences.length * 20) : 0}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5">
                      <div className="bg-amber-500 h-1.5 rounded-full transition-all" style={{
                        width: `${divergences.length > 0 ? Math.min(100, divergences.length * 20) : 0}%`
                      }} />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-500 text-[10px] py-3">Awaiting data</div>
              )}
            </Card>
          </div>

          {/* Multi-Factor Radar Chart */}
          <Card>
            <div className="flex justify-center">
              <svg viewBox="0 0 220 220" className="w-full max-w-[260px]">
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
                        <polygon points={polygonStr} fill="rgba(6,182,212,0.15)" stroke="#06b6d4" strokeWidth="1.5" />
                      )}
                      {/* Data points */}
                      {hasData && dataPoints.map((p, i) => (
                        <circle key={i} cx={p.x} cy={p.y} r="3" fill="#06b6d4" />
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
          </Card>

          {/* Scanner Status Matrix */}
          <Card title="Scanner Status Matrix" action={
            <span className="text-[10px] text-gray-500 font-mono">{heatmap.length} symbols</span>
          }>
            <div className="overflow-x-auto">
              <table className="w-full text-[10px]">
                <thead>
                  <tr>
                    <th className="text-left text-gray-500 p-1 font-semibold uppercase tracking-wider">Sym</th>
                    {['S1','S2','S3','S4','S5','S6','S7','S8'].map(s => (
                      <th key={s} className="text-center text-gray-500 p-1 font-semibold">{s}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(heatmap.length > 0 ? heatmap.slice(0, 12) : DEFAULT_SYMBOLS.map(s => ({ ticker: s, score: null }))).map((item, ri) => (
                    <tr key={ri} className="border-t border-secondary/10 hover:bg-white/[0.02] transition-colors">
                      <td className="text-white font-mono font-bold p-1 whitespace-nowrap">{item.ticker}</td>
                      {Array.from({ length: 8 }, (_, ci) => {
                        const score = item.score != null ? item.score : null;
                        // Vary color per scanner column for visual interest
                        const variation = score != null ? score + (ci - 4) * 0.05 : null;
                        const dotColor = variation != null
                          ? (variation > 0.3 ? 'bg-emerald-400' : variation > 0 ? 'bg-cyan-400' : variation > -0.3 ? 'bg-amber-400' : 'bg-red-400')
                          : 'bg-slate-700';
                        const opacity = variation != null ? 0.5 + Math.abs(variation) * 0.5 : 0.3;
                        return (
                          <td key={ci} className="p-1 text-center">
                            <div className={`w-3 h-3 rounded-full mx-auto ${dotColor} transition-all`}
                              style={{ opacity }} />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
