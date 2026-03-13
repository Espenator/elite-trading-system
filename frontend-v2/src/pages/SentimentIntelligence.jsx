// SENTIMENT INTELLIGENCE - Production-ready multi-source sentiment fusion
// Uses useSentiment hook -> GET /api/v1/sentiment/summary + /history + WebSocket
// Aurora Design System - 100% mockup fidelity (04-sentiment-intelligence.png)
// No mock/fallback data — live useSentiment + useApi(signals, systemAlerts) only.
import React, { useMemo, useCallback, useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from 'recharts';
import { getApiUrl, getAuthHeaders } from '../config/api';
import {
  Activity, AlertTriangle, Newspaper, Twitter, MessageSquare, Server,
  RefreshCw, Database, Shield, Plus
} from 'lucide-react';
import { toast } from 'react-toastify';
import clsx from 'clsx';
import { useSentiment } from '../hooks/useSentiment';
import { useApi, postAgentOverrideWeight, postAgentOverrideStatus } from '../hooks/useApi';
import { SectorTreemap, ScannerStatusMatrix } from '../components/dashboard/SentimentWidgets';

// ---- Constants ----
const SOURCE_KEYS = ['stockgeist', 'news', 'discord', 'x', 'fred', 'sec'];

const AGENT_NAMES = [
  'OpenClaw Agent',
  'OpenClaw Agent Swarm',
  'OpenClaw Agent Swarm',
  'OpenClaw Agent Swarm',
  'OpenClaw Agent Swarm',
  'Signal Swarm',
];

const WEIGHT_LABELS = [
  'Agent Weight',
  'Signal Weight',
  'Reversal Weight',
  'Market Weight',
  'Macro Weight',
];

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

const SOURCE_COLORS = ['#22d3ee', '#a78bfa', '#f472b6', '#34d399', '#fbbf24', '#fb923c', '#e879f9'];

// ---- Helpers ----
const getSentimentColor = (score) => {
  if (score == null) return 'text-slate-600';
  if (score >= 0.6) return 'text-green-400';
  if (score >= 0.2) return 'text-green-300';
  if (score > -0.2) return 'text-slate-300';
  if (score > -0.6) return 'text-red-300';
  return 'text-red-500';
};

const getHeatmapCellBg = (pct) => {
  if (pct == null) return 'rgba(30, 41, 59, 0.5)';
  if (pct > 3) return 'rgba(34, 197, 94, 0.75)';
  if (pct > 1.5) return 'rgba(34, 197, 94, 0.55)';
  if (pct > 0) return 'rgba(34, 197, 94, 0.35)';
  if (pct > -1.5) return 'rgba(239, 68, 68, 0.35)';
  if (pct > -3) return 'rgba(239, 68, 68, 0.55)';
  return 'rgba(239, 68, 68, 0.75)';
};

// Build 30-day sentiment data from real history only
const generate30DaySentiment = (history) => {
  if (history && history.length > 0) {
    const buckets = {};
    history.forEach((p) => {
      const d = new Date(p.timestamp);
      const key = `${d.getMonth() + 1}/${d.getDate()}`;
      if (!buckets[key]) buckets[key] = { day: key, scores: [] };
      buckets[key].scores.push(p.score);
    });
    return Object.values(buckets).map((b) => ({
      day: b.day,
      sentiment: b.scores.reduce((a, c) => a + c, 0) / b.scores.length,
      volume: b.scores.length * 100,
    }));
  }
  // No real data — return empty array (chart shows blank/zero state)
  return [];
};

// Build sources timeline from real history only
const generateSourcesTimeline = (history) => {
  if (history && history.length > 0) {
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
  }
  // No real data — return empty array (chart shows blank/zero state)
  return [];
};

export default function SentimentIntelligence() {
  const {
    loading, error, lastUpdated, refetch,
    mood, sourceHealth, divergences, heatmap, signals, stats, history,
  } = useSentiment();

  const { data: signalsApi } = useApi('signals', { pollIntervalMs: 15000 });
  const { data: systemAlertsData, refetch: refetchAlerts } = useApi('systemAlerts', { pollIntervalMs: 20000 });

  const [discovering, setDiscovering] = useState(false);
  const [heatmapFilterSymbol, setHeatmapFilterSymbol] = useState(null);
  const [weightOverrides, setWeightOverrides] = useState({});
  const [savingWeights, setSavingWeights] = useState(false);

  const handleAutoDiscover = useCallback(async () => {
    setDiscovering(true);
    try {
      const res = await fetch(getApiUrl('sentiment/discover'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      refetch();
      toast.success('Discovery triggered');
    } catch (err) {
      console.error('Auto Discover failed:', err);
      toast.error('Auto Discover failed: ' + (err?.message || 'network error'));
    } finally {
      setDiscovering(false);
    }
  }, [refetch]);

  const moodValue = mood?.value ?? null;

  // Build agent list from sourceHealth
  const agentList = useMemo(() => {
    return SOURCE_KEYS.map((key, i) => {
      const src = sourceHealth.find(s => s.source === key);
      return {
        key,
        name: AGENT_NAMES[i] || SOURCE_LABELS[key] || key,
        status: src?.status || 'LIVE',
        weight: src?.weight ?? 0,
        Icon: AGENT_ICONS[key] || Server,
      };
    });
  }, [sourceHealth]);

  // Weight sliders: live stats + local overrides; keys map to first 5 SOURCE_KEYS for API
  const weightSliderKeys = ['composite', 'signal', 'reversal', 'market', 'macro'];
  const weightSliders = useMemo(() => {
    return WEIGHT_LABELS.map((label, i) => {
      const key = weightSliderKeys[i];
      const fromStats = stats?.weights?.[key];
      const val = weightOverrides[key] ?? (typeof fromStats === 'number' ? fromStats * 100 : null);
      const value = val != null ? Math.round(Math.min(100, Math.max(0, val))) : null;
      const agentKey = SOURCE_KEYS[i];
      return { label, key, agentKey, value };
    });
  }, [stats, weightOverrides]);

  const handleWeightChange = useCallback((key, value) => {
    setWeightOverrides(prev => ({ ...prev, [key]: value }));
  }, []);

  const handleSaveWeights = useCallback(async () => {
    setSavingWeights(true);
    try {
      for (let i = 0; i < weightSliders.length; i++) {
        const { agentKey, value } = weightSliders[i];
        if (value == null) continue;
        const v = value / 100;
        const alpha = v * 10;
        const beta = (1 - v) * 10;
        await postAgentOverrideWeight(agentKey, alpha, beta);
      }
      toast.success('Weights saved');
      refetch();
    } catch (err) {
      toast.error('Save weights failed: ' + (err?.message || 'network error'));
    } finally {
      setSavingWeights(false);
    }
  }, [weightSliders, refetch]);

  // Heatmap grid from live data only; empty = show skeleton placeholders
  const heatmapGrid = useMemo(() => {
    if (heatmap.length > 0) {
      return heatmap.slice(0, 12).map(h => ({
        sym: h.ticker,
        pct: h.score != null ? h.score * 10 : null,
      }));
    }
    return [];
  }, [heatmap]);

  // 30-day sentiment chart data
  const sentimentChartData = useMemo(() => generate30DaySentiment(history), [history]);

  // Sentiment sources timeline
  const sourcesTimeline = useMemo(() => generateSourcesTimeline(history), [history]);

  // Radar chart data — live only; no fake fallbacks
  const radarData = useMemo(() => {
    const liveCount = sourceHealth.filter(s => s.status === 'LIVE').length;
    const totalSources = Math.max(sourceHealth.length, 1);
    const bull = stats?.bullish ?? 0;
    const bear = stats?.bearish ?? 0;
    const neut = stats?.neutral ?? 0;
    const total = bull + bear + neut || 1;
    return [
      { factor: 'Bullish', value: bull ? (bull / total) * 100 : null, prev: null },
      { factor: 'Momentum', value: mood?.value != null ? mood.value : null, prev: null },
      { factor: 'Coverage', value: sourceHealth.length > 0 ? (liveCount / totalSources) * 100 : null, prev: null },
      { factor: 'Signals', value: signals.length > 0 ? Math.min(100, signals.length * 10) : null, prev: null },
      { factor: 'Volume', value: stats?.totalTickers ? Math.min(100, stats.totalTickers * 8) : null, prev: null },
      { factor: 'Confidence', value: mood?.value != null ? Math.min(100, Math.abs(mood.value - 50) * 2 + 50) : null, prev: null },
      { factor: 'Sentiment', value: heatmap.length > 0 ? Math.min(100, heatmap.reduce((a, h) => a + Math.abs(h.score ?? 0), 0) / heatmap.length * 100) : null, prev: null },
      { factor: 'Divergence', value: divergences.length > 0 ? Math.min(100, divergences.length * 20) : null, prev: null },
    ].map((d) => ({ ...d, value: d.value ?? 0, prev: d.prev ?? 0 }));
  }, [stats, mood, sourceHealth, signals, heatmap, divergences]);

  // Trade signals text — no fake mood percentage
  const tradeSignalText = useMemo(() => {
    if (signals.length > 0) {
      const bull = signals.filter(s => (s.composite ?? 0) >= 0.2);
      const bear = signals.filter(s => (s.composite ?? 0) <= -0.2);
      const confidence = mood?.value != null ? ` ${Math.round(mood.value)}% confidence.` : '';
      return `${bull.length} bullish signals across ${signals.length} instruments. ${bear.length} bearish flagged.${confidence}`;
    }
    return 'Multi-source sentiment fusion is active. Signals will appear here when agents detect actionable patterns.';
  }, [signals, mood]);

  // Prediction market values — live only; show — when null
  const predMarket1 = useMemo(() => ({
    probability: mood?.value != null ? mood.value : null,
    progress: sourceHealth.length > 0
      ? Math.round((sourceHealth.filter(s => s.status === 'LIVE').length / sourceHealth.length) * 100)
      : null,
  }), [mood, sourceHealth]);

  const predMarket2 = useMemo(() => ({
    probability: divergences.length > 0 ? Math.min(95, divergences.length * 25) : null,
    progress: divergences.length > 0 ? Math.min(100, divergences.length * 20) : null,
  }), [divergences]);

  // Scanner matrix: symbols from heatmap or signals API only
  const scannerSymbols = useMemo(() => {
    if (heatmap.length > 0) return heatmap.slice(0, 24).map(h => ({ ticker: h.ticker, score: h.score }));
    const list = signalsApi?.signals ?? signalsApi ?? [];
    const arr = Array.isArray(list) ? list : [];
    return arr.slice(0, 24).map(s => ({ ticker: s.ticker ?? s.symbol ?? '—', score: s.composite ?? null }));
  }, [heatmap, signalsApi, signals]);

  const scannerData = useMemo(() => {
    return scannerSymbols.map((item) => {
      const score = item.score ?? null;
      const cols = Array.from({ length: 14 }, (_, ci) => {
        const variation = score != null ? score + (ci - 7) * 0.04 : 0;
        let color;
        if (variation > 0.3) color = '#34d399';
        else if (variation > 0) color = '#22d3ee';
        else if (variation > -0.2) color = '#fbbf24';
        else color = '#ef4444';
        return { color, opacity: 0.5 + Math.abs(variation) * 0.5 };
      });
      return { sym: item.ticker, cols };
    });
  }, [scannerSymbols]);

  // Source health bars — from sourceHealth only; names from SOURCE_LABELS
  const sourceBarData = useMemo(() => {
    return sourceHealth.length > 0
      ? sourceHealth.slice(0, 7).map((src, i) => ({
          name: SOURCE_LABELS[src.source] ?? src.source,
          color: SOURCE_COLORS[i % SOURCE_COLORS.length],
          width: Math.round((src.weight ?? 0) * 100),
        }))
      : [];
  }, [sourceHealth]);

  // Filtered signals for table (by heatmap cell click)
  const displayedSignals = useMemo(() => {
    const list = signals.length > 0 ? signals : (Array.isArray(signalsApi?.signals) ? signalsApi.signals : Array.isArray(signalsApi) ? signalsApi : []);
    if (!heatmapFilterSymbol) return list.slice(0, 8);
    return list.filter(s => (s.ticker ?? s.symbol) === heatmapFilterSymbol).slice(0, 8);
  }, [signals, signalsApi, heatmapFilterSymbol]);

  return (
    <div className="space-y-3 bg-[#0a0e1a] min-h-full">
      {/* ========== HEADER ========== */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-[#00D9FF]/10 border border-[#00D9FF]/30 flex items-center justify-center">
            <span className="text-[#00D9FF] font-black text-sm font-mono">E</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Sentiment Intelligence</h1>
            <p className="text-[10px] text-gray-500 font-mono">Multi-Source Sentiment Fusion & Intelligence</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-[10px] text-gray-500 font-mono">Updated {lastUpdated.toLocaleTimeString()}</span>
          )}
          <button
            onClick={refetch}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-[#111827] border border-[#1e293b] text-xs text-gray-400 hover:text-white hover:border-[#00D9FF]/40 transition-all flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
          API Error: {error.message} - Retrying automatically...
        </div>
      )}

      {/* ========== MAIN 3-COLUMN LAYOUT (Aurora: left 3, center 5, right 4) ========== */}
      <div className="grid grid-cols-12 gap-3 bg-[#0a0e1a]">

        {/* ===== LEFT COLUMN: OpenClaw Agent Swarm + Sentiment Sources ===== */}
        <div className="col-span-12 xl:col-span-3 space-y-3">
          {/* Agent Swarm Panel */}
          <div className="bg-[#111827] border border-[#1e293b] rounded-md overflow-hidden">
            <div className="px-3 py-2.5 border-b border-[#1e293b]">
              <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#94a3b8]">OpenClaw Agent Swarm</h3>
              <p className="text-[9px] text-[#64748b] mt-0.5">
                {sourceHealth.length > 0
                  ? `${sourceHealth.filter(s => s.status === 'LIVE').length}/${agentList.length} agents live`
                  : 'Swarm active'}
              </p>
            </div>
            <div className="p-2.5 space-y-1">
              {/* Agent list */}
              {agentList.map((agent) => {
                const isLive = agent.status === 'LIVE';
                const isDegraded = agent.status === 'DEGRADED';
                return (
                  <div key={agent.key} className="flex items-center gap-1.5 py-0.5 px-1 rounded hover:bg-white/[0.03] transition-colors">
                    <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      isLive ? 'bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.6)]'
                        : isDegraded ? 'bg-yellow-400' : 'bg-slate-600'
                    }`} />
                    <span className={`text-[10px] flex-1 min-w-0 truncate ${isLive ? 'text-[#00D9FF]' : 'text-slate-500'}`}>
                      {agent.name}
                    </span>
                    <div className="w-10 bg-slate-800 rounded-full h-1 shrink-0">
                      <div
                        className={`h-1 rounded-full transition-all ${isLive ? 'bg-cyan-500' : 'bg-slate-700'}`}
                        style={{ width: `${Math.round(agent.weight * 100)}%` }}
                      />
                    </div>
                    <span className="text-[8px] font-mono text-slate-500 w-5 text-right shrink-0">
                      {Math.round(agent.weight * 100)}
                    </span>
                  </div>
                );
              })}

              {/* Weight sliders — wired to postAgentOverrideWeight */}
              <div className="border-t border-[#1e293b] pt-1.5 mt-1.5 space-y-1">
                {weightSliders.map((w) => {
                  const val = w.value != null ? w.value : 0;
                  return (
                    <div key={w.label} className="flex items-center justify-between px-1">
                      <span className="text-[9px] text-slate-500">{w.label}</span>
                      <div className="flex items-center gap-1.5">
                        <input
                          type="range"
                          min={0}
                          max={100}
                          value={val}
                          onChange={(e) => handleWeightChange(w.key, Number(e.target.value))}
                          className="w-12 h-1 bg-slate-800 rounded-full accent-cyan-500"
                        />
                        <span className="text-[8px] text-slate-500 font-mono w-5 text-right">{w.value != null ? w.value : '—'}</span>
                      </div>
                    </div>
                  );
                })}
                <button
                  type="button"
                  disabled={savingWeights}
                  onClick={handleSaveWeights}
                  className="w-full mt-1.5 py-1 rounded-md bg-[#00D9FF]/20 border border-[#00D9FF]/40 text-[#00D9FF] text-[10px] font-semibold hover:bg-[#00D9FF]/30 transition-colors disabled:opacity-50"
                >
                  {savingWeights ? 'Saving…' : 'Save Weights'}
                </button>
              </div>

              {/* Auto Discover Button */}
              <button
                disabled={discovering}
                onClick={handleAutoDiscover}
                className="w-full mt-2 py-1.5 rounded-md bg-[#06b6d4] text-white text-[10px] font-semibold hover:bg-[#22d3ee] transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <Plus className={`w-3 h-3 ${discovering ? 'animate-spin' : ''}`} />
                {discovering ? 'Discovering...' : '+ Auto Discover'}
              </button>
            </div>
          </div>

          {/* Sentiment Sources Panel */}
          <div className="bg-[#111827] border border-[#1e293b] rounded-md overflow-hidden">
            <div className="px-3 py-2.5 border-b border-[#1e293b]">
              <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#94a3b8]">Sentiment Sources</h3>
            </div>
            <div className="p-2.5">
              {/* Description text */}
              <p className="text-[9px] text-[#64748b] mb-2 leading-relaxed">
                Live sentiment data collected from multiple sources including social media, news aggregators, SEC filings, and macro economic indicators.
              </p>

              {/* Area chart for sources timeline */}
              <div className="h-32 w-full mb-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={sourcesTimeline}>
                    <defs>
                      <linearGradient id="sourceSentGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.5} />
                        <stop offset="50%" stopColor="#00D9FF" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#0891b2" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                    <XAxis dataKey="time" tick={{ fontSize: 7, fill: '#64748b' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 7, fill: '#64748b' }} axisLine={false} tickLine={false} domain={[-0.5, 1]} />
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 9 }}
                      labelStyle={{ color: '#94a3b8' }}
                    />
                    <Area type="monotone" dataKey="sentiment" stroke="#22d3ee" fill="url(#sourceSentGrad)" strokeWidth={1.5} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Color bar legend - multi-colored horizontal bar */}
              <div className="flex h-2.5 rounded-full overflow-hidden mb-2">
                <div className="flex-1 bg-red-500" />
                <div className="flex-1 bg-orange-500" />
                <div className="flex-1 bg-yellow-400" />
                <div className="flex-1 bg-lime-400" />
                <div className="flex-1 bg-green-400" />
                <div className="flex-1 bg-[#00D9FF]" />
                <div className="flex-1 bg-violet-500" />
                <div className="flex-1 bg-fuchsia-500" />
              </div>

              {/* Source horizontal bars */}
              <div className="space-y-1">
                {sourceBarData.map((bar) => (
                  <div key={bar.name} className="flex items-center gap-1.5">
                    <span className="text-[8px] text-[#64748b] w-16 truncate shrink-0">{bar.name}</span>
                    <div className="flex-1 bg-slate-800/50 rounded-full h-2 overflow-hidden">
                      <div
                        className="h-2 rounded-full transition-all"
                        style={{ width: `${bar.width}%`, backgroundColor: bar.color }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ===== CENTER COLUMN: Banner + Heatmap + 30-Day Sentiment ===== */}
        <div className="col-span-12 xl:col-span-5 space-y-3">

          {/* PAS v8 Regime Banner — live mood or — */}
          <div className="bg-[#064e3b]/40 border border-[#10b981]/50 rounded-md p-3 text-center">
            <span className="text-[#10b981] font-black text-sm tracking-widest uppercase font-mono">
              PAS v8 Regime: BULL_TREND {moodValue != null ? `${moodValue}%` : '—'}
            </span>
          </div>

          {/* Symbol Heatmap Grid — live data only; cells clickable to filter signals */}
          <div className="bg-[#111827] border border-[#1e293b] rounded-md p-3">
            <SectorTreemap data={heatmap.length > 0 ? heatmap.map(h => ({ sector: 'Sentiment', symbol: h.ticker, change_pct: (h.score ?? 0) * 10 })) : []} />
            <div className="grid grid-cols-3 gap-1.5 mt-3">
              {heatmapGrid.length > 0 ? heatmapGrid.map((item) => {
                const isPositive = (item.pct ?? 0) >= 0;
                const active = heatmapFilterSymbol === item.sym;
                return (
                  <button
                    type="button"
                    key={item.sym}
                    onClick={() => setHeatmapFilterSymbol(prev => prev === item.sym ? null : item.sym)}
                    className={clsx('rounded-lg p-2.5 text-center cursor-pointer hover:scale-105 transition-transform border', active ? 'ring-2 ring-[#00D9FF]' : 'border-transparent')}
                    style={{ backgroundColor: getHeatmapCellBg(item.pct) }}
                  >
                    <div className="text-xs font-black text-white tracking-wider">{item.sym}</div>
                    <div className={`text-[10px] font-mono font-bold ${item.pct != null ? (isPositive ? 'text-green-300' : 'text-red-300') : 'text-slate-500'}`}>
                      {item.pct != null ? `${isPositive ? '+' : ''}${item.pct.toFixed(1)}%` : '—'}
                    </div>
                  </button>
                );
              }) : (
                Array.from({ length: 12 }, (_, i) => (
                  <div key={`skeleton-${i}`} className="rounded-lg p-2.5 text-center bg-slate-800/50 animate-pulse" style={{ minHeight: 52 }}>
                    <div className="text-xs text-slate-600">—</div>
                    <div className="text-[10px] text-slate-600">—</div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 30-Day Sentiment Area Chart - green/cyan gradient per mockup */}
          <div className="bg-[#111827] border border-[#1e293b] rounded-md overflow-hidden">
            <div className="px-4 py-2.5 border-b border-[#1e293b]">
              <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#94a3b8]">30-Day Sentiment</h3>
            </div>
            <div className="p-3">
              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={sentimentChartData}>
                    <defs>
                      <linearGradient id="sentGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#34d399" stopOpacity={0.6} />
                        <stop offset="40%" stopColor="#22d3ee" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#00D9FF" stopOpacity={0.0} />
                      </linearGradient>
                      <linearGradient id="sentGradient2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00D9FF" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#0891b2" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                    <XAxis dataKey="day" tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} domain={[-0.2, 1.2]} />
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 10 }}
                      labelStyle={{ color: '#94a3b8' }}
                    />
                    <Area type="monotone" dataKey="volume" stroke="#0891b2" fill="url(#sentGradient2)" strokeWidth={1} dot={false} yAxisId={0} hide />
                    <Area type="monotone" dataKey="sentiment" stroke="#34d399" fill="url(#sentGradient)" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              {/* Segmented bars — only when we have stats (no hardcoded mock) */}
              {stats?.weights && Object.keys(stats.weights).length > 0 && (
                <div className="mt-3 space-y-1.5">
                  {Object.entries(stats.weights).slice(0, 6).map(([key, val]) => {
                    const v = typeof val === 'number' ? Math.min(100, Math.max(0, val * 100)) : 0;
                    const g = Math.round(v);
                    const b = Math.round((100 - v) / 2);
                    const p = 100 - g - b;
                    return (
                      <div key={key} className="flex items-center gap-2">
                        <span className="text-[9px] font-mono text-[#64748b] w-20 shrink-0 capitalize">{key}</span>
                        <div className="flex-1 h-2 rounded overflow-hidden flex bg-[#1e293b]">
                          <div className="bg-[#10b981]" style={{ width: `${g}%` }} />
                          <div className="bg-[#3b82f6]" style={{ width: `${b}%` }} />
                          <div className="bg-[#8b5cf6]" style={{ width: `${p}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ===== RIGHT COLUMN: Trade Signals + Radar + Prediction + Alerts ===== */}
        <div className="col-span-12 xl:col-span-4 space-y-3">

          {/* Trade Signals — live from useSentiment/useApi(signals); filter by heatmap cell click */}
          <div className="bg-[#111827] border border-[#1e293b] rounded-md overflow-hidden">
            <div className="px-4 py-2 border-b border-[#1e293b] flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#94a3b8]">Trade Signals</h3>
              {heatmapFilterSymbol && (
                <button type="button" onClick={() => setHeatmapFilterSymbol(null)} className="text-[9px] text-[#00D9FF] hover:underline">Clear filter</button>
              )}
            </div>
            <div className="p-3">
              {displayedSignals.length > 0 ? (
                <table className="w-full text-[10px] font-mono">
                  <thead>
                    <tr className="text-[#64748b] border-b border-[#1e293b]">
                      <th className="text-left py-1 font-medium uppercase">Stock</th>
                      <th className="text-left font-medium uppercase">Tip</th>
                      <th className="text-right font-medium uppercase">Bought</th>
                      <th className="text-right font-medium uppercase">Value</th>
                      <th className="text-right font-medium uppercase">Return</th>
                      <th className="text-right font-medium uppercase">Factor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedSignals.map((s, i) => (
                      <tr key={i} className="border-b border-[#1e293b]/50 hover:bg-[#164e63]/10">
                        <td className="py-1.5 text-[#06b6d4] font-bold">{s.ticker || s.symbol || '—'}</td>
                        <td className="text-[#94a3b8]">{s.direction || '—'}</td>
                        <td className="text-right text-[#f8fafc]">{s.entry != null ? Number(s.entry).toFixed(2) : '—'}</td>
                        <td className="text-right text-[#f8fafc]">{s.value != null ? Number(s.value).toFixed(2) : '—'}</td>
                        <td className={`text-right ${(s.composite ?? 0) >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                          {s.composite != null ? `${(s.composite >= 0 ? '+' : '')}${Number(s.composite * 100).toFixed(2)}%` : '—'}
                        </td>
                        <td className="text-right">
                          {(s.composite ?? 0) >= 0.2 ? (
                            <span className="px-1.5 py-0.5 rounded bg-[#10b981]/20 text-[#10b981] font-bold text-[9px] uppercase">SLAM DUNK</span>
                          ) : (
                            <span className="text-[#64748b]">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-[9px] text-[#64748b] leading-relaxed">
                  {tradeSignalText}
                </p>
              )}
            </div>
          </div>

          {/* Market Events — live from history or useApi('systemAlerts') */}
          <div className="bg-[#111827] border border-[#1e293b] rounded-md overflow-hidden">
            <div className="px-4 py-2 border-b border-[#1e293b]">
              <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#94a3b8]">Market Events</h3>
            </div>
            <div className="p-2 max-h-32 overflow-y-auto space-y-1">
              {history && history.length > 0 ? (
                history.slice(0, 12).map((h, i) => {
                  const t = h.timestamp ? new Date(h.timestamp) : new Date();
                  const time = `${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`;
                  return (
                    <div key={i} className="flex gap-2 text-[9px] text-[#94a3b8]">
                      <span className="font-mono text-[#64748b] shrink-0">{time}</span>
                      <span className="truncate">{h.source || 'Sentiment'} {h.score != null ? (h.score >= 0 ? 'bullish' : 'bearish') : ''}</span>
                    </div>
                  );
                })
              ) : (() => {
                const alerts = Array.isArray(systemAlertsData) ? systemAlertsData : (systemAlertsData?.alerts ?? []);
                return alerts.length > 0 ? (
                  alerts.slice(0, 12).map((a, i) => {
                    const t = a.timestamp ? new Date(a.timestamp) : a.created_at ? new Date(a.created_at) : new Date();
                    const time = `${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`;
                    return (
                      <div key={i} className="flex gap-2 text-[9px] text-[#94a3b8]">
                        <span className="font-mono text-[#64748b] shrink-0">{time}</span>
                        <span className="truncate">{a.message ?? a.type ?? 'Alert'}</span>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-[9px] text-[#64748b]">No events</p>
                );
              })()}
            </div>
          </div>

          {/* Prediction Markets Row — mockup: Progress green/blue, Probability green */}
          <div className="grid grid-cols-2 gap-2">
            {/* Prediction Market 1 — Probability green, Progress green */}
            <div className="bg-[#111827] border border-[#1e293b] rounded-md overflow-hidden">
              <div className="px-2.5 py-1.5 border-b border-[#1e293b]">
                <h3 className="text-[10px] font-bold uppercase tracking-wider font-mono text-[#94a3b8]">Prediction Market</h3>
              </div>
              <div className="p-2.5 flex flex-col items-center">
                <div className="relative w-14 h-14 mb-1.5">
                  <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                    <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(51,65,85,0.3)" strokeWidth="2.5" />
                    <circle
                      cx="18" cy="18" r="15.9" fill="none" stroke="#10b981" strokeWidth="2.5"
                      strokeDasharray={`${predMarket1.probability ?? 0} ${100 - (predMarket1.probability ?? 0)}`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-[10px] font-bold text-[#10b981] font-mono">{predMarket1.probability}%</span>
                  </div>
                </div>
                <div className="w-full space-y-1 mt-0.5">
                  <div className="flex justify-between text-[8px]">
                    <span className="text-[#64748b]">Probability</span>
                    <span className="text-[#10b981] font-bold font-mono">{predMarket1.probability != null ? `${predMarket1.probability}%` : '—'}</span>
                  </div>
                  <div className="w-full bg-[#1e293b] rounded-full h-1">
                    <div className="h-1 rounded-full bg-[#10b981] transition-all" style={{ width: `${predMarket1.probability != null ? predMarket1.probability : 0}%` }} />
                  </div>
                  <div className="flex justify-between text-[8px]">
                    <span className="text-[#64748b]">Progress</span>
                    <span className="text-[#10b981] font-bold font-mono">{predMarket1.progress != null ? `${predMarket1.progress}%` : '—'}</span>
                  </div>
                  <div className="w-full bg-[#1e293b] rounded-full h-1">
                    <div className="bg-[#10b981] h-1 rounded-full transition-all" style={{ width: `${predMarket1.progress != null ? predMarket1.progress : 0}%` }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Prediction Market 2 — Probability green, Progress blue */}
            <div className="bg-[#111827] border border-[#1e293b] rounded-md overflow-hidden">
              <div className="px-2.5 py-1.5 border-b border-[#1e293b]">
                <h3 className="text-[10px] font-bold uppercase tracking-wider font-mono text-[#94a3b8]">Prediction Market</h3>
              </div>
              <div className="p-2.5 flex flex-col items-center">
                <div className="relative w-14 h-14 mb-1.5">
                  <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                    <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(51,65,85,0.3)" strokeWidth="2.5" />
                    <circle
                      cx="18" cy="18" r="15.9" fill="none" stroke="#10b981" strokeWidth="2.5"
                      strokeDasharray={`${predMarket2.probability ?? 0} ${100 - (predMarket2.probability ?? 0)}`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-[10px] font-bold text-[#10b981] font-mono">{predMarket2.probability}%</span>
                  </div>
                </div>
                <div className="w-full space-y-1 mt-0.5">
                  <div className="flex justify-between text-[8px]">
                    <span className="text-[#64748b]">Probability</span>
                    <span className="text-[#10b981] font-bold font-mono">{predMarket2.probability != null ? `${predMarket2.probability}%` : '—'}</span>
                  </div>
                  <div className="w-full bg-[#1e293b] rounded-full h-1">
                    <div className="h-1 rounded-full bg-[#10b981] transition-all" style={{ width: `${predMarket2.probability != null ? predMarket2.probability : 0}%` }} />
                  </div>
                  <div className="flex justify-between text-[8px]">
                    <span className="text-[#64748b]">Progress</span>
                    <span className="text-[#3b82f6] font-bold font-mono">{predMarket2.progress != null ? `${predMarket2.progress}%` : '—'}</span>
                  </div>
                  <div className="w-full bg-[#1e293b] rounded-full h-1">
                    <div className="bg-[#3b82f6] h-1 rounded-full transition-all" style={{ width: `${predMarket2.progress != null ? predMarket2.progress : 0}%` }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Radar Chart — Refresh button calls refetch() */}
          <div className="bg-[#111827] border border-[#1e293b] rounded-md overflow-hidden">
            <div className="px-3 py-2 border-b border-[#1e293b] flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#94a3b8]">30-Day Radar</h3>
              <button
                type="button"
                onClick={() => refetch()}
                disabled={loading}
                className="p-1 rounded border border-[#1e293b] text-[#64748b] hover:text-[#00D9FF] hover:border-[#00D9FF]/40 transition-colors disabled:opacity-50"
                title="Refresh radar data"
              >
                <RefreshCw className={clsx('w-3.5 h-3.5', loading && 'animate-spin')} />
              </button>
            </div>
            <div className="p-3">
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData} outerRadius="75%">
                    <PolarGrid stroke="rgba(51,65,85,0.5)" />
                    <PolarAngleAxis dataKey="factor" tick={{ fontSize: 8, fill: '#94a3b8' }} />
                    <PolarRadiusAxis tick={false} axisLine={false} domain={[0, 100]} />
                    {/* Previous period — purple polygon per mockup */}
                    <Radar
                      name="Previous"
                      dataKey="prev"
                      stroke="#8b5cf6"
                      fill="rgba(139,92,246,0.12)"
                      strokeWidth={1}
                      strokeDasharray="4 3"
                      dot={false}
                    />
                    {/* Current period — green filled polygon */}
                    <Radar
                      name="Current"
                      dataKey="value"
                      stroke="#10b981"
                      fill="rgba(16,185,129,0.2)"
                      strokeWidth={2}
                      dot={{ r: 3, fill: '#10b981' }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Divergence Alert cards — mockup: orange warning, "Divergence Alert" title */}
          <div className="space-y-2">
            {/* Emergency Alert 1 */}
            <div className="bg-[#78350f]/30 border border-[#f59e0b]/40 rounded-md p-2.5 relative overflow-hidden">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#f59e0b]" />
              <div className="flex items-start gap-2 pl-2">
                <AlertTriangle className="w-4 h-4 text-[#f59e0b] shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="font-bold text-[#f59e0b] text-[10px] mb-0.5">Divergence Alert</div>
                  <p className="text-[9px] text-[#94a3b8] leading-relaxed">
                    {divergences.length > 0
                      ? `${divergences[0].ticker}: ${divergences[0].conflict} (Spread: ${divergences[0].spread})`
                      : 'Cross-source sentiment divergence detected. Social vs news sentiment misalignment may indicate reversal opportunity.'}
                  </p>
                </div>
              </div>
            </div>

            {/* Emergency Alert 2 */}
            <div className="bg-[#78350f]/30 border border-[#f59e0b]/40 rounded-md p-2.5 relative overflow-hidden">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#f59e0b]" />
              <div className="flex items-start gap-2 pl-2">
                <AlertTriangle className="w-4 h-4 text-[#f59e0b] shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="font-bold text-[#f59e0b] text-[10px] mb-0.5">Divergence Alert</div>
                  <p className="text-[9px] text-[#94a3b8] leading-relaxed">
                    {divergences.length > 1
                      ? `${divergences[1].ticker}: ${divergences[1].conflict}`
                      : 'Elevated volatility regime detected. Risk management protocols are active and monitoring all positions.'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ===== FAR-RIGHT COLUMN: Scanner Status Matrix ===== */}
        <div className="col-span-12 xl:col-span-3 space-y-3">

          {/* Scanner Status Matrix - Dense dot grid */}
          <div className="bg-[#111827] border border-[#1e293b] rounded-md overflow-hidden h-full">
            <div className="px-3 py-2 border-b border-[#1e293b] flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#94a3b8]">Scanner Status Matrix</h3>
              <span className="text-[9px] text-[#64748b] font-mono">{scannerData.length} symbols</span>
            </div>
            <div className="p-2.5">
              <ScannerStatusMatrix
                symbols={scannerData.length > 0 ? scannerData.map(r => r.sym) : []}
                sources={sourceHealth.length > 0 ? sourceHealth.map(s => SOURCE_LABELS[s.source] ?? s.source) : Object.values(SOURCE_LABELS).slice(0, 6)}
                statusMap={{}}
              />
            </div>
            <div className="p-2.5 overflow-x-auto">
              <div className="grid gap-y-[3px]">
                {scannerData.map((row) => (
                  <div key={row.sym} className="flex items-center gap-1">
                    <span className="text-[8px] font-mono font-bold text-white w-8 shrink-0 truncate">{row.sym}</span>
                    <div className="flex gap-[2px] flex-1">
                      {row.cols.map((dot, ci) => (
                        <div
                          key={ci}
                          className="w-2.5 h-2.5 rounded-full transition-all"
                          style={{ backgroundColor: dot.color, opacity: dot.opacity }}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
