// DASHBOARD - Embodier.ai Glass House Intelligence System
// Main overview: Stats, P&L, active positions, signals, agent status
import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, DollarSign, Activity, Zap,
  Brain, BarChart3, ArrowUpRight, ArrowDownRight, Eye,
  Bot, Target, ShieldCheck, Clock
} from 'lucide-react';

function StatCard({ title, value, change, changeType, icon: Icon, color }) {
  const colors = {
    emerald: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/20',
    blue: 'from-blue-500/20 to-blue-500/5 border-blue-500/20',
    purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/20',
    amber: 'from-amber-500/20 to-amber-500/5 border-amber-500/20',
  };
  const iconColors = {
    emerald: 'text-emerald-400', blue: 'text-blue-400',
    purple: 'text-purple-400', amber: 'text-amber-400',
  };
  return (
    <div className={`bg-gradient-to-br ${colors[color]} border rounded-2xl p-5`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-400">{title}</span>
        <Icon className={`w-5 h-5 ${iconColors[color]}`} />
      </div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      {change && (
        <div className={`flex items-center gap-1 text-sm ${changeType === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
          {changeType === 'up' ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
          {change}
        </div>
      )}
    </div>
  );
}

function GlassCard({ title, icon: Icon, children, action }) {
  return (
    <div className="bg-slate-800/30 border border-white/10 rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          {Icon && <Icon className="w-4 h-4 text-gray-400" />}
          <h3 className="text-sm font-semibold text-white">{title}</h3>
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

export default function Dashboard() {
  const [positions] = useState([
    { ticker: 'AAPL', side: 'Long', entry: 189.50, current: 192.30, pnl: '+1.48%', pnlColor: 'text-emerald-400' },
    { ticker: 'TSLA', side: 'Long', entry: 245.30, current: 248.10, pnl: '+1.14%', pnlColor: 'text-emerald-400' },
    { ticker: 'NVDA', side: 'Long', entry: 875.00, current: 868.20, pnl: '-0.78%', pnlColor: 'text-red-400' },
    { ticker: 'SPY', side: 'Short', entry: 502.10, current: 500.85, pnl: '+0.25%', pnlColor: 'text-emerald-400' },
  ]);

  const [signals] = useState([
    { ticker: 'MSFT', type: 'Bullish Breakout', score: 87, time: '2m ago' },
    { ticker: 'AMD', type: 'Mean Reversion', score: 74, time: '15m ago' },
    { ticker: 'META', type: 'Momentum Surge', score: 82, time: '28m ago' },
  ]);

  const [agents] = useState([
    { name: 'Market Scanner', status: 'active', tasks: 142, icon: Eye },
    { name: 'Pattern AI', status: 'active', tasks: 38, icon: Brain },
    { name: 'Risk Manager', status: 'active', tasks: 12, icon: ShieldCheck },
    { name: 'YouTube Ingestion', status: 'learning', tasks: 5, icon: Bot },
  ]);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-sm text-gray-400 mt-1">Glass House Intelligence Overview</p>
      </div>

      {/* Stat cards row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Portfolio Value" value="$124,850" change="+2.4% today" changeType="up" icon={DollarSign} color="emerald" />
        <StatCard title="Daily P&L" value="+$2,340" change="+1.9%" changeType="up" icon={TrendingUp} color="blue" />
        <StatCard title="Active Signals" value="12" change="3 new" changeType="up" icon={Zap} color="purple" />
        <StatCard title="Win Rate (30d)" value="68.5%" change="+2.1%" changeType="up" icon={Target} color="amber" />
      </div>

      {/* Main grid: Positions + Signals + Agents */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Positions - spans 2 cols */}
        <div className="lg:col-span-2">
          <GlassCard
            title="Active Positions"
            icon={BarChart3}
            action={<Link to="/trades" className="text-xs text-blue-400 hover:text-blue-300">View All</Link>}
          >
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-xs text-gray-500 uppercase">
                    <th className="text-left pb-3">Ticker</th>
                    <th className="text-left pb-3">Side</th>
                    <th className="text-right pb-3">Entry</th>
                    <th className="text-right pb-3">Current</th>
                    <th className="text-right pb-3">P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {positions.map((p, i) => (
                    <tr key={i} className="hover:bg-white/5 transition-colors">
                      <td className="py-3 text-sm font-semibold text-white">{p.ticker}</td>
                      <td className="py-3 text-sm text-gray-400">{p.side}</td>
                      <td className="py-3 text-sm text-gray-400 text-right">${p.entry.toFixed(2)}</td>
                      <td className="py-3 text-sm text-white text-right">${p.current.toFixed(2)}</td>
                      <td className={`py-3 text-sm font-medium text-right ${p.pnlColor}`}>{p.pnl}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </div>

        {/* Latest Signals */}
        <GlassCard
          title="Latest Signals"
          icon={Zap}
          action={<Link to="/signals" className="text-xs text-blue-400 hover:text-blue-300">View All</Link>}
        >
          <div className="space-y-3">
            {signals.map((s, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/40 border border-white/5">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                  <Zap className="w-5 h-5 text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">{s.ticker}</span>
                    <span className="text-xs text-gray-500">{s.time}</span>
                  </div>
                  <div className="text-xs text-gray-400">{s.type}</div>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-bold ${s.score >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>{s.score}</div>
                  <div className="text-xs text-gray-500">score</div>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Agent Status Row */}
      <GlassCard title="Agent Status" icon={Bot}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {agents.map((a, i) => (
            <div key={i} className="flex items-center gap-3 p-4 rounded-xl bg-slate-800/40 border border-white/5">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <a.icon className="w-5 h-5 text-purple-400" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-white">{a.name}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <div className={`w-1.5 h-1.5 rounded-full ${a.status === 'active' ? 'bg-emerald-400' : 'bg-amber-400'} animate-pulse`} />
                  <span className="text-xs text-gray-500 capitalize">{a.status}</span>
                  <span className="text-xs text-gray-600">|</span>
                  <span className="text-xs text-gray-500">{a.tasks} tasks</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </GlassCard>

      {/* Quick Performance Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title="Recent Trades" icon={Clock}>
          <div className="space-y-2">
            {['AAPL +$320 (Long)', 'GOOGL +$180 (Long)', 'TSLA -$95 (Short)', 'SPY +$450 (Short)'].map((t, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                <span className="text-sm text-gray-300">{t.split(' ')[0]}</span>
                <span className={`text-sm font-medium ${t.includes('+') ? 'text-emerald-400' : 'text-red-400'}`}>
                  {t.split(' ').slice(1).join(' ')}
                </span>
              </div>
            ))}
          </div>
        </GlassCard>
        <GlassCard title="System Health" icon={Activity}>
          <div className="space-y-3">
            {[
              { label: 'API Latency', value: '12ms', status: 'good' },
              { label: 'WebSocket', value: 'Connected', status: 'good' },
              { label: 'ML Models', value: '4/4 Loaded', status: 'good' },
              { label: 'Data Feed', value: 'Live', status: 'good' },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                <span className="text-sm text-gray-400">{item.label}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-white">{item.value}</span>
                  <div className="w-2 h-2 rounded-full bg-emerald-400" />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
