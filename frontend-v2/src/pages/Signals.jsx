// SIGNAL INTELLIGENCE CENTER - Embodier.ai Glass Box Signal Command
// OLEH: Deep composite scoring breakdown, scrollable signal history,
//       manual signal override, futuristic spaceship aesthetic
// Backend: GET /api/v1/signals, POST /api/v1/signals/:id/override
// WebSocket: 'signals' channel for real-time signal stream

import { useState, useEffect, useCallback } from 'react';
import { getApiUrl } from '../config/api';

// ============================================================
// GLASSMORPHISM PANEL - Futuristic collapsible panel
// ============================================================
function GlassPanel({ title, icon, collapsed, onToggle, maxHeight = '500px', children, badge, headerActions, glowColor = 'cyan' }) {
  const glowMap = { cyan: 'border-cyan-500/30 shadow-cyan-500/10', emerald: 'border-emerald-500/30 shadow-emerald-500/10', purple: 'border-purple-500/30 shadow-purple-500/10', red: 'border-red-500/30 shadow-red-500/10', blue: 'border-blue-500/30 shadow-blue-500/10', yellow: 'border-yellow-500/30 shadow-yellow-500/10' };
  return (
    <div className={`bg-gradient-to-br from-gray-900/90 to-gray-950/95 backdrop-blur-xl border ${glowMap[glowColor] || glowMap.cyan} rounded-2xl overflow-hidden shadow-2xl`}>
      <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-gray-800/60 to-gray-900/60 cursor-pointer hover:from-gray-700/60 hover:to-gray-800/60 transition-all" onClick={onToggle}>
        <div className="flex items-center gap-3">
          <span className="text-lg">{icon}</span>
          <h3 className="text-sm font-bold text-white tracking-wide">{title}</h3>
          {badge && <span className="px-2 py-0.5 text-xs rounded-full bg-cyan-900/60 text-cyan-300 border border-cyan-500/20">{badge}</span>}
        </div>
        <div className="flex items-center gap-2">
          {headerActions}
          <svg className={`w-4 h-4 text-gray-400 transition-transform duration-300 ${collapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
        </div>
      </div>
      {!collapsed && <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight }}>{children}</div>}
    </div>
  );
}

// ============================================================
// COMPOSITE SCORE RING - Visual radial score display
// ============================================================
function ScoreRing({ score, size = 60, label, color = 'cyan' }) {
  const circumference = 2 * Math.PI * 22;
  const offset = circumference - (score / 100) * circumference;
  const colorMap = { cyan: '#22d3ee', emerald: '#34d399', red: '#f87171', purple: '#c084fc', blue: '#60a5fa', yellow: '#fbbf24' };
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} viewBox="0 0 50 50" className="-rotate-90">
        <circle cx="25" cy="25" r="22" fill="none" stroke="#1f2937" strokeWidth="3" />
        <circle cx="25" cy="25" r="22" fill="none" stroke={colorMap[color] || colorMap.cyan} strokeWidth="3" strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" className="transition-all duration-700" />
        <text x="25" y="25" textAnchor="middle" dominantBaseline="central" className="rotate-90 origin-center" fill="white" fontSize="11" fontWeight="bold" fontFamily="monospace">{score}</text>
      </svg>
      {label && <span className="text-xs text-gray-400 text-center leading-tight">{label}</span>}
    </div>
  );
}

// ============================================================
// SIGNAL DETAIL CARD - Expandable signal with full scoring
// ============================================================
function SignalCard({ signal, onOverride, expanded, onToggle }) {
  const dirColor = signal.direction === 'BUY' ? 'text-emerald-400' : signal.direction === 'SELL' ? 'text-red-400' : 'text-yellow-400';
  const dirBg = signal.direction === 'BUY' ? 'bg-emerald-500/10 border-emerald-500/30' : signal.direction === 'SELL' ? 'bg-red-500/10 border-red-500/30' : 'bg-yellow-500/10 border-yellow-500/30';
  const dirGlow = signal.direction === 'BUY' ? 'shadow-emerald-500/10' : signal.direction === 'SELL' ? 'shadow-red-500/10' : 'shadow-yellow-500/10';

  return (
    <div className={`bg-gradient-to-r from-gray-900/80 to-gray-950/90 backdrop-blur border ${dirBg} rounded-xl overflow-hidden shadow-lg ${dirGlow} mb-3 transition-all hover:shadow-xl`}>
      {/* Signal Header */}
      <div className="flex items-center justify-between px-4 py-3 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className={`text-lg font-bold ${dirColor}`}>{signal.direction}</span>
            <span className="text-white font-bold text-lg">{signal.ticker}</span>
          </div>
          <ScoreRing score={signal.compositeScore} size={44} color={signal.compositeScore >= 75 ? 'emerald' : signal.compositeScore >= 50 ? 'cyan' : 'red'} />
          <div className="hidden md:flex gap-3">
            <div className="text-center"><p className="text-xs text-gray-500">TA</p><p className="text-xs font-mono text-blue-300">{signal.scores?.technical || 0}</p></div>
            <div className="text-center"><p className="text-xs text-gray-500">Sent</p><p className="text-xs font-mono text-purple-300">{signal.scores?.sentiment || 0}</p></div>
            <div className="text-center"><p className="text-xs text-gray-500">Vol</p><p className="text-xs font-mono text-yellow-300">{signal.scores?.volume || 0}</p></div>
            <div className="text-center"><p className="text-xs text-gray-500">ML</p><p className="text-xs font-mono text-cyan-300">{signal.scores?.ml || 0}</p></div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <p className="text-xs text-gray-400">Entry: <span className="text-white font-mono">${signal.entryPrice}</span></p>
            <p className="text-xs text-gray-400">Conf: <span className="text-cyan-300 font-mono">{(signal.confidence * 100).toFixed(0)}%</span></p>
          </div>
          <span className="text-xs text-gray-500 font-mono">{signal.time}</span>
          <svg className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
        </div>
      </div>

      {/* Expanded Detail - Full Glass Box scoring */}
      {expanded && (
        <div className="border-t border-gray-700/50 p-4 space-y-4">
          {/* Composite Score Breakdown */}
          <div className="flex items-center gap-6 flex-wrap">
            <ScoreRing score={signal.compositeScore} size={80} label="Composite" color={signal.compositeScore >= 75 ? 'emerald' : 'cyan'} />
            <ScoreRing score={signal.scores?.technical || 0} size={60} label="Technical" color="blue" />
            <ScoreRing score={signal.scores?.sentiment || 0} size={60} label="Sentiment" color="purple" />
            <ScoreRing score={signal.scores?.volume || 0} size={60} label="Volume" color="yellow" />
            <ScoreRing score={signal.scores?.ml || 0} size={60} label="ML Model" color="cyan" />
            <ScoreRing score={signal.scores?.pattern || 0} size={60} label="Pattern" color="emerald" />
            <ScoreRing score={signal.scores?.optionsFlow || 0} size={60} label="Options" color="red" />
          </div>

          {/* Score Factor Details */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div className="bg-gray-800/40 rounded-lg p-2 border border-gray-700/30">
              <p className="text-xs text-blue-400 font-semibold mb-1">Technical Analysis</p>
              <div className="space-y-0.5 text-xs">
                <div className="flex justify-between"><span className="text-gray-400">RSI(14)</span><span className="text-white font-mono">{signal.factors?.rsi || 'N/A'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">MACD Signal</span><span className={signal.factors?.macd === 'bullish' ? 'text-emerald-300' : 'text-red-300'}>{signal.factors?.macd || 'N/A'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">EMA Cross</span><span className="text-white font-mono">{signal.factors?.emaCross || 'N/A'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Trend</span><span className="text-cyan-300">{signal.factors?.trend || 'N/A'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Support</span><span className="text-white font-mono">${signal.factors?.support || 'N/A'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Resistance</span><span className="text-white font-mono">${signal.factors?.resistance || 'N/A'}</span></div>
              </div>
            </div>
            <div className="bg-gray-800/40 rounded-lg p-2 border border-gray-700/30">
              <p className="text-xs text-purple-400 font-semibold mb-1">Sentiment / News</p>
              <div className="space-y-0.5 text-xs">
                <div className="flex justify-between"><span className="text-gray-400">News Sentiment</span><span className={signal.factors?.newsSentiment > 0 ? 'text-emerald-300' : 'text-red-300'}>{signal.factors?.newsSentiment > 0 ? '+' : ''}{signal.factors?.newsSentiment || 0}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Social Score</span><span className="text-white font-mono">{signal.factors?.socialScore || 'N/A'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Stockgeist</span><span className="text-white font-mono">{signal.factors?.stockgeist || 'N/A'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">SEC Filings</span><span className="text-cyan-300">{signal.factors?.secFilings || 'None'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">FRED Macro</span><span className="text-white font-mono">{signal.factors?.fredMacro || 'Neutral'}</span></div>
              </div>
            </div>
            <div className="bg-gray-800/40 rounded-lg p-2 border border-gray-700/30">
              <p className="text-xs text-yellow-400 font-semibold mb-1">Volume / Flow</p>
              <div className="space-y-0.5 text-xs">
                <div className="flex justify-between"><span className="text-gray-400">Vol Ratio</span><span className="text-white font-mono">{signal.factors?.volumeRatio || 'N/A'}x</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Dark Pool</span><span className="text-cyan-300">{signal.factors?.darkPool || 'N/A'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Options Flow</span><span className={signal.factors?.optionsFlow === 'bullish' ? 'text-emerald-300' : 'text-red-300'}>{signal.factors?.optionsFlow || 'N/A'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Unusual Activity</span><span className="text-yellow-300">{signal.factors?.unusualActivity ? 'YES' : 'No'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Institutional</span><span className="text-white font-mono">{signal.factors?.institutional || 'N/A'}</span></div>
              </div>
            </div>
          </div>

          {/* Trade Parameters + Manual Override */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-gray-800/40 rounded-lg p-3 border border-gray-700/30">
              <p className="text-xs text-cyan-400 font-semibold mb-2">Trade Parameters</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                <div className="flex justify-between"><span className="text-gray-400">Entry</span><span className="text-white font-mono">${signal.entryPrice}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Stop Loss</span><span className="text-red-300 font-mono">${signal.stopLoss}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Take Profit</span><span className="text-emerald-300 font-mono">${signal.takeProfit}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Position Size</span><span className="text-white font-mono">{signal.positionSize} shares</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Risk/Reward</span><span className="text-cyan-300 font-mono">{signal.riskReward || '1:2.0'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Timeframe</span><span className="text-white font-mono">{signal.timeframe || '1D'}</span></div>
              </div>
            </div>
            <div className="bg-gray-800/40 rounded-lg p-3 border border-gray-700/30">
              <p className="text-xs text-emerald-400 font-semibold mb-2">Operator Override</p>
              <div className="flex gap-2 mb-2">
                <button onClick={() => onOverride(signal.id, 'approve')} className="flex-1 px-2 py-1.5 text-xs bg-emerald-600/80 hover:bg-emerald-500 text-white rounded-lg transition-colors border border-emerald-500/30">Approve & Execute</button>
                <button onClick={() => onOverride(signal.id, 'reject')} className="flex-1 px-2 py-1.5 text-xs bg-red-600/80 hover:bg-red-500 text-white rounded-lg transition-colors border border-red-500/30">Reject Signal</button>
              </div>
              <div className="flex gap-2">
                <button onClick={() => onOverride(signal.id, 'modify')} className="flex-1 px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors">Modify Params</button>
                <button onClick={() => onOverride(signal.id, 'backtest')} className="flex-1 px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors">Backtest</button>
                <button onClick={() => onOverride(signal.id, 'watchlist')} className="flex-1 px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors">Watch</button>
              </div>
            </div>
          </div>

          {/* Agent reasoning */}
          <div className="bg-gray-800/40 rounded-lg p-3 border border-gray-700/30">
            <p className="text-xs text-cyan-400 font-semibold mb-1">AI Reasoning</p>
            <p className="text-xs text-gray-300 leading-relaxed">{signal.reasoning || 'Signal generated based on composite scoring of technical, sentiment, volume, and ML factors.'}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// MAIN EXPORT: Signal Intelligence Center
// ============================================================
export default function Signals() {
  const [signals, setSignals] = useState([]);
  const [expandedSignals, setExpandedSignals] = useState({});
  const [panels, setPanels] = useState({ live: true, history: true, stats: true, manual: false });
  const [filterDirection, setFilterDirection] = useState('ALL');
  const [filterMinScore, setFilterMinScore] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('time');
  const [refreshRate, setRefreshRate] = useState(5);

  const togglePanel = useCallback((key) => setPanels(prev => ({ ...prev, [key]: !prev[key] })), []);

  // Fetch signals
  useEffect(() => {
    const fetchSignals = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/v1/signals`);
        if (res.ok) { const data = await res.json(); setSignals(data.signals || []); }
      } catch (err) { console.error('Failed to fetch signals:', err); }
    };
    fetchSignals();
    const interval = setInterval(fetchSignals, refreshRate * 1000);
    return () => clearInterval(interval);
  }, [refreshRate]);

  // Mock signals - OLEH: Replace with real API data
  useEffect(() => {
    if (signals.length === 0) {
      setSignals([
        { id: 's1', ticker: 'NVDA', direction: 'BUY', compositeScore: 87, confidence: 0.89, entryPrice: '874.50', stopLoss: '857.50', takeProfit: '910.00', positionSize: 50, riskReward: '1:2.1', timeframe: '1D', time: '14:32:05', status: 'pending', scores: { technical: 91, sentiment: 82, volume: 88, ml: 85, pattern: 78, optionsFlow: 92 }, factors: { rsi: 58, macd: 'bullish', emaCross: '9/21 golden', trend: 'Uptrend', support: '855.00', resistance: '920.00', newsSentiment: 0.72, socialScore: 85, stockgeist: 'Very Bullish', secFilings: '10-K filed', fredMacro: 'Expansionary', volumeRatio: 1.8, darkPool: 'Net buying', optionsFlow: 'bullish', unusualActivity: true, institutional: 'Accumulating' }, reasoning: 'Strong bullish confluence: RSI momentum with golden cross, high options flow buying pressure, institutional accumulation detected via dark pool. ML model confidence 89% based on similar historical setups. FRED macro environment supportive.' },
        { id: 's2', ticker: 'AAPL', direction: 'BUY', compositeScore: 74, confidence: 0.78, entryPrice: '185.50', stopLoss: '181.00', takeProfit: '194.00', positionSize: 100, riskReward: '1:1.9', timeframe: '1D', time: '14:28:30', status: 'approved', scores: { technical: 72, sentiment: 76, volume: 71, ml: 78, pattern: 68, optionsFlow: 80 }, factors: { rsi: 52, macd: 'bullish', emaCross: 'above 50', trend: 'Uptrend', support: '180.00', resistance: '195.00', newsSentiment: 0.45, socialScore: 70, stockgeist: 'Bullish', secFilings: 'None recent', fredMacro: 'Neutral', volumeRatio: 1.3, darkPool: 'Neutral', optionsFlow: 'bullish', unusualActivity: false, institutional: 'Holding' }, reasoning: 'Moderate bullish setup with support at $180. Technical momentum positive but not extreme. Options flow shows bullish sentiment building.' },
        { id: 's3', ticker: 'TSLA', direction: 'SELL', compositeScore: 68, confidence: 0.72, entryPrice: '245.00', stopLoss: '255.00', takeProfit: '225.00', positionSize: 40, riskReward: '1:2.0', timeframe: '4H', time: '14:15:22', status: 'pending', scores: { technical: 65, sentiment: 58, volume: 72, ml: 70, pattern: 75, optionsFlow: 68 }, factors: { rsi: 72, macd: 'bearish', emaCross: 'death cross', trend: 'Downtrend', support: '220.00', resistance: '252.00', newsSentiment: -0.35, socialScore: 45, stockgeist: 'Bearish', secFilings: 'None', fredMacro: 'Tightening', volumeRatio: 1.5, darkPool: 'Net selling', optionsFlow: 'bearish', unusualActivity: true, institutional: 'Distributing' }, reasoning: 'Bearish divergence with overbought RSI, death cross forming. Institutional distribution detected. Short-term mean reversion opportunity.' },
        { id: 's4', ticker: 'AMD', direction: 'BUY', compositeScore: 81, confidence: 0.84, entryPrice: '165.00', stopLoss: '158.00', takeProfit: '180.00', positionSize: 75, riskReward: '1:2.1', timeframe: '1D', time: '13:55:10', status: 'executed', scores: { technical: 85, sentiment: 78, volume: 82, ml: 80, pattern: 76, optionsFlow: 84 }, factors: { rsi: 55, macd: 'bullish', emaCross: 'golden cross', trend: 'Uptrend', support: '155.00', resistance: '182.00', newsSentiment: 0.65, socialScore: 80, stockgeist: 'Bullish', secFilings: 'None', fredMacro: 'Neutral', volumeRatio: 2.1, darkPool: 'Net buying', optionsFlow: 'bullish', unusualActivity: true, institutional: 'Accumulating' }, reasoning: 'Strong AI chip demand narrative with technical breakout above resistance. Volume surge 2.1x average with options flow confirming.' },
        { id: 's5', ticker: 'SPY', direction: 'HOLD', compositeScore: 52, confidence: 0.55, entryPrice: '502.00', stopLoss: '496.00', takeProfit: '510.00', positionSize: 0, riskReward: '1:1.3', timeframe: '1D', time: '13:40:00', status: 'watching', scores: { technical: 50, sentiment: 55, volume: 48, ml: 52, pattern: 55, optionsFlow: 50 }, factors: { rsi: 50, macd: 'flat', emaCross: 'tangled', trend: 'Sideways', support: '495.00', resistance: '510.00', newsSentiment: 0.1, socialScore: 50, stockgeist: 'Neutral', secFilings: 'None', fredMacro: 'Mixed', volumeRatio: 0.9, darkPool: 'Neutral', optionsFlow: 'mixed', unusualActivity: false, institutional: 'Holding' }, reasoning: 'No clear directional bias. Market in consolidation range. Wait for breakout confirmation.' },
        { id: 's6', ticker: 'META', direction: 'BUY', compositeScore: 79, confidence: 0.82, entryPrice: '515.00', stopLoss: '500.00', takeProfit: '545.00', positionSize: 30, riskReward: '1:2.0', timeframe: '1D', time: '13:20:45', status: 'pending', scores: { technical: 80, sentiment: 82, volume: 75, ml: 78, pattern: 72, optionsFlow: 85 }, factors: { rsi: 56, macd: 'bullish', emaCross: 'above 20', trend: 'Uptrend', support: '498.00', resistance: '550.00', newsSentiment: 0.68, socialScore: 78, stockgeist: 'Bullish', secFilings: 'None', fredMacro: 'Neutral', volumeRatio: 1.4, darkPool: 'Net buying', optionsFlow: 'bullish', unusualActivity: false, institutional: 'Accumulating' }, reasoning: 'AI infrastructure investment thesis intact. Positive sentiment from earnings guidance. Technical breakout with volume confirmation.' },
        { id: 's7', ticker: 'MSFT', direction: 'BUY', compositeScore: 72, confidence: 0.76, entryPrice: '420.00', stopLoss: '410.00', takeProfit: '440.00', positionSize: 45, riskReward: '1:2.0', timeframe: '1D', time: '12:50:15', status: 'pending', scores: { technical: 70, sentiment: 75, volume: 68, ml: 74, pattern: 70, optionsFlow: 72 }, factors: { rsi: 54, macd: 'bullish', emaCross: 'above 50', trend: 'Uptrend', support: '408.00', resistance: '445.00', newsSentiment: 0.52, socialScore: 72, stockgeist: 'Bullish', secFilings: 'None', fredMacro: 'Neutral', volumeRatio: 1.1, darkPool: 'Neutral', optionsFlow: 'bullish', unusualActivity: false, institutional: 'Holding' }, reasoning: 'Cloud and AI growth story supporting valuation. Moderate technical setup with trend confirmation.' },
        { id: 's8', ticker: 'AMZN', direction: 'BUY', compositeScore: 76, confidence: 0.80, entryPrice: '185.00', stopLoss: '178.00', takeProfit: '198.00', positionSize: 60, riskReward: '1:1.9', timeframe: '1D', time: '12:30:00', status: 'executed', scores: { technical: 78, sentiment: 74, volume: 76, ml: 77, pattern: 73, optionsFlow: 78 }, factors: { rsi: 57, macd: 'bullish', emaCross: 'golden cross', trend: 'Uptrend', support: '176.00', resistance: '200.00', newsSentiment: 0.58, socialScore: 75, stockgeist: 'Bullish', secFilings: 'None', fredMacro: 'Expansionary', volumeRatio: 1.6, darkPool: 'Net buying', optionsFlow: 'bullish', unusualActivity: false, institutional: 'Accumulating' }, reasoning: 'AWS revenue acceleration and retail recovery. Golden cross with volume expansion supports upside continuation.' },
      ]);
    }
  }, []);

  // Override handler
  const handleOverride = useCallback(async (signalId, action) => {
    try {
      await fetch(`${getApiUrl()}/api/v1/signals/${signalId}/override`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
      });
    } catch (err) { console.error('Signal override failed:', err); }
  }, []);

  // Filtered and sorted signals
  const filteredSignals = signals
    .filter(s => filterDirection === 'ALL' || s.direction === filterDirection)
    .filter(s => s.compositeScore >= filterMinScore)
    .filter(s => s.ticker.toLowerCase().includes(searchTerm.toLowerCase()))
    .sort((a, b) => sortBy === 'score' ? b.compositeScore - a.compositeScore : 0);

  // Stats
  const buyCount = signals.filter(s => s.direction === 'BUY').length;
  const sellCount = signals.filter(s => s.direction === 'SELL').length;
  const avgScore = signals.length > 0 ? Math.round(signals.reduce((s, sig) => s + sig.compositeScore, 0) / signals.length) : 0;
  const pendingCount = signals.filter(s => s.status === 'pending').length;
  const executedCount = signals.filter(s => s.status === 'executed').length;

  return (
    <div className="space-y-4">
      {/* Futuristic Page Header */}
      <div className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-transparent to-purple-500/5 rounded-2xl" />
        <div className="relative flex items-center justify-between p-4">
          <div>
            <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">Signal Intelligence</h1>
            <p className="text-gray-400 text-sm">Deep composite scoring with full factor breakdown</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-gray-900/60 rounded-xl px-3 py-1.5 border border-gray-700/50">
              <span className="text-xs text-gray-400">Refresh:</span>
              <input type="range" min={1} max={30} value={refreshRate} onChange={(e) => setRefreshRate(parseInt(e.target.value))} className="w-16 h-1 accent-cyan-400" />
              <span className="text-xs text-cyan-300 font-mono">{refreshRate}s</span>
            </div>
          </div>
        </div>
      </div>

      {/* ===== Stats Overview ===== */}
      <GlassPanel title="Signal Overview" icon="\u{1F4CA}" collapsed={!panels.stats} onToggle={() => togglePanel('stats')} maxHeight="200px" glowColor="cyan">
        <div className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="bg-gradient-to-br from-emerald-900/30 to-emerald-950/50 backdrop-blur border border-emerald-500/20 rounded-xl p-3">
              <p className="text-xs text-emerald-400/70 uppercase tracking-wider">Buy Signals</p>
              <p className="text-2xl font-bold text-emerald-300 font-mono">{buyCount}</p>
            </div>
            <div className="bg-gradient-to-br from-red-900/30 to-red-950/50 backdrop-blur border border-red-500/20 rounded-xl p-3">
              <p className="text-xs text-red-400/70 uppercase tracking-wider">Sell Signals</p>
              <p className="text-2xl font-bold text-red-300 font-mono">{sellCount}</p>
            </div>
            <div className="bg-gradient-to-br from-cyan-900/30 to-cyan-950/50 backdrop-blur border border-cyan-500/20 rounded-xl p-3">
              <p className="text-xs text-cyan-400/70 uppercase tracking-wider">Avg Score</p>
              <p className="text-2xl font-bold text-cyan-300 font-mono">{avgScore}</p>
            </div>
            <div className="bg-gradient-to-br from-yellow-900/30 to-yellow-950/50 backdrop-blur border border-yellow-500/20 rounded-xl p-3">
              <p className="text-xs text-yellow-400/70 uppercase tracking-wider">Pending</p>
              <p className="text-2xl font-bold text-yellow-300 font-mono">{pendingCount}</p>
            </div>
            <div className="bg-gradient-to-br from-purple-900/30 to-purple-950/50 backdrop-blur border border-purple-500/20 rounded-xl p-3">
              <p className="text-xs text-purple-400/70 uppercase tracking-wider">Executed</p>
              <p className="text-2xl font-bold text-purple-300 font-mono">{executedCount}</p>
            </div>
          </div>
        </div>
      </GlassPanel>

      {/* ===== Live Signal Stream ===== */}
      <GlassPanel
        title="Live Signal Stream"
        icon="\u{26A1}"
        collapsed={!panels.live}
        onToggle={() => togglePanel('live')}
        badge={`${filteredSignals.length} signals`}
        maxHeight="900px"
        glowColor="emerald"
        headerActions={
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <input type="text" placeholder="Search ticker..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="bg-gray-800/60 border border-gray-600/50 text-xs text-white rounded-lg px-2 py-1 w-28 focus:outline-none focus:border-cyan-500/50" />
            <select value={filterDirection} onChange={(e) => setFilterDirection(e.target.value)} className="bg-gray-800/60 border border-gray-600/50 text-xs text-gray-200 rounded-lg px-2 py-1">
              <option value="ALL">All</option><option value="BUY">Buy</option><option value="SELL">Sell</option><option value="HOLD">Hold</option>
            </select>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-400">Min:</span>
              <input type="range" min={0} max={100} step={5} value={filterMinScore} onChange={(e) => setFilterMinScore(parseInt(e.target.value))} className="w-16 h-1 accent-cyan-400" />
              <span className="text-xs text-cyan-300 font-mono">{filterMinScore}</span>
            </div>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="bg-gray-800/60 border border-gray-600/50 text-xs text-gray-200 rounded-lg px-2 py-1">
              <option value="time">By Time</option><option value="score">By Score</option>
            </select>
          </div>
        }
      >
        <div className="p-3 space-y-1">
          {filteredSignals.map(signal => (
            <SignalCard
              key={signal.id}
              signal={signal}
              expanded={!!expandedSignals[signal.id]}
              onToggle={() => setExpandedSignals(prev => ({ ...prev, [signal.id]: !prev[signal.id] }))}
              onOverride={handleOverride}
            />
          ))}
          {filteredSignals.length === 0 && <p className="text-sm text-gray-500 italic text-center py-8">No signals match current filters</p>}
        </div>
      </GlassPanel>

      {/* ===== Manual Signal Input ===== */}
      <GlassPanel title="Manual Signal Input" icon="\u{270F}" collapsed={!panels.manual} onToggle={() => togglePanel('manual')} maxHeight="300px" glowColor="purple">
        <div className="p-4">
          <p className="text-xs text-gray-400 mb-3">Override the AI - inject your own operator signal based on intuition or external analysis</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <input type="text" placeholder="Ticker (e.g. NVDA)" className="bg-gray-800/60 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50" />
            <select className="bg-gray-800/60 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-gray-200">
              <option>BUY</option><option>SELL</option><option>HOLD</option>
            </select>
            <input type="number" placeholder="Entry Price" className="bg-gray-800/60 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50" />
            <input type="number" placeholder="Confidence (0-100)" className="bg-gray-800/60 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2">
            <input type="number" placeholder="Stop Loss" className="bg-gray-800/60 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50" />
            <input type="number" placeholder="Take Profit" className="bg-gray-800/60 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50" />
            <input type="number" placeholder="Position Size" className="bg-gray-800/60 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50" />
            <button className="bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg px-4 py-2 text-sm font-bold transition-all shadow-lg shadow-cyan-500/20">Submit Signal</button>
          </div>
          <textarea placeholder="Reasoning / Notes (optional)" className="w-full mt-2 bg-gray-800/60 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500/50 h-16" />
        </div>
      </GlassPanel>

    </div>
  );
}
