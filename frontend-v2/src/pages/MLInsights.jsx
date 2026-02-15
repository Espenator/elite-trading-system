// ML FLYWHEEL & TRAINING CENTER - Embodier.ai Glass Box AI Learning
// OLEH: Deep visibility into ML training, feature importance, backtest results,
//       Sunday learning cycles, YouTube digest learning, model performance
// Backend: GET /api/v1/training/status, GET /api/v1/flywheel/metrics
// WebSocket: 'training' channel for live training progress

import { useState, useEffect, useCallback } from 'react';
import { getApiUrl } from '../config/api';

// ============================================================
// GLASS PANEL - Futuristic collapsible with neon glow
// ============================================================
function GlassPanel({ title, icon, collapsed, onToggle, maxHeight = '500px', children, badge, headerActions, glowColor = 'purple' }) {
  const glowMap = { cyan: 'border-cyan-500/30 shadow-cyan-500/10', emerald: 'border-emerald-500/30 shadow-emerald-500/10', purple: 'border-purple-500/30 shadow-purple-500/10', red: 'border-red-500/30 shadow-red-500/10', blue: 'border-blue-500/30 shadow-blue-500/10', yellow: 'border-yellow-500/30 shadow-yellow-500/10' };
  return (
    <div className={`bg-gradient-to-br from-gray-900/90 to-gray-950/95 backdrop-blur-xl border ${glowMap[glowColor] || glowMap.purple} rounded-2xl overflow-hidden shadow-2xl`}>
      <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-gray-800/60 to-gray-900/60 cursor-pointer hover:from-gray-700/60 hover:to-gray-800/60 transition-all" onClick={onToggle}>
        <div className="flex items-center gap-3">
          <span className="text-lg">{icon}</span>
          <h3 className="text-sm font-bold text-white tracking-wide">{title}</h3>
          {badge && <span className="px-2 py-0.5 text-xs rounded-full bg-purple-900/60 text-purple-300 border border-purple-500/20">{badge}</span>}
        </div>
        <div className="flex items-center gap-2">{headerActions}<svg className={`w-4 h-4 text-gray-400 transition-transform duration-300 ${collapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg></div>
      </div>
      {!collapsed && <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight }}>{children}</div>}
    </div>
  );
}

// ============================================================
// PROGRESS BAR - Neon gradient progress
// ============================================================
function NeonBar({ value, max = 100, color = 'purple', label, showValue = true }) {
  const pct = Math.min((value / max) * 100, 100);
  const colorMap = { purple: 'from-purple-500 to-pink-500 shadow-purple-500/30', cyan: 'from-cyan-500 to-blue-500 shadow-cyan-500/30', emerald: 'from-emerald-500 to-teal-500 shadow-emerald-500/30', red: 'from-red-500 to-orange-500 shadow-red-500/30', yellow: 'from-yellow-500 to-amber-500 shadow-yellow-500/30', blue: 'from-blue-500 to-indigo-500 shadow-blue-500/30' };
  return (
    <div className="flex items-center gap-2">
      {label && <span className="text-xs text-gray-400 w-28 shrink-0">{label}</span>}
      <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
        <div className={`h-2 rounded-full bg-gradient-to-r ${colorMap[color]} shadow-lg transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      {showValue && <span className="text-xs text-gray-300 font-mono w-12 text-right">{value}%</span>}
    </div>
  );
}

// ============================================================
// INLINE SLIDER - Micro-control
// ============================================================
function InlineSlider({ label, value, onChange, min = 0, max = 100, step = 1, unit = '' }) {
  return (
    <div className="flex items-center gap-3 py-1">
      <span className="text-xs text-gray-400 w-32 shrink-0">{label}</span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(parseFloat(e.target.value))} className="flex-1 h-1.5 accent-purple-400 cursor-pointer" />
      <span className="text-xs text-purple-300 w-16 text-right font-mono">{value}{unit}</span>
    </div>
  );
}

