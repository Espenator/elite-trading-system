// ML INSIGHTS PAGE - Embodier.ai Glass House Intelligence System
// ML model performance, predictions, training status, flywheel metrics
import { useState } from 'react';
import { Brain, TrendingUp, BarChart3, RefreshCw, Zap, Target, Activity, Clock } from 'lucide-react';

const MODELS = [
  { id: 1, name: 'Pattern Classifier', accuracy: 87.3, precision: 84.1, recall: 89.2, f1: 86.6, lastTrained: '2h ago', status: 'active', predictions: 1420 },
  { id: 2, name: 'Price Predictor', accuracy: 72.8, precision: 70.5, recall: 74.1, f1: 72.3, lastTrained: '4h ago', status: 'active', predictions: 890 },
  { id: 3, name: 'Sentiment Analyzer', accuracy: 81.5, precision: 79.8, recall: 82.4, f1: 81.1, lastTrained: '1d ago', status: 'active', predictions: 2100 },
  { id: 4, name: 'Risk Scorer', accuracy: 90.1, precision: 88.7, recall: 91.3, f1: 90.0, lastTrained: '6h ago', status: 'active', predictions: 560 },
];

const PREDICTIONS = [
  { ticker: 'AAPL', prediction: 'Bullish', confidence: 88, model: 'Pattern Classifier', target: '+3.2%', timeframe: '5 days' },
  { ticker: 'MSFT', prediction: 'Bullish', confidence: 82, model: 'Price Predictor', target: '+2.8%', timeframe: '3 days' },
  { ticker: 'NVDA', prediction: 'Bearish', confidence: 71, model: 'Sentiment Analyzer', target: '-2.1%', timeframe: '2 days' },
  { ticker: 'TSLA', prediction: 'Bullish', confidence: 74, model: 'Pattern Classifier', target: '+4.5%', timeframe: '7 days' },
  { ticker: 'AMD', prediction: 'Bullish', confidence: 79, model: 'Price Predictor', target: '+3.8%', timeframe: '5 days' },
];

function MetricBar({ label, value, max = 100 }) {
  const pct = (value / max) * 100;
  const color = value >= 85 ? 'bg-emerald-500' : value >= 70 ? 'bg-blue-500' : 'bg-amber-500';
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-500 w-16 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-white w-12 text-right">{value}%</span>
    </div>
  );
}

export default function MLInsights() {
  const [tab, setTab] = useState('models');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">ML Insights</h1>
          <p className="text-sm text-gray-400 mt-1">Model performance and AI predictions</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-500 rounded-xl text-sm font-medium text-white transition-colors">
          <RefreshCw className="w-4 h-4" /> Retrain All
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Active Models', value: '4', icon: Brain, color: 'text-purple-400' },
          { label: 'Avg Accuracy', value: '82.9%', icon: Target, color: 'text-emerald-400' },
          { label: 'Total Predictions', value: '4,970', icon: Zap, color: 'text-blue-400' },
          { label: 'Flywheel Cycles', value: '142', icon: RefreshCw, color: 'text-amber-400' },
        ].map((s, i) => (
          <div key={i} className="bg-slate-800/30 border border-white/10 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <s.icon className={`w-4 h-4 ${s.color}`} />
              <span className="text-xs text-gray-500">{s.label}</span>
            </div>
            <div className="text-xl font-bold text-white">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-white/10">
        {['models', 'predictions', 'training'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-all capitalize ${
              tab === t ? 'text-blue-400 border-blue-400' : 'text-gray-500 border-transparent hover:text-white'
            }`}>{t}</button>
        ))}
      </div>

      {/* Models tab */}
      {tab === 'models' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {MODELS.map(m => (
            <div key={m.id} className="bg-slate-800/30 border border-white/10 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Brain className="w-5 h-5 text-purple-400" />
                  <span className="text-lg font-semibold text-white">{m.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs text-gray-500 capitalize">{m.status}</span>
                </div>
              </div>
              <div className="space-y-2 mb-4">
                <MetricBar label="Accuracy" value={m.accuracy} />
                <MetricBar label="Precision" value={m.precision} />
                <MetricBar label="Recall" value={m.recall} />
                <MetricBar label="F1 Score" value={m.f1} />
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500 pt-3 border-t border-white/5">
                <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Trained {m.lastTrained}</span>
                <span>{m.predictions.toLocaleString()} predictions</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Predictions tab */}
      {tab === 'predictions' && (
        <div className="bg-slate-800/30 border border-white/10 rounded-2xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="text-xs text-gray-500 uppercase border-b border-white/5">
                <th className="text-left px-5 py-3">Ticker</th>
                <th className="text-left px-3 py-3">Prediction</th>
                <th className="text-right px-3 py-3">Confidence</th>
                <th className="text-left px-3 py-3">Model</th>
                <th className="text-right px-3 py-3">Target</th>
                <th className="text-right px-5 py-3">Timeframe</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {PREDICTIONS.map((p, i) => (
                <tr key={i} className="hover:bg-white/5 transition-colors">
                  <td className="px-5 py-4 text-sm font-semibold text-white">{p.ticker}</td>
                  <td className="px-3 py-4">
                    <span className={`px-2 py-1 rounded-lg text-xs font-medium ${p.prediction === 'Bullish' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                      {p.prediction}
                    </span>
                  </td>
                  <td className="px-3 py-4 text-sm text-right">
                    <span className={`font-bold ${p.confidence >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>{p.confidence}%</span>
                  </td>
                  <td className="px-3 py-4 text-xs text-gray-400">{p.model}</td>
                  <td className={`px-3 py-4 text-sm font-medium text-right ${p.target.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>{p.target}</td>
                  <td className="px-5 py-4 text-sm text-gray-500 text-right">{p.timeframe}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Training tab */}
      {tab === 'training' && (
        <div className="space-y-4">
          <div className="bg-slate-800/30 border border-white/10 rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Self-Learning Flywheel</h3>
            <div className="space-y-4">
              {[
                { step: 'Data Ingestion', desc: 'Market data, YouTube transcripts, news feeds', status: 'complete', progress: 100 },
                { step: 'Feature Engineering', desc: 'Technical indicators, sentiment scores', status: 'complete', progress: 100 },
                { step: 'Model Training', desc: 'Pattern classifier retraining cycle #142', status: 'running', progress: 67 },
                { step: 'Validation', desc: 'Backtesting on recent market data', status: 'pending', progress: 0 },
                { step: 'Deployment', desc: 'Push updated models to production', status: 'pending', progress: 0 },
              ].map((s, i) => (
                <div key={i} className="flex items-center gap-4">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                    s.status === 'complete' ? 'bg-emerald-500/20 text-emerald-400' :
                    s.status === 'running' ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-700 text-gray-500'
                  }`}>{i + 1}</div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-white">{s.step}</div>
                    <div className="text-xs text-gray-500">{s.desc}</div>
                    {s.status === 'running' && (
                      <div className="h-1 bg-slate-700 rounded-full mt-2 overflow-hidden">
                        <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: `${s.progress}%` }} />
                      </div>
                    )}
                  </div>
                  <span className={`text-xs font-medium capitalize ${
                    s.status === 'complete' ? 'text-emerald-400' : s.status === 'running' ? 'text-blue-400' : 'text-gray-500'
                  }`}>{s.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
