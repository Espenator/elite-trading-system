// TRADES PAGE - Embodier.ai Glass House Intelligence System
// Trade management: active positions, order history, P&L tracking
import { useState } from 'react';
import {
  TrendingUp, TrendingDown, Clock, DollarSign,
  ArrowUpRight, ArrowDownRight, Filter, X
} from 'lucide-react';

const ACTIVE_POSITIONS = [
  { id: 1, ticker: 'AAPL', side: 'Long', qty: 50, entry: 189.50, current: 192.30, pnl: 140, pnlPct: 1.48, stop: 185.00, target: 198.00, signal: 'AI Signal #1', time: '2h ago' },
  { id: 2, ticker: 'TSLA', side: 'Long', qty: 30, entry: 245.30, current: 248.10, pnl: 84, pnlPct: 1.14, stop: 240.00, target: 260.00, signal: 'AI Signal #2', time: '4h ago' },
  { id: 3, ticker: 'NVDA', side: 'Long', qty: 10, entry: 875.00, current: 868.20, pnl: -68, pnlPct: -0.78, stop: 850.00, target: 920.00, signal: 'AI Signal #3', time: '1d ago' },
  { id: 4, ticker: 'SPY', side: 'Short', qty: 100, entry: 502.10, current: 500.85, pnl: 125, pnlPct: 0.25, stop: 506.00, target: 495.00, signal: 'AI Signal #4', time: '3h ago' },
];

const TRADE_HISTORY = [
  { id: 101, ticker: 'MSFT', side: 'Long', qty: 40, entry: 408.20, exit: 418.50, pnl: 412, pnlPct: 2.52, duration: '2d 4h', date: 'Feb 14' },
  { id: 102, ticker: 'AMD', side: 'Long', qty: 60, entry: 165.00, exit: 172.30, pnl: 438, pnlPct: 4.42, duration: '1d 8h', date: 'Feb 13' },
  { id: 103, ticker: 'META', side: 'Short', qty: 20, entry: 590.00, exit: 582.40, pnl: 152, pnlPct: 1.29, duration: '6h', date: 'Feb 13' },
  { id: 104, ticker: 'GOOGL', side: 'Long', qty: 50, entry: 178.50, exit: 175.20, pnl: -165, pnlPct: -1.85, duration: '1d 2h', date: 'Feb 12' },
  { id: 105, ticker: 'AMZN', side: 'Long', qty: 25, entry: 185.00, exit: 192.80, pnl: 195, pnlPct: 4.22, duration: '3d', date: 'Feb 11' },
];

