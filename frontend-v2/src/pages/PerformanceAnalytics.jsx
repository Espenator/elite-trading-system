// PERFORMANCE ANALYTICS - Embodier.ai Glass House Intelligence System
// Market overview, performance metrics, monthly heatmap, returns decomposition, ML insights
import { useState } from 'react';
import {
  Download, TrendingUp, TrendingDown, BarChart3,
  Brain, ShieldCheck, ChevronDown, Activity, Clock
} from 'lucide-react';

const MARKET_STATS = [
  { label: 'SPY (S&P 500 ETF)', value: '$498.75', change: '+0.85%', up: true },
  { label: 'VIX (Volatility Index)', value: '17.20', change: '-1.52%', up: false },
  { label: 'Market Breadth (Adv/Dec)', value: '+1,250', change: '+8.3%', up: true },
  { label: 'Sector Performance (Tech)', value: '+1.1%', sub: 'Leading', up: true },
];

const PERF_SUMMARY = [
  { label: 'Total Return', value: '+15.3%', sub: '+1.2% (last month)', up: true },
  { label: 'Annualized Return', value: '18.7%', sub: '-0.5% (vs. avg)', up: false },
  { label: 'Sharpe Ratio', value: '1.25', sub: '+0.03 (vs. benchmark)', up: true },
];

const MONTHLY_RETURNS = {
  2023: [3.5, 1.2, -0.8, 2.1, 4.0, 0.5, 1.8, -2.5, -1.0, 0.7, null, null],
  2024: [4.1, 2.5, 0.1, 1.5, 3.2, 1.0, null, null, null, null, null, null],
};

