// SENTIMENT INTELLIGENCE - Production-ready multi-source sentiment fusion
// Uses useSentiment hook -> GET /api/v1/sentiment/summary + /history + WebSocket
import React, { useState, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import SentimentTimelineLC from '../components/charts/SentimentTimelineLC';
import {
  Activity, TrendingUp, TrendingDown, AlertTriangle,
  Newspaper, Twitter, MessageSquare, Server,
  Flame, Zap, BarChart2, Radio, RefreshCw, Wifi, WifiOff
} from 'lucide-react';
import PageHeader from "../components/ui/PageHeader";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import { useSentiment } from "../hooks/useSentiment";

// ---- Helpers ----
const getSentimentColor = (score) => {
  if (score >= 0.6) return 'text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]';
  if (score >= 0.2) return 'text-green-300';
  if (score > -0.2) return 'text-slate-300';
  if (score > -0.6) return 'text-red-300';
  return 'text-red-500 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]';
};
const getSentimentBg = (score) => {
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
const SOURCE_ICONS = {
  stockgeist: <Activity className="w-4 h-4" />,
  news: <Newspaper className="w-4 h-4" />,
  discord: <MessageSquare className="w-4 h-4" />,
  x: <Twitter className="w-4 h-4" />,
};
const SOURCE_LABELS = { stockgeist: 'Stockgeist', news: 'News API', discord: 'Discord', x: 'X / Twitter' };
const FEAR_GREED_SEGMENTS = [
  { name: 'Extreme Fear', value: 20, color: '#ef4444' },
  { name: 'Fear', value: 20, color: '#f97316' },
  { name: 'Neutral', value: 20, color: '#eab308' },
  { name: 'Greed', value: 20, color: '#84cc16' },
  { name: 'Extreme Greed', value: 20, color: '#22c55e' },
];

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

  const moodValue = mood?.value ?? 50;
  const moodLabel = mood?.label ?? 'Loading...';

  // Empty state
  if (!loading && !error && signals.length === 0 && sourceHealth.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader icon={Radio} title="Sentiment Intelligence" description="Multi-Source Fusion, Divergence Detection & Social Volume" />
        <Card className="bg-slate-900/40 border-slate-700/50 p-12 text-center">
          <Radio className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-white mb-2">No Sentiment Data Yet</h3>
          <p className="text-slate-400 text-sm max-w-md mx-auto mb-6">
            Sentiment data will appear here once agents start collecting from Stockgeist, News API, Discord, and X.
            Submit data via POST /api/v1/sentiment or connect your sentiment agents.
          </p>
          <Button onClick={refetch} className="mx-auto"><RefreshCw className="w-4 h-4 mr-2" />Refresh</Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader icon={Radio} title="Sentiment Intelligence" description="Multi-Source Fusion, Divergence Detection & Social Volume">
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-slate-500">Updated {lastUpdated.toLocaleTimeString()}</span>
          )}
          <Button onClick={refetch} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Loading...' : 'Refresh'}
          </Button>
        </div>
      </PageHeader>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
          API Error: {error.message} - Retrying automatically...
        </div>
      )}

      {/* TOP ROW: Market Mood Gauge + Source Status Cards */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Fear & Greed Gauge */}
        <Card className="col-span-1 bg-slate-900/40 border-slate-700/50 backdrop-blur-md relative overflow-hidden flex flex-col items-center justify-center p-4">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest absolute top-4 left-4">Market Mood</h3>
          <div className="h-48 w-full mt-4 relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={FEAR_GREED_SEGMENTS} cx="50%" cy="80%" startAngle={180} endAngle={0} innerRadius={60} outerRadius={80} paddingAngle={2} dataKey="value" stroke="none">
                  {FEAR_GREED_SEGMENTS.map((entry, index) => (<Cell key={`cell-${index}`} fill={entry.color} />))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-end pb-4 pointer-events-none">
              <span className="text-4xl font-black text-white">{moodValue}</span>
              <span className={`font-bold tracking-wider uppercase text-xs ${moodValue >= 60 ? 'text-green-400' : moodValue <= 40 ? 'text-red-400' : 'text-yellow-400'}`}>{moodLabel}</span>
            </div>
          </div>
          {stats.totalTickers > 0 && (
            <div className="flex gap-4 mt-2 text-[10px] text-slate-500">
              <span className="text-green-400">{stats.bullish} Bullish</span>
              <span>{stats.neutral} Neutral</span>
              <span className="text-red-400">{stats.bearish} Bearish</span>
            </div>
          )}
        </Card>

        {/* Source Status Cards */}
        <div className="col-span-1 xl:col-span-3 grid grid-cols-2 md:grid-cols-4 gap-4">
          {sourceHealth.length > 0 ? sourceHealth.map((src, idx) => (
            <div key={idx} className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm flex flex-col justify-between group hover:bg-slate-800/60 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-slate-700/50 rounded text-slate-300">
                    {SOURCE_ICONS[src.source] || <Server className="w-4 h-4" />}
                  </div>
                  <span className="font-bold text-sm text-white">{SOURCE_LABELS[src.source] || src.source}</span>
                </div>
                <span className="text-[10px] font-black text-slate-500 bg-slate-900/50 px-1.5 py-0.5 rounded border border-slate-700/50">
                  {src.weight || 25}% WGT
                </span>
              </div>
              <div className="mt-4">
                <div className="flex justify-between items-end mb-1">
                  <span className="text-xs text-slate-400">Current Bias</span>
                  <span className={`text-lg font-black ${getSentimentColor(src.score)}`}>
                    {src.score > 0 ? '+' : ''}{src.score.toFixed(2)}
                  </span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-1.5 mb-3 overflow-hidden">
                  <div className={`h-1.5 rounded-full ${src.score > 0 ? 'bg-green-500' : 'bg-red-500'}`}
                    style={{ width: `${Math.abs(src.score) * 100}%`, marginLeft: src.score > 0 ? '50%' : `${50 - (Math.abs(src.score) * 50)}%` }}
                  ></div>
                </div>
                <div className="flex justify-between items-center text-[10px]">
                  <span className={`flex items-center gap-1 ${src.status === 'LIVE' ? 'text-green-400' : src.status === 'DEGRADED' ? 'text-yellow-400' : 'text-red-400'}`}>
                    {src.status === 'LIVE' ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />} {src.status}
                  </span>
                  <span className="text-slate-500">{src.latency_ms}ms</span>
                </div>
              </div>
            </div>
          )) : (
            ['Stockgeist', 'News API', 'Discord', 'X / Twitter'].map((name, idx) => (
              <div key={idx} className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm flex flex-col justify-center items-center">
                <div className="p-1.5 bg-slate-700/50 rounded text-slate-500 mb-2"><Server className="w-4 h-4" /></div>
                <span className="font-bold text-sm text-slate-500">{name}</span>
                <span className="text-[10px] text-slate-600 mt-1">Awaiting Connection</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* MIDDLE ROW: Timeline + Heatmap */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 24h Rolling Timeline */}
        <Card className="lg:col-span-2 bg-slate-900/40 border-slate-700/50 backdrop-blur-md p-5">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-400" />
              24H Rolling Macro Sentiment vs Social Volume
            </h3>
          </div>
          <div className="h-64 w-full">
            {timelineData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={timelineData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorSentiment" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} vertical={false} />
                  <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickMargin={10} />
                  <YAxis yAxisId="left" stroke="#64748b" fontSize={11} domain={[-1, 1]} />
                  <YAxis yAxisId="right" orientation="right" stroke="#64748b" fontSize={11} hide />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc', borderRadius: '8px' }} />
                  <ReferenceLine y={0} yAxisId="left" stroke="#475569" strokeDasharray="3 3" />
                  <Bar dataKey="volume" yAxisId="right" fill="#475569" opacity={0.3} radius={[4, 4, 0, 0]} name="Social Volume" />
                  <Area type="monotone" dataKey="sentiment" yAxisId="left" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorSentiment)" name="Sentiment" />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                Timeline data will populate as sentiment updates arrive
              </div>
            )}
          </div>
        </Card>

        {/* Social Volume Heatmap */}
        <Card className="lg:col-span-1 bg-slate-900/40 border-slate-700/50 backdrop-blur-md p-5 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-white flex items-center gap-2">
              <Flame className="w-5 h-5 text-orange-500" />
              Social Volume Heatmap
            </h3>
          </div>
          <div className="flex-1 grid grid-cols-3 gap-2">
            {heatmap.length > 0 ? heatmap.slice(0, 12).map((item) => (
              <div key={item.ticker} className={`rounded-lg flex flex-col items-center justify-center p-2 border transition-all hover:scale-105 cursor-pointer ${getSentimentBg(item.score)}`}
                style={{ opacity: 0.5 + (Math.min(item.volume, 100) / 200) }}>
                <span className="font-black text-white tracking-wider">{item.ticker}</span>
                <span className={`text-[10px] font-bold ${getSentimentColor(item.score)}`}>
                  {item.score > 0 ? '+' : ''}{item.score.toFixed(2)}
                </span>
              </div>
            )) : (
              <div className="col-span-3 flex items-center justify-center text-slate-500 text-sm">
                No heatmap data yet
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* BOTTOM ROW: Signals Table + Divergences */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Active Signals Table */}
        <div className="xl:col-span-2 space-y-4">
          <h3 className="font-bold text-white flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-purple-400" />
            Active Sentiment Signals ({signals.length})
          </h3>
          <div className="bg-slate-900/40 border border-slate-700/50 rounded-xl overflow-hidden backdrop-blur-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-800/60 border-b border-slate-700/50 text-xs uppercase tracking-wider text-slate-400">
                  <th className="p-4 font-semibold">Asset</th>
                  <th className="p-4 font-semibold">Composite</th>
                  <th className="p-4 font-semibold text-center hidden md:table-cell">Signal</th>
                  <th className="p-4 font-semibold text-center hidden sm:table-cell">Momentum</th>
                  <th className="p-4 font-semibold text-right">Volume</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {signals.map((sig) => (
                  <tr key={sig.ticker} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-4">
                      <div className="font-black text-white tracking-widest text-lg flex items-center gap-2">
                        {sig.ticker}
                        <span className={getSentimentColor(sig.composite)}>{getSentimentIcon(sig.composite)}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`px-3 py-1 rounded text-sm font-black tracking-widest border ${getSentimentBg(sig.composite)} ${getSentimentColor(sig.composite)}`}>
                        {sig.composite > 0 ? '+' : ''}{sig.composite.toFixed(2)}
                      </span>
                    </td>
                    <td className="p-4 text-center hidden md:table-cell">
                      <span className={`text-xs font-bold px-2 py-1 rounded ${
                        sig.profitSignal?.includes('BUY') ? 'bg-green-500/20 text-green-400' :
                        sig.profitSignal?.includes('SELL') ? 'bg-red-500/20 text-red-400' :
                        'bg-slate-500/20 text-slate-400'
                      }`}>{sig.profitSignal || 'HOLD'}</span>
                    </td>
                    <td className={`p-4 text-center text-xs hidden sm:table-cell ${
                      sig.momentum === 'accelerating' ? 'text-green-400' :
                      sig.momentum === 'decelerating' ? 'text-red-400' : 'text-slate-400'
                    }`}>{sig.momentum || 'stable'}</td>
                    <td className="p-4 text-right">
                      <span className={`text-xs font-bold ${sig.volume === 'Extreme' ? 'text-orange-400' : sig.volume === 'High' ? 'text-blue-400' : 'text-slate-400'}`}>
                        {(sig.volume || 'NORMAL').toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
                {signals.length === 0 && (
                  <tr><td colSpan={5} className="p-8 text-center text-slate-500">No signals yet - data arrives when agents submit sentiment</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Divergence Alerts */}
        <div className="xl:col-span-1 flex flex-col gap-6">
          <Card className="bg-slate-900/40 border-slate-700/50 backdrop-blur-md p-5">
            <h3 className="font-bold text-white flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              Source Divergence Alerts
            </h3>
            <div className="space-y-3">
              {divergences.length > 0 ? divergences.map((alert, idx) => (
                <div key={idx} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 relative overflow-hidden">
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-yellow-500"></div>
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-black text-white">{alert.ticker}</span>
                    <span className="text-[10px] text-slate-500">Spread: {alert.spread}</span>
                  </div>
                  <p className="text-xs text-slate-300 mb-2 bg-slate-950/50 p-1.5 rounded">{alert.conflict}</p>
                  <div className="text-[10px] font-bold text-yellow-400 uppercase tracking-wider flex items-center gap-1">
                    <Zap className="w-3 h-3" /> {alert.impact}
                  </div>
                </div>
              )) : (
                <div className="text-center text-slate-500 text-sm py-8">
                  <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                  No divergences detected - sources are aligned
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
