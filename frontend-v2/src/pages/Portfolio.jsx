// PORTFOLIO HEATMAP - Embodier.ai Glass House Intelligence System
// Sector heatmap, portfolio summary, detailed positions with P&L tracking
import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  LayoutGrid, Download, ShieldCheck, Calendar,
  ChevronDown, ExternalLink, TrendingUp, TrendingDown,
  PieChart, ArrowUpRight, ArrowDownRight, Eye
} from 'lucide-react';

const SECTORS = [
  { name: 'Tech', change: 3.25, color: 'bg-emerald-600' },
  { name: 'Finance', change: 1.80, color: 'bg-emerald-700' },
  { name: 'Healthcare', change: -0.75, color: 'bg-red-700' },
  { name: 'Energy', change: 5.10, color: 'bg-emerald-500' },
  { name: 'Consumer Disc.', change: 0.50, color: 'bg-emerald-800' },
  { name: 'Industrials', change: 2.15, color: 'bg-emerald-600' },
  { name: 'Utilities', change: -1.20, color: 'bg-red-600' },
  { name: 'Real Estate', change: 0.90, color: 'bg-emerald-800' },
  { name: 'Materials', change: 4.00, color: 'bg-emerald-500' },
  { name: 'Comm. Services', change: 2.90, color: 'bg-emerald-600' },
  { name: 'Consumer Staples', change: 0.10, color: 'bg-emerald-900' },
  { name: 'Information Tech', change: 3.80, color: 'bg-emerald-500' },
];

const POSITIONS = [
  { symbol: 'MSFT', name: 'Microsoft Corp.', quantity: 150, avgPrice: 320.50, currentPrice: 328.75, weight: 8.00 },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', quantity: 50, avgPrice: 850.00, currentPrice: 875.20, weight: 5.00 },
  { symbol: 'GOOG', name: 'Alphabet Inc. (Class C)', quantity: 70, avgPrice: 140.00, currentPrice: 141.50, weight: 3.00 },
  { symbol: 'JPM', name: 'JPMorgan Chase & Co.', quantity: 200, avgPrice: 185.00, currentPrice: 184.20, weight: 6.00 },
  { symbol: 'PFE', name: 'Pfizer Inc.', quantity: 300, avgPrice: 28.00, currentPrice: 28.50, weight: 2.00 },
  { symbol: 'TSLA', name: 'Tesla, Inc.', quantity: 80, avgPrice: 175.00, currentPrice: 178.50, weight: 4.00 },
];

const CONCENTRATION_DATA = [
  { label: 'Tech', color: 'bg-blue-500', pct: 35 },
  { label: 'Finance', color: 'bg-emerald-500', pct: 20 },
  { label: 'Healthcare', color: 'bg-amber-500', pct: 15 },
  { label: 'Energy', color: 'bg-green-500', pct: 15 },
  { label: 'Consumer', color: 'bg-red-400', pct: 10 },
  { label: 'Other', color: 'bg-gray-500', pct: 5 },
];

function HeatmapCell({ name, change }) {
  const bg = change >= 4 ? 'bg-emerald-500' : change >= 2 ? 'bg-emerald-600' : change >= 0.5 ? 'bg-emerald-700' : change >= 0 ? 'bg-emerald-800' : change >= -1 ? 'bg-red-700' : 'bg-red-600';
  return (
    <div className={`${bg} rounded-xl p-4 flex flex-col items-center justify-center min-h-[80px] hover:brightness-110 transition-all cursor-pointer`}>
      <span className="text-sm font-semibold text-white">{name}</span>
      <span className={`text-xs mt-1 ${change >= 0 ? 'text-emerald-200' : 'text-red-200'}`}>
        {change >= 0 ? '+' : ''}{change.toFixed(2)}%
      </span>
    </div>
  );
}

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