const FACTORS = [
  { name: 'Equity Exposure', value: '+7.2%', up: true },
  { name: 'Fixed Income', value: '+1.8%', up: true },
  { name: 'Alternatives', value: '-0.5%', up: false },
  { name: 'Currency Hedging', value: '+0.3%', up: true },
  { name: 'Sector Rotation', value: '+1.5%', up: true },
];

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function GlassCard({ title, children, action, className = '' }) {
  return (
    <div className={`bg-slate-800/30 border border-white/10 rounded-2xl overflow-hidden ${className}`}>
      {title && (
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

function MarketStat({ label, value, change, sub, up }) {
  return (
    <div className="bg-slate-900/40 border border-white/5 rounded-xl p-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-xl font-bold text-white">{value}</div>
      {change && (
        <div className={`flex items-center gap-1 text-xs mt-1 ${up ? 'text-emerald-400' : 'text-red-400'}`}>
          {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {change}
        </div>
      )}
      {sub && <div className={`text-xs mt-1 ${up ? 'text-emerald-400' : 'text-gray-400'}`}>{sub}</div>}
    </div>
  );
}

export default function PerformanceAnalytics() {
  const [timeframe, setTimeframe] = useState('1W');
  const timeframes = ['1H', '4H', '1D', '1W', '1M', '1Y', 'ALL'];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Performance Analytics</h1>
          <p className="text-sm text-gray-400 mt-1">Last updated 1 minute ago</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors">
          <Download className="w-4 h-4" /> Export Report
        </button>
      </div>

      {/* Market Overview */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Market Overview</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {MARKET_STATS.map((s, i) => <MarketStat key={i} {...s} />)}
        </div>
      </div>

      {/* Performance Summary */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Performance Summary</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {PERF_SUMMARY.map((s, i) => (
            <div key={i} className="bg-slate-900/40 border border-white/5 rounded-xl p-4">
              <div className="text-xs text-gray-500 mb-1">{s.label}</div>
              <div className="text-2xl font-bold text-white">{s.value}</div>
              <div className={`flex items-center gap-1 text-xs mt-1 ${s.up ? 'text-emerald-400' : 'text-red-400'}`}>
                {s.up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {s.sub}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Portfolio Performance chart */}
      <GlassCard title="Portfolio Performance" action={
        <div className="flex items-center gap-1">
          {timeframes.map(tf => (
            <button key={tf} onClick={() => setTimeframe(tf)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                timeframe === tf ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-700'
              }`}>{tf}</button>
          ))}
        </div>
      }>
        <div className="h-48 bg-slate-900/30 rounded-xl border border-white/5 flex items-end px-4 pb-4 gap-1">
          {[30, 32, 35, 33, 38, 40, 42, 45, 44, 48, 50, 52, 55, 58, 56, 60, 62, 65, 68, 72, 75, 78, 80, 85].map((v, i) => (
            <div key={i} className="flex-1 bg-gradient-to-t from-blue-600 to-blue-400 rounded-t opacity-80" style={{ height: `${v}%` }} />
          ))}
        </div>
      </GlassCard>

      {/* Monthly Heatmap + Returns Decomposition */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title="Monthly Returns Heatmap (2023-2024)">
          <p className="text-xs text-gray-500 mb-4">Color intensity indicates monthly performance.</p>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="text-left text-xs text-gray-500 pb-2"></th>
                  {MONTHS.map(m => <th key={m} className="text-center text-xs text-gray-500 pb-2 px-1">{m}</th>)}
                </tr>
              </thead>
              <tbody>
                {Object.entries(MONTHLY_RETURNS).map(([year, vals]) => (
                  <tr key={year}>
                    <td className="text-sm text-gray-400 pr-3 py-1">{year}</td>
                    {vals.map((v, i) => (
                      <td key={i} className="text-center py-1 px-1">
                        {v !== null ? (
                          <span className={`inline-block w-full px-1 py-0.5 rounded text-xs font-medium ${
                            v >= 3 ? 'bg-emerald-500/30 text-emerald-300' :
                            v >= 0 ? 'bg-emerald-500/15 text-emerald-400' :
                            v >= -1 ? 'bg-red-500/15 text-red-400' : 'bg-red-500/30 text-red-300'
                          }`}>{v.toFixed(1)}%</span>
                        ) : <span className="text-xs text-gray-700">-</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>

        <GlassCard title="Returns Decomposition">
          <p className="text-xs text-gray-500 mb-4">Breakdown of portfolio returns by factor.</p>
          <table className="w-full">
            <thead>
              <tr className="text-xs text-gray-500 uppercase">
                <th className="text-left pb-3">Factor</th>
                <th className="text-right pb-3">Contribution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {FACTORS.map((f, i) => (
                <tr key={i} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 text-sm text-gray-300">{f.name}</td>
                  <td className={`py-3 text-sm font-medium text-right ${f.up ? 'text-emerald-400' : 'text-red-400'}`}>{f.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </GlassCard>
      </div>

      {/* ML Insights + Risk Shield Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title="ML Insights">
          <div className="space-y-3">
            <button className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300">
              <ChevronDown className="w-4 h-4" /> View Details
            </button>
            <p className="text-sm text-gray-300 leading-relaxed">
              Our machine learning models predict a moderate uptrend for growth stocks in the next quarter,
              driven by expected interest rate stability. Specific sectors to watch include renewable energy
              and AI infrastructure. Consider tactical allocations to these areas for potential outperformance.
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Prediction accuracy: 78% for the next 30 days. Model last updated: 2024-07-20.
            </p>
          </div>
        </GlassCard>

        <GlassCard title="Risk Shield Summary">
          <div className="space-y-3">
            <button className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300">
              <ChevronDown className="w-4 h-4" /> View Details
            </button>
            <ul className="space-y-2 text-sm text-gray-300">
              <li className="flex items-start gap-2"><span className="text-gray-500">-</span>Total Portfolio VaR (99%, 1-day): -2.5%</li>
              <li className="flex items-start gap-2"><span className="text-gray-500">-</span>Current Beta vs. S&P 500: 1.15 (slightly aggressive)</li>
              <li className="flex items-start gap-2"><span className="text-gray-500">-</span>Concentration Risk (Top 5 Holdings): 35%</li>
              <li className="flex items-start gap-2"><span className="text-gray-500">-</span>Liquidity Profile: High. Majority of holdings are highly liquid.</li>
            </ul>
            <p className="text-sm text-gray-400 mt-2">
              Recommendations: Diversify exposure in technology sector to mitigate concentration risk.
            </p>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