// ============================================================
// MAIN EXPORT: ML Flywheel & Training Center
// ============================================================
export default function MLInsights() {
  const [panels, setPanels] = useState({ status: true, features: true, training: true, backtest: true, youtube: false, sunday: false, models: false });
  const togglePanel = useCallback((key) => setPanels(prev => ({ ...prev, [key]: !prev[key] })), []);

  // Training config state
  const [learningRate, setLearningRate] = useState(0.001);
  const [batchSize, setBatchSize] = useState(64);
  const [epochs, setEpochs] = useState(5);
  const [validSplit, setValidSplit] = useState(0.2);

  // Mock training data
  const trainingHistory = [
    { epoch: 1, loss: 0.0456, val_loss: 0.0512, accuracy: 87.2, val_accuracy: 85.1, lr: 0.001 },
    { epoch: 2, loss: 0.0312, val_loss: 0.0389, accuracy: 90.5, val_accuracy: 88.3, lr: 0.001 },
    { epoch: 3, loss: 0.0234, val_loss: 0.0289, accuracy: 92.8, val_accuracy: 91.0, lr: 0.0008 },
    { epoch: 4, loss: 0.0189, val_loss: 0.0267, accuracy: 94.1, val_accuracy: 91.8, lr: 0.0006 },
    { epoch: 5, loss: 0.0156, val_loss: 0.0251, accuracy: 95.2, val_accuracy: 92.4, lr: 0.0004 },
  ];

  const features = [
    { name: 'RSI(14)', importance: 92, category: 'technical', trend: 'up' },
    { name: 'MACD Histogram', importance: 88, category: 'technical', trend: 'stable' },
    { name: 'Volume Ratio', importance: 85, category: 'volume', trend: 'up' },
    { name: 'Options Flow', importance: 82, category: 'flow', trend: 'up' },
    { name: 'News Sentiment', importance: 78, category: 'sentiment', trend: 'down' },
    { name: 'EMA Cross Signal', importance: 76, category: 'technical', trend: 'stable' },
    { name: 'Dark Pool Activity', importance: 74, category: 'flow', trend: 'up' },
    { name: 'Stockgeist Score', importance: 71, category: 'sentiment', trend: 'stable' },
    { name: 'FRED Macro Index', importance: 68, category: 'macro', trend: 'down' },
    { name: 'SEC Filing Signal', importance: 65, category: 'fundamental', trend: 'stable' },
    { name: 'ATR(14)', importance: 63, category: 'technical', trend: 'up' },
    { name: 'Bollinger Band %', importance: 60, category: 'technical', trend: 'stable' },
    { name: 'Twitter Sentiment', importance: 58, category: 'sentiment', trend: 'up' },
    { name: 'Institutional Flow', importance: 55, category: 'flow', trend: 'stable' },
    { name: 'YouTube Digest', importance: 52, category: 'learning', trend: 'up' },
    { name: 'Correlation Index', importance: 48, category: 'risk', trend: 'stable' },
  ];

  const backtestResults = [
    { strategy: 'Momentum Alpha v2.1', winRate: 68.5, sharpe: 2.14, maxDD: -8.2, totalReturn: 34.7, trades: 142, period: '90 days', status: 'production' },
    { strategy: 'Mean Reversion v1.8', winRate: 62.3, sharpe: 1.87, maxDD: -5.4, totalReturn: 22.1, trades: 98, period: '90 days', status: 'testing' },
    { strategy: 'Sentiment Fusion v3.0', winRate: 71.2, sharpe: 2.45, maxDD: -6.1, totalReturn: 41.3, trades: 67, period: '60 days', status: 'production' },
    { strategy: 'Options Flow v1.2', winRate: 73.8, sharpe: 2.67, maxDD: -4.8, totalReturn: 28.5, trades: 45, period: '45 days', status: 'testing' },
    { strategy: 'Pattern ML v2.0', winRate: 65.1, sharpe: 1.92, maxDD: -7.1, totalReturn: 18.9, trades: 112, period: '90 days', status: 'deprecated' },
  ];

  const youtubeDigests = [
    { title: 'How I Trade Earnings Season', channel: 'TastyTrade', concepts: ['earnings straddles', 'IV crush', 'expected move'], confidence: 0.82, status: 'ingested' },
    { title: 'RSI Divergence Masterclass', channel: 'SMB Capital', concepts: ['RSI divergence', 'momentum shift', 'entry timing'], confidence: 0.91, status: 'ingested' },
    { title: 'Dark Pool Analysis for Retail', channel: 'Unusual Whales', concepts: ['dark pool prints', 'block trades', 'institutional flow'], confidence: 0.88, status: 'ingested' },
    { title: 'FRED Data Trading Edge', channel: 'Macro Trading', concepts: ['yield curve', 'CPI signals', 'employment data'], confidence: 0.75, status: 'processing' },
    { title: 'Options Flow Signals Guide', channel: 'OptionsPlay', concepts: ['sweep detection', 'unusual activity', 'smart money'], confidence: 0.85, status: 'queued' },
  ];

  return (
    <div className="space-y-4">
      {/* Futuristic Header */}
      <div className="relative">
        <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 via-transparent to-cyan-500/5 rounded-2xl" />
        <div className="relative flex items-center justify-between p-4">
          <div>
            <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">ML Flywheel & Training</h1>
            <p className="text-gray-400 text-sm">Self-learning intelligence with full Glass Box visibility</p>
          </div>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1.5 text-xs bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-xl transition-all shadow-lg shadow-purple-500/20 font-bold">Force Retrain</button>
            <button className="px-3 py-1.5 text-xs bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl transition-all shadow-lg shadow-cyan-500/20 font-bold">Run Backtest</button>
          </div>
        </div>
      </div>

      {/* ===== Model Status ===== */}
      <GlassPanel title="Model Status" icon="\u{1F9E0}" collapsed={!panels.status} onToggle={() => togglePanel('status')} maxHeight="250px" glowColor="purple">
        <div className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <div className="bg-gradient-to-br from-purple-900/30 to-purple-950/50 border border-purple-500/20 rounded-xl p-3">
              <p className="text-xs text-purple-400/70 uppercase tracking-wider">Model Version</p>
              <p className="text-xl font-bold text-purple-300 font-mono">v3.2.1</p>
            </div>
            <div className="bg-gradient-to-br from-emerald-900/30 to-emerald-950/50 border border-emerald-500/20 rounded-xl p-3">
              <p className="text-xs text-emerald-400/70 uppercase tracking-wider">Accuracy</p>
              <p className="text-xl font-bold text-emerald-300 font-mono">92.4%</p>
            </div>
            <div className="bg-gradient-to-br from-cyan-900/30 to-cyan-950/50 border border-cyan-500/20 rounded-xl p-3">
              <p className="text-xs text-cyan-400/70 uppercase tracking-wider">Sharpe Ratio</p>
              <p className="text-xl font-bold text-cyan-300 font-mono">2.45</p>
            </div>
            <div className="bg-gradient-to-br from-blue-900/30 to-blue-950/50 border border-blue-500/20 rounded-xl p-3">
              <p className="text-xs text-blue-400/70 uppercase tracking-wider">Training Data</p>
              <p className="text-xl font-bold text-blue-300 font-mono">45.2K</p>
            </div>
            <div className="bg-gradient-to-br from-yellow-900/30 to-yellow-950/50 border border-yellow-500/20 rounded-xl p-3">
              <p className="text-xs text-yellow-400/70 uppercase tracking-wider">Last Trained</p>
              <p className="text-xl font-bold text-yellow-300 font-mono">2h ago</p>
            </div>
            <div className="bg-gradient-to-br from-pink-900/30 to-pink-950/50 border border-pink-500/20 rounded-xl p-3">
              <p className="text-xs text-pink-400/70 uppercase tracking-wider">Status</p>
              <p className="text-xl font-bold text-pink-300 animate-pulse">Training</p>
            </div>
          </div>
        </div>
      </GlassPanel>

      {/* ===== Feature Importance - Scrollable ranked list ===== */}
      <GlassPanel title="Feature Importance (Ranked)" icon="\u{1F4CA}" collapsed={!panels.features} onToggle={() => togglePanel('features')} badge={`${features.length} features`} maxHeight="400px" glowColor="blue">
        <div className="p-4 space-y-2">
          {features.map((f, i) => {
            const catColors = { technical: 'text-blue-400', sentiment: 'text-purple-400', volume: 'text-yellow-400', flow: 'text-cyan-400', macro: 'text-emerald-400', fundamental: 'text-pink-400', learning: 'text-orange-400', risk: 'text-red-400' };
            const trendIcons = { up: '\u2191', down: '\u2193', stable: '\u2192' };
            const barColor = f.importance >= 80 ? 'emerald' : f.importance >= 60 ? 'cyan' : f.importance >= 40 ? 'yellow' : 'red';
            return (
              <div key={i} className="flex items-center gap-3">
                <span className="text-xs text-gray-500 font-mono w-6">#{i+1}</span>
                <span className={`text-xs w-28 shrink-0 ${catColors[f.category] || 'text-gray-400'}`}>{f.name}</span>
                <NeonBar value={f.importance} color={barColor} showValue={false} />
                <span className="text-xs text-white font-mono w-8">{f.importance}%</span>
                <span className={`text-xs ${f.trend === 'up' ? 'text-emerald-400' : f.trend === 'down' ? 'text-red-400' : 'text-gray-400'}`}>{trendIcons[f.trend]}</span>
                <span className="text-xs text-gray-600 w-20">{f.category}</span>
              </div>
            );
          })}
        </div>
      </GlassPanel>

      {/* ===== Training History ===== */}
      <GlassPanel title="Training History" icon="\u{1F4C8}" collapsed={!panels.training} onToggle={() => togglePanel('training')} maxHeight="500px" glowColor="purple">
        <div className="p-4 space-y-4">
          {/* Training Controls */}
          <div className="bg-gray-800/40 rounded-xl p-3 border border-purple-500/10">
            <h5 className="text-xs text-purple-300 font-semibold mb-2 uppercase tracking-wider">Training Parameters (Adjustable)</h5>
            <InlineSlider label="Learning Rate" value={learningRate} onChange={setLearningRate} min={0.0001} max={0.01} step={0.0001} />
            <InlineSlider label="Batch Size" value={batchSize} onChange={setBatchSize} min={8} max={256} step={8} />
            <InlineSlider label="Epochs" value={epochs} onChange={setEpochs} min={1} max={50} step={1} />
            <InlineSlider label="Validation Split" value={validSplit} onChange={setValidSplit} min={0.05} max={0.5} step={0.05} />
          </div>
          {/* Epoch-by-epoch table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-gray-400 border-b border-gray-700">
                <th className="py-2 px-2 text-left">Epoch</th><th className="py-2 px-2">Loss</th><th className="py-2 px-2">Val Loss</th><th className="py-2 px-2">Accuracy</th><th className="py-2 px-2">Val Accuracy</th><th className="py-2 px-2">LR</th><th className="py-2 px-2">Improving?</th>
              </tr></thead>
              <tbody>{trainingHistory.map((h, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 px-2 text-white font-mono">{h.epoch}</td>
                  <td className="py-2 px-2 text-red-300 font-mono">{h.loss.toFixed(4)}</td>
                  <td className="py-2 px-2 text-orange-300 font-mono">{h.val_loss.toFixed(4)}</td>
                  <td className="py-2 px-2 text-emerald-300 font-mono">{h.accuracy}%</td>
                  <td className="py-2 px-2 text-cyan-300 font-mono">{h.val_accuracy}%</td>
                  <td className="py-2 px-2 text-purple-300 font-mono">{h.lr}</td>
                  <td className="py-2 px-2">{i > 0 && trainingHistory[i].val_loss < trainingHistory[i-1].val_loss ? <span className="text-emerald-400">\u2713 Yes</span> : i === 0 ? <span className="text-gray-500">-</span> : <span className="text-red-400">\u2717 No</span>}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      </GlassPanel>

      {/* ===== Backtest Results ===== */}
      <GlassPanel title="Backtest Results" icon="\u{1F3AF}" collapsed={!panels.backtest} onToggle={() => togglePanel('backtest')} badge={`${backtestResults.length} strategies`} maxHeight="400px" glowColor="emerald">
        <div className="p-4">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-gray-400 border-b border-gray-700">
                <th className="py-2 px-2 text-left">Strategy</th><th className="py-2 px-2">Win Rate</th><th className="py-2 px-2">Sharpe</th><th className="py-2 px-2">Max DD</th><th className="py-2 px-2">Return</th><th className="py-2 px-2">Trades</th><th className="py-2 px-2">Period</th><th className="py-2 px-2">Status</th>
              </tr></thead>
              <tbody>{backtestResults.map((b, i) => (
                <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 px-2 text-white font-semibold">{b.strategy}</td>
                  <td className="py-2 px-2 text-emerald-300 font-mono">{b.winRate}%</td>
                  <td className="py-2 px-2 text-cyan-300 font-mono">{b.sharpe}</td>
                  <td className="py-2 px-2 text-red-300 font-mono">{b.maxDD}%</td>
                  <td className="py-2 px-2 text-emerald-300 font-mono">+{b.totalReturn}%</td>
                  <td className="py-2 px-2 text-white font-mono">{b.trades}</td>
                  <td className="py-2 px-2 text-gray-400">{b.period}</td>
                  <td className="py-2 px-2"><span className={`px-1.5 py-0.5 rounded text-xs ${b.status === 'production' ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-500/30' : b.status === 'testing' ? 'bg-yellow-900/50 text-yellow-300 border border-yellow-500/30' : 'bg-gray-700/50 text-gray-400 border border-gray-600/30'}`}>{b.status}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          <div className="mt-3 flex gap-2">
            <button className="px-3 py-1.5 text-xs bg-emerald-600/60 hover:bg-emerald-500 text-white rounded-lg transition-colors border border-emerald-500/30">Run All Backtests</button>
            <button className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors">Schedule Sunday Run</button>
            <button className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors">Export Results</button>
          </div>
        </div>
      </GlassPanel>

      {/* ===== YouTube Transcript Digests ===== */}
      <GlassPanel title="YouTube Learning Digest" icon="\u{1F3AC}" collapsed={!panels.youtube} onToggle={() => togglePanel('youtube')} badge={`${youtubeDigests.length} videos`} maxHeight="400px" glowColor="red">
        <div className="p-4 space-y-3">
          <p className="text-xs text-gray-400">Financial videos digested and concepts extracted for ML training</p>
          {youtubeDigests.map((yt, i) => (
            <div key={i} className="bg-gray-800/40 rounded-xl p-3 border border-gray-700/30">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm text-white font-semibold">{yt.title}</p>
                  <p className="text-xs text-gray-400">{yt.channel}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-cyan-300 font-mono">{(yt.confidence * 100).toFixed(0)}% conf</span>
                  <span className={`px-1.5 py-0.5 rounded text-xs ${yt.status === 'ingested' ? 'bg-emerald-900/50 text-emerald-300' : yt.status === 'processing' ? 'bg-yellow-900/50 text-yellow-300 animate-pulse' : 'bg-gray-700/50 text-gray-400'}`}>{yt.status}</span>
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                {yt.concepts.map((c, j) => <span key={j} className="px-2 py-0.5 text-xs bg-purple-900/40 text-purple-300 rounded-full border border-purple-500/20">{c}</span>)}
              </div>
            </div>
          ))}
          <div className="flex gap-2 mt-2">
            <input type="text" placeholder="Paste YouTube URL to digest..." className="flex-1 bg-gray-800/60 border border-gray-600/50 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500/50" />
            <button className="px-4 py-2 text-xs bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-500 hover:to-pink-500 text-white rounded-lg font-bold shadow-lg shadow-red-500/20">Digest</button>
          </div>
        </div>
      </GlassPanel>

      {/* ===== Sunday Learning Schedule ===== */}
      <GlassPanel title="Sunday Learning Cycle" icon="\u{1F4C5}" collapsed={!panels.sunday} onToggle={() => togglePanel('sunday')} maxHeight="300px" glowColor="yellow">
        <div className="p-4">
          <p className="text-xs text-gray-400 mb-3">Automated weekly learning, backtesting, and model improvement cycle</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-800/40 rounded-xl p-3 border border-yellow-500/10">
              <p className="text-xs text-yellow-400">Next Run</p>
              <p className="text-sm text-white font-mono">Sun 2:00 AM</p>
            </div>
            <div className="bg-gray-800/40 rounded-xl p-3 border border-yellow-500/10">
              <p className="text-xs text-yellow-400">Last Run</p>
              <p className="text-sm text-white font-mono">5 days ago</p>
            </div>
            <div className="bg-gray-800/40 rounded-xl p-3 border border-emerald-500/10">
              <p className="text-xs text-emerald-400">Last Improvement</p>
              <p className="text-sm text-emerald-300 font-mono">+1.2% accuracy</p>
            </div>
            <div className="bg-gray-800/40 rounded-xl p-3 border border-purple-500/10">
              <p className="text-xs text-purple-400">Total Cycles</p>
              <p className="text-sm text-white font-mono">12 completed</p>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button className="px-3 py-1.5 text-xs bg-yellow-600/60 hover:bg-yellow-500 text-white rounded-lg transition-colors border border-yellow-500/30">Run Now</button>
            <button className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors">Edit Schedule</button>
            <button className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors">View History</button>
          </div>
        </div>
      </GlassPanel>

    </div>
  );
}
