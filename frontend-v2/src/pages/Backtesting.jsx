// BACKTESTING LAB - Embodier.ai Glass House Intelligence System
// Strategy backtesting, parameter sweeps, results visualization, trade simulator
import { useState } from 'react';
import {
  Play, Square, Download, ChevronDown, Settings,
  TrendingUp, TrendingDown, BarChart3, Activity,
  Clock, Target, Percent, DollarSign, Loader2
} from 'lucide-react';

const STRATEGIES = ['Mean Reversion V2', 'ArbitrageAlpha', 'TrendFollowerV1', 'VolSurfaceBeta', 'MomentumShift'];

const PARALLEL_RUNS = [
  { id: 'R001', strategy: 'MeanReversionV2', status: 'Running' },
  { id: 'R002', strategy: 'ArbitrageAlpha', status: 'Completed' },
  { id: 'R003', strategy: 'TrendFollowerV1', status: 'Failed' },
  { id: 'R004', strategy: 'VolSurfaceBeta', status: 'Running' },
];

const SAMPLE_TRADES = [
  { time: '09:30:00', asset: 'AAPL', type: 'BUY', qty: 100, price: 175.25, pnl: 250 },
  { time: '09:45:15', asset: 'MSFT', type: 'SELL', qty: 50, price: 340.10, pnl: -120 },
  { time: '10:05:30', asset: 'GOOG', type: 'BUY', qty: 20, price: 1200.50, pnl: 500 },
  { time: '10:15:00', asset: 'TSLA', type: 'SELL', qty: 30, price: 230.70, pnl: 180 },
  { time: '10:30:45', asset: 'AMZN', type: 'BUY', qty: 40, price: 150.90, pnl: -75 },
];

const RUN_HISTORY = [
  { date: '2023-11-28', strategy: 'MeanReversionV1', pnl: 5200 },
  { date: '2023-11-20', strategy: 'ArbitrageAlpha', pnl: 3150 },
  { date: '2023-11-15', strategy: 'TrendFollowerV1', pnl: -1800 },
  { date: '2023-11-05', strategy: 'VolSurfaceBeta', pnl: 7800 },
  { date: '2023-10-30', strategy: 'MomentumShift', pnl: 2900 },
];

