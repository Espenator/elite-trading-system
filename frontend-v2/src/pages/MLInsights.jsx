import { 
  Brain, 
  Cpu, 
  BarChart2, 
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  TrendingUp
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid
} from 'recharts';
import { mockMLStats, mockWinRateHistory } from '../data/mockData';
import { format } from 'date-fns';
import clsx from 'clsx';

export default function MLInsights() {
  const ml = mockMLStats;
  
  const featureData = ml.topFeatures.map(f => ({
    name: f.name.replace(/_/g, ' '),
    importance: Math.round(f.importance * 100)
  }));

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">ML Insights</h1>
          <p className="text-gray-400 text-sm">Model performance and analysis</p>
        </div>
        <button className="flex items-center gap-2 bg-purple-500/10 text-purple-400 px-4 py-2 rounded-lg hover:bg-purple-500/20 transition-colors">
          <RefreshCw className="w-4 h-4" />
          Retrain Model
        </button>
      </div>

      {/* Model info cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
            <Cpu className="w-4 h-4" />
            Model Version
          </div>
          <div className="text-xl font-bold font-mono">{ml.modelVersion}</div>
          <div className="flex items-center gap-1 mt-2 text-xs text-bullish">
            <CheckCircle2 className="w-3 h-3" />
            Production
          </div>
        </div>

        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
            <TrendingUp className="w-4 h-4" />
            Accuracy
          </div>
          <div className={clsx(
            'text-xl font-bold font-mono',
            ml.accuracy >= 65 ? 'text-bullish' : 'text-regime-yellow'
          )}>
            {ml.accuracy.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500 mt-2">AUC: {ml.auc.toFixed(1)}%</div>
        </div>

        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
            <BarChart2 className="w-4 h-4" />
            Sharpe Ratio
          </div>
          <div className={clsx(
            'text-xl font-bold font-mono',
            ml.sharpeRatio >= 1.5 ? 'text-bullish' : 'text-gray-300'
          )}>
            {ml.sharpeRatio.toFixed(2)}
          </div>
          <div className="text-xs text-gray-500 mt-2">Risk-adjusted return</div>
        </div>

        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
            <Brain className="w-4 h-4" />
            Training Data
          </div>
          <div className="text-xl font-bold font-mono">
            {(ml.trainingSamples / 1000).toFixed(0)}K
          </div>
          <div className="text-xs text-gray-500 mt-2">
            Last: {format(ml.lastTrained, 'MMM d, HH:mm')}
          </div>
        </div>
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Feature importance */}
        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <h3 className="font-semibold mb-4">Feature Importance</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={featureData} layout="vertical" margin={{ left: 80 }}>
                <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 11 }} />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  tick={{ fill: '#9ca3af', fontSize: 11 }}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1a1d26',
                    border: '1px solid #2d3748',
                    borderRadius: '8px'
                  }}
                />
                <Bar dataKey="importance" fill="#a855f7" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Win rate over time */}
        <div className="bg-dark-card border border-dark-border rounded-xl p-4">
          <h3 className="font-semibold mb-4">Win Rate Trend</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockWinRateHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                <XAxis 
                  dataKey="week" 
                  tick={{ fill: '#6b7280', fontSize: 11 }}
                />
                <YAxis 
                  tick={{ fill: '#6b7280', fontSize: 11 }}
                  domain={[40, 80]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1a1d26',
                    border: '1px solid #2d3748',
                    borderRadius: '8px'
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="winRate" 
                  stroke="#22c55e" 
                  strokeWidth={2}
                  dot={{ fill: '#22c55e', r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Model health */}
      <div className="bg-dark-card border border-dark-border rounded-xl p-4">
        <h3 className="font-semibold mb-4">Model Health Checks</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-dark-bg rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Prediction Drift</span>
              <CheckCircle2 className="w-4 h-4 text-bullish" />
            </div>
            <p className="text-sm">No significant drift detected</p>
            <div className="mt-2 h-2 bg-dark-card rounded-full overflow-hidden">
              <div className="h-full w-1/4 bg-bullish rounded-full" />
            </div>
          </div>

          <div className="bg-dark-bg rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Feature Stability</span>
              <CheckCircle2 className="w-4 h-4 text-bullish" />
            </div>
            <p className="text-sm">All features within normal range</p>
            <div className="mt-2 h-2 bg-dark-card rounded-full overflow-hidden">
              <div className="h-full w-1/5 bg-bullish rounded-full" />
            </div>
          </div>

          <div className="bg-dark-bg rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Calibration</span>
              <AlertTriangle className="w-4 h-4 text-regime-yellow" />
            </div>
            <p className="text-sm">Slight overconfidence in predictions</p>
            <div className="mt-2 h-2 bg-dark-card rounded-full overflow-hidden">
              <div className="h-full w-2/5 bg-regime-yellow rounded-full" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