export default function Portfolio() {
  const [timeRange, setTimeRange] = useState('Last 30 Days');
  const [groupBy, setGroupBy] = useState('By Sector');
  const [positions] = useState(POSITIONS);

  const totalPnl = positions.reduce((sum, p) => sum + (p.currentPrice - p.avgPrice) * p.quantity, 0);
  const totalValue = positions.reduce((sum, p) => sum + p.currentPrice * p.quantity, 0);
  const totalPnlPct = ((totalPnl / (totalValue - totalPnl)) * 100);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Portfolio Heatmap</h1>
          <p className="text-sm text-gray-400 mt-1">Sector allocation and position performance</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-white/10 text-sm text-gray-300 hover:bg-slate-700/50 transition-colors">
            <Calendar className="w-4 h-4" />
            {timeRange}
            <ChevronDown className="w-3 h-3" />
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-white/10 text-sm text-gray-300 hover:bg-slate-700/50 transition-colors">
            {groupBy}
            <ChevronDown className="w-3 h-3" />
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800/50 border border-white/10 text-sm text-gray-300 hover:bg-slate-700/50 transition-colors">
            <Download className="w-4 h-4" />
            Export CSV
          </button>
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-sm text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
            RiskShield: Monitoring
          </div>
        </div>
      </div>

      {/* Heatmap + Summary row */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sector/Position Heatmap */}
        <div className="lg:col-span-3">
          <GlassCard title="Sector/Position Heatmap">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
              {SECTORS.map((s, i) => (
                <HeatmapCell key={i} name={s.name} change={s.change} />
              ))}
            </div>
          </GlassCard>
        </div>

        {/* Portfolio Summary */}
        <div className="lg:col-span-1">
          <GlassCard title="Portfolio Summary">
            <div className="space-y-4">
              <div>
                <div className="text-xs text-gray-500">Total P&L</div>
                <div className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
                </div>
                <div className={`text-sm ${totalPnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%
                </div>
              </div>

              <div className="pt-4 border-t border-white/5">
                <div className="text-xs text-gray-500 mb-3">Sector Concentration</div>
                {/* Simple donut representation */}
                <div className="flex justify-center mb-4">
                  <div className="relative w-24 h-24">
                    <svg viewBox="0 0 36 36" className="w-24 h-24 -rotate-90">
                      <circle cx="18" cy="18" r="15.5" fill="none" stroke="#1e293b" strokeWidth="3" />
                      <circle cx="18" cy="18" r="15.5" fill="none" stroke="#3b82f6" strokeWidth="3" strokeDasharray="35 65" strokeDashoffset="0" />
                      <circle cx="18" cy="18" r="15.5" fill="none" stroke="#10b981" strokeWidth="3" strokeDasharray="20 80" strokeDashoffset="-35" />
                      <circle cx="18" cy="18" r="15.5" fill="none" stroke="#f59e0b" strokeWidth="3" strokeDasharray="15 85" strokeDashoffset="-55" />
                      <circle cx="18" cy="18" r="15.5" fill="none" stroke="#22c55e" strokeWidth="3" strokeDasharray="15 85" strokeDashoffset="-70" />
                      <circle cx="18" cy="18" r="15.5" fill="none" stroke="#f87171" strokeWidth="3" strokeDasharray="10 90" strokeDashoffset="-85" />
                      <circle cx="18" cy="18" r="15.5" fill="none" stroke="#6b7280" strokeWidth="3" strokeDasharray="5 95" strokeDashoffset="-95" />
                    </svg>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {CONCENTRATION_DATA.map((c, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${c.color}`} />
                      <span className="text-xs text-gray-400">{c.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* Detailed Positions Table */}
      <GlassCard title="Detailed Positions">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-xs text-gray-500 uppercase">
                <th className="text-left pb-3">Symbol</th>
                <th className="text-left pb-3">Name</th>
                <th className="text-right pb-3">Quantity</th>
                <th className="text-right pb-3">Avg. Price</th>
                <th className="text-right pb-3">Current Price</th>
                <th className="text-right pb-3">P&L ($)</th>
                <th className="text-right pb-3">P&L (%)</th>
                <th className="text-right pb-3">Weight</th>
                <th className="text-right pb-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {positions.map((p, i) => {
                const pnlDollar = (p.currentPrice - p.avgPrice) * p.quantity;
                const pnlPct = ((p.currentPrice - p.avgPrice) / p.avgPrice) * 100;
                const isPositive = pnlDollar >= 0;
                return (
                  <tr key={i} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 text-sm font-semibold text-white">{p.symbol}</td>
                    <td className="py-3 text-sm text-gray-400">{p.name}</td>
                    <td className="py-3 text-sm text-gray-300 text-right">{p.quantity}</td>
                    <td className="py-3 text-sm text-gray-400 text-right">${p.avgPrice.toFixed(2)}</td>
                    <td className="py-3 text-sm text-white text-right">${p.currentPrice.toFixed(2)}</td>
                    <td className={`py-3 text-sm font-medium text-right ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                      {isPositive ? '+' : ''}{pnlDollar.toFixed(2)}
                    </td>
                    <td className={`py-3 text-sm font-medium text-right ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                      {isPositive ? '+' : ''}{pnlPct.toFixed(2)}%
                    </td>
                    <td className="py-3 text-sm text-gray-300 text-right">{p.weight.toFixed(2)}%</td>
                    <td className="py-3 text-right">
                      <Link to="/trades" className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
                        View Trade
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}