export default function Trades() {
  const [tab, setTab] = useState('active');

  const totalPnl = ACTIVE_POSITIONS.reduce((sum, p) => sum + p.pnl, 0);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Trades</h1>
          <p className="text-sm text-gray-400 mt-1">Manage positions and review history</p>
        </div>
        <div className="flex items-center gap-4">
          <div className={`px-4 py-2 rounded-xl border text-sm font-medium ${totalPnl >= 0 ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
            Today: {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(0)}
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Active Positions', value: ACTIVE_POSITIONS.length, icon: TrendingUp, color: 'text-blue-400' },
          { label: 'Unrealized P&L', value: `$${totalPnl >= 0 ? '+' : ''}${totalPnl}`, icon: DollarSign, color: totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400' },
          { label: 'Win Rate (30d)', value: '68.5%', icon: ArrowUpRight, color: 'text-emerald-400' },
          { label: 'Avg Hold Time', value: '1.4 days', icon: Clock, color: 'text-amber-400' },
        ].map((stat, i) => (
          <div key={i} className="bg-slate-800/30 border border-white/10 rounded-2xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
              <span className="text-xs text-gray-500">{stat.label}</span>
            </div>
            <div className="text-xl font-bold text-white">{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Tab navigation */}
      <div className="flex gap-2 border-b border-white/10 pb-0">
        {['active', 'history'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-all ${
              tab === t ? 'text-blue-400 border-blue-400' : 'text-gray-500 border-transparent hover:text-white'
            }`}>
            {t === 'active' ? `Active (${ACTIVE_POSITIONS.length})` : `History (${TRADE_HISTORY.length})`}
          </button>
        ))}
      </div>

      {/* Active Positions Table */}
      {tab === 'active' && (
        <div className="bg-slate-800/30 border border-white/10 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 uppercase border-b border-white/5">
                  <th className="text-left px-5 py-3">Ticker</th>
                  <th className="text-left px-3 py-3">Side</th>
                  <th className="text-right px-3 py-3">Qty</th>
                  <th className="text-right px-3 py-3">Entry</th>
                  <th className="text-right px-3 py-3">Current</th>
                  <th className="text-right px-3 py-3">P&L</th>
                  <th className="text-right px-3 py-3">Stop</th>
                  <th className="text-right px-3 py-3">Target</th>
                  <th className="text-left px-3 py-3">Signal</th>
                  <th className="text-right px-5 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {ACTIVE_POSITIONS.map(p => (
                  <tr key={p.id} className="hover:bg-white/5 transition-colors">
                    <td className="px-5 py-4 text-sm font-semibold text-white">{p.ticker}</td>
                    <td className="px-3 py-4">
                      <span className={`px-2 py-1 rounded-lg text-xs font-medium ${p.side === 'Long' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                        {p.side}
                      </span>
                    </td>
                    <td className="px-3 py-4 text-sm text-gray-400 text-right">{p.qty}</td>
                    <td className="px-3 py-4 text-sm text-gray-400 text-right">${p.entry.toFixed(2)}</td>
                    <td className="px-3 py-4 text-sm text-white text-right">${p.current.toFixed(2)}</td>
                    <td className={`px-3 py-4 text-sm font-medium text-right ${p.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {p.pnl >= 0 ? '+' : ''}${p.pnl} ({p.pnlPct >= 0 ? '+' : ''}{p.pnlPct}%)
                    </td>
                    <td className="px-3 py-4 text-sm text-red-400 text-right">${p.stop.toFixed(2)}</td>
                    <td className="px-3 py-4 text-sm text-emerald-400 text-right">${p.target.toFixed(2)}</td>
                    <td className="px-3 py-4 text-xs text-gray-500">{p.signal}</td>
                    <td className="px-5 py-4 text-right">
                      <button className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/30 transition-colors">
                        Close
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Trade History Table */}
      {tab === 'history' && (
        <div className="bg-slate-800/30 border border-white/10 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-xs text-gray-500 uppercase border-b border-white/5">
                  <th className="text-left px-5 py-3">Date</th>
                  <th className="text-left px-3 py-3">Ticker</th>
                  <th className="text-left px-3 py-3">Side</th>
                  <th className="text-right px-3 py-3">Qty</th>
                  <th className="text-right px-3 py-3">Entry</th>
                  <th className="text-right px-3 py-3">Exit</th>
                  <th className="text-right px-3 py-3">P&L</th>
                  <th className="text-right px-5 py-3">Duration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {TRADE_HISTORY.map(t => (
                  <tr key={t.id} className="hover:bg-white/5 transition-colors">
                    <td className="px-5 py-4 text-sm text-gray-500">{t.date}</td>
                    <td className="px-3 py-4 text-sm font-semibold text-white">{t.ticker}</td>
                    <td className="px-3 py-4">
                      <span className={`px-2 py-1 rounded-lg text-xs font-medium ${t.side === 'Long' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                        {t.side}
                      </span>
                    </td>
                    <td className="px-3 py-4 text-sm text-gray-400 text-right">{t.qty}</td>
                    <td className="px-3 py-4 text-sm text-gray-400 text-right">${t.entry.toFixed(2)}</td>
                    <td className="px-3 py-4 text-sm text-white text-right">${t.exit.toFixed(2)}</td>
                    <td className={`px-3 py-4 text-sm font-medium text-right ${t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {t.pnl >= 0 ? '+' : ''}${t.pnl} ({t.pnlPct >= 0 ? '+' : ''}{t.pnlPct}%)
                    </td>
                    <td className="px-5 py-4 text-sm text-gray-500 text-right">{t.duration}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
