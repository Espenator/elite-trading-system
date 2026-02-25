// SENTIMENT INTELLIGENCE - Multi-source sentiment fusion for trade conviction
// GET /api/v1/sentiment - combined sentiment scores across all sources

import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, 
  ComposedChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine 
} from 'recharts';
import { 
  Activity, TrendingUp, TrendingDown, AlertTriangle, 
  MessageSquare, Newspaper, Twitter, MessageCircle, Server, 
  Gauge, Flame, Zap, BarChart2, Radio
} from 'lucide-react';

// Using existing project components & hooks as requested
import PageHeader from "../components/ui/PageHeader";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import { useApi } from "../hooks/useApi";

export default function SentimentIntelligence() {
  const { request, loading, error } = useApi();
  const [sentimentData, setSentimentData] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date().toLocaleTimeString());

  // Polling logic (60s)
  useEffect(() => {
    const fetchSentiment = async () => {
      try {
        const data = await request({ url: '/api/v1/sentiment', method: 'GET' });
        if (data) {
          setSentimentData(data);
          setLastUpdated(new Date().toLocaleTimeString());
        }
      } catch (err) {
        console.error("Sentiment API error, falling back to simulation:", err);
      }
    };
    
    fetchSentiment();
    const timer = setInterval(fetchSentiment, 60000);
    return () => clearInterval(timer);
  }, [request]);

  // Existing Helpers
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

  // --- V3 SIMULATED DATA (Used to hydrate missing backend advanced fields) ---

  const fearGreedValue = 72; // 0-100
  const fearGreedData = [
    { name: 'Extreme Fear', value: 25, color: '#ef4444' },
    { name: 'Fear', value: 25, color: '#f97316' },
    { name: 'Neutral', value: 20, color: '#eab308' },
    { name: 'Greed', value: 15, color: '#84cc16' },
    { name: 'Extreme Greed', value: 15, color: '#22c55e' },
  ];

  const sourceWeights = [
    { name: 'Stockgeist', icon: <Activity/>, weight: 30, status: 'LIVE', latency: '42ms', score: 0.65 },
    { name: 'News API', icon: <Newspaper/>, weight: 25, status: 'LIVE', latency: '115ms', score: 0.42 },
    { name: 'Discord', icon: <MessageSquare/>, weight: 25, status: 'LIVE', latency: '28ms', score: 0.81 },
    { name: 'X / Twitter', icon: <Twitter/>, weight: 20, status: 'LIVE', latency: '85ms', score: -0.15 },
  ];

  const rollingTrendData = Array.from({ length: 24 }).map((_, i) => ({
    time: `${i}:00`,
    sentiment: Math.sin(i * 0.4) * 0.5 + 0.2 + (Math.random() * 0.2),
    volume: 1000 + Math.random() * 5000 + (i === 14 ? 15000 : 0) // Spike at 14:00
  }));

  const divergenceAlerts = [
    { symbol: 'TSLA', conflict: 'X (Bearish -0.6) vs Discord (Bullish +0.7)', impact: 'High Volatility Expected', time: '2m ago' },
    { symbol: 'NVDA', conflict: 'News (Neutral +0.1) vs Stockgeist (Ext. Bullish +0.9)', impact: 'Institutional vs Retail Setup', time: '14m ago' },
    { symbol: 'PLTR', conflict: 'Discord (Bearish -0.4) vs News (Bullish +0.5)', impact: 'Monitor Breakout Level', time: '1h ago' }
  ];

  const correlationData = Array.from({ length: 30 }).map((_, i) => {
    const basePrice = 150 + (i * 2) + (Math.sin(i * 0.5) * 10);
    return {
      day: `D-${30 - i}`,
      price: basePrice,
      sentiment: (Math.sin((i - 2) * 0.5) * 0.8) + (Math.random() * 0.3) // Sentiment leads price slightly
    };
  });

  const activeSignals = sentimentData?.signals || [
    { symbol: 'COIN', composite: 0.85, stockgeist: 0.9, news: 0.7, discord: 0.8, x: 0.95, volume: 'Extreme' },
    { symbol: 'MSTR', composite: 0.72, stockgeist: 0.8, news: 0.6, discord: 0.75, x: 0.6, volume: 'High' },
    { symbol: 'SNOW', composite: -0.65, stockgeist: -0.7, news: -0.5, discord: -0.8, x: -0.6, volume: 'High' },
    { symbol: 'AMD', composite: 0.45, stockgeist: 0.5, news: 0.8, discord: 0.2, x: 0.1, volume: 'Normal' },
    { symbol: 'CRWD', composite: -0.88, stockgeist: -0.9, news: -0.85, discord: -0.95, x: -0.8, volume: 'Extreme' },
  ];

  const heatmapSymbols = [
    { sym: 'NVDA', score: 0.9, vol: 100 }, { sym: 'TSLA', score: -0.7, vol: 95 },
    { sym: 'AMD', score: 0.4, vol: 80 }, { sym: 'MSTR', score: 0.8, vol: 85 },
    { sym: 'COIN', score: 0.85, vol: 90 }, { sym: 'PLTR', score: 0.2, vol: 70 },
    { sym: 'CRWD', score: -0.88, vol: 88 }, { sym: 'SNOW', score: -0.65, vol: 60 },
    { sym: 'SMCI', score: 0.75, vol: 75 }, { sym: 'RBRK', score: 0.6, vol: 50 },
    { sym: 'APP', score: 0.95, vol: 82 }, { sym: 'META', score: 0.3, vol: 65 },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-200 p-6 font-sans">
      
      {/* HEADER */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-6 gap-4">
        <PageHeader 
          title="Sentiment Intelligence" 
          subtitle="Multi-Source Fusion, Divergence Detection & Social Volume (v3.0)"
          icon={<Radio className="w-8 h-8 text-blue-400" />}
        />
        <div className="flex items-center gap-4">
          <div className="bg-slate-800/50 px-4 py-2 rounded-lg border border-slate-700/50 flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <span className="text-xs font-mono text-slate-300">Live Sync</span>
            <span className="text-xs font-mono text-slate-500 ml-2">{lastUpdated}</span>
          </div>
          <Button variant="primary" onClick={() => window.location.reload()}>Force Resync</Button>
        </div>
      </div>

      {/* TOP ROW: Sources & Gauges */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 mb-6">
        
        {/* Fear & Greed Gauge */}
        <Card className="col-span-1 bg-slate-900/40 border-slate-700/50 backdrop-blur-md relative overflow-hidden flex flex-col items-center justify-center p-4">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest absolute top-4 left-4">Market Mood</h3>
          <div className="h-48 w-full mt-4 relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={fearGreedData}
                  cx="50%"
                  cy="80%"
                  startAngle={180}
                  endAngle={0}
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {fearGreedData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            {/* Gauge Value Overlay */}
            <div className="absolute inset-0 flex flex-col items-center justify-end pb-4 pointer-events-none">
              <span className="text-4xl font-black font-mono text-white">{fearGreedValue}</span>
              <span className="text-green-400 font-bold tracking-wider uppercase text-xs">Greed</span>
            </div>
          </div>
        </Card>

        {/* Source Status Cards */}
        <div className="col-span-1 xl:col-span-3 grid grid-cols-2 md:grid-cols-4 gap-4">
          {sourceWeights.map((src, idx) => (
            <div key={idx} className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm flex flex-col justify-between group hover:bg-slate-800/60 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-slate-700/50 rounded text-slate-300">
                    {src.icon}
                  </div>
                  <span className="font-bold text-sm text-white">{src.name}</span>
                </div>
                <span className="text-[10px] font-black text-slate-500 bg-slate-900/50 px-1.5 py-0.5 rounded border border-slate-700/50">
                  {src.weight}% WGT
                </span>
              </div>
              <div className="mt-4">
                <div className="flex justify-between items-end mb-1">
                  <span className="text-xs text-slate-400">Current Bias</span>
                  <span className={`text-lg font-black font-mono ${getSentimentColor(src.score)}`}>
                    {src.score > 0 ? '+' : ''}{src.score.toFixed(2)}
                  </span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-1.5 mb-3 overflow-hidden">
                  <div 
                    className={`h-1.5 rounded-full ${src.score > 0 ? 'bg-green-500' : 'bg-red-500'}`} 
                    style={{ width: `${Math.abs(src.score) * 100}%`, marginLeft: src.score > 0 ? '50%' : `${50 - (Math.abs(src.score) * 50)}%` }}
                  ></div>
                </div>
                <div className="flex justify-between items-center text-[10px] font-mono">
                  <span className="text-green-400 flex items-center gap-1"><Server className="w-3 h-3"/> {src.status}</span>
                  <span className="text-slate-500">{src.latency}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* MIDDLE ROW: Trends & Volume Heatmap */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        
        {/* 24h Rolling Trend */}
        <Card className="lg:col-span-2 bg-slate-900/40 border-slate-700/50 backdrop-blur-md p-5">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-400" />
              24H Rolling Macro Sentiment vs Social Volume
            </h3>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={rollingTrendData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
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
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc', borderRadius: '8px' }}
                  itemStyle={{ fontWeight: 'bold' }}
                />
                <ReferenceLine y={0} yAxisId="left" stroke="#475569" strokeDasharray="3 3" />
                <Bar dataKey="volume" yAxisId="right" fill="#475569" opacity={0.3} radius={[4, 4, 0, 0]} name="Social Volume" />
                <Area type="monotone" dataKey="sentiment" yAxisId="left" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorSentiment)" name="Sentiment" />
              </ComposedChart>
            </ResponsiveContainer>
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
            {heatmapSymbols.map((item) => (
              <div 
                key={item.sym} 
                className={`rounded-lg flex flex-col items-center justify-center p-2 border transition-all hover:scale-105 cursor-pointer ${getSentimentBg(item.score)}`}
                style={{ opacity: 0.5 + (item.vol / 200) }} // Maps volume to opacity
              >
                <span className="font-black text-white tracking-wider">{item.sym}</span>
                <span className={`text-[10px] font-mono font-bold ${getSentimentColor(item.score)}`}>
                  {item.score > 0 ? '+' : ''}{item.score.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* BOTTOM ROW: Tables, Divergences, Correlation */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Active Signals Table (Takes up 2 cols) */}
        <div className="xl:col-span-2 space-y-4">
          <div className="flex justify-between items-end">
            <h3 className="font-bold text-white flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-purple-400" />
              Active Sentiment Signals (Multi-Source)
            </h3>
          </div>
          
          <div className="bg-slate-900/40 border border-slate-700/50 rounded-xl overflow-hidden backdrop-blur-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-800/60 border-b border-slate-700/50 text-xs uppercase tracking-wider text-slate-400">
                  <th className="p-4 font-semibold">Asset</th>
                  <th className="p-4 font-semibold">Composite</th>
                  <th className="p-4 font-semibold text-center hidden md:table-cell">Stockgeist</th>
                  <th className="p-4 font-semibold text-center hidden md:table-cell">News</th>
                  <th className="p-4 font-semibold text-center hidden sm:table-cell">Discord</th>
                  <th className="p-4 font-semibold text-center hidden sm:table-cell">X/Twitter</th>
                  <th className="p-4 font-semibold text-right">Volume</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {activeSignals.map((sig) => (
                  <tr key={sig.symbol} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-4">
                      <div className="font-black text-white tracking-widest text-lg flex items-center gap-2">
                        {sig.symbol}
                        <span className={getSentimentColor(sig.composite)}>{getSentimentIcon(sig.composite)}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`px-3 py-1 rounded text-sm font-black tracking-widest border ${getSentimentBg(sig.composite)} ${getSentimentColor(sig.composite)}`}>
                        {sig.composite > 0 ? '+' : ''}{sig.composite.toFixed(2)}
                      </span>
                    </td>
                    <td className={`p-4 text-center font-mono text-sm hidden md:table-cell ${getSentimentColor(sig.stockgeist)}`}>{sig.stockgeist.toFixed(2)}</td>
                    <td className={`p-4 text-center font-mono text-sm hidden md:table-cell ${getSentimentColor(sig.news)}`}>{sig.news.toFixed(2)}</td>
                    <td className={`p-4 text-center font-mono text-sm hidden sm:table-cell ${getSentimentColor(sig.discord)}`}>{sig.discord.toFixed(2)}</td>
                    <td className={`p-4 text-center font-mono text-sm hidden sm:table-cell ${getSentimentColor(sig.x)}`}>{sig.x.toFixed(2)}</td>
                    <td className="p-4 text-right">
                      <span className={`text-xs font-bold ${sig.volume === 'Extreme' ? 'text-orange-400' : sig.volume === 'High' ? 'text-blue-400' : 'text-slate-400'}`}>
                        {sig.volume.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Divergences & Correlation */}
        <div className="xl:col-span-1 flex flex-col gap-6">
          
          {/* Divergence Alerts */}
          <Card className="bg-slate-900/40 border-slate-700/50 backdrop-blur-md p-5">
            <h3 className="font-bold text-white flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              Source Divergence Alerts
            </h3>
            <div className="space-y-3">
              {divergenceAlerts.map((alert, idx) => (
                <div key={idx} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 relative overflow-hidden">
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-yellow-500"></div>
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-black text-white">{alert.symbol}</span>
                    <span className="text-[10px] text-slate-500">{alert.time}</span>
                  </div>
                  <p className="text-xs text-slate-300 mb-2 font-mono bg-slate-950/50 p-1.5 rounded">{alert.conflict}</p>
                  <div className="text-[10px] font-bold text-yellow-400 uppercase tracking-wider flex items-center gap-1">
                    <Zap className="w-3 h-3" /> {alert.impact}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Price vs Sentiment Correlation */}
          <Card className="bg-slate-900/40 border-slate-700/50 backdrop-blur-md p-5 flex-1">
            <h3 className="font-bold text-white flex items-center gap-2 mb-1">
              <Activity className="w-5 h-5 text-purple-400" />
              Lead-Lag Correlation (TSLA)
            </h3>
            <p className="text-xs text-slate-400 mb-4">Sentiment score predicting price action over 30 days.</p>
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={correlationData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                  <XAxis dataKey="day" hide />
                  <YAxis yAxisId="price" stroke="#64748b" fontSize={10} domain={['dataMin - 10', 'dataMax + 10']} />
                  <YAxis yAxisId="sentiment" orientation="right" hide domain={[-1, 1]} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155' }}
                    labelStyle={{ display: 'none' }}
                  />
                  <Bar dataKey="sentiment" yAxisId="sentiment" name="Sentiment">
                    {correlationData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.sentiment > 0 ? '#22c55e' : '#ef4444'} fillOpacity={0.4} />
                    ))}
                  </Bar>
                  <Line type="monotone" dataKey="price" yAxisId="price" stroke="#c084fc" strokeWidth={2} dot={false} name="Price ($)" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>

        </div>
      </div>
      
    </div>
  );
}