function GlassCard({ title, children, className = '' }) {
  return (
    <div className={`bg-slate-800/30 border border-white/10 rounded-2xl overflow-hidden ${className}`}>
      {title && (
        <div className="px-5 py-4 border-b border-white/5">
          <h3 className="text-sm font-semibold text-white">{title}</h3>
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  const styles = {
    Running: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    Completed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    Failed: 'bg-red-500/20 text-red-400 border-red-500/30',
  };
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status] || 'bg-gray-500/20 text-gray-400'}`}>
      {status}
    </span>
  );
}

function ResultStat({ label, value, icon: Icon }) {
  return (
    <div className="text-center">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-lg font-bold text-white">{value}</div>
    </div>
  );
}

export default function Backtesting() {
  const [strategy, setStrategy] = useState('Mean Reversion V2');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');
  const [assets, setAssets] = useState('AAPL, MSFT, GOOG, TSLA, AMZN');
  const [capital, setCapital] = useState('100000');
  const [paramA, setParamA] = useState(50);
  const [paramBMin, setParamBMin] = useState('10');
  const [paramBMax, setParamBMax] = useState('100');
  const [runMode, setRunMode] = useState('single');
  const [isRunning, setIsRunning] = useState(false);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Backtesting Lab</h1>
        <p className="text-sm text-gray-400 mt-1">Run strategy backtests with parameter optimization</p>
      </div>

      {/* Configuration row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Backtest Configuration */}
        <GlassCard title="Backtest Configuration">
          <div className="space-y-4">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Strategy</label>
              <select
                value={strategy}
                onChange={e => setStrategy(e.target.value)}
                className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50"
              >
                {STRATEGIES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Start Date</label>
                <input type="text" value={startDate} onChange={e => setStartDate(e.target.value)}
                  className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50" />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">End Date</label>
                <input type="text" value={endDate} onChange={e => setEndDate(e.target.value)}
                  className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50" />
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Asset Universe (CSV)</label>
              <textarea value={assets} onChange={e => setAssets(e.target.value)} rows={2}
                className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50 resize-none" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Initial Capital</label>
              <input type="text" value={capital} onChange={e => setCapital(e.target.value)}
                className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50" />
            </div>
          </div>
        </GlassCard>

        {/* Parameter Sweeps & Controls */}
        <GlassCard title="Parameter Sweeps & Controls">
          <div className="space-y-5">
            <div>
              <label className="text-xs text-gray-500 mb-2 block">Parameter A (Sensitivity): {paramA}</label>
              <input type="range" min="0" max="100" value={paramA} onChange={e => setParamA(Number(e.target.value))}
                className="w-full accent-purple-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-2 block">Parameter B Range</label>
              <div className="grid grid-cols-2 gap-4">
                <input type="text" value={paramBMin} onChange={e => setParamBMin(e.target.value)}
                  className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50" />
                <input type="text" value={paramBMax} onChange={e => setParamBMax(e.target.value)}
                  className="w-full bg-slate-900/50 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500/50" />
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-2 block">Run Mode</label>
              <div className="flex items-center gap-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="runMode" value="single" checked={runMode === 'single'}
                    onChange={() => setRunMode('single')} className="accent-purple-500" />
                  <span className="text-sm text-gray-300">Single Run</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="runMode" value="sweep" checked={runMode === 'sweep'}
                    onChange={() => setRunMode('sweep')} className="accent-purple-500" />
                  <span className="text-sm text-gray-300">Parameter Sweep</span>
                </label>
              </div>
            </div>
            <div className="flex items-center gap-3 pt-2">
              <button onClick={() => setIsRunning(true)}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium transition-colors">
                <Play className="w-4 h-4" /> Run Backtest
              </button>
              <button onClick={() => setIsRunning(false)}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium transition-colors">
                <Square className="w-4 h-4" /> Stop Run
              </button>
              <button className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium transition-colors">
                <Download className="w-4 h-4" /> Export Configuration
              </button>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Results + Parallel Runs row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Results Visualization */}
        <div className="lg:col-span-2">
          <GlassCard title="Results Visualization">
            <div className="grid grid-cols-5 gap-4 mb-6">
              <ResultStat label="Net PnL" value="+$25,000" />
              <ResultStat label="Sharpe Ratio" value="1.15" />
              <ResultStat label="Max Drawdown" value="-8.2%" />
              <ResultStat label="Win Rate" value="68%" />
              <ResultStat label="Total Trades" value="1,250" />
            </div>
            {/* Equity curve placeholder */}
            <div className="h-40 bg-slate-900/30 rounded-xl border border-white/5 flex items-end px-4 pb-4 gap-1">
              {[40, 42, 38, 45, 50, 48, 55, 60, 58, 65, 70, 68, 75, 80, 78, 85, 90, 88, 95, 98].map((v, i) => (
                <div key={i} className="flex-1 bg-blue-500/60 rounded-t" style={{ height: `${v}%` }} />
              ))}
            </div>
            <div className="flex items-center justify-center gap-4 mt-3">
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-blue-500" /><span className="text-xs text-gray-400">Equity</span></div>
            </div>
            {/* Drawdown area placeholder */}
            <div className="h-24 bg-slate-900/30 rounded-xl border border-white/5 mt-4 flex items-start px-4 pt-4 gap-1">
              {[5, 8, 3, 12, 18, 15, 10, 20, 25, 18, 12, 22, 28, 20, 15, 10, 8, 12, 5, 3].map((v, i) => (
                <div key={i} className="flex-1 bg-red-500/40 rounded-b" style={{ height: `${v * 3}%` }} />
              ))}
            </div>
            <div className="flex items-center justify-center gap-4 mt-3">
              <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-red-400" /><span className="text-xs text-gray-400">Drawdown</span></div>
            </div>
          </GlassCard>
        </div>

        {/* Parallel Run Manager */}
        <GlassCard title="Parallel Run Manager">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 uppercase">
                  <th className="text-left pb-3">Run ID</th>
                  <th className="text-left pb-3">Strategy</th>
                  <th className="text-right pb-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {PARALLEL_RUNS.map((r, i) => (
                  <tr key={i} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 text-sm font-medium text-white">{r.id}</td>
                    <td className="py-3 text-sm text-gray-400">{r.strategy}</td>
                    <td className="py-3 text-right"><StatusBadge status={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </div>

      {/* Trade Simulator + Run History row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trade-by-Trade Simulator */}
        <GlassCard title="Trade-by-Trade Simulator">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 uppercase">
                  <th className="text-left pb-3">Time</th>
                  <th className="text-left pb-3">Asset</th>
                  <th className="text-left pb-3">Type</th>
                  <th className="text-right pb-3">QTY</th>
                  <th className="text-right pb-3">Price</th>
                  <th className="text-right pb-3">PNL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {SAMPLE_TRADES.map((t, i) => (
                  <tr key={i} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 text-sm text-gray-400">{t.time}</td>
                    <td className="py-3 text-sm font-medium text-white">{t.asset}</td>
                    <td className="py-3 text-sm">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${t.type === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>{t.type}</span>
                    </td>
                    <td className="py-3 text-sm text-gray-300 text-right">{t.qty}</td>
                    <td className="py-3 text-sm text-gray-300 text-right">{t.price}</td>
                    <td className={`py-3 text-sm font-medium text-right ${t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {t.pnl >= 0 ? '+' : ''}{t.pnl}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>

        {/* Run History & Export */}
        <GlassCard title="Run History & Export">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 uppercase">
                  <th className="text-left pb-3">Date</th>
                  <th className="text-left pb-3">Strategy</th>
                  <th className="text-right pb-3">PNL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {RUN_HISTORY.map((r, i) => (
                  <tr key={i} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 text-sm text-gray-400">{r.date}</td>
                    <td className="py-3 text-sm text-white">{r.strategy}</td>
                    <td className={`py-3 text-sm font-medium text-right ${r.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {r.pnl >= 0 ? '+' : ''}${Math.abs(r.pnl).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium transition-colors">
            <Download className="w-4 h-4" /> Export All Results
          </button>
        </GlassCard>
      </div>
    </div>
  );
}
